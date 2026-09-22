# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for Sendov's conjecture: a complex polynomial of
# degree n with all roots in the unit disk, scored by the largest distance from any root
# to the nearest critical point (probing the Sendov bound C(n) = 1).
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

# Sendov conjectured C(n) = 1 for every n >= 2; the n-th roots of unity attain exactly 1
# (their only critical point is the origin, at distance 1 from each root). We therefore use
# the conjectured optimal constant as the benchmark.
BENCHMARK = 1.0
TOL = 1e-6
NUM_ROOTS = 6


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        roots = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            roots = program.sendov_polynomial6()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(roots, np.ndarray):
            roots = np.array(roots)
        roots = roots.astype(np.complex128).reshape(-1)

        if roots.shape != (NUM_ROOTS,):
            raise ValueError(f"Invalid shape: roots = {roots.shape}, expected {(NUM_ROOTS,)}")

        if not np.all(np.isfinite(roots)):
            raise ValueError("Roots contain NaN or infinite values.")

        # Feasibility: every root must lie inside the closed unit disk.
        if np.any(np.abs(roots) > 1.0 + TOL):
            raise ValueError("At least one root lies outside the unit disk (|z| > 1).")

        # Build the monic polynomial with these roots and its derivative (pure numpy).
        poly = np.poly(roots)
        poly_der = np.polyder(poly)
        crit_points = np.roots(poly_der)

        if crit_points.size == 0:
            raise ValueError("Polynomial has no critical points.")
        if not np.all(np.isfinite(crit_points)):
            raise ValueError("Critical points contain NaN or infinite values.")

        # Sendov distance: maximize over roots the distance to the nearest critical point.
        diffs = np.abs(roots[:, None] - crit_points[None, :])
        sendov_distance = float(np.max(np.min(diffs, axis=1)))

        combined_score = sendov_distance / BENCHMARK
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "sendov_distance": float(sendov_distance),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
