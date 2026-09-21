# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the finite-field sum-product problem over F_31.
#
# ===--------------------------------------------------------------------------------------===#

import time
import numpy as np
import sys
import os
from importlib import __import__

BENCHMARK = 45
P = 31


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        elements = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            elements = program.sum_product_set()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(elements, np.ndarray):
            elements = np.array(elements)

        A = np.unique(np.asarray(elements, dtype=np.int64).ravel() % P)

        if len(A) < 2:
            raise ValueError(f"Need at least 2 distinct elements, got {len(A)}")

        sumset = set(int((a + b) % P) for a in A for b in A)
        prodset = set(int((a * b) % P) for a in A for b in A)
        total = len(sumset) + len(prodset)

        if total <= 0:
            return {"combined_score": 0.0, "error": "non-positive total"}

        return {
            "sum_product_size": int(total),
            "combined_score": float(BENCHMARK / total),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
