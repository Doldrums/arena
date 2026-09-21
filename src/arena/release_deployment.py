"""Worker-only preparation of reviewed SCiEL private-image deployment manifests.

This command validates provenance and writes an operator artifact. It never runs,
pulls, builds, pushes or publishes an image and does not admit a queue template.
The image broker must independently verify the approved digest at execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time

from .releases import (ReleaseError, public_release, resolve_release,
                       validate_private_release, validate_public_release)

SCHEMA = "arena.release-deployment/1"
CONTRACT = "sciel-cli-v1"
ENTRYPOINT = ["/opt/venv/bin/python", "-m", "sciel.cli.main"]
MAX_BYTES = 1024 * 1024


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def binding_digest(binding):
    return hashlib.sha256(canonical_bytes(validate_private_release(binding))).hexdigest()


def _decode(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ReleaseError("Duplicate deployment fields are not allowed")
            result[key] = value
        return result
    try:
        return json.loads(data, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ReleaseError("Invalid deployment JSON") from error


def _absolute(value, label):
    if not isinstance(value, str) or not Path(value).is_absolute() or ".." in Path(value).parts or "\x00" in value:
        raise ReleaseError(f"{label} must be an absolute path")
    return Path(value)


def _read(path, *, private=True):
    path = Path(path)
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ReleaseError("Deployment input paths must not traverse symlinks")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise ReleaseError("Deployment input must be a bounded regular file")
        if private and (info.st_mode & 0o007 or info.st_mode & 0o022 or info.st_uid not in {0, os.getuid()}):
            raise ReleaseError("Deployment input must be private and not writable by another account")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ReleaseError("Deployment input exceeds the size limit")
        return data
    finally:
        os.close(fd)


def inspect_image_evidence(value, binding):
    """Validate selected Docker image-inspect evidence, without executing it.

    Labels are operator-reviewed metadata, not a cryptographic build attestation.
    The broker must query its own daemon again before admitting the image.
    """
    binding = validate_private_release(binding)
    if type(value) is not list or len(value) != 1 or type(value[0]) is not dict:
        raise ReleaseError("Expected one Docker image inspection record")
    item = value[0]
    image_id = item.get("Id")
    if not isinstance(image_id, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
        raise ReleaseError("Image inspection needs an immutable image ID")
    digests = item.get("RepoDigests")
    if type(digests) is not list or binding["image"] not in digests:
        raise ReleaseError("The bound repository digest must exist in actual image RepoDigests")
    config = item.get("Config")
    labels = config.get("Labels") if type(config) is dict else None
    if type(labels) is not dict:
        raise ReleaseError("Image needs reviewed source and native contract labels")
    required = {"org.opencontainers.image.revision": binding["repository"]["commit"],
                "org.opencontainers.image.source": binding["repository"]["url"],
                "io.arena.sciel.contract": CONTRACT}
    if any(labels.get(key) != value for key, value in required.items()):
        raise ReleaseError("Image labels do not match the immutable source and SCiEL contract")
    if config.get("Entrypoint") != ENTRYPOINT:
        raise ReleaseError("Private SCiEL image must declare the reviewed native entrypoint")
    # Deliberately omit Config.Env, history, registry credentials and arbitrary
    # labels. The output is bounded private provenance, not an image dump.
    return {"reference": binding["image"], "image_id": image_id,
            "entrypoint": list(ENTRYPOINT), "labels": required,
            "metadata_is_build_attestation": False}


def validate_manifest(value):
    fields = {"schema", "release", "binding", "binding_sha256", "source", "image", "broker", "review"}
    if type(value) is not dict or set(value) != fields or value.get("schema") != SCHEMA:
        raise ReleaseError("Expected arena.release-deployment/1")
    reference = validate_public_release(value["release"])
    binding = validate_private_release(value["binding"])
    if reference["system"] != "sciel" or public_release(binding) != reference:
        raise ReleaseError("This deployment contract supports only the matching SCiEL release")
    if value["binding_sha256"] != binding_digest(binding):
        raise ReleaseError("Deployment binding digest does not match")
    source = value["source"]
    if type(source) is not dict or set(source) != {"path", "commit", "tree"}:
        raise ReleaseError("Deployment needs an exact source checkout identity")
    _absolute(source["path"], "source.path")
    if source["commit"] != binding["repository"]["commit"] or not isinstance(source["tree"], str) or re.fullmatch(r"[0-9a-f]{40}", source["tree"]) is None:
        raise ReleaseError("Deployment source must match the private release pin")
    image = value["image"]
    if type(image) is not dict or set(image) != {"reference", "image_id", "entrypoint", "labels", "metadata_is_build_attestation"} or image["metadata_is_build_attestation"] is not False:
        raise ReleaseError("Deployment needs bounded reviewed image evidence")
    expected = inspect_image_evidence([{"Id": image.get("image_id"), "RepoDigests": [image.get("reference")],
                                        "Config": {"Entrypoint": image.get("entrypoint"), "Labels": image.get("labels")}}], binding)
    if image != expected:
        raise ReleaseError("Unexpected image evidence fields")
    broker = value["broker"]
    if type(broker) is not dict or set(broker) != {"contract", "socket"} or broker["contract"] != CONTRACT:
        raise ReleaseError("Deployment requires the private SCiEL image broker")
    _absolute(broker["socket"], "broker.socket")
    review = value["review"]
    if type(review) is not dict or set(review) != {"operator", "reference", "reviewed_at"}:
        raise ReleaseError("Operator review identity must be explicit")
    if not isinstance(review["operator"], str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", review["operator"]) is None:
        raise ReleaseError("Invalid operator identity")
    if not isinstance(review["reference"], str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/#-]{0,239}", review["reference"]) is None:
        raise ReleaseError("Review reference must be a credential-free review identifier")
    if type(review["reviewed_at"]) is not int or review["reviewed_at"] < 0:
        raise ReleaseError("Invalid review timestamp")
    if len(canonical_bytes(value)) > MAX_BYTES:
        raise ReleaseError("Deployment manifest exceeds size limit")
    return value


def load_manifest(path, *, expected_release=None):
    data = _read(path)
    value = validate_manifest(_decode(data))
    if expected_release is not None and value["release"] != validate_public_release(expected_release):
        raise ReleaseError("Deployment does not match the requested public release")
    return value, hashlib.sha256(data).hexdigest()


def prepare_deployment(reference, store_dir, source_dir, image_inspection, *, broker_socket, operator, review_reference):
    """Read and verify an existing checkout; no checkout, framework or image runs."""
    reference = validate_public_release(reference)
    if reference["system"] != "sciel":
        raise ReleaseError("Only SCiEL has this private image contract")
    binding = resolve_release(Path(store_dir), reference)
    source = _absolute(str(source_dir), "source_dir")
    if source.is_symlink() or source.resolve() != source:
        raise ReleaseError("Use the exact immutable checkout path without symlinks")
    from .frameworks.runtime import verify_source
    try:
        revision = verify_source(source, binding["repository"]["commit"])
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise ReleaseError("Source is not the clean private release checkout") from error
    image = inspect_image_evidence(image_inspection, binding)
    value = {"schema": SCHEMA, "release": reference, "binding": binding,
             "binding_sha256": binding_digest(binding), "source": {"path": str(source), **revision},
             "image": image, "broker": {"contract": CONTRACT, "socket": str(broker_socket)},
             "review": {"operator": operator, "reference": review_reference, "reviewed_at": int(time.time())}}
    return validate_manifest(value)


def write_manifest(path, value):
    value = validate_manifest(value)
    path = Path(path)
    if not path.is_absolute() or path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ReleaseError("Deployment output must be an absolute private path without symlinks")
    root = Path(__file__).resolve().parents[2]
    if path.is_relative_to(root):
        raise ReleaseError("Deployment manifests must remain outside the source/public tree")
    info = path.parent.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ReleaseError("Deployment output directory must be owned and mode 0700")
    data = canonical_bytes(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)
    return hashlib.sha256(data).hexdigest()


def materialize_template(manifest_path, approved_manifest, *, template_id, name, model,
                         python, config, tasks_root, resources, timeout_seconds,
                         seed=0, budget=1, environment_names=()):
    """Prepare an explicit control template only after matching broker approval.

    The caller is the operator editing private control configuration. An approval
    file is evidence of that local operation, not a portable signature; the root
    broker still independently looks up the exact hash in its own private store.
    """
    manifest, digest = load_manifest(manifest_path)
    approved, approved_digest = load_manifest(approved_manifest, expected_release=manifest["release"])
    if approved_digest != digest or approved != manifest:
        raise ReleaseError("Broker approval must match the exact deployment manifest")
    if Path(approved_manifest).name != digest + ".json":
        raise ReleaseError("Broker approval must be named by its exact manifest SHA-256")
    if type(resources) is not dict or set(resources) != {"cpus", "memory_mb", "evaluation_slots", "pids"}:
        raise ReleaseError("Explicit reviewed resource and evaluation concurrency limits are required")
    request = {"python": str(python), "release": manifest["release"], "deployment": str(manifest_path),
               "config": str(config), "tasks_root": str(tasks_root), "seed": seed, "budget": budget}
    from .frameworks.sciel_release import SCiELReleaseAdapter
    adapter = SCiELReleaseAdapter(request=request)
    # This validates paths and argument bounds without contacting the broker.
    adapter.prepare(Path(manifest["source"]["path"]), request, Path("/arena-template-output-not-created"))
    template = {"id": template_id, "name": name, "framework": "sciel-release", "profile": CONTRACT,
                "model": model, "status": "ready", "blocked_reason": None, "resources": dict(resources),
                "containment": "cgroup-v2", "evaluation_concurrency_verified": True,
                "spec": {"schema": "arena.native-run/1", "framework": "sciel-release",
                         "source_dir": manifest["source"]["path"], "output_dir": "{output_dir}",
                         "timeout_seconds": timeout_seconds, "request": request,
                         "environment_names": list(environment_names)}}
    from .control import validate_config
    # A shape/bounds check; actual deployment capacities are checked again when
    # the operator installs this template into the real control configuration.
    validate_config({"schema": "arena.control/1", "state_dir": "/private-control-template-validation",
                     "cgroup_root": "/sys/fs/cgroup/private-control-template-validation",
                     "limits": {"cpus": resources["cpus"], "memory_mb": resources["memory_mb"],
                                "evaluation_slots": 32, "max_active": 1, "max_queued": 1,
                                "max_runs_per_key": 1, "max_reserved_seconds_per_key": 604800},
                     "templates": [template]})
    return template


def _write_private_template(path, value):
    path = Path(path)
    if not path.is_absolute() or path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ReleaseError("Template output must be an absolute private file path")
    if path.is_relative_to(Path(__file__).resolve().parents[2]):
        raise ReleaseError("Private templates must remain outside the source/public tree")
    info = path.parent.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ReleaseError("Template output directory must be owned and mode 0700")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(canonical_bytes(value))
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    for name in ("reference", "store", "source", "image-inspection", "broker-socket", "output"):
        prepare.add_argument("--" + name, type=Path, required=True)
    prepare.add_argument("--operator", required=True)
    prepare.add_argument("--review-reference", required=True)
    check = sub.add_parser("check")
    check.add_argument("manifest", type=Path)
    template = sub.add_parser("template")
    for name in ("manifest", "approved-manifest", "python", "config", "tasks-root", "output"):
        template.add_argument("--" + name, type=Path, required=True)
    for name in ("id", "name", "model"):
        template.add_argument("--" + name, required=True)
    for name in ("cpus", "memory-mb", "evaluation-slots", "pids", "timeout-seconds", "budget"):
        template.add_argument("--" + name, type=int, required=True)
    template.add_argument("--seed", type=int, default=0)
    template.add_argument("--environment-name", action="append", default=[])
    template.add_argument("--verified-native-concurrency", action="store_true", required=True,
                          help="Operator confirms the fixed native configuration fits the declared evaluation slots")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            reference = validate_public_release(_decode(_read(args.reference, private=False)))
            inspection = _decode(_read(args.image_inspection))
            manifest = prepare_deployment(reference, args.store, args.source, inspection,
                                          broker_socket=args.broker_socket, operator=args.operator,
                                          review_reference=args.review_reference)
            digest = write_manifest(args.output, manifest)
        elif args.command == "check":
            manifest, digest = load_manifest(args.manifest)
        else:
            manifest, digest = load_manifest(args.manifest)
            template = materialize_template(args.manifest, args.approved_manifest,
                template_id=args.id, name=args.name, model=args.model, python=args.python, config=args.config,
                tasks_root=args.tasks_root, resources={"cpus": args.cpus, "memory_mb": args.memory_mb,
                    "evaluation_slots": args.evaluation_slots, "pids": args.pids}, timeout_seconds=args.timeout_seconds,
                seed=args.seed, budget=args.budget, environment_names=args.environment_name)
            _write_private_template(args.output, template)
        print(json.dumps({"release": manifest["release"], "status": "template_prepared_not_submitted" if args.command == "template" else "prepared_not_admitted",
                          "deployment_sha256": digest}, sort_keys=True))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError):
        parser.exit(2, "Private deployment validation failed; no execution was admitted.\n")


if __name__ == "__main__":
    raise SystemExit(main())
