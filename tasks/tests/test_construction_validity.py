"""Same-call feasibility, rejected raw casts, and retained original scoring."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "suite/_lib")]
from autoresearch_tasks.registry import get_task
from autoresearch_tasks.runner import evaluate_suite
from arena_construction_capture import evaluate_construction

FACTOR_BODY = """count = 0
    for number in range(2, 101):
        divisor = 2
        while divisor * divisor <= number:
            while number % divisor == 0:
                count += 1
                number //= divisor
            divisor += 1
        if number > 1:
            count += 1
    return [0] * count"""
CASES = {
    "sciel-math-no-5-on-a-sphere": ("no_5_on_a_sphere8",
        "return [[0,0,0], [1,0,0], [0,1,0], [0,0,1]]",
        "return [[0,0,0], [1,0,0], [0,1,0], [1,1,0], [2,0,0]]"),
    "sciel-bench-k-module-problem": ("configure_pipeline",
        "return dict(loader='json_reader', preprocess='standardize', algorithm='mergesort', formatter='xml')",
        "return dict(loader='invalid', preprocess='standardize', algorithm='mergesort', formatter='xml')"),
    "sciel-math-erdos-squarefree": ("erdos_squarefree500", "return [7,32]", "return [1,2]"),
    "sciel-math-factoring-factorials": ("factoring_factorials100", FACTOR_BODY, "return [0]"),
    "sciel-math-furstenberg-sarkozy": ("furstenberg_sarkozy_205", "return [0,2]", "return [0,1]"),
    "sciel-math-subsets-grid-no-isosceles": ("grid_subset",
        "return [[0,0], [1,0], [0,2]]", "return [[0,0], [1,0], [0,1]]"),
    "sciel-math-flat-polynomials": ("flat_polynomial",
        "return [-0.25, 0, 0.5] * 13 + [-0.25, 0.5]", "return [1] * 40"),
    "sciel-math-sendov-conjecture": ("sendov_polynomial6",
        "return [[1+0j] * 3, [0j] * 3]", "return [1.1] * 6"),
}


def score(root, task, body, *, original=False, marker=None):
    name = CASES[task["id"]][0]
    with tempfile.TemporaryDirectory() as directory:
        candidate = Path(directory) / "construction.py"
        count = ""
        if marker is not None:
            count = ("from pathlib import Path\n    "
                     f"p=Path({str(marker)!r})\n    "
                     "p.write_text(str(int(p.read_text())+1 if p.exists() else 1))\n    ")
        candidate.write_text(f"def {name}():\n    {count}{body}\n")
        metadata = deepcopy(task)
        if original:
            metadata["execution"]["suite"]["evaluator"] = "upstream_evaluator.py"
            metadata["execution"]["suite"].pop("validity_key")
        return evaluate_suite(root, metadata, candidate, Path(sys.executable), timeout=20)


class ConstructionValidityTests(unittest.TestCase):
    def test_valid_constructions_keep_original_scores_and_are_not_executed_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            for task_id, (_, body, _) in CASES.items():
                with self.subTest(task=task_id):
                    task = get_task(ROOT, task_id)
                    marker = Path(directory) / task_id
                    adapted = score(ROOT, task, body, marker=marker)
                    original = score(ROOT, task, body, original=True)
                    self.assertIs(adapted["valid"], True, adapted)
                    self.assertEqual(adapted["status"], "completed", adapted)
                    self.assertEqual(adapted["score"], original["score"])
                    self.assertIsNone(original["valid"])
                    self.assertEqual(marker.read_text(), "1")
                    info = adapted["upstream_result"]["arena_validation"]
                    self.assertEqual(info["candidate_observations"], 1)
                    self.assertEqual(info["evaluator_observations"], 1)
                    self.assertTrue(all(info["checks"].values()), info)

    def test_invalid_constructions_are_rejected_even_when_a_score_is_returned(self):
        for task_id, (_, _, invalid) in CASES.items():
            with self.subTest(task=task_id):
                result = score(ROOT, get_task(ROOT, task_id), invalid)
                self.assertEqual(result["status"], "failed", result)
                self.assertIs(result["upstream_result"]["arena_valid"], False, result)
                if task_id.endswith("erdos-squarefree"):
                    self.assertEqual(result["upstream_result"]["violations"], 1)
                    self.assertIsInstance(result["score"], float)

    def test_raw_fractional_constructions_are_not_blessed_by_rounding_or_casts(self):
        cases = {
            "no-5-on-a-sphere": "return [[1.000001,0,0]]",
            "erdos-squarefree": "return [7.000001,32]",
            "furstenberg-sarkozy": "return [0,2.000001]",
            "subsets-grid-no-isosceles": "return [[0.9,0.9], [1.9,0.9]]",
        }
        for suffix, body in cases.items():
            with self.subTest(task=suffix):
                task = get_task(ROOT, "sciel-math-" + suffix)
                original = score(ROOT, task, body, original=True)
                adapted = score(ROOT, task, body)
                self.assertEqual(original["status"], "completed", original)
                self.assertGreater(original["score"], 0)
                self.assertEqual(adapted["score"], original["score"])
                self.assertIs(adapted["valid"], False, adapted)

    def test_nonfinite_overflow_and_out_of_range_inputs_are_not_valid(self):
        cases = {
            "no-5-on-a-sphere": ["return [[float('nan'),0,0]]", "return [[1e308,0,0]]"],
            "erdos-squarefree": ["return [float('inf')]", "return [1e308]"],
            "factoring-factorials": [FACTOR_BODY.replace("[0] * count", "[1e308] * count"),
                                     FACTOR_BODY.replace("[0] * count", "[0.5] * count")],
            "furstenberg-sarkozy": ["return [float('nan')]", "return [1e308]"],
            "subsets-grid-no-isosceles": ["return [[float('nan'),0]]", "return [[1e308,0]]"],
            "flat-polynomials": ["return [float('nan')] * 41", "return [float('inf')] * 41"],
            "sendov-conjecture": ["return [complex(0,float('inf'))] * 6", "return [1e308] * 6"],
        }
        for suffix, bodies in cases.items():
            for body in bodies:
                with self.subTest(task=suffix, body=body):
                    result = score(ROOT, get_task(ROOT, "sciel-math-" + suffix), body)
                    self.assertIs(result["valid"], False, result)

    def test_explicit_normalization_is_feasible_without_claiming_high_quality(self):
        flat = get_task(ROOT, "sciel-math-flat-polynomials")
        first = score(ROOT, flat, "return [1e308, -1e308, 0] * 13 + [0, 0]")
        signs = score(ROOT, flat, "return [1, -1, 1] * 13 + [1, 1]")
        self.assertIs(first["valid"], True, first)
        self.assertEqual(first["score"], signs["score"])
        task = get_task(ROOT, "sciel-bench-k-module-problem")
        result = score(ROOT, task, CASES[task["id"]][1])
        self.assertIs(result["valid"], True, result)
        self.assertEqual(result["score"], 0.0, "Feasible choices need not match any target choice")

    def test_source_bytes_are_preserved_and_old_evidence_is_not_new_protocol_evidence(self):
        for task_id in CASES:
            task = get_task(ROOT, task_id)
            suite = task["execution"]["suite"]
            self.assertEqual(suite["protocol"], "recreated")
            self.assertEqual(suite["validity_key"], "arena_valid")
            original = ROOT / "suite" / task_id / "upstream_evaluator.py"
            self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),
                             suite["adaptation"]["upstream_evaluator_sha256"])
            self.assertNotIn("execution_evidence", task["validation"])
            self.assertIs(task["validation"]["upstream_reproduction"], False)

    def test_absent_multiple_or_indirect_constructor_calls_stay_unknown(self):
        expressions = ["pass", "program.flat_polynomial(); program.flat_polynomial()", "indirect()"]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "upstream_evaluator.py"
            for expression in expressions:
                with self.subTest(expression=expression):
                    source.write_text("from types import SimpleNamespace\n"
                        "SEQ_LENGTH=41\n"
                        "program=SimpleNamespace(flat_polynomial=lambda: [1]*41)\n"
                        "def indirect(): return program.flat_polynomial()\n"
                        "def evaluate(path):\n    program=globals()['program']\n"
                        f"    {expression}\n    return {{'combined_score': 100}}\n")
                    digest = hashlib.sha256(source.read_bytes()).hexdigest()
                    result = evaluate_construction("unused", Path(directory)/"evaluator.py",
                                                   "flat_sign_polynomial", digest)
                    self.assertIsNone(result["arena_valid"], result)

    def test_profile_is_restored_after_an_evaluator_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "upstream_evaluator.py"
            source.write_text("def evaluate(path): raise RuntimeError('test failure')\n")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            previous = sys.getprofile()
            with self.assertRaisesRegex(RuntimeError, "test failure"):
                evaluate_construction("unused", Path(directory)/"evaluator.py",
                                      "flat_sign_polynomial", digest)
            self.assertIs(sys.getprofile(), previous)

    def test_a_verified_unrelated_construction_cannot_bless_the_scored_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "upstream_evaluator.py"
            source.write_text("from types import SimpleNamespace\nimport numpy as np\nN=8\n"
                "program=SimpleNamespace(no_5_on_a_sphere8=lambda: [[0,0,0]])\n"
                "def _has_five_cospherical(points): return False\n"
                "def evaluate(path):\n    program=globals()['program']\n"
                "    points=np.asarray(program.no_5_on_a_sphere8())\n"
                "    _has_five_cospherical(np.asarray([[1,1,1]]))\n"
                "    return {'combined_score': 100}\n")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            result = evaluate_construction("unused", Path(directory)/"evaluator.py",
                                           "no_five_sphere", digest)
            self.assertIs(result["arena_valid"], False, result)
            self.assertIs(result["arena_validation"]["checks"]["same_checked_points"], False)

    def test_unreviewed_source_bytes_are_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "upstream_evaluator.py"
            source.write_text("raise AssertionError('must not execute changed source')\n")
            with self.assertRaisesRegex(ValueError, "differs from the reviewed"):
                evaluate_construction("unused", Path(directory)/"evaluator.py",
                                      "flat_sign_polynomial", "0" * 64)


if __name__ == "__main__":
    unittest.main()
