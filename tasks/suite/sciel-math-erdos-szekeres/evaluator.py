# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the Erdos-Szekeres "Happy Ending" problem, with
# k = 7 (so n = 2^(k-2) + 1 = 33 points in the unit square).
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
import math
from importlib import __import__
import itertools

# Polygon size and point count for this instance.
K = 7
NUM_POINTS = 2 ** (K - 2) + 1  # = 33

# BENCHMARK is the RECORD number of convex k-gons. AlphaEvolve reported constructions with
# 0 convex k-gons for k = 7 (n = 33) and k = 8 (n = 65), i.e. candidate counterexamples to
# the Erdos-Szekeres "Happy Ending" conjecture. So the record / best possible value is 0.
# This is a MINIMIZATION problem; we convert to a higher-is-better combined_score below via
#     combined_score = 1.0 / (1.0 + (num_convex_kgons - BENCHMARK))
# which equals 1.0 exactly when the construction matches the record of 0 convex k-gons.
BENCHMARK = 0

# Feasibility tolerances.
COLLINEAR_TOL = 1e-9   # min |signed area| for a triple to count as "general position"
ORIENT_TOL = 1e-9      # orientation sign threshold (mirrors the upstream scorer)
MIN_DIST_SQ = 1e-12    # min squared pairwise distance (avoids float issues in orientations)
BOUNDS_TOL = 1e-6      # points must lie in the unit square within this tolerance


def _orientation(p, q, r):
    """Sign of the turn p -> q -> r: +1 left/CCW, -1 right/CW, 0 collinear."""
    val = (q[0] - p[0]) * (r[1] - q[1]) - (q[1] - p[1]) * (r[0] - q[0])
    if val > ORIENT_TOL:
        return 1
    if val < -ORIENT_TOL:
        return -1
    return 0


def _count_convex_kgons(points, k):
    """
    Count the number of convex k-gons whose vertices come from `points` (a (num, 2) array).
    Pure-numpy / pure-Python port of the upstream Numba dynamic-programming scorer.
    """
    P = sorted(tuple(p) for p in points.tolist())
    num = len(P)
    if num < k or k < 3:
        return 0

    total = 0
    for i in range(num):
        pivot = P[i]
        Q_unsorted = P[i + 1:]
        if len(Q_unsorted) < k - 1:
            continue
        # Sort the remaining points by angle around the pivot.
        Q = sorted(
            Q_unsorted,
            key=lambda pt: math.atan2(pt[1] - pivot[1], pt[0] - pivot[0]),
        )
        M = len(Q)

        # dp[length][a][b] = number of convex chains of `length` vertices starting at the
        # pivot, with the last two vertices being Q[a] then Q[b].
        dp = [[[0] * M for _ in range(M)] for _ in range(k + 1)]

        for j in range(M):
            for a in range(j):
                if _orientation(pivot, Q[a], Q[j]) > 0:
                    dp[3][a][j] = 1

        for length in range(4, k + 1):
            dp_prev = dp[length - 1]
            dp_len = dp[length]
            for j in range(M):
                for a in range(j):
                    Qa = Q[a]
                    Qj = Q[j]
                    acc = 0
                    for prev in range(a):
                        c = dp_prev[prev][a]
                        if c > 0 and _orientation(Q[prev], Qa, Qj) > 0:
                            acc += c
                    if acc:
                        dp_len[a][j] += acc

        dp_k = dp[k]
        for j in range(M):
            for a in range(j):
                c = dp_k[a][j]
                if c > 0 and _orientation(Q[a], Q[j], pivot) > 0:
                    total += c

    return total


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
            points = program.erdos_szekeres_problem7()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(points, np.ndarray):
            points = np.array(points)
        points = points.astype(np.float64)

        if points.shape != (NUM_POINTS, 2):
            raise ValueError(
                f"Invalid shape: points = {points.shape}, expected {(NUM_POINTS, 2)}"
            )

        if not np.all(np.isfinite(points)):
            raise ValueError("Points contain NaN or infinite values.")

        # Feasibility: points must lie within the unit square.
        if np.any(points < -BOUNDS_TOL) or np.any(points > 1.0 + BOUNDS_TOL):
            raise ValueError("Points must lie inside the unit square [0, 1] x [0, 1].")

        # Feasibility: no two points may coincide (or be numerically too close).
        for p1, p2 in itertools.combinations(points, 2):
            d = p1 - p2
            if float(d[0] * d[0] + d[1] * d[1]) < MIN_DIST_SQ:
                raise ValueError("Two points are coincident or numerically too close.")

        # Feasibility: general position (no three collinear) within tolerance.
        for p1, p2, p3 in itertools.combinations(points, 3):
            area = (
                p1[0] * (p2[1] - p3[1])
                + p2[0] * (p3[1] - p1[1])
                + p3[0] * (p1[1] - p2[1])
            )
            if abs(float(area)) < COLLINEAR_TOL:
                raise ValueError("Three points are collinear; not in general position.")

        num_convex_kgons = _count_convex_kgons(points, K)

        combined_score = 1.0 / (1.0 + float(num_convex_kgons - BENCHMARK))
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "num_convex_kgons": float(num_convex_kgons),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
