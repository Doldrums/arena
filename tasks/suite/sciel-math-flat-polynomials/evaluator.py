# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the flat polynomials problem (low-autocorrelation
# binary sequences), maximizing the Littlewood merit factor for a sequence of length 41.
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

BENCHMARK = 6.0
SEQ_LENGTH = 41
DENOM_CAP = 1e6


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        x = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            x = program.flat_polynomial()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        x = np.asarray(x, dtype=float)

        if x.shape != (SEQ_LENGTH,):
            raise ValueError(f"Invalid shape: x = {x.shape}, expected {(SEQ_LENGTH,)}")

        if not np.all(np.isfinite(x)):
            raise ValueError("Sequence contains NaN or infinite values.")

        # Coerce any sign pattern to +/-1.
        a = np.where(x >= 0, 1.0, -1.0)

        n = SEQ_LENGTH
        denom_sum = 0.0
        for k in range(1, n):
            c_k = np.sum(a[: n - k] * a[k:])
            denom_sum += c_k * c_k

        if denom_sum == 0.0:
            merit_factor = DENOM_CAP
        else:
            merit_factor = (n * n) / (2.0 * denom_sum)

        if not np.isfinite(merit_factor):
            combined_score = 0.0
        else:
            combined_score = merit_factor / BENCHMARK

        return {
            "merit_factor": float(merit_factor),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
