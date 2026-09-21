# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the two-dimensional Kakeya-needle area
# minimization problem with n = 64 triangles.
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
# Problem. For position index i (0-based, i = 0..n-1) let a_i = (i + 1) / n and
# define the triangle R_i with vertices (x_i, 0), (x_i + 1/n, 0), (x_i + a_i, 1).
# The primary metric is the AREA of the union of the n triangles (MINIMIZE). Lower
# area is better, so we convert to a higher-is-better score via
# combined_score = BENCHMARK / union_area, where BENCHMARK is the AlphaEvolve
# record union area for n = 64.
#
# The union area is computed exactly (up to a fine y-quadrature) without any
# external geometry library: at height y in [0, 1] every triangle's horizontal
# cross-section is an interval of equal width w(y) = (1 - y)/n with left endpoint
# L_i(y) = x_i + a_i * y. The union length of n equal-width sorted intervals is
# w + sum_k min(gap_k, w); integrating that over y gives the union area.

import time
import numpy as np
import sys
import os
from importlib import __import__

# AlphaEvolve record union area for n = 64 (source: upstream notebook cell
# "AE Triangle constructions", suggested_positions_64, scored by the union-area
# evaluator). The Keich baseline for n = 64 has area 0.13469442.
BENCHMARK = 0.12173517736734375
NUM_POINTS = 64
NUM_Y_LEVELS = 20000


def _union_area(positions: np.ndarray) -> float:
    n = len(positions)
    a = (np.arange(n) + 1.0) / n
    ys = (np.arange(NUM_Y_LEVELS) + 0.5) / NUM_Y_LEVELS  # midpoints in [0, 1]
    left = positions[None, :] + a[None, :] * ys[:, None]  # (M, n)
    left.sort(axis=1)
    w = (1.0 - ys) / n  # (M,)
    diffs = np.diff(left, axis=1)
    lengths = w + np.minimum(diffs, w[:, None]).sum(axis=1)
    return float(lengths.mean())


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        positions = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            positions = program.kakeya_needle_2d_positions64()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(positions, np.ndarray):
            positions = np.array(positions, dtype=np.float64)
        positions = positions.astype(np.float64).reshape(-1)

        if positions.shape != (NUM_POINTS,):
            raise ValueError(
                f"Invalid shape: positions = {positions.shape}, expected {(NUM_POINTS,)}"
            )

        if not np.all(np.isfinite(positions)):
            raise ValueError("Positions contain NaN or infinite values.")

        union_area = _union_area(positions)

        if not np.isfinite(union_area) or union_area <= 0.0:
            raise ValueError("Computed a non-positive or non-finite union area.")

        combined_score = BENCHMARK / union_area
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "union_area": float(union_area),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
