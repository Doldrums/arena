# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for IMO 2025 Problem 6 (grid tiling): place
# non-overlapping axis-aligned rectangular tiles on an n x n grid so that every row and
# every column has exactly one uncovered unit square, using as few tiles as possible.
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
import math

N = 36
# Known optimal number of tiles for this grid tiling problem: n + 2*sqrt(n) - 3.
# (See the upstream notebook plot: "Optimal: n + 2*sqrt(n) - 3".)
BENCHMARK = N + 2 * math.sqrt(N) - 3  # = 45.0 for n = 36


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        tiles = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            tiles = program.grid_tiling_imo2025_p6_n36()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(tiles, np.ndarray):
            tiles = np.array(tiles)

        # Allow an empty tiling array to be shaped (0, 4); otherwise require (T, 4).
        if tiles.ndim != 2 or tiles.shape[1] != 4:
            raise ValueError(f"Invalid shape: tiles = {tiles.shape}, expected (T, 4)")

        if not np.all(np.isfinite(tiles)):
            raise ValueError("Tiles contain NaN or infinite values.")

        # Tiles must be integer-valued (grid-aligned).
        if np.any(tiles != np.round(tiles)):
            raise ValueError("Tile coordinates must be integers (grid-aligned).")
        tiles = tiles.astype(np.int64)

        n = N
        grid = np.zeros((n, n), dtype=np.int64)
        for r0, c0, r1, c1 in tiles:
            # Bounds and well-formedness: 0 <= r0 < r1 <= n, 0 <= c0 < c1 <= n.
            if not (0 <= r0 < r1 <= n and 0 <= c0 < c1 <= n):
                raise ValueError(f"Tile out of bounds or degenerate: {(int(r0), int(c0), int(r1), int(c1))}")
            block = grid[r0:r1, c0:c1]
            if np.any(block):
                raise ValueError("Tiles overlap.")
            block[:] = 1

        # Exactly one uncovered unit square per row and per column.
        uncovered_per_row = n - grid.sum(axis=1)
        uncovered_per_col = n - grid.sum(axis=0)
        if not (np.all(uncovered_per_row == 1) and np.all(uncovered_per_col == 1)):
            raise ValueError(
                "Each row and column must have exactly one uncovered square "
                f"(row counts unique={set(uncovered_per_row.tolist())}, "
                f"col counts unique={set(uncovered_per_col.tolist())})."
            )

        num_tiles = int(tiles.shape[0])
        if num_tiles <= 0:
            raise ValueError("A valid tiling must use at least one tile.")

        # Minimization problem: fewer tiles is better. Convert to higher-better by
        # dividing the benchmark (optimal count) by the achieved count, so ~1.0 means
        # matching the optimum and >1.0 would beat it.
        combined_score = BENCHMARK / num_tiles
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "num_tiles": float(num_tiles),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
