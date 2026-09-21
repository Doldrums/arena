# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the Erdos "squares in a square" problem:
# pack n squares with disjoint interiors into the unit square so as to maximize the
# sum of their side lengths. Here n = 10.
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

# Known optimal sum of side lengths for n = 10: C(10) = 3 + 1/6 = 19/6 ~= 3.16667
# (from the upstream notebook's verified optimal construction).
BENCHMARK = 19.0 / 6.0
TOL = 1e-7
NUM_SQUARES = 10


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        result = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            result = program.squares_in_square10()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(result, (tuple, list)) or len(result) != 2:
            raise ValueError("Constructor must return a (centers, sides) pair.")

        centers, sides = result
        if not isinstance(centers, np.ndarray):
            centers = np.array(centers)
        if not isinstance(sides, np.ndarray):
            sides = np.array(sides)
        centers = centers.astype(np.float64)
        sides = sides.astype(np.float64)

        if centers.shape != (NUM_SQUARES, 2):
            raise ValueError(
                f"Invalid shape: centers = {centers.shape}, expected {(NUM_SQUARES, 2)}"
            )
        if sides.shape != (NUM_SQUARES,):
            raise ValueError(
                f"Invalid shape: sides = {sides.shape}, expected {(NUM_SQUARES,)}"
            )

        if not np.all(np.isfinite(centers)) or not np.all(np.isfinite(sides)):
            raise ValueError("Centers or sides contain NaN or infinite values.")

        if np.any(sides <= 0.0):
            raise ValueError("All side lengths must be strictly positive.")

        # Boundary constraint: every square must lie inside the unit square.
        half = sides / 2.0
        lo = centers - half[:, None]
        hi = centers + half[:, None]
        if np.any(lo < -TOL) or np.any(hi > 1.0 + TOL):
            raise ValueError("A square extends outside the unit square.")

        # Disjoint-interiors constraint: two axis-aligned squares overlap iff their
        # interiors overlap on BOTH axes. Touching (equality) is allowed.
        for i, j in itertools.combinations(range(NUM_SQUARES), 2):
            dx = abs(centers[i, 0] - centers[j, 0])
            dy = abs(centers[i, 1] - centers[j, 1])
            thresh = (sides[i] + sides[j]) / 2.0 - TOL
            if dx < thresh and dy < thresh:
                raise ValueError(f"Squares {i} and {j} have overlapping interiors.")

        sum_sides = float(np.sum(sides))

        combined_score = sum_sides / BENCHMARK
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "sum_sides": float(sum_sides),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
