"""SCiEL private-image adapter; only an approved image broker executes code."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re

from ..release_deployment import load_manifest
from ..releases import validate_public_release
from .sciel import SCiELAdapter


def _path(value, name, *, directory=False):
    if not isinstance(value, str) or not Path(value).is_absolute() or ".." in Path(value).parts:
        raise ValueError(f"{name} must be an absolute path")
    path = Path(value)
    if path.is_symlink() and name != "python":
        raise ValueError(f"{name} must not be a symlink")
    if name != "python" and any(parent.is_symlink() for parent in path.parents):
        raise ValueError(f"{name} ancestors must not be symlinks")
    if not (path.is_dir() if directory else path.is_file()):
        raise ValueError(f"{name} does not exist")
    return path


class SCiELReleaseAdapter:
    id = "sciel-release"

    def __init__(self, *, request=None):
        self.commit = None
        self.manifest = None
        self.manifest_sha256 = None
        if request is not None:
            if type(request) is not dict or "release" not in request or "deployment" not in request:
                raise ValueError("A private SCiEL run requires release identity and an approved deployment")
            reference = validate_public_release(request["release"])
            deployment = _path(request["deployment"], "deployment")
            self.manifest, self.manifest_sha256 = load_manifest(deployment, expected_release=reference)
            self.commit = self.manifest["binding"]["repository"]["commit"]

    def prepare(self, source_dir: Path, request: dict, output_dir: Path):
        required = {"python", "release", "deployment", "config", "tasks_root"}
        optional = {"seed", "budget", "campaign", "arm"}
        if type(request) is not dict or not required <= request.keys() or set(request) - required - optional:
            raise ValueError("Private SCiEL request has missing or unknown fields")
        if self.manifest is None:
            raise ValueError("Resolve the private deployment before checking the source pin")
        current, digest = load_manifest(_path(request["deployment"], "deployment"), expected_release=request["release"])
        if digest != self.manifest_sha256 or current != self.manifest:
            raise ValueError("Private deployment changed during planning")
        source = _path(str(source_dir), "source_dir", directory=True)
        if str(source) != self.manifest["source"]["path"]:
            raise ValueError("Source checkout must match the reviewed private deployment")
        python = _path(request["python"], "python")
        if not os.access(python, os.X_OK):
            raise ValueError("python must be an executable Arena interpreter")
        config = _path(request["config"], "config")
        tasks = _path(request["tasks_root"], "tasks_root", directory=True)
        for name, minimum in (("seed", 0), ("budget", 1)):
            if name in request and (type(request[name]) is not int or not minimum <= request[name] <= 10**9):
                raise ValueError(f"{name} must be a bounded integer")
        for name in ("campaign", "arm"):
            if name in request and (not isinstance(request[name], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", request[name])):
                raise ValueError(f"{name} must be a short identifier")
        root = Path(__file__).resolve().parents[2]
        return {"argv": [str(python), "-P", "-m", "arena.frameworks.drivers.sciel_release",
                         "--deployment", request["deployment"], "--deployment-sha256", digest,
                         "--output", str(output_dir)],
                "cwd": str(source), "env": {"PYTHONPATH": str(root)},
                "input_paths": [request["deployment"], str(config), str(tasks)],
                "expected_artifacts": ["native/sciel_events.jsonl", "native/checkpoint.json",
                                       ".arena/private-image-result.json"],
                "private_image": {"release": self.manifest["release"],
                                  "deployment_sha256": digest, "image": self.manifest["image"]["reference"],
                                  "image_id": self.manifest["image"]["image_id"], "source_commit": self.commit},
                "execution_backend": "private_sciel_image_broker"}

    def read_results(self, output_dir: Path):
        result = SCiELAdapter().read_results(output_dir)
        result["framework"] = self.id
        receipt = output_dir / ".arena" / "private-image-result.json"
        if receipt.exists():
            if receipt.is_symlink() or (output_dir / ".arena").is_symlink() or not receipt.is_file() or receipt.stat().st_size > 65536:
                raise ValueError("Private image result must be a bounded regular artifact")
            raw = receipt.read_bytes()
            value = json.loads(raw)
            if type(value) is not dict or value.get("type") != "result":
                raise ValueError("Invalid private image result artifact")
            result["private_image_result"] = value
            result["artifacts"].append({"path": ".arena/private-image-result.json", "sha256": hashlib.sha256(raw).hexdigest()})
            result["warnings"].append("The image result is a worker-local receipt copy; authoritative execution provenance stays in the private broker.")
        return result
