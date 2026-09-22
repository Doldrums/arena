"""Explicit feasibility predicates for eight pinned, same-call constructions.

These checks certify the stated discrete domain or numerical representation.
They do not certify optimality, a conjecture, or reproduction of a paper result.
"""
from __future__ import annotations

import itertools
import math

import numpy as np


def _real(value, *, integer=False):
    values = np.asarray(value)
    if values.dtype.kind not in "biuf" or not np.all(np.isfinite(values)):
        raise ValueError("Expected finite real coordinates")
    if integer and not np.all(values == np.floor(values)):
        raise ValueError("Expected exact integers before upstream normalization")
    return values


def _equal(left, right):
    return bool(np.array_equal(left, right))


def _helper(observations, name):
    rows = observations.get(name, [])
    if len(rows) != 1 or not rows[0]["trusted_call"]:
        raise LookupError("Expected exactly one trusted verifier call")
    return rows[0]


def _grid(raw, local, dimension, maximum):
    points = _real(raw, integer=True)
    domain = (points.ndim == 2 and points.shape[1] == dimension and
              np.all(points >= 0) and np.all(points <= maximum))
    if not domain:
        return points, {"integer_grid_domain": False}
    return points.astype(np.int64), {
        "integer_grid_domain": True,
        "distinct_points": len(np.unique(points, axis=0)) == len(points),
        "same_normalized_points": _equal(points, local["points"]),
    }


def _sphere(module, raw, local, observations):
    points, checks = _grid(raw, local, 3, module.N - 1)
    if not all(checks.values()):
        return checks
    seen = _helper(observations, "_has_five_cospherical")
    checks.update({
        "same_checked_points": _equal(seen["arguments"]["points"], points),
        "no_cospherical_or_coplanar_five": seen["conclusion"] is False,
    })
    return checks


def _configuration(module, raw, local, observations):
    domain = (type(raw) is dict and all(
        key in raw and raw[key] in options
        for key, options in module.VALID_OPTIONS.items()))
    checks = {"configuration_domain": domain}
    if not domain:
        return checks
    seen = _helper(observations, "validate_config")
    checks.update({"same_configuration": raw == local["config"] == seen["arguments"]["config"],
                   "validator_has_no_errors": seen["conclusion"] == []})
    return checks


def _integer_subset(raw, local, key, minimum, maximum):
    values = _real(raw, integer=True).reshape(-1)
    domain = bool(values.size and np.all(values >= minimum) and np.all(values <= maximum))
    if not domain:
        return values, {"integer_subset_domain": False}
    return values.astype(np.int64), {
        "integer_subset_domain": True,
        "distinct_elements": len(np.unique(values)) == len(values),
        "same_normalized_subset": _equal(values, local[key]),
    }


def _squarefree(module, raw, local, observations):
    values, checks = _integer_subset(raw, local, "subset", 1, module.N)
    if not all(checks.values()):
        return checks
    seen = _helper(observations, "_squarefree_sieve")
    sieve = np.asarray(seen["conclusion"])
    checks["canonical_sieve_domain"] = bool(
        seen["arguments"]["limit"] == module.N * module.N + 1 and
        sieve.dtype == np.dtype(bool) and sieve.shape == (module.N * module.N + 2,))
    if checks["canonical_sieve_domain"]:
        violations = int(np.sum(np.triu(sieve[np.outer(values, values) + 1], k=1)))
        checks["same_sieve"] = _equal(sieve, local["sf"])
        checks["no_squarefree_distinct_pair"] = violations == local["violations"] == 0
    return checks


def _factorization(module, raw, local, observations):
    assignment = _real(raw, integer=True)
    seen = _helper(observations, "_prime_factors_factorial")
    primes = seen["conclusion"]
    checks = {"canonical_factor_multiset": (
        seen["arguments"]["n"] == module.N and type(primes) is list and
        primes == local["primes"] and math.prod(primes) == math.factorial(module.N))}
    domain = (assignment.shape == (len(primes),) and
              np.all(assignment >= 0) and np.all(assignment < module.N))
    checks["integer_assignment_domain"] = bool(domain)
    if not all(checks.values()):
        return checks
    checks["same_assignment"] = _equal(assignment, local["assign_int"])
    expected = [1] * module.N
    for bucket, prime in zip(assignment, primes):
        expected[int(bucket)] *= prime
    checks["same_factor_products"] = expected == local["products"]
    checks["exact_factorial_product"] = (
        math.prod(expected) == local["prod_all"] == local["total"] == math.factorial(module.N))
    return checks


def _sarkozy(module, raw, local, observations):
    values, checks = _integer_subset(raw, local, "elements", 0, module.M - 1)
    if all(checks.values()):
        forbidden = {pow(value, module.K, module.M) for value in range(1, module.M)} - {0}
        checks["no_forbidden_oriented_difference"] = all(
            (int(a) - int(b)) % module.M not in forbidden and
            (int(b) - int(a)) % module.M not in forbidden
            for a, b in itertools.combinations(values, 2))
    return checks


def _isosceles(module, raw, local, observations):
    points, checks = _grid(raw, local, 2, module.GRID_MAX)
    if all(checks.values()):
        def distance(a, b):
            return sum((int(x) - int(y)) ** 2 for x, y in zip(a, b))
        checks["no_isosceles_triple"] = all(
            len({distance(a, b), distance(b, c), distance(c, a)}) == 3
            for a, b, c in itertools.combinations(points, 3))
    return checks


def _flat(module, raw, local, observations):
    values = _real(raw)
    checks = {"finite_sequence_shape": values.shape == (module.SEQ_LENGTH,)}
    if checks["finite_sequence_shape"]:
        signs = np.where(values >= 0, 1.0, -1.0)
        checks["same_normalized_signs"] = _equal(signs, local["a"])
        checks["binary_coefficients"] = bool(np.all(np.isin(local["a"], (-1, 1))))
    return checks


def _sendov(module, raw, local, observations):
    raw_values = np.asarray(raw)
    if raw_values.dtype.kind not in "biufc":
        raise ValueError("Expected numeric roots")
    roots = raw_values.astype(np.complex128).reshape(-1)
    domain = (roots.shape == (module.NUM_ROOTS,) and np.all(np.isfinite(roots)) and
              np.all(np.abs(roots) <= 1 + module.TOL))
    checks = {"finite_roots_in_unit_disk": bool(domain)}
    if domain:
        critical = np.asarray(local["crit_points"])
        checks["same_polynomial_roots"] = _equal(roots, local["roots"])
        checks["same_monic_polynomial"] = _equal(np.poly(roots), local["poly"])
        checks["finite_derivative_roots"] = bool(
            critical.shape == (module.NUM_ROOTS - 1,) and np.all(np.isfinite(critical)))
    return checks


CHECKS = {
    "no_five_sphere": _sphere, "pipeline_config": _configuration,
    "squarefree_subset": _squarefree, "factorial_assignment": _factorization,
    "sarkozy_subset": _sarkozy, "no_isosceles_grid": _isosceles,
    "flat_sign_polynomial": _flat, "sendov_roots": _sendov,
}


def check_construction(contract, module, raw, local, observations):
    try:
        checks = CHECKS[contract](module, raw, local, observations)
        return {name: bool(value) for name, value in checks.items()}
    except LookupError:
        return None  # Missing or ambiguous trusted observations remain unknown.
    except (ValueError, TypeError, IndexError, AttributeError, OverflowError):
        return {"well_formed_finite_domain": False}
