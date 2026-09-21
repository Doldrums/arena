"""Writable task resources live outside the immutable Arena task library."""
from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import shutil

LIBRARY_ROOT = Path(__file__).resolve().parents[2]


def external_path(path):
    """Reject cache overrides that could modify the source collection."""
    target = Path(path).expanduser().resolve()
    if target.is_relative_to(LIBRARY_ROOT):
        raise ValueError("Task cache and prepared data must be outside the task library")
    return target


def cache_root():
    configured = os.environ.get("ARENA_TASK_CACHE_DIR")
    if configured:
        return external_path(configured)
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")).expanduser()
    if not base.is_absolute():
        base = Path.home() / ".cache"
    return external_path(base / "empira" / "tasks")


def cache_path(*parts):
    relative = PurePosixPath(*map(str, parts))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Runtime cache paths must be relative and contained")
    return external_path(cache_root() / relative)


def data_root():
    return cache_path("data")


def runtime_path(relative):
    """Resolve source-era cache locations without writing to those locations."""
    text = str(relative).replace("\\", "/")
    for prefix, replacement in (
        ("../../.cache/", ""), (".cache/", ""),
        ("suite/_lib/data/", "data/"), ("suite/_lib/vendor/", "vendor/"),
        ("validation/", "receipts/"),
    ):
        if text.startswith(prefix):
            text = replacement + text[len(prefix):]
            break
    return cache_path(text)


def receipt_path(name):
    path = cache_path("receipts", name)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def stage_vendor(source, relative, destination):
    """Combine immutable benchmark code and prepared data in a run's scratch dir."""
    source, destination = Path(source), Path(destination)
    shutil.copytree(source, destination)
    prepared = cache_path("vendor", relative)
    if prepared.is_dir():
        for path in prepared.rglob("*"):
            if path.is_file():
                target = destination / path.relative_to(prepared)
                if target.exists():
                    if target.read_bytes() != path.read_bytes():
                        raise ValueError("Prepared data must not replace bundled benchmark code")
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)
    return destination
