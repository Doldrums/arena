"""Task setup and response caching must leave the signed source tree unchanged."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent / "src")]
from autoresearch_tasks.runner import checkout_path, setup_upstream
from arena_task_paths import cache_path, cache_root, data_root, runtime_path
from arena.task_library import verify_task_library


class TaskCachePathsTests(unittest.TestCase):
    def test_setup_uses_external_cache_and_preserves_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            library, registry = base / "tasks", base / "registry"
            library.mkdir()
            registry.mkdir()
            (library / "seed.py").write_text("answer = 42\n")
            manifest = {"schema": "arena.task-library/1", "files": {
                "seed.py": hashlib.sha256((library / "seed.py").read_bytes()).hexdigest(),
            }}
            raw = json.dumps(manifest).encode()
            (registry / "task-library-manifest.json").write_bytes(raw)
            source = {"kind": "bundled", "id": "fixture", "root_path": "tasks",
                      "manifest_path": "registry/task-library-manifest.json",
                      "manifest_sha256": hashlib.sha256(raw).hexdigest()}
            before = verify_task_library(library, source, registry_root=registry)
            task = {"execution": {"repository": "https://github.com/example/runtime", "commit": "a" * 40}}
            with patch.dict(os.environ, {"ARENA_TASK_CACHE_DIR": str(base / "runtime-cache")}), \
                    patch("autoresearch_tasks.runner.subprocess.run") as git, \
                    patch("autoresearch_tasks.runner.subprocess.check_output", return_value="a" * 40):
                result = setup_upstream(library, task)
                checkout = checkout_path(library, task["execution"])
                self.assertTrue(checkout.is_dir())
                self.assertTrue(checkout.is_relative_to(base / "runtime-cache"))
                self.assertEqual(result["status"], "source_fetched")
                self.assertEqual(git.call_count, 4)
            self.assertEqual(verify_task_library(library, source, registry_root=registry), before)
            self.assertEqual(list(library.iterdir()), [library / "seed.py"])

    def test_preparation_and_file_requirements_resolve_to_same_external_data(self):
        with tempfile.TemporaryDirectory() as temporary, \
                patch.dict(os.environ, {"ARENA_TASK_CACHE_DIR": temporary}):
            self.assertEqual(runtime_path("suite/_lib/data/physics-expansion/P01/benchmark.npz"),
                             data_root() / "physics-expansion/P01/benchmark.npz")
            self.assertEqual(runtime_path("../../.cache/science-biology/B01.json"),
                             cache_path("science-biology", "B01.json"))
            self.assertEqual(runtime_path("suite/_lib/vendor/adrs/eplb/expert-load.json"),
                             cache_path("vendor/adrs/eplb/expert-load.json"))
            with self.assertRaises(ValueError):
                cache_path("../../outside")

    def test_source_tree_cache_override_is_rejected(self):
        with patch.dict(os.environ, {"ARENA_TASK_CACHE_DIR": str(ROOT / ".cache")}):
            with self.assertRaisesRegex(ValueError, "outside the task library"):
                cache_root()


if __name__ == "__main__":
    unittest.main()
