# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the Thomson problem, with 12 points.
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

BENCHMARK = 49.165253058
TOL = 1e-6
NUM_POINTS = 12


def coulomb_energy(points: np.ndarray) -> float:
    """Computes E = sum over i<j of 1 / ||x_i - x_j|| for points on the unit sphere."""
    energy = 0.0
    for p1, p2 in itertools.combinations(points, 2):
        energy += 1.0 / np.linalg.norm(p1 - p2)
    return energy


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
            points = program.thomson_problem12()
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
        if np.any(norms <= 0):
            raise ValueError("Each point must have a nonzero norm to project onto the unit sphere.")
        points = points / norms[:, None]

        energy = coulomb_energy(points)

        if energy <= 0 or not np.isfinite(energy):
            combined_score = 0.0
        else:
            combined_score = BENCHMARK / energy

        return {
            "energy": float(energy),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
