# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the Arithmetic Kakeya conjecture (entropy
# formulation): maximize the entropy projection ratio of a joint distribution on a grid.
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

# No known optimal/record constant is given in the upstream notebook for these slopes, so
# BENCHMARK is the score of the baseline (uniform) construction; combined_score therefore
# starts near 1.0 and evolution pushes the entropy ratio higher.
BENCHMARK = 0.8648337767671102
TOL = 1e-9
N = 10
SLOPES = (0.0, 1.0, 2.0)  # finite slopes r_1, ..., r_k
R_INF = -1.0  # distinguished slope r_inf


def _projection_entropy(P: np.ndarray, r: float) -> float:
    """Shannon entropy (bits) of the distribution of pi_r(x, y) = x + r * y under P[y, x]."""
    ny, nx = P.shape
    proj_probs = {}
    for y in range(ny):
        for x in range(nx):
            val = x + r * y
            proj_probs[val] = proj_probs.get(val, 0.0) + P[y, x]
    p = np.array(list(proj_probs.values()), dtype=np.float64)
    p = p[p > 0.0]
    return float(-np.sum(p * np.log2(p)))


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        P = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            P = program.arithmetic_kakeya_distribution()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(P, np.ndarray):
            P = np.array(P)
        P = P.astype(np.float64)

        if P.shape != (N, N):
            raise ValueError(f"Invalid shape: P = {P.shape}, expected {(N, N)}")

        if not np.all(np.isfinite(P)):
            raise ValueError("Distribution contains NaN or infinite values.")

        if np.any(P < -TOL):
            raise ValueError("Distribution contains negative probabilities; infeasible.")

        P = np.clip(P, 0.0, None)
        total = float(P.sum())
        if total <= TOL:
            raise ValueError("Distribution has non-positive total mass; cannot normalize.")
        P = P / total

        H_inf = _projection_entropy(P, R_INF)
        max_H_i = max(_projection_entropy(P, r) for r in SLOPES)
        if max_H_i <= TOL:
            raise ValueError("All finite-slope projections are degenerate (zero entropy).")

        entropy_ratio = H_inf / max_H_i

        combined_score = entropy_ratio / BENCHMARK
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "entropy_ratio": float(entropy_ratio),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
