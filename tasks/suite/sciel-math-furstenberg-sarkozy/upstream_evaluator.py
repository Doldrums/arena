# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the Furstenberg-Sarkozy problem in the modular
# setting Z/mZ, with m = 205 and k = 2 (squares).
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
# Note on the benchmark and definition:
#   * The objective is to find a subset of Z/mZ of maximum size with no two elements
#     differing by a nonzero perfect k-th power modulo m. This is a MAXIMIZATION problem,
#     so combined_score = subset_size / BENCHMARK (higher is better; ~1.0 matches the
#     AlphaEvolve record).
#   * BENCHMARK = 12 is the AlphaEvolve record size for (m=205, k=2), taken from the
#     notebook's `get_optimal_sarkozy_subset(205, 2)`. The notebook ALSO hard-codes the
#     actual subset constant, but that constant fails its own `check_sarkozy_subset`
#     validity test (an upstream transcription bug), so we do not reproduce it; we keep
#     the record SIZE as the target and validate feasibility ourselves with the exact
#     same modular k-th-power-residue rule the notebook's checker uses.

import time
import numpy as np
import sys
import os
from importlib import __import__

BENCHMARK = 12  # AlphaEvolve record size for (m=205, k=2), per the upstream notebook.
M = 205
K = 2


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
            subset = program.furstenberg_sarkozy_205()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(subset, np.ndarray):
            subset = np.array(subset)

        subset = np.asarray(subset).ravel()

        if subset.size == 0:
            raise ValueError("Empty subset returned.")

        if not np.all(np.isfinite(subset)):
            raise ValueError("Subset contains NaN or infinite values.")

        # Must be integer-valued residues.
        rounded = np.rint(subset)
        if not np.allclose(subset, rounded, atol=1e-9):
            raise ValueError("Subset contains non-integer values.")
        elements = rounded.astype(np.int64)

        if np.any(elements < 0) or np.any(elements >= M):
            raise ValueError(f"Subset elements must lie in [0, {M - 1}].")

        if np.unique(elements).size != elements.size:
            raise ValueError("Subset contains duplicate elements.")

        # Forbidden differences: the nonzero k-th power residues modulo M.
        forbidden = set(pow(x, K, M) for x in range(1, M))
        forbidden.discard(0)

        elems = elements.tolist()
        n = len(elems)
        for i in range(n):
            for j in range(i + 1, n):
                d1 = (elems[i] - elems[j]) % M
                d2 = (elems[j] - elems[i]) % M
                if d1 in forbidden or d2 in forbidden:
                    raise ValueError(
                        f"Infeasible: elements {elems[i]} and {elems[j]} differ by a "
                        f"perfect {K}-th power modulo {M}."
                    )

        subset_size = int(n)
        combined_score = subset_size / BENCHMARK
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "subset_size": float(subset_size),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
