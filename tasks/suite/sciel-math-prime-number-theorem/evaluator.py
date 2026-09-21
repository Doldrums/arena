# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the Prime Number Theorem partial-function problem:
# construct a partial function f from a subset of the positive integers to the reals that
# maximizes a hidden number-theoretic objective.
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

# The stated optimal score of the hidden objective is 1.0 (approached by the Mobius
# function, for which the Prime Number Theorem gives -sum mu(k) log(k)/k -> 1).
BENCHMARK = 1.0
CLIP = 10.0  # all function values are clipped to [-CLIP, CLIP] during evaluation
FEAS_TOL = 1.0001  # the constraint M(x) <= 1 is checked with this slack (as upstream)
MAX_KEY = 200_000  # guard so the deterministic constraint sweep stays bounded


def _evaluate_partial_function(domain: np.ndarray, values: np.ndarray) -> float:
    """Exact (deterministic) replica of the hidden evaluate_partial_function.

    Upstream samples x ~ U(1, 10*max_key) by Monte-Carlo and rejects (score = -inf) if
    any sampled x_sum = sum_k f(k)*floor(x/k) exceeds 1.0001. Because that quantity is a
    step function that is constant on [n, n+1) for integer n, its supremum over the real
    interval [1, 10*max_key] is attained at an integer. We therefore check every integer
    x in [1, 10*max_key] -> this is deterministic and is the exact feasibility test that
    the upstream Monte-Carlo sampling approximates.

    Returns the objective a = -sum_k f(k) log(k)/k, or -inf if infeasible.
    """
    # Clip values to [-CLIP, CLIP], mirroring the hidden evaluator.
    values = np.clip(values.astype(np.float64), -CLIP, CLIP)
    keys = domain.astype(np.int64)

    # Adjust f(1) so that sum_k f(k)/k == 0 (upstream subtracts the running total from
    # f(1), creating the entry for key 1 if it does not exist).
    fmap = {int(k): float(v) for k, v in zip(keys, values)}
    total = float(np.sum(values / keys))
    fmap[1] = fmap.get(1, 0.0) - total

    keys = np.array(sorted(fmap.keys()), dtype=np.int64)
    values = np.array([fmap[int(k)] for k in keys], dtype=np.float64)

    max_key = int(keys.max())
    upper = 10 * max_key
    if upper > 10 * MAX_KEY:
        raise ValueError(f"max key {max_key} exceeds bound {MAX_KEY}; constraint sweep too large")

    # M(x) = sum_k f(k) * floor(x/k), evaluated at every integer x in [1, upper].
    x = np.arange(1, upper + 1, dtype=np.int64)
    m_x = np.zeros(upper, dtype=np.float64)
    for k, v in zip(keys, values):
        m_x += v * (x // k)

    if np.any(m_x > FEAS_TOL):
        return float("-inf")  # infeasible construction

    # log(1) == 0, so the (adjusted) key-1 term never contributes to the objective.
    a_value = -float(np.sum(values * np.log(keys) / keys))
    return a_value


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
            result = program.prime_number_theorem_partial_function()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        # The constructor returns (domain, values).
        domain, values = result
        domain = np.asarray(domain)
        values = np.asarray(values)

        if domain.ndim != 1 or values.ndim != 1:
            raise ValueError(f"domain/values must be 1-D, got {domain.shape}, {values.shape}")
        if domain.shape != values.shape:
            raise ValueError(f"length mismatch: domain {domain.shape} vs values {values.shape}")
        if domain.size == 0:
            raise ValueError("empty partial function")
        if not np.all(np.isfinite(values)):
            raise ValueError("values contain NaN or infinite entries")

        # Domain must be distinct positive integers.
        if not np.all(np.isfinite(domain)):
            raise ValueError("domain contains NaN or infinite entries")
        domain_int = np.round(domain).astype(np.int64)
        if not np.all(domain_int == domain):
            raise ValueError("domain entries must be integers")
        if np.any(domain_int < 1):
            raise ValueError("domain entries must be positive integers")
        if np.unique(domain_int).size != domain_int.size:
            raise ValueError("domain entries must be distinct")

        score = _evaluate_partial_function(domain_int, values)

        combined_score = score / BENCHMARK
        if not np.isfinite(combined_score):
            combined_score = 0.0  # infeasible / non-finite -> zero (never reward infeasible)

        return {
            "pnt_score": float(score) if np.isfinite(score) else 0.0,
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
