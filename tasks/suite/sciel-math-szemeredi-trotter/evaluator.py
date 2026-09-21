# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the Szemeredi-Trotter incidence maximization
# problem: maximize point-line incidences between 54 points and 27 lines in the plane.
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
import math
import numpy as np
import sys
import os
from importlib import __import__

# No closed-form record is known for this specific (n, m) instance, so the BENCHMARK is the
# baseline construction's own incidence count (the classical Szemeredi-Trotter extremal grid
# with k = 3): n^(2/3) m^(2/3)-optimal up to a constant, giving k^4 = 81 incidences. This
# makes combined_score start at exactly 1.0; evolved constructions that find more incidences
# between the SAME 54 points and 27 lines score above 1.0.
BENCHMARK = 81.0
TOL = 1e-6
NUM_POINTS = 54
NUM_LINES = 27


def _canonical_line(a, b, c):
    """Reduce a line A*x + B*y + C = 0 to a canonical integer form for de-duplication."""
    a, b, c = int(a), int(b), int(c)
    if a == 0 and b == 0:
        raise ValueError("Degenerate line with zero (A, B) coefficients.")
    g = math.gcd(math.gcd(abs(a), abs(b)), abs(c))
    if g == 0:
        g = 1
    a, b, c = a // g, b // g, c // g
    for v in (a, b, c):
        if v != 0:
            if v < 0:
                a, b, c = -a, -b, -c
            break
    return (a, b, c)


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
            result = program.szemeredi_trotter_incidences()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not (isinstance(result, (tuple, list)) and len(result) == 2):
            raise ValueError("Constructor must return a (points, lines) pair.")

        points, lines = result
        if not isinstance(points, np.ndarray):
            points = np.array(points)
        if not isinstance(lines, np.ndarray):
            lines = np.array(lines)

        if points.shape != (NUM_POINTS, 2):
            raise ValueError(f"Invalid points shape {points.shape}, expected {(NUM_POINTS, 2)}.")
        if lines.shape != (NUM_LINES, 3):
            raise ValueError(f"Invalid lines shape {lines.shape}, expected {(NUM_LINES, 3)}.")

        if not (np.all(np.isfinite(points)) and np.all(np.isfinite(lines))):
            raise ValueError("Points or lines contain NaN or infinite values.")

        # Require integer-lattice coordinates / integer line coefficients.
        if not (np.all(np.abs(points - np.round(points)) < TOL)
                and np.all(np.abs(lines - np.round(lines)) < TOL)):
            raise ValueError("Points and line coefficients must be integers.")
        points = np.round(points).astype(np.int64)
        lines = np.round(lines).astype(np.int64)

        # Points must be distinct (no duplicate points to inflate incidences).
        if np.unique(points, axis=0).shape[0] != NUM_POINTS:
            raise ValueError("Points must be distinct.")

        # Lines must be distinct as geometric objects (canonical form).
        canon = set()
        for row in lines:
            canon.add(_canonical_line(row[0], row[1], row[2]))
        if len(canon) != NUM_LINES:
            raise ValueError("Lines must be distinct.")

        # Count incidences exactly via integer arithmetic:
        # incidence iff A*px + B*py + C == 0.
        A = lines[:, 0]
        B = lines[:, 1]
        C = lines[:, 2]
        vals = (np.outer(points[:, 0], A)
                + np.outer(points[:, 1], B)
                + C[None, :])
        incidences = int(np.count_nonzero(vals == 0))

        combined_score = incidences / BENCHMARK
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "incidences": float(incidences),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
