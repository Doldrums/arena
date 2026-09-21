#!/usr/bin/env python3
"""Explicit no-model VM conformance probe; requires root and starts one container.

Creates a synthetic bounded run cgroup, drops to the worker UID, and evaluates
the pinned reference SAT seed through the proxy. It does not submit a queue run
or contact a model provider. Probe artifacts remain under their fresh run UUID.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

from arena.evaluator_proxy import Config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("/etc/arena/evaluator.json"))
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("Run the explicit conformance probe as root")
    config = Config.read(args.config)
    run_id, eval_id = uuid.uuid4().hex, uuid.uuid4().hex
    name = "arena-eval-" + uuid.uuid4().hex
    run_dir = config.run_roots[0] / run_id
    receipt = run_dir / "artifacts" / "canonical-evaluations" / eval_id
    candidate, output = receipt / "input", receipt / "native-output"
    candidate.mkdir(parents=True); output.mkdir()
    shutil.copyfile(config.tasks_root / "suite/reference-sat/initial_program.py", candidate / "program.py")
    for root, directories, files in os.walk(run_dir):
        os.chown(root, config.worker_uid, config.worker_gid)
        for file in files:
            os.chown(Path(root) / file, config.worker_uid, config.worker_gid)
    (candidate / "program.py").chmod(0o444)
    group = Path("/sys/fs/cgroup") / config.cgroup_root.lstrip("/") / ("arena-control-" + run_id)
    group.mkdir()
    (group / "cpu.max").write_text("200000 100000")
    (group / "memory.max").write_text(str(4 * 1024 ** 3))
    (group / "pids.max").write_text("256")
    (group / "cgroup.subtree_control").write_text("+cpu +memory +pids")
    (group / "main").mkdir()
    argv = ["docker", "run", "--rm", "--pull=never", "--name", name,
            "--network", "none", "--read-only", "--cpus", "1", "--memory", "2g",
            "--pids-limit", "128", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--user", f"{config.worker_uid}:{config.worker_gid}",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=268435456",
            "--mount", f"type=bind,src={config.tasks_root},dst=/tasks,readonly",
            "--mount", f"type=bind,src={candidate},dst=/candidate,readonly",
            "--mount", f"type=bind,src={output},dst=/results",
            "--env", "PYTHONDONTWRITEBYTECODE=1", "--workdir", "/tmp",
            "--label", "arena.evaluator=canonical-v1", "--label", "arena.control-run=" + run_id,
            "--cgroup-parent", str(group).removeprefix("/sys/fs/cgroup"), config.images[0],
            "python", "/tasks/run.py", "--root", "/tasks", "evaluate", "reference-sat",
            "--candidate", "/candidate/program.py", "--python", "python", "--timeout", "120",
            "--output", "/results/native.json"]
    child = '''import json,subprocess
environment={"PATH":"/usr/bin:/bin","DOCKER_HOST":SOCKET}
preflight=subprocess.run(["docker","info","--format","{{.CgroupDriver}} {{.CgroupVersion}}"],env=environment,capture_output=True,timeout=10)
process=subprocess.run(ARGV,env=environment,capture_output=True,timeout=145)
denied=subprocess.run(["docker","ps"],env=environment,capture_output=True,timeout=10)
cleanup=subprocess.run(["docker","rm","--force",NAME],env=environment,capture_output=True,timeout=10)
print(json.dumps({"cgroup_preflight":preflight.stdout.decode().strip(),"docker_exit":process.returncode,
 "docker_stderr":process.stderr.decode()[-1000:],"inventory_denied":denied.returncode!=0,"cleanup_exit":cleanup.returncode}))
'''
    child = f"SOCKET={('unix://' + str(config.socket_path))!r}\nARGV={argv!r}\nNAME={name!r}\n" + child
    # Root moves into the delegated run before dropping privilege: an arbitrary
    # SSH session cannot migrate itself from its outer cgroup as the worker UID.
    wrapper = ("import os,pathlib;pathlib.Path(" + repr(str(group / "main/cgroup.procs")) +
               ").write_text(str(os.getpid()));os.setgroups([]);os.setgid(" + str(config.worker_gid) +
               ");os.setuid(" + str(config.worker_uid) + ");os.execv(" + repr(sys.executable) +
               ", [" + repr(sys.executable) + ",' -c'.strip()," + repr(child) + "])")
    report = {"schema": "arena.evaluator-proxy-conformance/1", "run_id": run_id,
              "image": config.images[0], "task_id": "reference-sat", "model_calls": 0,
              "synthetic_cgroup_probe": True, "native_result": str(output / "native.json")}
    try:
        result = subprocess.run([sys.executable, "-c", wrapper], capture_output=True, text=True, timeout=165)
        report["worker_exit"] = result.returncode
        if result.returncode:
            report["worker_error"] = result.stderr[-1000:]
        else:
            report.update(json.loads(result.stdout))
        native = output / "native.json"
        if native.is_file():
            raw = native.read_bytes()
            data = json.loads(raw)
            report.update(native_status=data.get("status"), valid=data.get("valid"), score=data.get("score"),
                          native_sha256=hashlib.sha256(raw).hexdigest())
        leftovers = subprocess.run(["docker", "ps", "-aq", "--filter", "label=arena.control-run=" + run_id],
                                   capture_output=True, text=True, timeout=10)
        report["container_remaining"] = bool(leftovers.stdout.strip())
    finally:
        (group / "cgroup.kill").write_text("1")
        subprocess.run(["docker", "rm", "--force", name], capture_output=True, timeout=10)
        for path in (group / "main", group):
            try:
                path.rmdir()
            except OSError:
                pass
    print(json.dumps(report, indent=2))
    return 0 if (report.get("docker_exit") == 0 and report.get("valid") is True
                 and report.get("score") == 1.0 and report.get("inventory_denied")
                 and not report["container_remaining"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
