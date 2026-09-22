"""Expose five pinned mathematical verifiers without rerunning a constructor.

The original scorer remains byte-for-byte intact. A valid observation requires
exactly one verifier call from its trusted evaluation path, domain checks on
that call's normalized construction, and the verifier's explicit conclusion.
This is evaluator feasibility, not a theorem, optimum, or paper reproduction.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys

import numpy as np


CONTRACTS = {
    "sidon": ("is_sidon", "evaluate"),
    "nikodym": ("_is_valid_nikodym", "evaluate"),
    "turan": ("_is_tetrahedron_free", "evaluate"),
    "convex_polygon": ("is_convex_polygon", "calculate_polygon_score"),
    "discrepancy": ("compute_discrepancy", "evaluate"),
}


def _integer_array(value):
    array = np.asarray(value)
    return array, bool(np.all(np.isfinite(array)) and
                       np.all(array == np.floor(array)))


def _domain(contract, module, arguments, local_inputs):
    """Check the normalized construction the original verifier actually sees."""
    try:
        if contract == "sidon":
            values, integral = _integer_array(arguments[0])
            # Upstream casts before validating; NaN can cast to zero on some
            # NumPy/platform combinations. Bind to the same raw local basis.
            basis, raw_integral = _integer_array(local_inputs["basis"])
            return bool(raw_integral and basis.ndim == 1 and
                        integral and values.ndim == 1 and
                        len(np.unique(values)) == len(values) and
                        np.all(values >= module.MIN_VAL) and
                        np.all(values <= module.MAX_VAL))
        if contract == "nikodym":
            points, integral = _integer_array(arguments[0])
            q, add, multiply = arguments[1:]
            return bool(integral and points.ndim == 1 and points.size > 0 and
                        q == module.Q and np.all(points >= 0) and
                        np.all(points < q * q) and
                        add.shape == multiply.shape == (q, q))
        if contract == "turan":
            count, edges = arguments
            weights = np.asarray(local_inputs["w"])
            total = local_inputs["total"]
            return bool(type(count) is int and count > 0 and edges and
                        np.isfinite(total) and total > module.TOL and
                        weights.shape == (count,) and np.all(np.isfinite(weights)) and
                        np.all(weights >= 0) and np.isclose(weights.sum(), 1.0,
                                                          rtol=1e-12, atol=1e-12) and
                        all(len(edge) == 3 and all(type(v) is int and
                            0 <= v < count for v in edge) for edge in edges))
        if contract == "convex_polygon":
            points = np.asarray(arguments[0])
            return bool(points.shape == (module.NUM_VERTEX, 2) and
                        np.all(np.isfinite(points)))
        if contract == "discrepancy":
            pattern, integral = _integer_array(arguments[0])
            return bool(integral and pattern.ndim == 1 and pattern.size > 0 and
                        np.all(np.isin(pattern, (-1, 1))))
    except (TypeError, ValueError, IndexError, AttributeError, KeyError):
        return False
    return False


def evaluate_verified(program_path, wrapper_file, contract, upstream_sha256):
    path = Path(wrapper_file).with_name("upstream_evaluator.py")
    if hashlib.sha256(path.read_bytes()).hexdigest() != upstream_sha256:
        raise ValueError("Original evaluator differs from the reviewed mathematical contract")
    spec = importlib.util.spec_from_file_location("arena_original_" + contract, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    verifier_name, caller_name = CONTRACTS[contract]
    original = getattr(module, verifier_name)
    trusted_caller = getattr(module, caller_name).__code__
    observations = []

    def observed(*arguments, **kwargs):
        # Constructor code calling a verifier is not a trusted evaluation step.
        caller = sys._getframe(1)
        caller_matches = caller.f_code is trusted_caller
        domain_valid = not kwargs and _domain(contract, module, arguments, caller.f_locals)
        conclusion = original(*arguments, **kwargs)
        if contract == "discrepancy":
            valid = (type(conclusion) is int and
                     0 <= conclusion <= module.DISCREPANCY_LIMIT)
        else:
            valid = type(conclusion) is bool and conclusion
        observations.append({"trusted_call": caller_matches,
                             "domain_valid": bool(domain_valid), "valid": bool(valid)})
        return conclusion

    setattr(module, verifier_name, observed)
    result = module.evaluate(str(program_path))
    if type(result) is not dict:
        raise ValueError("Original evaluator did not return its metric dictionary")
    validity = None
    if len(observations) == 1 and observations[0]["trusted_call"]:
        validity = observations[0]["domain_valid"] and observations[0]["valid"]
    if result.get("error"):
        validity = False
    return {**result, "arena_valid": validity, "arena_validation": {
        "contract": contract, "upstream_evaluator_sha256": upstream_sha256,
        "verifier": verifier_name, "observations": observations,
        "scope": "Feasibility of this evaluation's normalized construction; not an optimality claim.",
    }}
