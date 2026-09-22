"""Named finite-construction predicates for the eight pinned JAX examples.

Numerical ratios and floating tensor equality are representation checks, not
certificates of continuous inequalities or exact algebraic complexity bounds.
"""
from __future__ import annotations

import itertools
import math

import numpy as np

from arena_construction_capture import UNSUPPORTED


def _real(value):
    if value is UNSUPPORTED:
        raise LookupError("Unsupported return representation")
    array = np.asarray(value)
    if array.dtype.kind not in "iuf" or not np.all(np.isfinite(array)):
        raise ValueError("Expected finite real numerical data")
    return array


def _number(value):
    array = _real(value)
    if array.ndim != 0:
        raise ValueError("Expected a finite real scalar")
    return float(array)


def _integer(value, *, minimum=1):
    number = _number(value)
    if number != math.floor(number) or number < minimum:
        raise ValueError("Expected an exact integer before conversion")
    integer = int(value)
    if integer != number:
        raise ValueError("Integer is not represented faithfully")
    return integer


def _same(left, right):
    if left is UNSUPPORTED or right is UNSUPPORTED:
        raise LookupError("Unsupported binding representation")
    return bool(np.array_equal(left, right))


def _close(left, right, *, atol=1e-12, rtol=1e-12):
    return math.isclose(_number(left), _number(right), abs_tol=atol, rel_tol=rtol)


def _parts(raw, count):
    if type(raw) not in (tuple, list) or len(raw) != count:
        raise ValueError("Constructor returned an unexpected tuple")
    return raw


def _vector_binding(raw, local, verifier, key, size):
    array = _real(raw)
    if array.shape != (size,):
        raise ValueError("Vector dimension differs from the declared integer size")
    return array, {
        "finite_vector_domain": True,
        "same_scored_vector": _same(array, local[key]),
        "same_verified_vector": _same(array, verifier["arguments"][key]),
        "same_integer_size": (_integer(local["n_points"]) == size ==
                              _integer(verifier["arguments"]["n_points"])),
    }


def _autocorrelation(contract, module, raw, local, result, verifier):
    values, reported, _loss, count = _parts(raw, 4)
    size = _integer(count)
    values, checks = _vector_binding(values, local, verifier, "f_values", size)
    checks["finite_score"] = math.isfinite(_number(result["combined_score"]))
    if not all(checks.values()):
        return checks, {}
    dx = 0.5 / size
    if contract == "autocorrelation_c2":
        checks["nonnegative_before_declared_clipping"] = bool(np.all(values >= -1e-6))
        values = np.maximum(values, 0.0)
        convolution = np.convolve(values, values, mode="full")
        norm1 = np.sum(np.abs(convolution)) / (len(convolution) + 1)
        norminf = np.max(np.abs(convolution))
        # Preserve the scorer's NumPy scalar arithmetic and rounding. Casting
        # each norm to Python float first can change a float32 denominator.
        denominator = norm1 * norminf
        checks["positive_finite_norms"] = bool(np.isfinite(denominator) and norm1 > 0 and norminf > 0)
        if not all(checks.values()):
            return checks, {}
        points = np.concatenate(([0], convolution, [0]))
        intervals = np.diff(np.linspace(-0.5, 0.5, len(convolution) + 2))
        integral = sum((width / 3) * (a * a + a * b + b * b)
                       for a, b, width in zip(points[:-1], points[1:], intervals))
        computed = _number(integral / denominator)
        checks.update({
            "same_recomputed_c2": _close(computed, verifier["conclusion"]),
            "same_scored_c2": _close(computed, local["c2_verified"]) and _close(computed, result["c2"]),
            "score_uses_recomputed_c2": _close(result["combined_score"], computed / module.BENCHMARK),
        })
        return checks, {"recomputed_ratio": computed, "clipping_floor": 0.0,
                        "allowed_negative_roundoff": 1e-6, "reported_c2_is_authoritative": False}
    integral_sq = _number((np.sum(values) * dx) ** 2)
    first = contract == "autocorrelation_c1"
    checks["nonzero_integral"] = integral_sq >= (1e-8 if first else 1e-9)
    if first:
        checks["nonnegative_function"] = bool(np.all(values >= 0))
    if not all(checks.values()):
        return checks, {}
    convolution = np.convolve(values, values, mode="full") * dx
    computed = _number(np.max(convolution if first else np.abs(convolution)) / integral_sq)
    key, tolerance = ("c1_achieved", 1e-6) if first else ("c3_achieved", 1e-3)
    metric = "c1" if first else "c3"
    reported = _number(reported)
    checks.update({
        "positive_reported_ratio": reported > 0,
        "same_reported_ratio": _same(reported, local[key]) and _same(reported, verifier["arguments"][key]),
        "ratio_consistent_at_declared_tolerance": _close(computed, reported, atol=tolerance, rtol=0),
        "same_scored_ratio": _same(reported, result[metric]),
        "score_bound_to_reported_ratio": _close(result["combined_score"], module.BENCHMARK / reported),
    })
    return checks, {"recomputed_ratio": computed, "absolute_tolerance": tolerance,
                    "relative_tolerance": 0.0, "integral_squared": integral_sq}


