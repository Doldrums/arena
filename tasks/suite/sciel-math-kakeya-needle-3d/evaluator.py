# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the three-dimensional Kakeya needle problem
# with grid parameter N = 8 (64 generalized tubes).
#
# ===--------------------------------------------------------------------------------------===#
#
# Some of the code in this file is adapted from:
#
# google-deepmind/alphaevolve_results:
# Licensed under the Apache License v2.0.
#
# ===--------------------------------------------------------------------------------------===#
#
# OBJECTIVE (faithful to the upstream notebook kakeya_needle_3d.ipynb):
#   Build N*N tubes indexed by (i, j). Tube (i, j) with base (x, y) occupies, at
#   height c in [0, 1], the square [x + c*i/N, x + 1/N + c*i/N] x [y + c*j/N, y + 1/N + c*j/N].
#   Minimize the VOLUME of the union of all tubes (a discrete Kakeya/Besicovitch set).
#   The upstream get_score() estimates this union measure by Monte Carlo; we do the same
#   in pure numpy over an enclosing bounding box, so "union_volume" is the true union
#   measure (lower is better).
#
#   This is a MINIMIZATION, converted to higher-is-better via
#       combined_score = BENCHMARK / union_volume   (~1.0 means matching the record).
#
# BENCHMARK: 0.133310 is the union volume of the best construction found by AlphaEvolve
#   for N = 8 (notebook cell "Constructions found by AlphaEvolve", arrays X_RAND / Y_RAND),
#   measured under the exact Monte Carlo settings (NUM_MC_POINTS, MC_SEED) used below.
#   The notebook publishes no closed-form 3-D record constant, so the record construction's
#   own measured volume is used as the benchmark. The Keich product baseline shipped in
#   initial_program.py measures ~0.1798, i.e. combined_score ~ 0.74.

import time
import numpy as np
import sys
import os
from importlib import __import__

BENCHMARK = 0.133310
TOL = 1e-9
N_GRID = 8
NUM_TUBES = N_GRID * N_GRID
NUM_MC_POINTS = 500000
MC_SEED = 12345


def _union_volume(base_x, base_y):
    """Monte Carlo estimate of the union volume of the N_GRID^2 tubes."""
    inv_n = 1.0 / N_GRID
    i_grid, j_grid = np.meshgrid(np.arange(N_GRID), np.arange(N_GRID), indexing="ij")
    i_flat = i_grid.flatten().astype(np.float64)
    j_flat = j_grid.flatten().astype(np.float64)

    # Enclosing bounding box of the union over all tubes and all heights c in [0, 1].
    x_min = float(base_x.min())
    x_max = float((base_x + inv_n + i_flat * inv_n).max())
    y_min = float(base_y.min())
    y_max = float((base_y + inv_n + j_flat * inv_n).max())
    box_vol = (x_max - x_min) * (y_max - y_min) * 1.0
    if box_vol <= TOL:
        return 0.0

    rng = np.random.default_rng(MC_SEED)
    a = rng.uniform(x_min, x_max, NUM_MC_POINTS)
    b = rng.uniform(y_min, y_max, NUM_MC_POINTS)
    c = rng.uniform(0.0, 1.0, NUM_MC_POINTS)

    inside = np.zeros(NUM_MC_POINTS, dtype=bool)
    for k in range(NUM_TUBES):
        x_lo = base_x[k] + c * i_flat[k] * inv_n
        y_lo = base_y[k] + c * j_flat[k] * inv_n
        inside |= (
            (a >= x_lo) & (a <= x_lo + inv_n) & (b >= y_lo) & (b <= y_lo + inv_n)
        )
    return float(inside.mean()) * box_vol


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
            positions = program.kakeya_needle_3d8()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(positions, np.ndarray):
            positions = np.array(positions)
        positions = positions.astype(np.float64)

        if positions.shape != (NUM_TUBES, 2):
            raise ValueError(
                f"Invalid shape: positions = {positions.shape}, expected {(NUM_TUBES, 2)}"
            )

        if not np.all(np.isfinite(positions)):
            raise ValueError("Positions contain NaN or infinite values.")

        base_x = positions[:, 0]
        base_y = positions[:, 1]

        union_volume = _union_volume(base_x, base_y)
        if not np.isfinite(union_volume) or union_volume <= 0.0:
            raise ValueError("Non-positive or non-finite union volume.")

        # Minimization -> higher-is-better: combined_score = BENCHMARK / union_volume.
        combined_score = BENCHMARK / union_volume
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "union_volume": float(union_volume),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
