"""Regression for the pinned seed's device scalar and conservative capture limits."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "suite/_lib"))
from arena_construction_capture import UNSUPPORTED, _snapshot as plain_snapshot
from arena_jax_snapshot import snapshot
from test_jax_construction_validity import score

JAX_AVAILABLE = importlib.util.find_spec("jax") is not None


class JaxScalarSnapshotTests(unittest.TestCase):
    def test_plain_data_remains_copied_and_unknown_conversion_hooks_are_not_called(self):
        values = np.array([0, 1])
        copied = snapshot((values, {"reported": np.float32(1)}))
        values[0] = 9
        np.testing.assert_array_equal(copied[0], [0, 1])
        self.assertEqual(copied[1]["reported"], 1)
        class Untrusted:
            def __array__(self, *args, **kwargs):
                raise AssertionError("Must not coerce an arbitrary candidate object")
            def __float__(self):
                raise AssertionError("Must not coerce an arbitrary candidate object")
        self.assertIs(snapshot(Untrusted()), UNSUPPORTED)
        self.assertIs(snapshot({0: 1}), UNSUPPORTED)
        self.assertIs(snapshot(1, depth=6), UNSUPPORTED)

    @unittest.skipUnless(JAX_AVAILABLE, "Real JAX scalar cases run in the pinned CPU image")
    def test_exact_device_scalar_preserves_value_dtype_and_nested_binding(self):
        import jax.numpy as jnp
        for dtype in (jnp.int32, jnp.float32):
            value = jnp.asarray(1, dtype=dtype)
            self.assertIs(plain_snapshot(value), UNSUPPORTED)
            copied = snapshot((np.array([0, 1]), {"reported": value}))[1]["reported"]
            self.assertIs(type(copied), np.ndarray)
            self.assertEqual(copied.shape, ())
            self.assertEqual(copied.dtype, value.dtype)
            self.assertEqual(copied.item(), 1)

    @unittest.skipUnless(JAX_AVAILABLE, "Real JAX scalar cases run in the pinned CPU image")
    def test_jax_vectors_boolean_and_complex_values_remain_unsupported(self):
        import jax.numpy as jnp
        for value in (jnp.array([1.0]), jnp.array(True), jnp.array(1 + 0j)):
            with self.subTest(value=value):
                self.assertIs(snapshot(value), UNSUPPORTED)

    @unittest.skipUnless(JAX_AVAILABLE, "Real JAX scalar cases run in the pinned CPU image")
    def test_sums_scalar_is_bound_to_same_verified_set_without_changing_upstream_score(self):
        body = "import numpy as np\n    import jax.numpy as jnp\n    return np.array([0,1]),jnp.asarray(1.0,dtype=jnp.float32)"
        adapted = score("sums-diffs-finite-sets", body)
        original = score("sums-diffs-finite-sets", body, original=True)
        self.assertIs(adapted["valid"], True, adapted)
        self.assertEqual(adapted["score"], original["score"])
        self.assertIsNone(original["valid"])
        evidence = adapted["upstream_result"]["arena_validation"]
        self.assertEqual(evidence["candidate_observations"], 1)
        self.assertEqual(evidence["verifier_observations"], 1)
        self.assertTrue(all(evidence["checks"].values()), evidence)
        self.assertTrue(evidence["checks"]["same_reported_ratio"])

    @unittest.skipUnless(JAX_AVAILABLE, "Real JAX scalar cases run in the pinned CPU image")
    def test_device_type_never_substitutes_for_finite_consistent_ratio_or_integer_set(self):
        for expression, values in (("float('nan')", "[0,1]"), ("float('inf')", "[0,1]"),
                                   ("0.5", "[0,1]"), ("True", "[0,1]"), ("1.0", "[0,0.5]")):
            with self.subTest(expression=expression, values=values):
                body = ("import numpy as np\n    import jax.numpy as jnp\n    return np.array(" +
                        values + "),jnp.asarray(" + expression + ")")
                result = score("sums-diffs-finite-sets", body)
                self.assertIsNot(result["valid"], True, result)


if __name__ == "__main__":
    unittest.main()
