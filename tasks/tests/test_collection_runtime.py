"""Regression checks for Arena's self-contained task runtime."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from autoresearch_tasks.registry import get_task, validate
from autoresearch_tasks.runner import evaluate_suite
from autoresearch_tasks.source_assets import records, require_prepared, status


class LocalLibraryTests(unittest.TestCase):
    def test_complete_corpus_validates_without_external_checkout(self):
        result = validate(ROOT)
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["task_count"], 1163)
        self.assertEqual(result["paper_count"], 98)

    def test_task_identifier_cannot_escape_suite(self):
        for task_id in ("../catalog/papers", "/etc/passwd", "task/../../other"):
            with self.subTest(task_id=task_id), self.assertRaises(ValueError):
                get_task(ROOT, task_id)

    def test_missing_native_seed_requires_explicit_preparation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "catalog").mkdir()
            lock = {"schema": "arena.source-assets/1", "files": [{
                "path": "suite/example/initial_program.cpp", "sha256": "0" * 64,
                "task_ids": ["example"], "role": "native_seed",
                "url": "https://example.invalid/never-fetched",
            }]}
            (root / "catalog/source-assets.json").write_text(json.dumps(lock))
            self.assertEqual(status(root, "example")[0]["status"], "missing")
            with self.assertRaisesRegex(ValueError, "prepare_source_assets.py"):
                require_prepared(root, "example")
            self.assertFalse((root / "suite").exists())

    def test_source_asset_lock_rejects_escaping_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "catalog").mkdir()
            lock = {"schema": "arena.source-assets/1", "files": [{
                "path": "../outside", "sha256": "0" * 64, "task_ids": ["example"],
            }]}
            (root / "catalog/source-assets.json").write_text(json.dumps(lock))
            with self.assertRaises(ValueError):
                records(root)

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "optional numerical runtime")
    def test_packing_evaluator_accepts_seed_and_rejects_overlapping_circles(self):
        task = get_task(ROOT, "alphaevolve-circle-packing-in-unit-square")
        result = evaluate_suite(ROOT, task, python=Path(sys.executable), timeout=20)
        self.assertEqual(result["status"], "completed", result)
        self.assertTrue(result["valid"])
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "invalid.py"
            candidate.write_text("import numpy as np\ndef construct():\n    return np.ones((26, 3))\n")
            rejected = evaluate_suite(ROOT, task, candidate, Path(sys.executable), timeout=20)
            self.assertEqual(rejected["status"], "failed", rejected)
            self.assertIsNone(rejected["score"])


if __name__ == "__main__":
    unittest.main()
