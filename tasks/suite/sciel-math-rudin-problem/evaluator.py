# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the Rudin problem for polynomials: minimizing the
# L^4/L^2 norm ratio of a real degree-10 spherical harmonic on the unit sphere S^2.
#
# ===--------------------------------------------------------------------------------------===#
#
# Some of the code in this file is adapted from:
#
# google-deepmind/alphaevolve_results:
# Licensed under the Apache License v2.0.
#
# ===--------------------------------------------------------------------------------------===#
#
# NOTE ON THE IMPLEMENTATION:
# The upstream notebook scores constructions with an exact, symbolic L^4/L^2 norm computed
# from Gaunt coefficients / Wigner-3j symbols (via sympy/scipy). To keep this evaluator pure
# numpy + stdlib, we instead compute the same L^4 and L^2 norms by high-order numerical
# quadrature on the sphere: Gauss-Legendre nodes in cos(theta) and a uniform (spectrally
# exact) grid in the azimuth phi. For a degree-D spherical harmonic this integrates |f|^2 and
# |f|^4 exactly to machine precision with the grid sizes below, so the ratio is exact. The
# absolute ratio differs from the notebook only by a fixed basis-convention factor on the
# real -> complex coefficient map; the optimization problem (minimize L^4/L^2) is identical.

import time
import numpy as np
import sys
import os
from importlib import __import__
from math import lgamma

# Fixed problem degree (notebook's default evaluation degree). f is a degree-DEGREE harmonic
# with 2*DEGREE + 1 real coefficients.
DEGREE = 10
NUM_COEFFS = 2 * DEGREE + 1

# Quadrature grid (chosen large enough to integrate |f|^4 of a degree-DEGREE harmonic exactly).
N_THETA = 6 * DEGREE + 10
N_PHI = 12 * DEGREE + 10

# BENCHMARK: the upstream notebook gives no known optimal constant for this problem, so we use
# the baseline construction's own score, i.e. the L^4/L^2 ratio (full surface measure dOmega)
# of the all-ones degree-10 harmonic. combined_score therefore starts at ~1.0 for the baseline
# and rises above 1.0 as evolution lowers the ratio.
BENCHMARK = 0.7331274141614718

# Feasibility guards (from the notebook): reject degenerate (all-tiny) or blown-up coefficients.
MIN_COEFF_SCALE = 1e-3
MAX_COEFF_SCALE = 1e5


def _assoc_legendre_fixed_l(l: int, x: np.ndarray) -> np.ndarray:
    """Associated Legendre functions P_l^m(x) for fixed l, all m = 0..l.

    Returns an array of shape (l + 1, len(x)); row m holds P_l^m(x) (Condon-Shortley
    phase). Built via the standard upward recurrences in pure numpy.
    """
    x = np.asarray(x, dtype=np.float64)
    somx2 = np.sqrt(np.maximum(0.0, 1.0 - x * x))

    # Diagonal P_m^m for m = 0..l.
    pmm = [None] * (l + 1)
    cur = np.ones_like(x)  # P_0^0 = 1
    pmm[0] = cur.copy()
    for m in range(1, l + 1):
        cur = cur * (-(2 * m - 1)) * somx2  # P_m^m = -(2m-1) * sqrt(1-x^2) * P_{m-1}^{m-1}
        pmm[m] = cur.copy()

    out = np.zeros((l + 1, x.shape[0]), dtype=np.float64)
    for m in range(l + 1):
        if l == m:
            out[m] = pmm[m]
            continue
        p_m1 = x * (2 * m + 1) * pmm[m]  # P_{m+1}^m
        if l == m + 1:
            out[m] = p_m1
            continue
        a, b = pmm[m], p_m1
        for ll in range(m + 2, l + 1):
            c = ((2 * ll - 1) * x * b - (ll + m - 1) * a) / (ll - m)
            a, b = b, c
        out[m] = b
    return out


def _norm_factor(l: int, m: int) -> float:
    """Normalization sqrt((2l+1)/(4 pi) * (l-m)!/(l+m)!) for fully-normalized real SH."""
    log_val = np.log((2 * l + 1) / (4.0 * np.pi)) + lgamma(l - m + 1) - lgamma(l + m + 1)
    return float(np.exp(0.5 * log_val))


def _l4_l2_ratio(coeffs: np.ndarray, degree: int) -> float:
    """Exact (to machine precision) ||f||_{L^4(dOmega)} / ||f||_{L^2(dOmega)} of the real
    degree-`degree` spherical harmonic f = sum_m coeffs[m] * Y_degree^m, by quadrature."""
    coeffs = np.asarray(coeffs, dtype=np.float64)

    x, w = np.polynomial.legendre.leggauss(N_THETA)  # nodes/weights on [-1, 1] for cos(theta)
    phi = 2.0 * np.pi * np.arange(N_PHI) / N_PHI

    p_lm = _assoc_legendre_fixed_l(degree, x)  # (degree + 1, N_THETA)

    f = np.zeros((N_THETA, N_PHI), dtype=np.float64)
    for i, m in enumerate(range(-degree, degree + 1)):
        am = abs(m)
        norm = _norm_factor(degree, am)
        if m == 0:
            ang = np.ones(N_PHI)
        elif m > 0:
            ang = np.sqrt(2.0) * np.cos(m * phi)
        else:
            ang = np.sqrt(2.0) * np.sin(am * phi)
        f += coeffs[i] * np.outer(norm * p_lm[am], ang)

    # Surface measure dOmega = sin(theta) dtheta dphi -> (dx in [-1,1]) * dphi.
    meas = np.outer(w, (2.0 * np.pi / N_PHI) * np.ones(N_PHI))
    i2 = float(np.sum(meas * f**2))
    i4 = float(np.sum(meas * f**4))
    if not np.isfinite(i2) or i2 <= 0.0:
        raise ValueError("Non-positive or non-finite L^2 norm.")
    l2 = np.sqrt(i2)
    l4 = i4**0.25
    return l4 / l2


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        coeffs = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            coeffs = program.rudin_problem10()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(coeffs, np.ndarray):
            coeffs = np.array(coeffs, dtype=np.float64)
        coeffs = coeffs.astype(np.float64).ravel()

        if coeffs.shape != (NUM_COEFFS,):
            raise ValueError(
                f"Invalid shape: coeffs = {coeffs.shape}, expected {(NUM_COEFFS,)}"
            )

        if not np.all(np.isfinite(coeffs)):
            raise ValueError("Coefficients contain NaN or infinite values.")

        max_abs = float(np.max(np.abs(coeffs)))
        if max_abs < MIN_COEFF_SCALE:
            raise ValueError("Degenerate construction: all coefficients are ~0.")
        if max_abs > MAX_COEFF_SCALE:
            raise ValueError("Coefficients are unreasonably large.")

        ratio = _l4_l2_ratio(coeffs, DEGREE)
        if not np.isfinite(ratio) or ratio <= 0.0:
            raise ValueError("Non-finite or non-positive L^4/L^2 ratio.")

        # MINIMIZATION problem -> convert to higher-is-better with BENCHMARK / ratio.
        combined_score = BENCHMARK / ratio
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "l4_l2_ratio": float(ratio),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
