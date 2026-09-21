"""Read digest-verified task metadata without importing task or evaluator code."""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess

from .task_sources import source_url


class TaskSourceReader:
    def __init__(self, root, source, *, registry_root=None, require_clean=True):
        self.source = source
        self.root = Path(root).absolute()
        self.cache = {}
        self.bundled = source.get("kind") == "bundled"
        if self.bundled:
            from .task_library import load_task_manifest, verify_task_library
            verify_task_library(self.root, source, registry_root=registry_root)
            self.hashes = load_task_manifest(source, registry_root=registry_root)["files"]
            self.paths = set(self.hashes)
            return
        self.pin = source["repository"]["commit"]
        self.git = ["git", "--no-replace-objects", "-C", str(self.root)]
        if require_clean:
            revision = subprocess.check_output([*self.git, "rev-parse", "HEAD"], text=True).strip()
            if revision != self.pin:
                raise ValueError(f"Expected task revision {self.pin}, got {revision}")
            if subprocess.check_output([*self.git, "status", "--porcelain", "--untracked-files=no"], text=True).strip():
                raise ValueError("Tracked source files are modified; pinned evidence must be clean")
        self.paths = set(subprocess.check_output(
            [*self.git, "ls-tree", "-r", "--name-only", self.pin], text=True).splitlines())

    def read(self, path):
        if path not in self.paths:
            raise ValueError(f"Evidence file is not tracked at the source revision: {path}")
        if path not in self.cache:
            if self.bundled:
                from .task_library import read_task_file
                self.cache[path] = read_task_file(self.root, path, self.hashes[path])
            else:
                self.cache[path] = subprocess.check_output([*self.git, "show", f"{self.pin}:{path}"])
        return self.cache[path]

    def evidence(self, path, locator=None):
        result = {"path": path, "url": source_url(self.source, path),
                  "sha256": hashlib.sha256(self.read(path)).hexdigest()}
        if locator is not None:
            result["locator"] = locator
        return result
