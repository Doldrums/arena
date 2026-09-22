"""Integrity checks for local, immutable SD1.4 assets and the GPU protocol."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys

PROTOCOL = "arena.lmx-sd14-excess-rgb/1"
REVISION = "2880f2ca379f41b0226444936bb7a6766a227587"
MAXIMUM_SCORE = 512 * 512 * 255
CUDA_ALLOCATOR_LIMIT_BYTES = 8 * 1024 ** 3
RUNTIME = {"torch": "2.9.1+cu128", "torchvision": "0.24.1+cu128",
           "diffusers": "0.35.2", "transformers": "4.57.3", "Pillow": "11.3.0",
           "safetensors": "0.7.0", "ftfy": "6.3.1", "numpy": "2.2.6", "scipy": "1.15.3"}
MANIFEST_PATH = Path(__file__).resolve().parents[3] / "adapters" / "lmx_sd_assets.json"
GENERATION = {"height": 512, "width": 512, "num_inference_steps": 10,
              "guidance_scale": 7.5, "negative_prompt": None,
              "num_images_per_prompt": 1, "eta": 0.0, "output_type": "pil"}


def verify_runtime():
    if sys.version_info[:2] != (3, 11):
        raise ValueError("The pinned LMX runtime requires Python 3.11")
    installed = {name: importlib.metadata.version(name) for name in RUNTIME}
    if installed != RUNTIME:
        raise ValueError("LMX runtime package versions differ from the pinned protocol")
    return installed


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def verify_assets(root=None, *, manifest_path=MANIFEST_PATH):
    root = Path(root or os.environ.get("LMX_SD_ASSETS_DIR", "/model"))
    if not root.is_absolute() or root.is_symlink() or root.resolve() != root:
        raise ValueError("SD assets require an absolute path without symlinks")
    raw = Path(manifest_path).read_bytes()
    lock = json.loads(raw)
    if (lock.get("schema") != "arena.lmx-sd-assets/1" or lock.get("revision") != REVISION
            or lock.get("model_id") != "CompVis/stable-diffusion-v1-4"):
        raise ValueError("Unexpected SD model identity")
    inventory = set()
    for entry in root.rglob("*"):
        info = entry.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_mode & 0o222:
            raise ValueError("The complete model tree must be immutable and not symlinked")
        if stat.S_ISREG(info.st_mode):
            inventory.add(str(entry.relative_to(root)))
        elif not stat.S_ISDIR(info.st_mode):
            raise ValueError("Model tree contains a non-regular entry")
    if inventory != set(lock["files"]):
        raise ValueError("Model tree inventory differs from the pinned asset lock")
    for name, expected in lock["files"].items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or str(relative) != name:
            raise ValueError("Unsafe model file path")
        target = root / relative
        for part in [target, *target.parents]:
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or info.st_mode & 0o222:
                raise ValueError("Model files and directories must be immutable and not symlinked")
            if part == root:
                break
        info = target.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_size != expected["size"]
                or digest(target) != expected["sha256"]):
            raise ValueError(f"Model file integrity mismatch: {name}")
    return root, {"model_id": lock["model_id"], "revision": REVISION,
                  "manifest_sha256": hashlib.sha256(raw).hexdigest(),
                  "verified_files": len(lock["files"])}
