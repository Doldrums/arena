# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the Tammes problem on the unit sphere, with
# 13 points.
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

BENCHMARK = 0.9557
TOL = 1e-6
NUM_POINTS = 13


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        points = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            points = program.tammes_problem13()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(points, np.ndarray):
            points = np.array(points)

        if points.shape != (NUM_POINTS, 3):
            raise ValueError(f"Invalid shapes: points = {points.shape}, expected {(NUM_POINTS,3)}")

        if not np.all(np.isfinite(points)):
            raise ValueError("Points contain NaN or infinite values.")

        norms = np.linalg.norm(points, axis=1)
        if np.any(norms < TOL):
            raise ValueError("Encountered a zero-norm row; cannot project onto the unit sphere.")
        points = points / norms[:, None]

        min_distance = min(
            float(np.linalg.norm(p1 - p2)) for p1, p2 in itertools.combinations(points, 2)
        )

        combined_score = min_distance / BENCHMARK
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "min_distance": float(min_distance),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
