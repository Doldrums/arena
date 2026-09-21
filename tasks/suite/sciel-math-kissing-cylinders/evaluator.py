# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the kissing cylinders problem: arranging 7
# mutually tangent infinite unit-radius cylinders in R^3.
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

# The raw objective minimizes the total squared tangency error
#   E = sum_{i<j} (dist(axis_i, axis_j) - TARGET_DIST)^2
# over all pairs of cylinders. A perfect arrangement of mutually tangent cylinders has
# E = 0, so the known optimal / record value of E for n = 7 is 0 (perfect tangency).
# Because the record is exactly 0, the template's "primary / BENCHMARK" division is not
# usable directly; we convert the minimization to a higher-is-better, bounded score:
#   combined_score = 1 / (1 + E)
# which equals 1.0 at the record (E = 0) and decreases monotonically as the arrangement
# deviates from mutual tangency.
BENCHMARK = 0.0  # optimal total squared tangency error for 7 mutually tangent unit cylinders
TARGET_DIST = 2.0  # axis-to-axis distance for two tangent unit-radius cylinders
TOL = 1e-6
NUM_CYLINDERS = 7
CONTACT_BOX_LIMIT = 100.0  # contact midpoints must lie within [-LIMIT, LIMIT]^3


def _distance_between_axes(p1, v1, p2, v2):
    """Shortest distance between two axis lines L1 = p1 + t*v1 and L2 = p2 + s*v2."""
    p1p2 = p2 - p1
    cross = np.cross(v1, v2)
    n = np.linalg.norm(cross)
    if n < 1e-9:  # parallel axes
        return float(np.linalg.norm(np.cross(p1p2, v1)))
    return float(np.abs(np.dot(p1p2, cross)) / n)


def _closest_approach_midpoint(p1, v1, p2, v2):
    """Midpoint of the segment of closest approach between the two axis lines."""
    dp = p1 - p2
    v1_dot_v2 = float(np.dot(v1, v2))
    if np.abs(np.abs(v1_dot_v2) - 1.0) < 1e-7:  # parallel
        mid = (p1 + p2) / 2.0
        return mid - np.dot(mid, v1) * v1
    dp_dot_v1 = float(np.dot(dp, v1))
    dp_dot_v2 = float(np.dot(dp, v2))
    denom = 1.0 - v1_dot_v2 * v1_dot_v2
    t_c = (v1_dot_v2 * (-dp_dot_v2) - (-dp_dot_v1)) / denom
    s_c = ((-dp_dot_v2) - v1_dot_v2 * (-dp_dot_v1)) / denom
    c1 = p1 + t_c * v1
    c2 = p2 + s_c * v2
    return (c1 + c2) / 2.0


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        cylinders = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            cylinders = program.kissing_cylinders7()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(cylinders, np.ndarray):
            cylinders = np.array(cylinders)
        cylinders = cylinders.astype(np.float64)

        if cylinders.shape != (NUM_CYLINDERS, 2, 3):
            raise ValueError(
                f"Invalid shape: cylinders = {cylinders.shape}, expected {(NUM_CYLINDERS, 2, 3)}"
            )

        if not np.all(np.isfinite(cylinders)):
            raise ValueError("Cylinder parameters contain NaN or infinite values.")

        P = cylinders[:, 0, :]
        V = cylinders[:, 1, :]

        # Direction vectors must be non-degenerate; normalize to unit length.
        norms = np.linalg.norm(V, axis=1)
        if np.any(norms < TOL):
            raise ValueError("Encountered a zero-length direction vector.")
        V = V / norms[:, None]

        # Standardize each axis point so that P . v = 0 (closest point to the origin).
        P = P - np.sum(P * V, axis=1, keepdims=True) * V

        # Feasibility: all pairwise contact midpoints must lie inside the bounding box.
        for i, j in itertools.combinations(range(NUM_CYLINDERS), 2):
            mid = _closest_approach_midpoint(P[i], V[i], P[j], V[j])
            if np.any(np.abs(mid) > CONTACT_BOX_LIMIT):
                raise ValueError("Contact midpoint outside the allowed bounding box.")

        # Total squared tangency error over all pairs (the raw minimization objective).
        tangency_error = 0.0
        for i, j in itertools.combinations(range(NUM_CYLINDERS), 2):
            d = _distance_between_axes(P[i], V[i], P[j], V[j])
            tangency_error += (d - TARGET_DIST) ** 2
        tangency_error = float(tangency_error)

        combined_score = 1.0 / (1.0 + tangency_error)
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "tangency_error": float(tangency_error),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
