"""Host-only identity checks for the single reviewed GPU capability."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat

from .evaluator_gpu import (DEVICE_NODES, DEVICE_UUID, DRIVER_SHA, DRIVER_VERSION,
                            HASH, MODEL_SHA, TASK_IDS, require)
from .evaluator_policy import directory_fd, json_object

OWNER_UID = 0
KERNEL_VERSION = Path("/proc/driver/nvidia/version")
GPU_INFORMATION = Path("/proc/driver/nvidia/gpus")


def relative(value):
    require(type(value) is str and value and "\\" not in value and "\x00" not in value)
    path = PurePosixPath(value)
    require(not path.is_absolute() and all(part not in {"", ".", ".."} for part in value.split("/")))
    return Path(*path.parts)


def trusted_directory(path, *, readonly=False):
    descriptor = directory_fd(path)
    os.close(descriptor)
    for ancestor in (path, *path.parents):
        info = ancestor.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid in {0, OWNER_UID} and not info.st_mode & 0o022,
                "GPU resources require root-owned non-writable ancestors")
    if readonly:
        require(path.stat().st_uid == OWNER_UID and not path.stat().st_mode & 0o222, "GPU asset roots must be read-only")


def file_digest(path, *, readonly=False):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == OWNER_UID and before.st_nlink == 1
                and not before.st_mode & (0o222 if readonly else 0o022), "Unsafe GPU resource file")
        value = hashlib.sha256()
        while block := os.read(descriptor, 1024 * 1024):
            value.update(block)
        after, current = os.fstat(descriptor), path.lstat()
        fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        require(all(getattr(before, k) == getattr(after, k) == getattr(current, k) for k in fields),
                "GPU resource changed during verification")
        return value.hexdigest(), before.st_size
    finally:
        os.close(descriptor)


def manifest(path, sha, limit):
    trusted_directory(path.parent)
    actual, size = file_digest(path)
    require(actual == sha and size <= limit, "GPU resource manifest identity differs")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == sha)
    return json_object(raw)


def task_tree(capability):
    from .task_library import is_bytecode_cache
    trusted_directory(capability.tasks_root)
    value = manifest(capability.task_manifest, capability.task_manifest_sha256, 16 * 1024 ** 2)
    require(value.get("schema") == "arena.task-library/1" and type(value.get("files")) is dict
            and value["files"], "Expected a complete task content manifest")
    required, external = value["files"], value.get("external_files", {})
    require(type(external) is dict and not required.keys() & external.keys())
    files = required | external
    for name, sha in files.items():
        relative(name)
        require(type(sha) is str and HASH.fullmatch(sha))
    require(all(f"suite/{task}/task.json" in required and f"suite/{task}/evaluator.py" in required
                for task in TASK_IDS), "All three LMX definitions must belong to the complete manifest")
    found = set()
    for path in capability.tasks_root.rglob("*"):
        info = path.lstat()
        require(info.st_uid == OWNER_UID and not info.st_mode & 0o022
                and (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)))
        if stat.S_ISREG(info.st_mode):
            name = str(path.relative_to(capability.tasks_root))
            if is_bytecode_cache(name, files):
                continue
            require(name in files, "Unregistered GPU task library file")
            require(file_digest(path)[0] == files[name], "Task library content differs from its manifest")
            found.add(name)
    require(required.keys() <= found, "GPU task library is incomplete")


def model_tree(capability):
    value = manifest(capability.model_manifest, MODEL_SHA, 256 * 1024)
    require(value.get("schema") == "arena.lmx-sd-assets/1"
            and value.get("model_id") == "CompVis/stable-diffusion-v1-4"
            and value.get("revision") == "2880f2ca379f41b0226444936bb7a6766a227587"
            and type(value.get("files")) is dict and len(value["files"]) == 17)
    trusted_directory(capability.model_root, readonly=True)
    found = set()
    for path in capability.model_root.rglob("*"):
        info = path.lstat()
        require(info.st_uid == OWNER_UID and not info.st_mode & 0o222
                and (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)), "Unsafe model tree entry")
        if stat.S_ISREG(info.st_mode):
            name = str(path.relative_to(capability.model_root))
            require(name in value["files"], "Unregistered model asset")
            expected = value["files"][name]
            require(file_digest(path, readonly=True) == (expected["sha256"], expected["size"]))
            found.add(name)
    require(found == set(value["files"]), "Model asset inventory is incomplete")


def driver_tree(capability):
    value = manifest(capability.driver_manifest, DRIVER_SHA, 64 * 1024)
    require(value.get("schema") == "arena.private-nvidia-userland/1"
            and type(value.get("files")) is list and len(value["files"]) == 8)
    trusted_directory(capability.driver_root, readonly=True)
    names, links = {}, {}
    for row in value["files"]:
        name = row["file"]
        require(relative(name).name == name and name not in names)
        names[name] = row
        soname = row["soname"]
        if soname is not None and soname != name:
            require(relative(soname).name == soname and soname not in links)
            links[soname] = name
    require(not names.keys() & links.keys())
    require({path.name for path in capability.driver_root.iterdir()} == names.keys() | links.keys(),
            "Driver tree differs from the reviewed inventory")
    for name, row in names.items():
        path = capability.driver_root / name
        require(file_digest(path, readonly=True) == (row["sha256"], row["size"]))
    for name, target in links.items():
        path = capability.driver_root / name
        info = path.lstat()
        require(stat.S_ISLNK(info.st_mode) and info.st_uid == OWNER_UID and os.readlink(path) == target,
                "Only the pinned direct soname links are allowed")


def device_identity():
    require(re.search(r"NVRM version:[^\n]*\b" + re.escape(DRIVER_VERSION) + r"\b", KERNEL_VERSION.read_text()),
            "Loaded NVIDIA kernel differs from the reviewed driver")
    matches = []
    for path in GPU_INFORMATION.glob("*/information"):
        fields = dict(line.split(":", 1) for line in path.read_text().splitlines() if ":" in line)
        if fields.get("GPU UUID", "").strip() == DEVICE_UUID:
            matches.append(fields.get("Device Minor", "").strip())
    require(matches == ["0"], "GPU UUID does not identify the reviewed device minor")
    for path, major, minor in DEVICE_NODES:
        info = Path(path).lstat()
        require(stat.S_ISCHR(info.st_mode) and info.st_uid == 0
                and (os.major(info.st_rdev), os.minor(info.st_rdev)) == (major, minor),
                "GPU device node differs from the reviewed host binding")


def validate_host(capability):
    task_tree(capability)
    model_tree(capability)
    driver_tree(capability)
    device_identity()
