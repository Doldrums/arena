#!/usr/bin/env python3
"""Build/push an explicit private SCiEL engine image; never run model research.

The input context, exact wheel hashes, source pins and installed image identity
remain in the requested new build directory. Docker's legacy build CPU/memory
limits bound build containers. Run this operator command on the prepared worker.
"""
from __future__ import annotations

import argparse
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile

PIN = "0d67f813dd4ac21dee304f2b0de0b0ce59bf4157"
VERSION = "0.1.0+arena.0d67f813.worker1"


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while data := stream.read(1024 * 1024):
            value.update(data)
    return value.hexdigest()


def canonical_name(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def pinned_requirements(text):
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.fullmatch(r"(?:sciel|research-arena) @ file:///[^\s]+", line):
            continue  # these two are captured as source trees, not mutable paths
        match = re.fullmatch(r"([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9][A-Za-z0-9.+!_-]*)", line)
        if not match:
            raise ValueError("Dependency inventory must contain exact versions, not URLs or credentials")
        name = canonical_name(match[1])
        if name in result:
            raise ValueError("Duplicate dependency")
        result[name] = match[2]
    if result.get("torch") != "2.14.0+cpu" or not result:
        raise ValueError("This engine profile requires the inspected CPU torch dependency")
    return result


def wheel_lock(wheelhouse, expected):
    rows = {}
    for path in sorted(Path(wheelhouse).iterdir()):
        if path.is_symlink() or not path.is_file() or path.suffix != ".whl":
            raise ValueError("Wheelhouse must contain only regular wheel files")
        with zipfile.ZipFile(path) as wheel:
            candidates = [name for name in wheel.namelist()
                          if name.count("/") == 1 and name.endswith(".dist-info/METADATA")]
            if len(candidates) != 1:
                raise ValueError("Wheel metadata identity is ambiguous")
            metadata = BytesParser().parsebytes(wheel.read(candidates[0]))
        name, version = canonical_name(metadata["Name"]), metadata["Version"]
        if name in rows or expected.get(name) != version:
            raise ValueError("Wheel identity differs from the pinned dependency inventory")
        rows[name] = {"version": version, "filename": path.name, "sha256": digest(path)}
    if set(rows) != set(expected):
        raise ValueError("Wheelhouse is missing pinned dependencies")
    lock = "".join(f"{name}=={row['version']} --hash=sha256:{row['sha256']}\n" for name, row in sorted(rows.items()))
    return lock, rows


def snapshot_files(root):
    records = {}
    for path in sorted(Path(root).rglob("*")):
        if path.is_symlink():
            raise ValueError("Build snapshots cannot contain symlinks")
        if path.is_file():
            records[path.relative_to(root).as_posix()] = digest(path)
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest(), records


def validate_image_config(identity, version):
    """Fail before publishing when the image violates the release contract."""
    from arena.release_deployment import CONTRACT, ENTRYPOINT
    config = identity.get("Config", {})
    required = {"org.opencontainers.image.revision": PIN,
                "org.opencontainers.image.source": "https://github.com/Doldrums/sciel",
                "org.opencontainers.image.version": version,
                "io.arena.sciel.contract": CONTRACT}
    labels = config.get("Labels", {})
    if any(labels.get(key) != value for key, value in required.items()):
        raise ValueError("Built image labels do not satisfy the SCiEL release contract")
    if config.get("Entrypoint") != ENTRYPOINT or config.get("User") != "998:998":
        raise ValueError("Built image has an unexpected native entrypoint or user")
    if identity.get("Architecture") != "amd64":
        raise ValueError("Built image must target the reviewed amd64 worker")
    return required


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, default=Path("/opt/arena/current"))
    parser.add_argument("--source", type=Path, default=Path("/srv/arena/sources/sciel"))
    parser.add_argument("--freeze", type=Path, default=Path("/srv/arena/build/sciel-freeze.txt"))
    parser.add_argument("--bridge-file", type=Path, help="Explicit reviewed evaluation.py for the image snapshot; does not modify the live app")
    parser.add_argument("--base-image", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--tag", default="127.0.0.1:5000/empira/sciel:0.1.0-arena.0d67f813.worker1")
    parser.add_argument("--push", action="store_true")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"127\.0\.0\.1:5000/[a-z0-9._/-]+@sha256:[0-9a-f]{64}", args.base_image):
        parser.error("Use the immutable base digest in the private loopback registry")
    if not re.fullmatch(r"127\.0\.0\.1:5000/[a-z0-9._/-]+:[a-zA-Z0-9._-]+", args.tag):
        parser.error("Engine push is restricted to the private loopback registry")
    destination = args.destination
    if not destination.is_absolute() or destination.exists() or destination.is_symlink():
        parser.error("Build destination must be a new absolute directory")
    sys.path.insert(0, str(args.app / "src"))
    from arena.frameworks.runtime import verify_source
    source = verify_source(args.source, PIN)
    requirements = pinned_requirements(args.freeze.read_text())
    destination.mkdir(parents=True, mode=0o700)
    context = destination / "context"
    context.mkdir()
    log = (destination / "build.log").open("w")
    def call(argv, **kwargs):
        return subprocess.run(argv, check=True, stdout=log, stderr=subprocess.STDOUT, **kwargs)
    source_archive = destination / "sciel-source.tar"
    with source_archive.open("wb") as output:
        subprocess.run(["git", "--no-replace-objects", "-C", str(args.source), "archive", PIN], stdout=output, check=True)
    sciel = context / "sciel"
    sciel.mkdir()
    with tarfile.open(source_archive) as archive:
        for member in archive.getmembers():
            if member.issym() or member.islnk() or member.name.startswith("/") or ".." in Path(member.name).parts:
                raise ValueError("SCiEL snapshot contains an unsafe archive member")
        archive.extractall(sciel, filter="data")
    # Keep the exact shallow object identity for native journal provenance, but
    # copy no host remote URL, hooks, credentials or user Git configuration.
    gitdir = sciel / ".git"
    gitdir.mkdir()
    shutil.copytree(args.source / ".git/objects", gitdir / "objects")
    for name in ("HEAD", "index", "shallow"):
        path = args.source / ".git" / name
        if path.exists(): shutil.copyfile(path, gitdir / name)
    (gitdir / "config").write_text("[core]\n\trepositoryformatversion = 0\n\tbare = false\n\tfilemode = true\n")
    (gitdir / "refs").mkdir()
    arena = context / "arena"
    for relative in ("src/arena", "registry", "schemas"):
        shutil.copytree(args.app / relative, arena / relative,
                        symlinks=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".env", ".env.*"))
    if args.bridge_file is not None:
        if not args.bridge_file.is_absolute() or args.bridge_file.is_symlink() or not args.bridge_file.is_file():
            raise ValueError("Bridge input must be an explicit absolute regular file")
        shutil.copyfile(args.bridge_file, arena / "src/arena/frameworks/evaluation.py")
    arena_digest, arena_files = snapshot_files(arena)
    python = Path(sys.executable)
    downloader = destination / "download-venv"
    call([str(python), "-m", "venv", str(downloader)])
    pip = [str(downloader / "bin/python"), "-m", "pip", "--isolated", "download", "--only-binary=:all:", "--no-deps", "--dest", str(context / "wheelhouse")]
    normal = destination / "requirements-download.txt"
    normal.write_text("".join(f"{name}=={version}\n" for name, version in sorted(requirements.items()) if name != "torch"))
    call([*pip, "--index-url", "https://pypi.org/simple", "-r", str(normal)])
    call([*pip, "--index-url", "https://download.pytorch.org/whl/cpu", "torch==" + requirements["torch"]])
    lock, wheels = wheel_lock(context / "wheelhouse", requirements)
    (context / "requirements.lock").write_text(lock)
    for name in ("git", "docker"):
        executable = Path(shutil.which(name))
        shutil.copyfile(executable, context / name)
        (context / name).chmod(0o755)
    git_source = Path("/srv/arena/build/git-2.55.0-release")
    shutil.copyfile(git_source / "git-2.55.0/COPYING", context / "git-COPYING")
    shutil.copyfile(Path(__file__).with_name("sciel-engine") / "Dockerfile", context / "Dockerfile")
    inputs = {"schema": "arena.sciel-engine-inputs/1", "version": VERSION, "source": source,
              "source_archive_sha256": digest(source_archive), "arena_snapshot_sha256": arena_digest,
              "arena_files": arena_files, "base_image": args.base_image, "wheels": wheels,
              "git_build": json.loads((git_source / "environment.json").read_text()),
              "git_binary_sha256": digest(context / "git"), "docker_binary_sha256": digest(context / "docker"),
              "docker_cli_version": subprocess.check_output([str(context / "docker"), "--version"], text=True).strip(),
              "dockerfile_sha256": digest(context / "Dockerfile"), "research_executed": False,
              "build_limits": {"cpu_quota": 200000, "cpu_period": 100000, "memory_bytes": 8589934592}}
    (context / "build-inputs.json").write_text(json.dumps(inputs, indent=2, sort_keys=True) + "\n")
    env = {**os.environ, "DOCKER_BUILDKIT": "0"}
    call(["docker", "build", "--network=none", "--cpu-quota=200000", "--cpu-period=100000", "--memory=8g",
          "--build-arg", "BASE_IMAGE=" + args.base_image, "--build-arg", "SCIEL_COMMIT=" + PIN,
          "--build-arg", "ENGINE_VERSION=" + VERSION, "--build-arg", "ARENA_SNAPSHOT_SHA256=" + arena_digest,
          "--tag", args.tag, str(context)], env=env)
    identity = json.loads(subprocess.check_output(["docker", "image", "inspect", args.tag], text=True))[0]
    labels = validate_image_config(identity, VERSION)
    if args.push:
        call(["docker", "push", args.tag])
        identity = json.loads(subprocess.check_output(["docker", "image", "inspect", args.tag], text=True))[0]
    report = {"schema": "arena.sciel-engine-build/1", "version": VERSION, "tag": args.tag,
              "image_id": identity["Id"], "repo_digests": identity.get("RepoDigests", []),
              "architecture": identity["Architecture"], "labels": labels, "user": identity["Config"]["User"],
              "entrypoint": identity["Config"]["Entrypoint"], "inputs_sha256": digest(context / "build-inputs.json"),
              "arena_snapshot_sha256": arena_digest, "source": source, "research_executed": False}
    (destination / "build-receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
