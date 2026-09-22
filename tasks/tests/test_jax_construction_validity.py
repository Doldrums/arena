"""Same-call JAX construction contracts using cheap, deterministic fixtures."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "suite/_lib")]
from autoresearch_tasks.runner import evaluate_suite
from arena_jax_capture import evaluate_jax_construction


MATMUL = """import numpy as np
    a=np.zeros((8,40)); b=np.zeros((20,40)); c=np.zeros((10,40))
    r=0
    for i in range(2):
        for j in range(4):
            for k in range(5):
                a[i*4+j,r]=b[j*5+k,r]=c[k*2+i,r]=1
                r+=1
    return (a,b,c),2,4,5,0.0,40"""
CASES = {
    "first-autocorr-ineq": "import numpy as np\n    return np.ones(4),2.0,0.0,4",
    "second-autocorr-ineq": "import numpy as np\n    return np.ones(4),123.0,0.0,4",
    "third-autocorr-ineq": "import numpy as np\n    return np.ones(4),2.0,0.0,4",
    "erdos-min-overlap": "import numpy as np\n    return np.full(4,0.5),0.5,4",
    "sums-diffs-finite-sets": "import numpy as np\n    return np.array([0,1]),1.0",
    "heilbronn-convex-14": "import numpy as np\n    return np.array([[i,i*i] for i in range(14)],dtype=float)",
    "matmul": MATMUL,
    # Coefficients returned by the unchanged source seed on the pinned JAX CPU
    # image; this avoids rerunning optimization in a contract unit fixture.
    "uncertainty-ineq": ("import numpy as np\n    return np.array([-7.780032849030249,"
                         "0.40340909361839294,0.0014901554677635431,6.54855909942853e-7]),"
                         "0.41806114679067513,1.620726890940549"),
}


def metadata(suffix):
    return json.loads((ROOT / "suite" / ("sciel-math-" + suffix) / "task.json").read_bytes())


def score(suffix, body, *, original=False, marker=None):
    task = deepcopy(metadata(suffix))
    name = "heilbronn_convex14" if suffix == "heilbronn-convex-14" else "run"
    if original:
        task["execution"]["suite"]["evaluator"] = "upstream_evaluator.py"
        task["execution"]["suite"].pop("validity_key")
    with tempfile.TemporaryDirectory() as directory:
        candidate = Path(directory) / "construction.py"
        count = ""
        if marker is not None:
            count = ("from pathlib import Path\n    " + f"p=Path({str(marker)!r})\n    " +
                     "p.write_text(str(int(p.read_text())+1 if p.exists() else 1))\n    ")
        candidate.write_text(f"def {name}():\n    {count}{body}\n")
        return evaluate_suite(ROOT, task, candidate, Path(sys.executable), timeout=30)


class JaxConstructionValidityTests(unittest.TestCase):
    def available(self, suffix):
        package = {"heilbronn-convex-14": "scipy", "uncertainty-ineq": "sympy"}.get(suffix)
        return package is None or importlib.util.find_spec(package) is not None

    def test_feasible_constructions_keep_original_scores_and_call_candidate_once(self):
        with tempfile.TemporaryDirectory() as directory:
            for suffix, body in CASES.items():
                if not self.available(suffix):
                    continue
                with self.subTest(task=suffix):
                    marker = Path(directory) / suffix
                    adapted = score(suffix, body, marker=marker)
                    original = score(suffix, body, original=True)
                    self.assertIs(adapted["valid"], True, adapted)
                    self.assertEqual(adapted["score"], original["score"])
                    self.assertIsNone(original["valid"])
                    self.assertEqual(marker.read_text(), "1")
                    evidence = adapted["upstream_result"]["arena_validation"]
                    self.assertEqual(evidence["candidate_observations"], 1)
                    self.assertEqual(evidence["evaluator_observations"], 1)
                    self.assertTrue(all(evidence["checks"].values()), evidence)

    def test_original_matmul_shape_and_empty_factor_loopholes_are_closed(self):
        cases = ["import numpy as np\n    return (np.ones((1,1)),)*3,1,1,1,0.0,1",
                 "import numpy as np\n    return (np.empty((0,1)),)*3,2,4,5,0.0,1"]
        for body in cases:
            with self.subTest(body=body):
                original = score("matmul", body, original=True)
                adapted = score("matmul", body)
                self.assertEqual(original["status"], "completed", original)
                self.assertGreater(original["score"], 0)
                self.assertEqual(adapted["score"], original["score"])
                self.assertIs(adapted["valid"], False, adapted)

    def test_dimensions_and_rank_reject_boolean_fractional_and_nonfinite_inputs(self):
        for value in ("True", "1.1", "float('nan')", "float('inf')"):
            for slot in ("rank", "dimension"):
                with self.subTest(value=value, slot=slot):
                    body = (MATMUL.replace(",0.0,40", ",0.0," + value) if slot == "rank"
                            else MATMUL.replace(",2,4,5,", "," + value + ",4,5,"))
                    result = score("matmul", body)
                    self.assertIs(result["upstream_result"]["arena_valid"], False, result)

    def test_finite_set_domain_is_checked_before_rounding_or_overflow(self):
        for values in ("[0,0.5]", "[0,1,1]", "[0,float('nan')]", "[False,True]", "[0]", "[1,2]"):
            with self.subTest(values=values):
                result = score("sums-diffs-finite-sets", "import numpy as np\n    return np.array(" + values + "),1.0")
                self.assertIs(result["upstream_result"]["arena_valid"], False, result)
        # Native uint64 arithmetic wraps; the adapted domain/count check uses
        # the original integers, never an int64 cast of those values.
        body = "import numpy as np\n    return np.array([0,2**63,2**64-1],dtype=np.uint64),1.0"
        result = score("sums-diffs-finite-sets", body)
        self.assertIsNot(result["valid"], True, result)

    def test_ratio_domain_and_finite_input_failures(self):
        cases = {
            "first-autocorr-ineq": ["np.array([1,-1,1,1])", "np.zeros(4)", "np.full(4,float('nan'))"],
            "second-autocorr-ineq": ["np.full(4,-1.0)", "np.zeros(4)", "np.full(4,float('inf'))"],
            "third-autocorr-ineq": ["np.array([1,-1,1,-1])", "np.full(4,float('nan'))"],
        }
        for suffix, values in cases.items():
            for value in values:
                with self.subTest(task=suffix, value=value):
                    result = score(suffix, f"import numpy as np\n    return {value},2.0,0.0,4")
                    self.assertIsNot(result["valid"], True, result)
                    self.assertEqual(result["status"], "failed", result)
                    if "upstream_result" in result:
                        self.assertIs(result["upstream_result"]["arena_valid"], False, result)
        result = score("erdos-min-overlap", "import numpy as np\n    return np.full(4,0.25),0.5,4")
        self.assertIs(result["upstream_result"]["arena_valid"], False, result)

    def test_c2_uses_recomputed_score_and_its_explicit_clipping(self):
        body = "import numpy as np\n    return np.array([-1e-7,1,1,1]),float('nan'),0.0,4"
        result = score("second-autocorr-ineq", body)
        original = score("second-autocorr-ineq", body, original=True)
        self.assertIs(result["valid"], True, result)
        self.assertEqual(result["score"], original["score"])
        self.assertIs(result["upstream_result"]["arena_validation"]["measurements"]["reported_c2_is_authoritative"], False)

    def test_c2_preserves_float32_denominator_rounding(self):
        body = "import numpy as np\n    return np.array([0.13,0.71,1.19,0.43],dtype=np.float32),0.0,0.0,4"
        result = score("second-autocorr-ineq", body)
        original = score("second-autocorr-ineq", body, original=True)
        self.assertIs(result["valid"], True, result)
        self.assertEqual(result["score"], original["score"])

    def test_nonplain_auxiliary_loss_does_not_erase_the_actual_construction(self):
        body = ("import numpy as np\n    class Loss:\n        def __float__(self): return 0.0\n"
                "    return np.ones(4),2.0,Loss(),4")
        result = score("first-autocorr-ineq", body)
        self.assertIs(result["valid"], True, result)

    def test_geometric_and_symbolic_checks_are_not_claimed_as_theorems(self):
        for suffix in ("heilbronn-convex-14", "uncertainty-ineq"):
            if not self.available(suffix):
                continue
            result = score(suffix, CASES[suffix])
            self.assertIs(result["valid"], True, result)
            info = result["upstream_result"]["arena_validation"]
            self.assertIn("not a theorem", info["scope"])
        if self.available("uncertainty-ineq"):
            for body in ["import numpy as np\n    return np.zeros(1),1.,1.",
                         CASES["uncertainty-ineq"].replace("1.620726890940549", "2.0")]:
                result = score("uncertainty-ineq", body)
                self.assertIs(result["upstream_result"]["arena_valid"], False, result)

    def test_original_bytes_and_protocol_evidence_are_separate(self):
        for suffix in CASES:
            task = metadata(suffix)
            suite = task["execution"]["suite"]
            original = ROOT / "suite" / task["id"] / "upstream_evaluator.py"
            self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),
                             suite["adaptation"]["upstream_evaluator_sha256"])
            self.assertEqual(suite["protocol"], "recreated")
            self.assertFalse(task["validation"]["execution_tested"])
            self.assertNotIn("execution_evidence", task["validation"])
            self.assertNotIn("recovery_evidence", task["validation"])

    def test_missing_duplicate_or_unrelated_observations_cannot_bless_a_score(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for call in ("pass", "program.run(); program.run()", "values=program.run(); verify_c5_solution(np.ones(4),0.5,4)"):
                source = ("import numpy as np\nfrom types import SimpleNamespace\nBENCHMARK=1.0\n"
                          "program=SimpleNamespace(run=lambda:(np.full(4,0.5),0.5,4))\n"
                          "def verify_c5_solution(h_values,c5_achieved,n_points): return None\n"
                          "def evaluate(path):\n    program=globals()['program']\n"
                          f"    {call}\n    h_values=np.full(4,0.5); c5_bound=0.5; n_points=4\n"
                          "    return {'combined_score':2.0,'c5_bound':0.5}\n")
                p = root / "upstream_evaluator.py"
                p.write_text(source)
                result = evaluate_jax_construction("unused", root / "evaluator.py", "minimum_overlap",
                                                  hashlib.sha256(p.read_bytes()).hexdigest())
                self.assertIsNot(result["arena_valid"], True, result)

    def test_profile_restoration_and_changed_original_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            p = root / "upstream_evaluator.py"
            p.write_text("def verify_c5_solution(h_values,c5_achieved,n_points): return None\n"
                         "def evaluate(path): raise RuntimeError('deliberate fixture')\n")
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            previous = sys.getprofile()
            with self.assertRaisesRegex(RuntimeError, "deliberate"):
                evaluate_jax_construction("unused", root / "evaluator.py", "minimum_overlap", digest)
            self.assertIs(sys.getprofile(), previous)
            p.write_text(p.read_text() + "# altered\n")
            with self.assertRaisesRegex(ValueError, "differs"):
                evaluate_jax_construction("unused", root / "evaluator.py", "minimum_overlap", digest)


if __name__ == "__main__":
    unittest.main()
