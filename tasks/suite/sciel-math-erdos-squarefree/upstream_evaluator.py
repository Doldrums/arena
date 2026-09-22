# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the Erdos squarefree problem on {1, ..., 500}:
# find a maximum subset A such that a*b + 1 is not square-free for all a, b in A.
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

# Record density achieved by the 7 (mod 25) residue-class construction for N = 500:
# 20 elements, zero square-free violations, so score = 20/500 - 0 = 0.04.
# Source: AlphaEvolve evolved construction in the upstream erdos_squarefree notebook.
BENCHMARK = 0.04
N = 500


def _squarefree_sieve(limit: int) -> np.ndarray:
    """Boolean array sf where sf[k] is True iff k is square-free, for k in [0, limit]."""
    sf = np.ones(limit + 1, dtype=bool)
    sf[0] = False  # 0 is divisible by every square; treat as not square-free.
    i = 2
    while i * i <= limit:
        sq = i * i
        sf[sq::sq] = False
        i += 1
    return sf


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        subset = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            subset = program.erdos_squarefree500()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(subset, np.ndarray):
            subset = np.array(subset)
        subset = np.asarray(subset).reshape(-1)

        if subset.size == 0:
            raise ValueError("Subset is empty.")

        if not np.all(np.isfinite(subset)):
            raise ValueError("Subset contains NaN or infinite values.")

        # Must be integers in {1, ..., N}.
        if not np.allclose(subset, np.round(subset)):
            raise ValueError("Subset must contain integer values.")
        subset = np.round(subset).astype(np.int64)

        if np.any(subset < 1) or np.any(subset > N):
            raise ValueError(f"Subset elements must lie in {{1, ..., {N}}}.")

        # A subset has distinct elements.
        if np.unique(subset).size != subset.size:
            raise ValueError("Subset contains duplicate elements.")

        # Precompute square-free status for every possible product a*b + 1.
        sf = _squarefree_sieve(N * N + 1)

        # Vectorized violation count: pairs (i < j) whose product + 1 is square-free.
        products = np.outer(subset, subset) + 1  # (m, m)
        is_sf = sf[products]  # True where square-free => a violation
        violations = int(np.sum(np.triu(is_sf, k=1)))

        density = subset.size / N
        subset_score = density - violations

        combined_score = subset_score / BENCHMARK
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "subset_score": float(subset_score),
            "subset_size": int(subset.size),
            "violations": int(violations),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
