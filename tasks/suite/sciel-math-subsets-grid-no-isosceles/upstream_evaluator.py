# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the "subsets of the 7x7 grid with no
# isosceles triangles" problem.
#
# ===--------------------------------------------------------------------------------------===#

import time
import numpy as np
import sys
import os
from importlib import __import__
import itertools

BENCHMARK = 8
GRID_MAX = 6


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
            points = program.grid_subset()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(points, np.ndarray):
            points = np.array(points)
        points = points.astype(int)

        if points.ndim != 2 or points.shape[1] != 2:
            return {
                "subset_size": 0,
                "combined_score": 0.0,
                "eval_time": float(eval_time),
                "error": f"Invalid shape: {points.shape}, expected (k,2)",
            }

        k = int(points.shape[0])

        # Validate coordinate range.
        if k > 0 and (points.min() < 0 or points.max() > GRID_MAX):
            return {
                "subset_size": k,
                "combined_score": 0.0,
                "eval_time": float(eval_time),
                "error": "Point out of range [0,6]",
            }

        # Validate all points distinct.
        unique_points = {tuple(p) for p in points}
        if len(unique_points) != k:
            return {
                "subset_size": k,
                "combined_score": 0.0,
                "eval_time": float(eval_time),
                "error": "Duplicate point",
            }

        # Reject any isosceles triple (at least two equal pairwise squared distances).
        for a, b, c in itertools.combinations(points, 3):
            d_ab = int((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
            d_bc = int((b[0] - c[0]) ** 2 + (b[1] - c[1]) ** 2)
            d_ca = int((c[0] - a[0]) ** 2 + (c[1] - a[1]) ** 2)
            if d_ab == d_bc or d_bc == d_ca or d_ca == d_ab:
                return {
                    "subset_size": k,
                    "combined_score": 0.0,
                    "eval_time": float(eval_time),
                    "error": "Isosceles triple exists",
                }

        return {
            "subset_size": k,
            "combined_score": float(k / BENCHMARK),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
