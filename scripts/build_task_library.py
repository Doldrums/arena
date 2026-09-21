#!/usr/bin/env python3
"""Check or rebuild Arena's complete bundled task-library integrity manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from arena.task_library import is_bytecode_cache, read_task_file, resolve_task_root


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()


def build_manifest(root):
    """Hash data and code as bytes; never import any bundled implementation."""
    tasks = resolve_task_root(Path(root) / "tasks")
    catalog = json.loads(read_task_file(tasks, "catalog/tasks.json"))
    if (type(catalog) is not list or any(type(row) is not dict or type(row.get("id")) is not str for row in catalog)
            or len({row["id"] for row in catalog}) != len(catalog)):
        raise ValueError("Task catalog must contain unique task records")
    optional = {}
    assets_path = tasks / "catalog/source-assets.json"
    if assets_path.exists():
        assets = json.loads(read_task_file(tasks, "catalog/source-assets.json"))
        if type(assets) is not dict or assets.get("schema") != "arena.source-assets/1" or type(assets.get("files")) is not list:
            raise ValueError("Invalid source-assets declaration")
        for row in assets["files"]:
            if (type(row) is not dict or type(row.get("path")) is not str or row["path"] in optional
                    or type(row.get("sha256")) is not str or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"])):
                raise ValueError("External task files need unique paths and immutable SHA256 digests")
            path = row["path"]
            if (not path or "\\" in path or "\x00" in path or path.startswith("/")
                    or any(part in {"", ".", ".."} for part in path.split("/"))):
                raise ValueError("External task file path is not contained")
            optional[path] = row["sha256"]
    paths = []
    for directory, dirs, names in os.walk(tasks, followlinks=False):
        for name in dirs + names:
            path = Path(directory) / name
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                raise ValueError("Task bundle cannot contain links or special files")
        paths.extend((Path(directory) / name).relative_to(tasks).as_posix() for name in names)
    registered = set(paths) | optional.keys()
    files = {}
    for relative in sorted(paths):
        if "__pycache__" in Path(relative).parts:
            if not is_bytecode_cache(relative, registered):
                raise ValueError(f"Unrecognized bytecode artifact: {relative}")
            continue
        if relative in optional:
            read_task_file(tasks, relative, optional[relative])
        else:
            files[relative] = hashlib.sha256(read_task_file(tasks, relative)).hexdigest()
    return {"schema": "arena.task-library/1", "task_count": len(catalog),
            "files": files, "external_files": dict(sorted(optional.items()))}


def update(root, *, write=False):
    root = Path(root).resolve()
    manifest = build_manifest(root)
    data = encoded(manifest)
    digest = hashlib.sha256(data).hexdigest()
    path = root / "registry/task-library-manifest.json"
    registration_path = root / "registry/task-sources/arena-tasks.json"
    if path.is_symlink() or registration_path.is_symlink():
        raise ValueError("Task manifest and registration must not be symlinks")
    registration = json.loads(registration_path.read_bytes())
    if registration.get("storage") != "bundled" or registration.get("manifest_path") != "registry/task-library-manifest.json":
        raise ValueError("Expected Arena's bundled task registration")
    if write:
        registration["manifest_sha256"] = digest
        path.write_bytes(data)
        registration_path.write_bytes(encoded(registration))
    elif not path.is_file() or path.read_bytes() != data or registration.get("manifest_sha256") != digest:
        raise ValueError("Task library manifest is stale; review changes and run scripts/build_task_library.py --write")
    return manifest, digest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--check", action="store_true", help="Read-only consistency check (default)")
    actions.add_argument("--write", action="store_true", help="Rebuild after reviewing task-library changes")
    args = parser.parse_args(argv)
    try:
        manifest, digest = update(args.root, write=args.write)
    except (OSError, TypeError, ValueError) as error:
        parser.exit(1, f"Task library check failed: {error}\n")
    print(f"Task library {'written' if args.write else 'verified'}: {manifest['task_count']} tasks, "
          f"{len(manifest['files'])} bundled files, {len(manifest['external_files'])} optional source assets, {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
