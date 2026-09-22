"""Replay recorded evaluator signals without running models or task programs."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from autoresearch_tasks.registry import get_task
from autoresearch_tasks import runner

AUDIT = json.loads((ROOT / "validation/validity-mapping-audit.json").read_text())
REPAIRS = [row for row in AUDIT["tasks"] if row["validity_key"]]


def replay(task, upstream):
    """Feed a captured bridge response through the production result parser."""
    adapter, environment = runner.suite_adapter(ROOT, task)
    directory = ROOT / "suite" / task["id"]

    def process(_command, **kwargs):
        kwargs["stdout"].write(json.dumps(upstream).encode())
        return SimpleNamespace(returncode=0)

    initial = {"status": "failed", "valid": None, "score": None}
    with patch.object(runner, "run_process", process):
        return runner._bridge(ROOT, directory, adapter,
                              directory / "initial_program.py", sys.executable,
                              10, initial, environment)


class ExplicitValidityMetadataTests(unittest.TestCase):
    def test_audit_keeps_unverified_contracts_and_dependency_failure_pending(self):
        self.assertEqual(len(AUDIT["tasks"]), 60)
        self.assertEqual(len(REPAIRS), 5)
        pending = [r for r in AUDIT["tasks"]
                   if r["status"] == "explicit_validity_contract_required"]
        self.assertEqual(len(pending), 54)
        for row in pending:
            self.assertIsNone(row["validity_key"])
            self.assertNotIn("validity_key", get_task(ROOT, row["task_id"])["execution"]["suite"])
        failure = next(r for r in AUDIT["tasks"]
                       if r["status"] == "explicit_evaluator_error")
        self.assertEqual(failure["task_id"], "sciel-math-sums-diffs-finite-sets")
        self.assertIn("jax", failure["evaluator_error"])

    def test_repaired_metadata_preserves_evaluator_program_and_protocol(self):
        for row in REPAIRS:
            with self.subTest(task=row["task_id"]):
                task = get_task(ROOT, row["task_id"])
                self.assertEqual(task["execution"]["suite"]["protocol"], "original")
                self.assertEqual(task["execution"]["suite"]["validity_key"], row["validity_key"])
                for name, field in [("evaluator.py", "evaluator_sha256"),
                                    ("initial_program.py", "candidate_sha256")]:
                    raw = (ROOT / "suite" / row["task_id"] / name).read_bytes()
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), row["original_receipt"][field])

    def test_recorded_true_signal_reaches_canonical_runner_without_changing_score(self):
        for row in REPAIRS:
            with self.subTest(task=row["task_id"]):
                result = replay(get_task(ROOT, row["task_id"]), row["upstream_result"])
                self.assertIs(result["valid"], True)
                self.assertEqual(result["status"], "completed")
                self.assertEqual(result["score"], row["original_receipt"]["raw_score"])

    def test_false_and_absent_validity_never_become_valid_from_a_finite_score(self):
        for row in REPAIRS:
            task = get_task(ROOT, row["task_id"])
            for signal in (False, 0.0, None):
                with self.subTest(task=row["task_id"], signal=signal):
                    payload = copy.deepcopy(row["upstream_result"])
                    if signal is None:
                        payload.pop(row["validity_key"])
                    else:
                        payload[row["validity_key"]] = signal
                    result = replay(task, payload)
                    self.assertIs(result["valid"], None if signal is None else False)
                    self.assertEqual(result["status"], "completed" if signal is None else "failed")
                    self.assertEqual(result["score"], row["original_receipt"]["raw_score"])


if __name__ == "__main__":
    unittest.main()
