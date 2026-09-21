# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the block-stacking (single-wide overhang)
# problem with 30 blocks.
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

# Known optimum for n blocks: C(n) = (1/2) * H_n, the n-th harmonic number.
# For n = 30, H_30 = 3.9949871309203906, so C(30) = 1.9974935654601953.
BENCHMARK = 1.9974935654601953
NUM_BLOCKS = 30
FLOAT_TOLERANCE = sys.float_info.epsilon * 100


def get_positions_score(positions) -> float:
    """Returns the top block's overhang for a stable stack, or -1.0 if unstable.

    Mirrors the upstream AlphaEvolve scorer. positions[k] is block k's center; the
    block occupies [positions[k] - 0.5, positions[k] + 0.5]. Stability requires (a) the
    center of mass of the whole stack to lie over the table (edge at x = 0) and (b) for
    every block, the center of mass of the blocks resting on top of it to lie within
    that block's footprint.
    """
    n = len(positions)
    if n == 0:
        return 0.0

    if n == 1:
        if positions[0] - 0.5 >= 0.0 - FLOAT_TOLERANCE:
            return -1.0
        return float(positions[0])

    sum_all = 0.0
    for k in range(n):
        sum_all += positions[k] - 0.5
    sum_all_avg = sum_all / n
    if sum_all_avg >= 0.0 - FLOAT_TOLERANCE:
        return -1.0

    upper_sum = positions[n - 1] - 0.5
    upper_count = 1.0

    for i in range(n - 2, -1, -1):
        upper_sum_avg = upper_sum / upper_count
        lb = positions[i] - 1.0
        ub = positions[i]
        if not (lb - FLOAT_TOLERANCE <= upper_sum_avg <= ub + FLOAT_TOLERANCE):
            return -1.0
        upper_sum += positions[i] - 0.5
        upper_count += 1.0

    return float(positions[-1])


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        positions = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            positions = program.block_stacking30()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(positions, np.ndarray):
            positions = np.array(positions, dtype=np.float64)
        positions = positions.astype(np.float64).reshape(-1)

        if positions.shape != (NUM_BLOCKS,):
            raise ValueError(
                f"Invalid shape: positions = {positions.shape}, expected {(NUM_BLOCKS,)}"
            )

        if not np.all(np.isfinite(positions)):
            raise ValueError("Positions contain NaN or infinite values.")

        overhang = get_positions_score(positions)

        # An unstable / infeasible stack scores -1.0 from the scorer; never reward it.
        if overhang < 0.0:
            return {
                "overhang": 0.0,
                "combined_score": 0.0,
                "eval_time": float(eval_time),
            }

        combined_score = overhang / BENCHMARK
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "overhang": float(overhang),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
