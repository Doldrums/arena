# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the Erdos discrepancy problem: building the
# longest +/-1 sign pattern whose discrepancy over homogeneous progressions is at most 2.
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
# NOTE ON REPRESENTATION: unlike the fixed-size templates (e.g. Tammes), the quantity being
# maximized here is the LENGTH of the pattern itself, so the constructor returns a 1-D array
# of variable length. The evaluator therefore validates the +/-1 entries and the discrepancy
# constraint rather than a fixed shape, and uses the pattern length as the primary metric.

import time
import numpy as np
import sys
import os
from importlib import __import__

# Known record for discrepancy <= 2: the largest N for which a +/-1 pattern of discrepancy
# at most 2 exists is 1160 (Konev & Lisitsa, 2014; 1161 was proven impossible via SAT).
BENCHMARK = 1160
DISCREPANCY_LIMIT = 2


def compute_discrepancy(pattern: np.ndarray) -> int:
    """Maximum |a_d + a_2d + ... + a_kd| over all homogeneous progressions in the pattern."""
    n = pattern.shape[0]
    max_disc = 0
    for d in range(1, n + 1):
        partial = np.cumsum(pattern[d - 1 :: d])
        if partial.size:
            max_disc = max(max_disc, int(np.max(np.abs(partial))))
    return max_disc


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        pattern = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            pattern = program.erdos_discrepancy_pattern()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(pattern, np.ndarray):
            pattern = np.array(pattern)
        pattern = np.asarray(pattern).reshape(-1)

        if pattern.ndim != 1 or pattern.size == 0:
            raise ValueError(f"Invalid pattern: expected a non-empty 1-D array, got shape {pattern.shape}")

        if not np.all(np.isfinite(pattern)):
            raise ValueError("Pattern contains NaN or infinite values.")

        if not np.all(np.isin(pattern, (-1, 1))):
            raise ValueError("Pattern must contain only the values -1 and +1.")

        pattern = pattern.astype(np.int64)

        length = int(pattern.shape[0])
        discrepancy = compute_discrepancy(pattern)

        if discrepancy > DISCREPANCY_LIMIT:
            raise ValueError(
                f"Infeasible: discrepancy {discrepancy} exceeds the limit of {DISCREPANCY_LIMIT}."
            )

        combined_score = length / BENCHMARK
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "length": float(length),
            "discrepancy": float(discrepancy),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