def _overlap(module, raw, local, result, verifier):
    values, reported, count = _parts(raw, 3)
    size = _integer(count)
    values, checks = _vector_binding(values, local, verifier, "h_values", size)
    mass = _number(np.sum(values) * (2.0 / size))
    checks.update({"unit_interval_values": bool(np.all((values >= 0) & (values <= 1))),
                   "unit_integral_at_declared_tolerance": _close(mass, 1, atol=1e-3, rtol=1e-5)})
    if not all(checks.values()):
        return checks, {"integral": mass}
    computed = _number(np.max(np.correlate(values, 1 - values, mode="full") * (2.0 / size)))
    reported = _number(reported)
    checks.update({"positive_ratio": reported > 0 and computed > 0,
        "same_reported_ratio": _same(reported, local["c5_bound"]) and _same(reported, verifier["arguments"]["c5_achieved"]),
        "correlation_ratio_consistent": _close(computed, reported, atol=1e-4, rtol=1e-5),
        "same_scored_ratio": _same(reported, result["c5_bound"]),
        "score_bound_to_ratio": _close(result["combined_score"], module.BENCHMARK / reported)})
    return checks, {"recomputed_ratio": computed, "integral": mass,
                    "ratio_absolute_tolerance": 1e-4, "relative_tolerance": 1e-5}


def _finite_set(module, raw, local, result, verifier):
    values, reported = _parts(raw, 2)
    values = _real(values)
    domain = bool(values.ndim == 1 and values.size > 1 and np.all(values >= 0)
                  and np.all(values == np.floor(values)))
    checks = {"nonnegative_integer_set_domain": domain}
    if not domain:
        return checks, {}
    # Python integers avoid overflow in pair sums/differences; never cast raw
    # fractional entries to integers or infer validity from NumPy's wraparound.
    integers = [int(value) for value in values]
    maximum = max(integers)
    checks.update({"distinct_elements": len(set(integers)) == len(integers),
                   "contains_zero_and_nontrivial_maximum": 0 in integers and maximum > 0,
                   "same_scored_set": _same(values, local["u_set"]),
                   "same_verified_set": _same(values, verifier["arguments"]["u_set"])})
    if not all(checks.values()):
        return checks, {}
    plus = {a + b for a in integers for b in integers}
    minus = {a - b for a in integers for b in integers}
    computed = 1 + math.log(len(minus) / len(plus)) / math.log(2 * maximum + 1)
    reported = _number(reported)
    checks.update({"same_reported_ratio": _same(reported, local["c6_bound"]) and _same(reported, verifier["arguments"]["c6_achieved"]),
                   "integer_counts_match_reported_ratio": _close(computed, reported, atol=1e-8, rtol=1e-5),
                   "same_scored_ratio": _same(reported, result["c6_bound"]),
                   "same_set_cardinality": _integer(result["set_size"]) == len(integers),
                   "same_maximum": _integer(result["max_val"]) == maximum,
                   "score_bound_to_ratio": _close(result["combined_score"], reported / module.BENCHMARK)})
    return checks, {"sum_set_cardinality": len(plus), "difference_set_cardinality": len(minus),
                    "recomputed_ratio": computed, "absolute_tolerance": 1e-8, "relative_tolerance": 1e-5}


