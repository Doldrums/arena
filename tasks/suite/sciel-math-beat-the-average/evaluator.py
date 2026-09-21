# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the "beat the average" game: maximizing
# P[X1 + X2 + X3 < 2*X4] over discrete probability measures on [0, inf), to lower-bound
# the constant C = sup_mu P[X1 + X2 + X3 < 2*X4].
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

# State-of-the-art lower bound reported in the upstream notebook's AlphaEvolve search
# configuration ("the state of the art score of 0.4006").
BENCHMARK = 0.4006
TOL = 1e-9


def _success_probability(support: np.ndarray, weights: np.ndarray) -> float:
    """
    Exact (no Monte Carlo) value of P[X1 + X2 + X3 < 2*X4] for the discrete measure
    given by (support, weights), where X1..X4 are i.i.d.

    Computed via the distribution of the pairwise sum X1 + X2 followed by an exact
    threshold count against 2*X4 - X3. Complexity O(n^2 log n) in the support size n.
    """
    s = np.asarray(support, dtype=np.float64)
    w = np.asarray(weights, dtype=np.float64)
    w = w / w.sum()

    # Distribution of X1 + X2: values P2 with weights W2.
    P2 = (s[:, None] + s[None, :]).ravel()
    W2 = (w[:, None] * w[None, :]).ravel()
    order = np.argsort(P2, kind="stable")
    P2s = P2[order]
    W2s = W2[order]
    # prefix[i] = mass of pairwise sums strictly before sorted index i.
    prefix = np.concatenate([[0.0], np.cumsum(W2s)])

    total = 0.0
    for k in range(len(s)):
        # For X3 = s[k], over all X4 = s[l]: need P[X1+X2 < 2*s[l] - s[k]].
        thresholds = 2.0 * s - s[k]
        idx = np.searchsorted(P2s, thresholds, side="left")  # strict "<"
        mass = prefix[idx]  # mass of X1+X2 strictly below each threshold
        total += w[k] * float(np.sum(w * mass))
    return total


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        result = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            result = program.beat_the_average_measure()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(result, (tuple, list)) or len(result) != 2:
            raise ValueError("Constructor must return a (support, weights) pair.")

        support, weights = result
        support = np.asarray(support, dtype=np.float64).ravel()
        weights = np.asarray(weights, dtype=np.float64).ravel()

        if support.shape != weights.shape:
            raise ValueError(
                f"support and weights must have the same shape: {support.shape} vs {weights.shape}"
            )
        if support.size < 1:
            raise ValueError("Measure must have at least one support point.")
        if not np.all(np.isfinite(support)) or not np.all(np.isfinite(weights)):
            raise ValueError("support/weights contain NaN or infinite values.")
        if np.any(support < -TOL):
            raise ValueError("Support points must lie in [0, inf).")
        if np.any(weights < -TOL):
            raise ValueError("Weights must be non-negative.")

        weight_sum = float(np.sum(weights))
        if weight_sum <= TOL:
            raise ValueError("Total weight must be positive.")

        success_prob = _success_probability(support, weights)

        combined_score = success_prob / BENCHMARK
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "success_prob": float(success_prob),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
