# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the finite-field Kakeya problem in F_p^2
# with p = 7.
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

BENCHMARK = 28
P = 7


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        entries = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            entries = program.kakeya_set()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        entries = np.asarray(entries).astype(int).reshape(-1) % P

        if entries.shape != (P + 1,):
            raise ValueError(
                f"Invalid shape: entries = {entries.shape}, expected {(P + 1,)}"
            )

        points = set()
        for m in range(P):
            for x in range(P):
                points.add((x, (m * x + entries[m]) % P))
        for y in range(P):
            points.add((entries[P] % P, y))

        kakeya_size = len(points)
        if kakeya_size <= 0:
            return {
                "kakeya_size": int(kakeya_size),
                "combined_score": 0.0,
                "eval_time": float(eval_time),
            }

        return {
            "kakeya_size": int(kakeya_size),
            "combined_score": float(BENCHMARK / kakeya_size),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
