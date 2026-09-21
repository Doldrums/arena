#!/usr/bin/env python3
"""Prepare exact optional native source assets without executing them.

The task library and its evaluators are bundled in Arena. A few native benchmark
dependencies and single-file reference seeds are installed explicitly from their
original projects, just like the benchmark environments they require.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from urllib.parse import urlsplit
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 16 * 1024 * 1024


def load_assets(root: Path) -> list[dict]:
    value = json.loads((root / "catalog/source-assets.json").read_text())
    if value.get("schema") != "arena.source-assets/1" or not isinstance(value.get("files"), list):
        raise ValueError("Expected an Arena source asset lock")
    paths = set()
    for item in value["files"]:
        if not isinstance(item, dict) or set(item) != {"path", "url", "sha256", "task_ids", "role"}:
            raise ValueError("Invalid source asset record")
        path = PurePosixPath(item["path"])
        if (path.is_absolute() or not path.parts or ".." in path.parts or "\\" in item["path"]
                or path.as_posix() != item["path"] or item["path"] in paths):
            raise ValueError("Source asset paths must be unique and contained")
        paths.add(item["path"])
        if not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
            raise ValueError("Source assets require SHA-256 hashes")
        url = urlsplit(item["url"])
        if (url.scheme != "https" or url.netloc != "raw.githubusercontent.com"
                or url.query or url.fragment
                or not re.fullmatch(r"/[^/]+/[^/]+/[0-9a-f]{40}/.+", url.path)):
            raise ValueError("Source assets must use immutable primary GitHub source URLs")
        if (not isinstance(item["task_ids"], list) or not item["task_ids"]
                or any(not isinstance(task, str) or not re.fullmatch(r"[a-z0-9-]+", task)
                       for task in item["task_ids"])):
            raise ValueError("Source assets must name their tasks")
    return value["files"]


def destination(root: Path, relative: str) -> Path:
    path = root / relative
    if root.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError("Source asset paths must not follow symlinks")
    if path.is_symlink():
        raise ValueError("Source asset paths must not follow symlinks")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Source asset path escapes the task library")
    return path


def status(root: Path, item: dict) -> str:
    path = destination(root, item["path"])
    if not path.exists():
        return "missing"
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        return "mismatch"
    return "ready" if hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"] else "mismatch"


def prepare(root: Path, item: dict, opener=urlopen) -> str:
    current = status(root, item)
    if current == "ready":
        return current
    if current == "mismatch":
        raise ValueError(f"Existing source asset differs from its lock: {item['path']}")
    with opener(item["url"], timeout=60) as response:
        final = urlsplit(response.geturl())
        if final.scheme != "https" or final.netloc != "raw.githubusercontent.com":
            raise ValueError("Source download redirected outside its primary source host")
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES or hashlib.sha256(raw).hexdigest() != item["sha256"]:
        raise ValueError(f"Source asset failed its size/hash check: {item['path']}")
    path = destination(root, item["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".source-asset-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
        os.chmod(temporary, 0o644)
        # Refuse replacement if another setup process populated the path.
        os.link(temporary, path)
    finally:
        os.unlink(temporary)
    return "ready"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--task", help="Task ID whose native assets to prepare")
    selection.add_argument("--all", action="store_true", help="Prepare every optional native source asset")
    parser.add_argument("--check", action="store_true", help="Check only; never download or modify files")
    args = parser.parse_args(argv)
    try:
        assets = load_assets(args.root)
        if args.task and not (args.root / "suite" / args.task / "task.json").is_file():
            raise ValueError("Unknown task ID")
        selected = [item for item in assets if args.all or args.task in item["task_ids"]]
        rows = [{"path": item["path"], "status": status(args.root, item) if args.check
                 else prepare(args.root, item)} for item in selected]
        print(json.dumps({"assets": rows, "executed": False}, indent=2))
        return int(any(row["status"] != "ready" for row in rows))
    except (OSError, ValueError) as error:
        parser.exit(2, f"Source asset preparation failed: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
