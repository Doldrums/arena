# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the "no 5 on a sphere" problem on the
# 8 x 8 x 8 integer grid.
#
# ===--------------------------------------------------------------------------------------===#
#
# Some of the code in this file is adapted from:
#
# google-deepmind/alphaevolve_results:
# Licensed under the Apache License v2.0.
#
# ===--------------------------------------------------------------------------------------===#

import time
import numpy as np
import sys
import os
from importlib import __import__
import itertools

# BENCHMARK is the record size found by AlphaEvolve for the n=8 grid (the
# construction `construction_n_8_8_8` displayed in the upstream notebook has 23
# points; the previously known maximum was 22). The objective is maximized, so
# combined_score = num_points / BENCHMARK approaches 1.0 as the record is matched.
BENCHMARK = 23
N = 8
DET_TOL = 0.5  # integer determinants: a nonzero one has |det| >= 1


def _has_five_cospherical(points: np.ndarray) -> bool:
    """Return True if any five of the points are co-spherical / co-planar.

    Processes points incrementally: a point added after at least four others is
    checked against every 4-subset of the points already seen. This visits every
    5-subset exactly once (the subset whose last-added member is the new point),
    and stops early on the first violation, so it is cheap on infeasible inputs.
    """
    m = len(points)
    seen = points[:0].astype(np.float64)
    for idx in range(m):
        p = points[idx].astype(np.float64)
        k = len(seen)
        if k >= 4:
            w = np.empty((k, 4), dtype=np.float64)
            w[:, 0:3] = seen - p
            w[:, 3] = (seen ** 2).sum(axis=1) - (p ** 2).sum()
            combos = np.array(list(itertools.combinations(range(k), 4)))
            sub = w[combos]  # (C, 4, 4)
            if np.any(np.abs(np.linalg.det(sub)) < DET_TOL):
                return True
        seen = np.vstack([seen, p[None, :]]) if k else p[None, :]
    return False


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        points = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            points = program.no_5_on_a_sphere8()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(points, np.ndarray):
            points = np.array(points)

        if points.ndim != 2 or points.shape[1] != 3:
            raise ValueError(f"Invalid shape: points = {points.shape}, expected (k, 3)")

        if not np.all(np.isfinite(points)):
            raise ValueError("Points contain NaN or infinite values.")

        # Coordinates must be integers within the n x n x n grid [0, N-1].
        if not np.allclose(points, np.round(points)):
            raise ValueError("Points must have integer coordinates.")
        points = np.round(points).astype(np.int64)
        if np.any(points < 0) or np.any(points > N - 1):
            raise ValueError(f"Points must lie in the grid [0, {N - 1}]^3.")

        # Points must be distinct.
        if len(np.unique(points, axis=0)) != len(points):
            raise ValueError("Points must be distinct.")

        # Feasibility: no five points may be co-spherical (or co-planar).
        if _has_five_cospherical(points):
            raise ValueError("Infeasible: five points are co-spherical / co-planar.")

        num_points = int(len(points))

        combined_score = num_points / BENCHMARK
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "num_points": float(num_points),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
