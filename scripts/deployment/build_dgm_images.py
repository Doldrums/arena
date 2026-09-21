#!/usr/bin/env python3
"""Operator-only approved DGM build, offline conformance and loopback publication.

This program never launches a research run or installs a broker approval.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time
import uuid

CGROUP = "/arena-builds/dgm-images-20260921"
MEMORY = 24 * 1024**3


def dump(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2) + "\n")


def command(argv, **kwargs):
    return subprocess.run(argv, check=True, text=True, **kwargs)


def inspect(image):
    return json.loads(subprocess.check_output(["docker", "image", "inspect", image], text=True))[0]


def verify_context(directory, job):
    actual = {}
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise ValueError("Build context symlink")
        if path.is_file() and path.name != "context-manifest.json":
            actual[path.relative_to(directory).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != job["files"]:
        raise ValueError("Reviewed build context changed")


def build_argv(directory, job, receipt):
    return ["docker", "build", "--platform", "linux/amd64", "--memory", str(MEMORY),
        "--memory-swap", str(MEMORY), "--cpu-period", "100000", "--cpu-quota", "800000",
        "--cgroup-parent", CGROUP, "--force-rm", "--iidfile", str(receipt / "image.id"),
        "--tag", job["lookup"], str(directory)]


def setup_cgroup():
    if os.geteuid() != 0:
        raise ValueError("This reviewed operator build requires root")
    if json.loads(subprocess.check_output(["docker", "info", "--format", '{{json .CgroupDriver}}'], text=True)) != "cgroupfs":
        raise ValueError("Resource proof requires the reviewed cgroupfs Docker driver")
    root = Path("/sys/fs/cgroup")
    if not (root / "cgroup.controllers").is_file():
        raise ValueError("Resource proof requires cgroup v2")
    parent = root / "arena-builds"
    parent.mkdir(exist_ok=True)
    (parent / "cgroup.subtree_control").write_text("+cpu +memory +pids")
    child = parent / "dgm-images-20260921"
    child.mkdir(exist_ok=True)
    (child / "cpu.max").write_text("800000 100000")
    (child / "memory.max").write_text(str(MEMORY))
    (child / "memory.swap.max").write_text("0")
    (child / "pids.max").write_text("4096")
    (child / "cgroup.subtree_control").write_text("+cpu +memory +pids")


def conformance(image, job, context_root, receipt):
    name = "arena-dgm-conformance-" + uuid.uuid4().hex
    argv = ["docker", "create", "--name", name, "--network", "none", "--read-only", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges", "--cgroup-parent", CGROUP, "--cpus", "4", "--memory", str(8 * 1024**3),
        "--memory-swap", str(8 * 1024**3), "--pids-limit", "512", "--user", "0:0",
        "--tmpfs", "/dgm:rw,nosuid,nodev,exec,size=1073741824", "--tmpfs", "/testbed:rw,nosuid,nodev,exec,size=134217728",
        "--tmpfs", "/tmp:rw,nosuid,nodev,exec,size=268435456", "--tmpfs", "/root:rw,nosuid,nodev,exec,size=67108864",
        "--env", "ARENA_DGM_MODEL=gpt-5.6-sol", image]
    command(argv, stdout=subprocess.DEVNULL)
    try:
        command(["docker", "start", name], stdout=subprocess.DEVNULL)
        for _ in range(60):
            if subprocess.run(["docker", "exec", name, "test", "-f", "/tmp/.arena-dgm-ready"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("Native image bootstrap did not become ready")
        if job["id"] != "dgm":
            # Docker's archive API refuses a read-only root even for tmpfs.
            # Reproduce the nine native uploads through the broker's fixed
            # exec-tar mechanism, retaining the read-only container contract.
            source = context_root / "dgm/source"
            archive = io.BytesIO()
            with tarfile.open(fileobj=archive, mode="w") as tar:
                for entry in ("requirements.txt", "pytest.ini", "tools", "utils", "tests", "prompts", "llm.py", "llm_withtools.py", "coding_agent_polyglot.py"):
                    def reviewed_member(member):
                        if not (member.isfile() or member.isdir()):
                            raise ValueError("Conformance upload contains a non-regular member")
                        member.uid = member.gid = 0
                        member.uname = member.gname = ""
                        return member
                    tar.add(source / entry, arcname="coding_agent.py" if entry == "coding_agent_polyglot.py" else entry, filter=reviewed_member)
            if archive.tell() > 64 * 1024**2:
                raise ValueError("Conformance upload exceeds 64 MiB")
            subprocess.run(["docker", "exec", "-i", name, "tar", "--no-same-owner", "-xf", "-", "-C", "/dgm"],
                           input=archive.getvalue(), check=True, timeout=120)
        with (receipt / "conformance.log").open("x") as log:
            checks = ["python --version", "python -m pip check", "pytest --version",
                "python -c 'import llm, llm_withtools; assert llm_withtools.OPENAI_MODEL == \"gpt-5.6-sol\"'",
                "python coding_agent.py --help"]
            if job["id"] == "dgm":
                checks += ["python DGM_outer.py --help", "python self_improve_step.py --help"]
            else:
                checks += ["git -C /testbed rev-parse HEAD", "git -C /testbed status --porcelain"]
            for check in checks:
                command(["docker", "exec", "--workdir", "/dgm", name, "/bin/sh", "-c", check], stdout=log, stderr=subprocess.STDOUT, timeout=120)
            # Native runtime pip is intentionally offline; this must be satisfied
            # already, without installing anything into the read-only root.
            command(["docker", "exec", name, "python", "-m", "pip", "install", "-r", "/dgm/requirements.txt"], stdout=log, stderr=subprocess.STDOUT, timeout=120)
        command(["docker", "cp", name + ":/opt/arena-build-evidence", str(receipt / "interpreter-evidence")], stdout=subprocess.DEVNULL)
        return {"status": "passed", "network": "none", "read_only": True, "capabilities": "ALL dropped",
                "archive_upload": "not_required" if job["id"] == "dgm" else "fixed exec-tar into /dgm; Docker archive API refuses read-only rootfs",
                "resources": {"cpus": 4, "memory_bytes": 8 * 1024**3, "pids": 512},
                "checks": checks, "model_calls": 0, "task_evaluations": 0, "optimizer_runs": 0}
    finally:
        subprocess.run(["docker", "rm", "--force", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def extract_build_evidence(image, receipt):
    """Copy build metadata from a never-started container, without executing it."""
    name = "arena-dgm-evidence-" + uuid.uuid4().hex
    command(["docker", "create", "--name", name, "--network", "none", "--read-only", "--cap-drop", "ALL",
             "--entrypoint", "/bin/true", image], stdout=subprocess.DEVNULL)
    try:
        command(["docker", "cp", name + ":/opt/arena-build-evidence", str(receipt / "interpreter-evidence")], stdout=subprocess.DEVNULL)
    finally:
        subprocess.run(["docker", "rm", "--force", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--contexts", required=True, type=Path)
    parser.add_argument("--receipts", required=True, type=Path)
    parser.add_argument("--job", required=True)
    parser.add_argument("--parent-receipt", type=Path)
    args = parser.parse_args()
    plan = json.loads((args.contexts / "build-plan.json").read_text())
    jobs = [item for item in plan["jobs"] if item["id"] == args.job]
    if len(jobs) != 1 or plan["secret_scan"] != "passed":
        raise ValueError("Choose one reviewed credential-scanned context")
    job = jobs[0]
    if not job["registry_tag"].startswith("127.0.0.1:5000/arena-dgm:"):
        raise ValueError("Publication is restricted to the private loopback registry")
    verify_context(args.contexts / job["id"], job)
    parent_record = None
    parent_name = "polyglot-base" if job["id"] == "polyglot-env" else "polyglot-env" if job["id"].startswith("python__") else None
    if parent_name:
        if args.parent_receipt is None:
            raise ValueError("Require the preceding native hierarchy image receipt")
        parent_record = json.loads(args.parent_receipt.read_text())
        parent_job = next(item for item in plan["jobs"] if item["id"] == parent_name)
        if (parent_record.get("schema") != "arena.dgm-image-build/1" or parent_record.get("job") != parent_name
                or parent_record.get("context_sha256") != parent_job["context_sha256"]
                or inspect(parent_job["lookup"])["Id"] != parent_record["image_id"]
                or inspect(parent_record["repository_digest"])["Id"] != parent_record["image_id"]):
            raise ValueError("Native parent image is not the recorded immutable build")
    if shutil.disk_usage(args.contexts).free < 80 * 1024**3:
        raise ValueError("Keep at least 80 GiB free before this build")
    args.receipts.mkdir(mode=0o700, parents=True, exist_ok=False)
    client_config = args.receipts / "docker-client"
    client_config.mkdir(mode=0o700)
    dump(client_config / "config.json", {"auths": {}})
    os.environ["DOCKER_CONFIG"] = str(client_config)
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(name, None)
    setup_cgroup()
    argv = build_argv(args.contexts / job["id"], job, args.receipts)
    dump(args.receipts / "request.json", {"job": job["id"], "context_sha256": job["context_sha256"], "argv": argv,
        "limits": {"cpus": 8, "memory_bytes": MEMORY, "cgroup_parent": CGROUP},
        "limitation": "Limits cover build RUN containers and conformance; daemon-side pulls/layer extraction are not cgroup-isolated by these flags"})
    with (args.receipts / "build.log").open("x") as log:
        command(argv, env={**os.environ, "DOCKER_BUILDKIT": "0"}, stdout=log, stderr=subprocess.STDOUT, timeout=5400)
    info = inspect(job["lookup"])
    if info["Id"] != (args.receipts / "image.id").read_text().strip():
        raise ValueError("Built image ID changed")
    if parent_name and inspect(parent_job["lookup"])["Id"] != parent_record["image_id"]:
        raise ValueError("Native parent lookup alias changed during this build")
    checks = None
    if job["runnable"]:
        cfg = info["Config"]
        if (cfg.get("Entrypoint") != ["/usr/local/bin/arena-dgm-bootstrap"] or cfg.get("Cmd") != ["tail", "-f", "/dev/null"]
                or cfg.get("Volumes") or cfg.get("Healthcheck") or cfg.get("Labels", {}).get("io.arena.dgm.contract") != "dgm-prebuilt-v1"):
            raise ValueError("Image does not meet the broker's immutable execution contract")
        checks = conformance(info["Id"], job, args.contexts, args.receipts)
    else:
        extract_build_evidence(info["Id"], args.receipts)
    command(["docker", "tag", info["Id"], job["registry_tag"]])
    with (args.receipts / "push.log").open("x") as log:
        command(["docker", "push", job["registry_tag"]], stdout=log, stderr=subprocess.STDOUT, timeout=1200)
    published = inspect(job["registry_tag"])
    digests = [value for value in published.get("RepoDigests", []) if value.startswith("127.0.0.1:5000/arena-dgm@sha256:")]
    if published["Id"] != info["Id"] or len(digests) != 1:
        raise ValueError("Loopback registry publication did not retain immutable image identity")
    evidence = {str(p.relative_to(args.receipts)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in args.receipts.rglob("*") if p.is_file()}
    receipt = {"schema": "arena.dgm-image-build/1", "job": job["id"], "context_sha256": job["context_sha256"],
        "image_id": info["Id"], "repository_digest": digests[0], "created": info["Created"], "size": info["Size"],
        "parent_image": None if parent_record is None else {key: parent_record[key] for key in ("image_id", "repository_digest", "context_sha256")},
        "conformance": checks, "evidence_sha256": evidence, "broker_approved": False,
        "model_calls": 0, "task_evaluations": 0, "optimizer_runs": 0}
    dump(args.receipts / "receipt.json", receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
