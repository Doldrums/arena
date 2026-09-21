# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the difference bases problem (Sidon set / B_2 set),
# in the range [0, 60].
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

BENCHMARK = 8
MIN_VAL = 0
MAX_VAL = 60


def is_sidon(values: np.ndarray) -> bool:
    """Checks that all pairwise differences |a_i - a_j| (i < j) are distinct.

    Args:
        values: 1-D array of distinct non-negative integers.
    """
    diffs = [abs(int(a) - int(b)) for a, b in itertools.combinations(values, 2)]
    return len(diffs) == len(set(diffs))


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        basis = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            basis = program.difference_basis()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(basis, np.ndarray):
            basis = np.array(basis)

        values = np.unique(basis.astype(np.int64))
        set_size = int(values.size)

        if np.any(values < MIN_VAL) or np.any(values > MAX_VAL):
            return {
                "set_size": set_size,
                "combined_score": 0.0,
                "error": "not a Sidon set",
            }

        if not is_sidon(values):
            return {
                "set_size": set_size,
                "combined_score": 0.0,
                "error": "not a Sidon set",
            }

        return {
            "set_size": set_size,
            "combined_score": float(set_size / BENCHMARK),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
