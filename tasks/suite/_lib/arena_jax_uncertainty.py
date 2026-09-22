"""Finite Hermite-polynomial domain and same-verifier numerical binding."""
from __future__ import annotations

import numpy as np

from arena_jax_checks import _close, _number, _parts, _real, _same


def check_uncertainty(module, raw, local, result, verifier):
    import sympy as sp

    coefficients, reported_c4, reported_radius = _parts(raw, 3)
    coefficients = _real(coefficients)
    checks = {"finite_nonempty_coefficient_vector": coefficients.ndim == 1 and coefficients.size > 0}
    if not checks["finite_nonempty_coefficient_vector"]:
        return checks, {}
    # This is the original scorer's explicit float conversion, followed by
    # exact Rational representation of those binary floating-point values.
    normalized = coefficients.astype(float)
    seen = verifier["arguments"]
    checks.update({"same_scored_coefficients": _same(normalized, local["coeffs"]),
                   "same_verified_coefficients": _same(normalized, seen["user_coeffs"]),
                   "nonzero_coefficients": bool(np.any(normalized != 0))})
    if not all(checks.values()):
        return checks, {}
    x = sp.symbols("x")
    count = len(normalized)
    hermite = [sp.polys.orthopolys.hermite_poly(4 * k, x=x) for k in range(count + 1)]
    partial = sum(sp.Rational(float(c)) * h for c, h in zip(normalized, hermite))
    polynomial = sp.Poly(partial - partial.subs(x, 0) / hermite[-1].subs(x, 0) * hermite[-1], x)
    if polynomial.LC() < 0:
        polynomial = -polynomial
    checks.update({"polynomial_vanishes_at_origin": polynomial.eval(0) == 0,
                   "even_real_polynomial": all(power[0] % 2 == 0 and coefficient.is_real is True
                                               for power, coefficient in polynomial.terms()),
                   "positive_leading_coefficient": bool(polynomial.LC() > 0)})
    c4, radius = (_number(value) for value in _parts(verifier["conclusion"], 2))
    reported_c4, reported_radius = _number(reported_c4), _number(reported_radius)
    checks.update({"positive_verified_c4_and_radius": c4 > 0 and radius > 0,
        "same_reported_c4": _same(reported_c4, local["c4_bound"]) and _same(reported_c4, seen["reported_c4"]),
        "same_reported_radius": _same(reported_radius, local["r_max"]) and _same(reported_radius, seen["reported_rmax"]),
        "reported_c4_matches_strict_verifier": _close(c4, reported_c4, atol=1e-9, rtol=1e-9),
        "reported_radius_matches_strict_verifier": _close(radius, reported_radius, atol=1e-9, rtol=1e-9),
        "same_scored_c4": _same(c4, local["c4"]) and _same(c4, result["c4_bound"]),
        "same_scored_radius": _same(radius, local["rmax"]) and _same(radius, result["r_max"]),
        "same_returned_coefficients": _same(normalized, result["coeffs"]),
        "c4_radius_relation": _close(c4, radius * radius / (2 * np.pi)),
        "score_bound_to_verified_c4": _close(result["combined_score"], module.BENCHMARK / c4)})
    return checks, {"hermite_terms_before_forced_zero": count,
                    "polynomial_degree": int(polynomial.degree()),
                    "verified_radius": radius, "verified_c4": c4,
                    "absolute_tolerance": 1e-9, "relative_tolerance": 1e-9,
                    "scope": "Finite Hermite construction and the pinned strict symbolic verifier's numerical radius; not an independent continuous-bound proof"}
