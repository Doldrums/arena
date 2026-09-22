#!/usr/bin/env python3
"""Refresh only Arena in a pinned private SCiEL image, preserving its engine and dependencies.

No dependency download, model call, live service change or queue admission occurs.
The original image remains addressable by its immutable digest.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_sciel_engine import PIN, release_identity, snapshot_arena, snapshot_files, validate_image_config

IMAGE = re.compile(r"127\.0\.0\.1:5000/[a-z0-9._/-]+@sha256:[0-9a-f]{64}")
TAG = re.compile(r"127\.0\.0\.1:5000/[a-z0-9._/-]+:[A-Za-z0-9._-]+")
PRESERVED = ("Entrypoint", "Cmd", "Env", "User", "WorkingDir")
PROOF = '''import hashlib, importlib.metadata, json, subprocess
from pathlib import Path
from arena.registry import get_catalog
from arena.task_library import resolve_task_root, verify_task_library
dependencies = sorted((d.metadata['Name'].lower().replace('_','-'), d.version)
                      for d in importlib.metadata.distributions())
source = next(s for s in get_catalog()['sources'] if s['id'] == 'arena-tasks')
identity = verify_task_library(resolve_task_root(source=source), source)
commit = subprocess.check_output(['git','--no-replace-objects','-C','/opt/sciel',
                                  'rev-parse','HEAD'], text=True).strip()
root = Path('/opt/arena')
files = {}
for path in sorted(root.rglob('*')):
    if path.is_symlink(): raise ValueError('Linked runtime file')
    if path.is_file():
        files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
snapshot = hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
print(json.dumps({'source_commit': commit, 'sciel_version': importlib.metadata.version('sciel'),
    'dependency_sha256': hashlib.sha256(json.dumps(dependencies,separators=(',',':')).encode()).hexdigest(),
    'dependency_count': len(dependencies), 'task_source': identity,
    'arena_snapshot_sha256': snapshot, 'arena_file_count': len(files)}))
'''


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def inspect(reference):
    result = subprocess.run(["docker", "image", "inspect", reference],
                            capture_output=True, text=True, check=True)
    rows = json.loads(result.stdout)
    if type(rows) is not list or len(rows) != 1:
        raise ValueError("Expected exactly one local immutable image")
    return rows[0]


def validate_parent(parent, reference, version):
    if not IMAGE.fullmatch(reference) or reference not in parent.get("RepoDigests", []):
        raise ValueError("Parent must be an already available immutable private image")
    if not version.startswith("0.2.0+arena." + PIN[:8] + "."):
        raise ValueError("Refresh requires an explicit build of the pinned SCiEL v0.2.0")
    validate_image_config(parent, version, PIN)
    if parent.get("Config", {}).get("WorkingDir") != "/opt/sciel":
        raise ValueError("Unexpected SCiEL working directory")
    if parent["Config"].get("OnBuild") not in (None, []):
        raise ValueError("Inherited build triggers cannot modify a runtime-only refresh")
    layers = parent.get("RootFS", {}).get("Layers")
    if type(layers) is not list or not layers or not all(
            type(layer) is str and re.fullmatch(r"sha256:[0-9a-f]{64}", layer) for layer in layers):
        raise ValueError("Parent image layer identity is missing")


def dockerfile(parent_reference, version, snapshot):
    release_identity(PIN, version)
    if not IMAGE.fullmatch(parent_reference) or not re.fullmatch(r"[0-9a-f]{64}", snapshot):
        raise ValueError("Build inputs must be immutable identities")
    return (f"FROM {parent_reference}\nUSER 0:0\n"
            "RUN rm -rf /opt/arena\nCOPY arena/ /opt/arena/\n"
            "COPY refresh-inputs.json /opt/arena-build/refresh-inputs.json\n"
            f'LABEL org.opencontainers.image.version="{version}" '
            f'org.empira.arena.snapshot-sha256="{snapshot}"\n'
            "USER 998:998\n")


def proof(reference):
    result = subprocess.run(["docker", "run", "--rm", "--pull=never", "--network=none", "--read-only",
        "--cpus=1", "--memory=2g", "--memory-swap=2g", "--pids-limit=128", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "--tmpfs=/tmp:rw,nosuid,nodev,size=268435456",
        "--entrypoint=/opt/venv/bin/python", reference, "-c", PROOF],
        capture_output=True, text=True, check=True, timeout=120)
    value = json.loads(result.stdout)
    if (type(value) is not dict or value.get("source_commit") != PIN
            or value.get("sciel_version") != "0.2.0"
            or type(value.get("dependency_count")) is not int or value["dependency_count"] < 1
            or type(value.get("dependency_sha256")) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", value["dependency_sha256"])):
        raise ValueError("Runtime proof does not match the pinned SCiEL release")
    return value


def verify_child(parent, child, version, snapshot, before, after, task_source):
    labels = validate_image_config(child, version, PIN)
    if child["Config"].get("Labels", {}).get("org.empira.arena.snapshot-sha256") != snapshot:
        raise ValueError("Child image has a different Arena snapshot")
    if any(child["Config"].get(key) != parent["Config"].get(key) for key in PRESERVED):
        raise ValueError("Refresh changed the engine execution configuration")
    layers = parent["RootFS"]["Layers"]
    if child.get("RootFS", {}).get("Layers", [])[:len(layers)] != layers:
        raise ValueError("Child image does not retain the exact parent layers")
    if any(before.get(key) != after.get(key) for key in
           ("source_commit", "sciel_version", "dependency_sha256", "dependency_count")):
        raise ValueError("Refresh changed the SCiEL source or installed dependency inventory")
    if after.get("task_source") != task_source:
        raise ValueError("Child runtime does not contain the exact prepared task library")
    if after.get("arena_snapshot_sha256") != snapshot:
        raise ValueError("Installed Arena files differ from the complete prepared snapshot")
    return labels


def registry_tag(tag):
    """Read one private v2 manifest; only an explicit 404 means unclaimed."""
    if not TAG.fullmatch(tag):
        raise ValueError("Only a private loopback registry tag is allowed")
    repository, name = tag.removeprefix("127.0.0.1:5000/").split(":")
    client = http.client.HTTPConnection("127.0.0.1", 5000, timeout=15)
    try:
        client.request("GET", f"/v2/{repository}/manifests/{name}", headers={"Accept":
            "application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json"})
        response = client.getresponse()
        if response.status == 404:
            return None
        if response.status != 200:
            raise ValueError("Private registry did not return a verified tag state")
        raw = response.read(8 * 1024 * 1024 + 1)
        digest = response.getheader("Docker-Content-Digest")
        if len(raw) > 8 * 1024 * 1024 or digest != "sha256:" + sha(raw):
            raise ValueError("Private registry manifest digest is missing or inconsistent")
        value = json.loads(raw)
        image_id = value.get("config", {}).get("digest")
        if value.get("schemaVersion") != 2 or not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id or ""):
            raise ValueError("Expected a single-platform image manifest")
        return {"reference": "127.0.0.1:5000/" + repository + "@" + digest, "image_id": image_id}
    finally:
        client.close()


def push_verified(tag, image_id, log):
    if registry_tag(tag) is not None:
        raise ValueError("Refusing to overwrite an existing private release tag")
    if inspect(tag).get("Id") != image_id:
        raise ValueError("Local release tag changed after runtime verification")
    subprocess.run(["docker", "push", tag], stdout=log, stderr=subprocess.STDOUT, check=True)
    published = registry_tag(tag)
    image = inspect(image_id)  # Never replace the verified identity with a mutable tag lookup.
    if (published is None or published["image_id"] != image_id
            or image.get("Id") != image_id
            or published["reference"] not in image.get("RepoDigests", [])):
        raise ValueError("Pushed registry manifest does not identify the verified image bytes")
    return image


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--parent-image", required=True)
    parser.add_argument("--parent-version", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--tag")
    parser.add_argument("--push", action="store_true")
    args = parser.parse_args(argv)
    for path in (args.app, args.destination):
        if not path.is_absolute() or path.resolve() != path:
            parser.error("Use absolute operator paths without symlinks")
    sys.path.insert(0, str(args.app / "src"))
    release = release_identity(PIN, args.version)
    if (not args.version.startswith("0.2.0+arena." + PIN[:8] + ".")
            or args.version == args.parent_version):
        parser.error("Choose a new build version of pinned SCiEL v0.2.0")
    args.tag = args.tag or "127.0.0.1:5000/empira/sciel:" + args.version.replace("+", "-")
    if not TAG.fullmatch(args.tag):
        parser.error("Only a private loopback image tag is allowed")
    if args.destination.exists() or args.destination.is_relative_to(args.app):
        parser.error("Destination must be new and separate from the app snapshot")
    existing = subprocess.run(["docker", "image", "inspect", args.tag], capture_output=True)
    if existing.returncode == 0:
        parser.error("Refusing to replace an existing local image tag")
    if args.push and registry_tag(args.tag) is not None:
        parser.error("Refusing to replace an existing private release tag")
    parent = inspect(args.parent_image)
    validate_parent(parent, args.parent_image, args.parent_version)
    before = proof(args.parent_image)
    if before.get("arena_snapshot_sha256") != parent["Config"]["Labels"].get("org.empira.arena.snapshot-sha256"):
        raise ValueError("Parent installed Arena bytes differ from its recorded snapshot")
    args.destination.mkdir(parents=True, mode=0o700)
    context = args.destination / "context"
    context.mkdir()
    task_source = snapshot_arena(args.app, context / "arena")
    snapshot, files = snapshot_files(context / "arena")
    inputs = {"schema": "arena.sciel-runtime-refresh/1", "release": release,
        "parent_image": args.parent_image, "parent_image_id": parent["Id"],
        "parent_release_version": args.parent_version, "parent_layers": parent["RootFS"]["Layers"],
        "arena_snapshot_sha256": snapshot, "arena_files": files, "task_source": task_source,
        "parent_runtime": before, "research_executed": False, "dependency_downloads": 0}
    (context / "refresh-inputs.json").write_bytes(encoded(inputs))
    definition = dockerfile(args.parent_image, args.version, snapshot)
    (context / "Dockerfile").write_text(definition)
    with (args.destination / "build.log").open("w") as log:
        subprocess.run(["docker", "build", "--pull=false", "--network=none", "--cpu-quota=200000",
            "--cpu-period=100000", "--memory=2g", "--tag", args.tag, str(context)],
            env={**os.environ, "DOCKER_BUILDKIT": "0"}, stdout=log, stderr=subprocess.STDOUT, check=True)
        child = inspect(args.tag)
        after = proof(child["Id"])
        labels = verify_child(parent, child, args.version, snapshot, before, after, task_source)
        if args.push:
            child = push_verified(args.tag, child["Id"], log)
    receipt = {"schema": "arena.sciel-engine-refresh-build/1", "release": release,
        "image_id": child["Id"], "repo_digests": child.get("RepoDigests", []), "tag": args.tag,
        "labels": labels, "parent_image": args.parent_image, "runtime": after,
        "arena_snapshot_sha256": snapshot, "inputs_sha256": sha(encoded(inputs)),
        "dockerfile_sha256": sha(definition.encode()), "preserved_execution_fields": list(PRESERVED),
        "dependency_downloads": 0, "research_executed": False, "queue_mutated": False}
    (args.destination / "build-receipt.json").write_bytes(encoded(receipt))
    print(json.dumps({key: receipt[key] for key in ("release", "image_id", "repo_digests", "queue_mutated")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
