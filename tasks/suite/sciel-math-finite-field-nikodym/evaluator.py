# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the finite-field Nikodym problem in F_q^2
# with q = p^2 and p = 7.
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

# p = 7, q = p^2 = 49, full space F_q^2 has q^2 = 2401 points.
P = 7
Q = P * P

# The objective being MAXIMIZED is the size of the complement of the Nikodym set
# (the number of excluded points). The AlphaEvolve notebook reports that the
# optimal construction misses about p^3 = q^(3/2) points from F_q^2 (for p=29 the
# record complement ~24000 is close to 29^3 = 24389). We therefore use the
# optimal target p^3 as the benchmark; combined_score ~ 1.0 means matching it.
BENCHMARK = P ** 3  # 343


def _build_field(p):
    """Build F_q = F_p[alpha], alpha^2 = k (smallest non-residue). Returns
    (q, add_table, mul_table) where elements are indexed idx = a*p + b for the
    F_q element a + b*alpha."""
    q = p * p
    k = None
    for c in range(2, p):
        if pow(c, (p - 1) // 2, p) == p - 1:
            k = c
            break
    if k is None:
        raise ValueError(f"no quadratic non-residue found mod {p}")

    a = np.arange(q) // p  # a-component of each element index
    b = np.arange(q) % p   # b-component

    # Addition table: (a+c, b+d) mod p.
    add_a = (a[:, None] + a[None, :]) % p
    add_b = (b[:, None] + b[None, :]) % p
    add_table = add_a * p + add_b

    # Multiplication table: (ac + bd*k, ad + bc) mod p.
    mul_a = (a[:, None] * a[None, :] + b[:, None] * b[None, :] * k) % p
    mul_b = (a[:, None] * b[None, :] + b[:, None] * a[None, :]) % p
    mul_table = mul_a * p + mul_b
    return q, add_table.astype(np.int64), mul_table.astype(np.int64)


def _is_valid_nikodym(point_ids, q, add_table, mul_table):
    """Check the Nikodym property for the set given by membership flags.

    A point x is "covered" iff some full line L through x has its punctured
    version L \\ {x} contained in N. Per direction we enumerate every line and
    count its complement points c:
      - c == 0: the whole line is in N, so every point on it is covered;
      - c == 1: only the single complement point on the line gets covered;
      - c >= 2: the line covers nobody.
    N is a valid Nikodym set iff every one of the q^2 points is covered.
    """
    n_pts = q * q
    in_N = np.zeros(n_pts, dtype=bool)
    in_N[point_ids] = True
    comp = ~in_N
    covered = np.zeros(n_pts, dtype=bool)

    one = P  # index of the F_q element (1, 0) = 1*p + 0

    # Directions (projective): (1, m) for all m in F_q, plus (0, 1).
    directions = [(one, m) for m in range(q)] + [(0, one)]

    base_x = np.arange(n_pts) // q
    base_y = np.arange(n_pts) % q
    t = np.arange(q)

    for vx, vy in directions:
        tvx = mul_table[t, vx]            # t * v_x for all t  -> (q,)
        tvy = mul_table[t, vy]            # t * v_y for all t  -> (q,)
        new_x = add_table[base_x[:, None], tvx[None, :]]  # (n_pts, q)
        new_y = add_table[base_y[:, None], tvy[None, :]]  # (n_pts, q)
        line_pts = new_x * q + new_y      # point ids on each line -> (n_pts, q)

        comp_on = comp[line_pts]          # (n_pts, q) complement membership
        counts = comp_on.sum(axis=1)

        mask0 = counts == 0
        if mask0.any():
            covered[line_pts[mask0].ravel()] = True

        mask1 = counts == 1
        if mask1.any():
            sel = line_pts[mask1]         # (n1, q)
            covered[sel[comp_on[mask1]]] = True  # one complement pt per line

        if covered.all():
            return True

    return bool(covered.all())


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
            points = program.nikodym_set()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        points = np.asarray(points)
        if not np.all(np.isfinite(points)):
            raise ValueError("solution contains non-finite values")
        points = points.astype(np.int64)

        if points.ndim != 3 or points.shape[1:] != (2, 2):
            raise ValueError(
                f"Invalid shape: points = {points.shape}, expected (k, 2, 2)"
            )
        if points.shape[0] == 0:
            raise ValueError("empty set is not a Nikodym set")

        points = points % P

        # Coordinate (a, b) -> F_q element index a*p + b; point id = X*q + Y.
        x_idx = points[:, 0, 0] * P + points[:, 0, 1]
        y_idx = points[:, 1, 0] * P + points[:, 1, 1]
        point_ids = np.unique(x_idx * Q + y_idx)

        q, add_table, mul_table = _build_field(P)

        complement_size = int(Q * Q - point_ids.shape[0])

        valid = _is_valid_nikodym(point_ids, q, add_table, mul_table)
        if not valid:
            return {
                "complement_size": complement_size,
                "combined_score": 0.0,
                "eval_time": float(eval_time),
            }

        return {
            "complement_size": complement_size,
            "combined_score": float(complement_size / BENCHMARK),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
