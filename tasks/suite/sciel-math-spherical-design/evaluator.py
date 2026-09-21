# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the spherical 2-design problem, with
# 12 points on the unit sphere S^2.
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

NUM_POINTS = 12


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
            points = program.spherical_design()
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
            raise ValueError("Points contain NaN or inf values.")

        norms = np.linalg.norm(points, axis=1)
        if np.any(norms == 0):
            raise ValueError("At least one point has zero norm and cannot be normalized.")

        X = points / norms[:, None]

        m = X.mean(axis=0)
        term1 = float(m @ m)
        M = (3.0 / NUM_POINTS) * (X.T @ X)
        term2 = float(np.sum((M - np.eye(3)) ** 2))
        defect = term1 + term2

        combined_score = 1.0 / (1.0 + defect)
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "defect": float(defect),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