def _matmul(module, raw, local, result, verifier):
    factors, n, m, p, _loss, rank = _parts(raw, 6)
    dimensions = tuple(_integer(value) for value in (n, m, p))
    rank = _integer(rank)
    checks = {"intended_dimensions_2_4_5": dimensions == (2, 4, 5)}
    if not checks["intended_dimensions_2_4_5"]:
        return checks, {}
    factors = tuple(_real(value) for value in _parts(factors, 3))
    checks["nonempty_factor_shapes"] = all(a.shape == (size, rank) for a, size in zip(factors, (8, 20, 10)))
    if not checks["nonempty_factor_shapes"]:
        return checks, {}
    seen = verifier["arguments"]
    checks.update({
        "same_scored_factors": all(_same(a, b) for a, b in zip(factors, _parts(local["decomposition"], 3))),
        "same_verified_factors": all(_same(a, b) for a, b in zip(factors, _parts(seen["decomposition"], 3))),
        "same_fixed_dimensions": all(_integer(local[k]) == _integer(seen[k]) == v for k, v in zip(("n", "m", "p"), dimensions)),
        "same_rank": rank == _integer(local["rank"]) == _integer(seen["rank"]) == _integer(result["rank"]),
    })
    target = np.zeros((8, 20, 10), dtype=np.float32)
    for i, j, k in itertools.product(range(2), range(4), range(5)):
        target[i * 4 + j, j * 5 + k, k * 2 + i] = 1
    tensor = np.einsum("ir,jr,kr->ijk", *factors)
    residual = _number(np.max(np.abs(tensor - target)))
    checks.update({"floating_tensor_identity": bool(np.array_equal(tensor, target)),
                   "score_bound_to_rank": _close(result["combined_score"], 32 / rank)})
    return checks, {"tensor_max_absolute_residual": residual,
                    "comparison": "np.array_equal on computed floating-point tensor; not an exact algebraic certificate"}


def _heilbronn(module, raw, local, result, verifier):
    from scipy.spatial import ConvexHull
    points = _real(raw)
    checks = {"fourteen_two_dimensional_points": points.shape == (14, 2)}
    if not checks["fourteen_two_dimensional_points"]:
        return checks, {}
    checks.update({"distinct_points": len(np.unique(points, axis=0)) == 14,
                   "same_scored_points": _same(points, local["points"])})
    if not all(checks.values()):
        return checks, {}
    areas = [abs(a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1])) / 2
             for a, b, c in itertools.combinations(points, 3)]
    minimum = _number(min(areas))
    hull = _number(ConvexHull(points).volume)
    checks["positive_hull_area"] = hull > 0
    if hull <= 0:
        return checks, {}
    ratio = minimum / hull
    checks.update({"nonnegative_triangle_areas": all(_number(a) >= 0 for a in areas),
                   "same_minimum_triangle_area": _close(minimum, local["min_triangle_area"]),
                   "same_convex_hull_area": _close(hull, local["convex_hull_area"]),
                   "same_normalized_area": _close(ratio, local["min_area_normalized"]) and _close(ratio, result["min_area_normalized"]),
                   "score_bound_to_area_ratio": _close(result["combined_score"], ratio / module.BENCHMARK)})
    return checks, {"triangle_count": len(areas), "minimum_triangle_area": minimum,
                    "convex_hull_area": hull, "numerical_area_ratio": ratio}


def _uncertainty(module, raw, local, result, verifier):
    from arena_jax_uncertainty import check_uncertainty
    return check_uncertainty(module, raw, local, result, verifier)


def check_jax_construction(contract, module, raw, local, result, verifier):
    try:
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            if contract.startswith("autocorrelation_"):
                return _autocorrelation(contract, module, raw, local, result, verifier)
            check = {"minimum_overlap": _overlap, "finite_sum_difference": _finite_set,
                     "matmul_2_4_5": _matmul, "heilbronn_convex_14": _heilbronn,
                     "sign_uncertainty": _uncertainty}[contract]
            return check(module, raw, local, result, verifier)
    except LookupError:
        return None, {}
    except (TypeError, ValueError, OverflowError, ZeroDivisionError, FloatingPointError):
        return {"finite_well_formed_construction": False}, {}
