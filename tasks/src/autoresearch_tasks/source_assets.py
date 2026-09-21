"""Read-only status of explicitly prepared native benchmark dependencies."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re


def records(root):
    lock = Path(root) / "catalog/source-assets.json"
    if not lock.is_file():
        return []
    value = json.loads(lock.read_text())
    if value.get("schema") != "arena.source-assets/1" or not isinstance(value.get("files"), list):
        raise ValueError("Invalid native source asset lock")
    entries = value["files"]
    seen = set()
    for entry in entries:
        relative = entry.get("path") if isinstance(entry, dict) else None
        if not isinstance(relative, str):
            raise ValueError("Native source asset must have a relative path")
        path = PurePosixPath(relative)
        if (path.is_absolute() or not path.parts or ".." in path.parts or "\\" in relative
                or path.as_posix() != relative or relative in seen):
            raise ValueError("Native source asset path is unsafe or duplicated")
        seen.add(relative)
        if not re.fullmatch(r"[0-9a-f]{64}", str(entry.get("sha256", ""))):
            raise ValueError("Native source asset requires a SHA-256 hash")
        if not isinstance(entry.get("task_ids"), list):
            raise ValueError("Native source asset must declare its task IDs")
    return entries


def status(root, task_id=None):
    root = Path(root).resolve()
    rows = []
    for entry in records(root):
        if task_id is not None and task_id not in entry["task_ids"]:
            continue
        path = root / entry["path"]
        if not path.resolve().is_relative_to(root) or any(parent.is_symlink() for parent in path.parents) or path.is_symlink():
            state = "mismatch"
        elif not path.exists():
            state = "missing"
        elif not path.is_file() or path.stat().st_size > 16 * 1024 * 1024:
            state = "mismatch"
        else:
            state = "ready" if hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"] else "mismatch"
        rows.append({"path": entry["path"], "status": state})
    return rows


def require_prepared(root, task_id):
    pending = [row for row in status(root, task_id) if row["status"] != "ready"]
    if pending:
        names = ", ".join(row["path"] for row in pending)
        raise ValueError(
            f"Native benchmark assets need preparation for {task_id}: {names}. "
            f"Run python {Path(root) / 'scripts/prepare_source_assets.py'} --task {task_id}"
        )
