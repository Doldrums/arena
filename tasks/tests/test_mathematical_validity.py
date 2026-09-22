"""Original verifier calls, real invalid constructions, and truthful route metadata."""
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
from arena_verified_contract import evaluate_verified

CASES = {
    "difference-bases": ("difference_basis", "return [0, 1, 2]", "return [float('nan')]"),
    "finite-field-nikodym": ("nikodym_set", "return [[[0, 0], [0, 0]]]", "return [1, 2]"),
    "turan-hypergraph": ("turan_hypergraph_tetrahedron",
        "return [1, 1, 1, 1], [[0,1,2], [0,1,3], [0,2,3], [1,2,3]]",
        "return [-1, 2], [[0,0,1]]"),
    "equidistant-points-convex": ("equidistant_points_polygon20",
        "import numpy as np; a=np.arange(20)*2*np.pi/20; p=np.stack([np.cos(a),np.sin(a)],axis=1); p[[0,2]]=p[[2,0]]; return p",
        "import numpy as np; return np.full((20,2), float('nan'))"),
    "erdos-discrepancy": ("erdos_discrepancy_pattern", "return [1, 1, 1]", "return [0, 1]"),
}


class MathematicalValidityTests(unittest.TestCase):
    def test_existing_seeds_retain_original_scores_and_have_one_verified_construction(self):
        for suffix in CASES:
            with self.subTest(task=suffix):
                task = get_task(ROOT, "sciel-math-" + suffix)
                baseline = deepcopy(task)
                baseline["execution"]["suite"]["evaluator"] = "upstream_evaluator.py"
                baseline["execution"]["suite"].pop("validity_key")
                original = evaluate_suite(ROOT, baseline, python=Path(sys.executable), timeout=20)
                adapted = evaluate_suite(ROOT, task, python=Path(sys.executable), timeout=20)
                self.assertEqual(adapted["status"], "completed", adapted)
                self.assertIs(adapted["valid"], True, adapted)
                self.assertIsNone(original["valid"])
                self.assertEqual(adapted["score"], original["score"])
                metrics = adapted["upstream_result"]
                expected = original["upstream_result"]
                self.assertEqual({k: v for k, v in metrics.items()
                                  if k not in {"eval_time", "arena_valid", "arena_validation"}},
                                 {k: v for k, v in expected.items() if k != "eval_time"})
                self.assertEqual(metrics["arena_validation"]["observations"],
                                 [{"trusted_call": True, "domain_valid": True, "valid": True}])

    def test_invalid_constructions_and_malformed_domains_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid_construction.py"
            for suffix, (name, invalid, malformed) in CASES.items():
                for body in (invalid, malformed):
                    with self.subTest(task=suffix, body=body):
                        path.write_text(f"def {name}():\n    {body}\n")
                        result = evaluate_suite(ROOT, get_task(ROOT, "sciel-math-" + suffix),
                                                path, Path(sys.executable), timeout=20)
                        self.assertIs(result["valid"], False, result)
                        self.assertEqual(result["status"], "failed", result)

    def test_candidate_is_called_once_and_its_verified_result_is_used(self):
        suffix, name = "difference-bases", CASES["difference-bases"][0]
        task = get_task(ROOT, "sciel-math-" + suffix)
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            marker, candidate = directory / "calls", directory / "single_call.py"
            candidate.write_text("from pathlib import Path\n"
                f"def {name}():\n    p=Path({str(marker)!r})\n"
                "    calls=int(p.read_text())+1 if p.exists() else 1\n"
                "    p.write_text(str(calls))\n"
                "    return [0, 1, 3] if calls == 1 else [0, 1, 2]\n")
            result = evaluate_suite(ROOT, task, candidate, Path(sys.executable), timeout=20)
            self.assertIs(result["valid"], True, result)
            self.assertEqual(result["upstream_result"]["set_size"], 3)
            self.assertEqual(marker.read_text(), "1")

    def test_fractional_sidon_basis_is_not_blessed_by_upstream_integer_cast(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "fractional_sidon.py"
            candidate.write_text("def difference_basis(): return [0, 1.5, 4]\n")
            result = evaluate_suite(ROOT, get_task(ROOT, "sciel-math-difference-bases"),
                                    candidate, Path(sys.executable), timeout=20)
            self.assertIs(result["valid"], False, result)
            observation = result["upstream_result"]["arena_validation"]["observations"][0]
            self.assertIs(observation["domain_valid"], False)
            self.assertIs(observation["valid"], True, "Cast values pass the original Sidon check")

    def test_overflowed_turan_weights_are_not_a_normalized_distribution(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "overflow_turan.py"
            candidate.write_text("def turan_hypergraph_tetrahedron():\n"
                                 "    return [1e308, 1e308], [[0, 0, 1]]\n")
            result = evaluate_suite(ROOT, get_task(ROOT, "sciel-math-turan-hypergraph"),
                                    candidate, Path(sys.executable), timeout=20)
            self.assertIs(result["valid"], False, result)
            self.assertEqual(result["score"], 0.0, "Finite scorer output cannot establish feasibility")
            observation = result["upstream_result"]["arena_validation"]["observations"][0]
            self.assertIs(observation["domain_valid"], False)
            self.assertIs(observation["valid"], True, "The edge pattern itself is tetrahedron-free")

    def test_missing_multiple_or_unrelated_verifier_calls_stay_unknown(self):
        calls = ["pass", "is_sidon([0,1,3]); is_sidon([0,1,3])", "unrelated()"]
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source = directory / "upstream_evaluator.py"
            for call in calls:
                with self.subTest(call=call):
                    source.write_text("MIN_VAL=0\nMAX_VAL=60\n"
                        "def is_sidon(values): return True\n"
                        "def unrelated(): return is_sidon([0,1,3])\n"
                        f"def evaluate(path):\n    {call}\n    return {{'combined_score': 1.0}}\n")
                    digest = hashlib.sha256(source.read_bytes()).hexdigest()
                    result = evaluate_verified("unused", directory / "evaluator.py", "sidon", digest)
                    self.assertIsNone(result["arena_valid"])

    def test_upstream_bytes_are_bound_and_sidon_is_not_a_difference_cover(self):
        for suffix in CASES:
            task = get_task(ROOT, "sciel-math-" + suffix)
            self.assertEqual(task["execution"]["suite"]["protocol"], "recreated")
            original = ROOT / "suite" / task["id"] / "upstream_evaluator.py"
            self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),
                             task["execution"]["suite"]["adaptation"]["upstream_evaluator_sha256"])
        task = get_task(ROOT, "sciel-math-difference-bases")
        self.assertIn("Sidon", task["name"])
        self.assertIn("differences distinct", task["description"])

    def test_sums_diffs_default_seed_keeps_its_actual_dependencies_and_route(self):
        task = get_task(ROOT, "sciel-math-sums-diffs-finite-sets")
        suite, direct = task["execution"]["suite"], task["execution"]["evaluator_adapter"]
        self.assertEqual(set(suite["requires"]), {"py:numpy", "py:jax", "py:tqdm"})
        self.assertEqual(suite["initial_program"], "initial_program.py")
        self.assertEqual(direct["baseline_path"], "adapters/recovered/sciel_sums_diffs/seed.py")
        self.assertEqual(direct["dependencies"], ["numpy"])


if __name__ == "__main__":
    unittest.main()
