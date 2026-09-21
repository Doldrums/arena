"""Locate and verify the task library shipped with Arena without importing it.

The reviewed registry pins every bundled file through a SHA256 manifest. A
copied deployment or installed wheel has the same identity without a Git clone.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

from arena.registry import resolve_registry_root

_SHA256 = re.compile(r"[0-9a-f]{64}")


def _relative(value):
    if (type(value) is not str or not value or "\\" in value or "\x00" in value
            or PurePosixPath(value).is_absolute() or any(part in {"", ".", ".."} for part in value.split("/"))):
        raise ValueError("Task library paths must be contained canonical relative paths")
    return Path(*value.split("/"))


def _root(value):
    if not isinstance(value, (str, Path)) or not str(value) or "\x00" in str(value):
        raise ValueError("Task library root must be an absolute path")
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or path.resolve() != path:
        raise ValueError("Task library root must be an absolute directory without links or traversal")
    if not path.is_dir():
        raise ValueError("Bundled task library directory is missing")
    return path


def resolve_task_root(value=None, *, source=None, registry_root=None):
    """Default to repo/tasks or installed arena/_assets/tasks, not another repo."""
    if value is not None:
        return _root(value)
    source = source or {"root_path": "tasks"}
    base = resolve_registry_root(registry_root).parent
    relative = _relative(source["root_path"])
    cursor = base
    for part in relative.parts:
        cursor /= part
        if cursor.is_symlink():
            raise ValueError("Task library directory must not contain links")
    return _root(cursor)


def read_task_file(root, relative, expected_sha256=None):
    """Read one stable regular file; never follow a task-controlled symlink."""
    root = _root(root)
    relative = _relative(relative)
    descriptors = []
    try:
        parent = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(parent)
        for part in relative.parts[:-1]:
            parent = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            descriptors.append(parent)
        descriptor = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        descriptors.append(descriptor)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("Task library file must be regular")
        chunks = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
        current = os.stat(relative.name, dir_fd=parent, follow_symlinks=False)
        fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if any(getattr(before, key) != getattr(after, key) or getattr(before, key) != getattr(current, key)
               for key in fields):
            raise ValueError("Task library file changed during verification")
        # Detect detached or replaced ancestor directories while retaining the
        # no-follow descriptors that constrained the read itself.
        path = root
        for index, part in enumerate((None, *relative.parts[:-1])):
            if part is not None:
                path /= part
            current = path.lstat()
            opened = os.fstat(descriptors[index])
            if (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
                raise ValueError("Task library directory changed during verification")
    except OSError as error:
        raise ValueError(f"Task library path is missing, linked or unreadable: {relative}") from error
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    raw = b"".join(chunks)
    if expected_sha256 is not None and hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError(f"Task library digest mismatch: {relative.as_posix()}")
    return raw


def load_task_manifest(source, *, registry_root=None):
    """Read only the registry-bound manifest, not a caller-supplied trust file."""
    if source.get("kind") != "bundled" or not _SHA256.fullmatch(source.get("manifest_sha256", "")):
        raise ValueError("Canonical evaluation requires a registered bundled task library")
    base = resolve_registry_root(registry_root).parent
    raw = read_task_file(base, source["manifest_path"], source["manifest_sha256"])
    def unique_keys(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("Duplicate task manifest key")
            value[key] = item
        return value
    manifest = json.loads(raw, object_pairs_hook=unique_keys)
    if (type(manifest) is not dict or manifest.get("schema") != "arena.task-library/1"
            or type(manifest.get("files")) is not dict or not manifest["files"]):
        raise ValueError("Invalid bundled task library manifest")
    external = manifest.get("external_files", {})
    if type(external) is not dict or manifest["files"].keys() & external.keys():
        raise ValueError("External task files must have distinct manifest paths")
    for path, digest in (manifest["files"] | external).items():
        _relative(path)
        if type(digest) is not str or not _SHA256.fullmatch(digest):
            raise ValueError("Task manifest requires a SHA256 for every file")
    return manifest



def is_bytecode_cache(relative, registered_files):
    """Recognize CPython/install and pytest caches; execution uses a fresh root."""
    path = _relative(relative)
    if path.parent.name != "__pycache__":
        return False
    match = re.fullmatch(
        r"(.+)\.cpython-[0-9]{2,3}t?(?:\.opt-[012]|-pytest-[0-9]+\.[0-9]+\.[0-9]+)?\.pyc", path.name)
    return bool(match and (path.parent.parent / (match[1] + ".py")).as_posix() in registered_files)


def verify_task_library(root, source, *, registry_root=None):
    """Verify the complete bundle, including helpers, seeds and data, every time."""
    root = _root(root)
    manifest = load_task_manifest(source, registry_root=registry_root)
    required = manifest["files"]
    files = required | manifest.get("external_files", {})
    found = set()
    for directory, dirs, names in os.walk(root, followlinks=False):
        for name in dirs + names:
            path = Path(directory) / name
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
                raise ValueError("Task library must not contain links or special files")
        for name in names:
            relative = (Path(directory) / name).relative_to(root).as_posix()
            if is_bytecode_cache(relative, files):
                continue
            if relative not in files:
                raise ValueError(f"Unregistered task library file: {relative}")
            read_task_file(root, relative, files[relative])
            found.add(relative)
    if not required.keys() <= found:
        raise ValueError("Bundled task library is missing registered files")
    identity = {"kind": "bundled", "id": source["id"], "manifest_sha256": source["manifest_sha256"],
                "file_count": len(found)}
    if manifest.get("external_files"):
        present = {path: files[path] for path in sorted(found - required.keys())}
        identity["external_files_sha256"] = hashlib.sha256(json.dumps(present, sort_keys=True).encode()).hexdigest()
    return identity
