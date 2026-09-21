# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for Crouzeix's conjecture: scoring a matrix A and a
# polynomial p by the Crouzeix ratio ||p(A)||_op / sup_{z in W(A)} |p(z)|.
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

# Crouzeix's conjecture asserts the ratio never exceeds 2; 2 is the conjectured supremum
# (and the value approached by the AlphaEvolve tridiagonal construction). Source: problem
# statement and evolved-code comment in the upstream crouzeix_conjecture notebook.
BENCHMARK = 2.0
TOL = 1e-9
NUM_BOUNDARY = 720  # samples of the numerical-range boundary


def _numerical_range_boundary(A: np.ndarray, num_points: int = NUM_BOUNDARY) -> np.ndarray:
    """Sample the boundary of the numerical range W(A) via supporting hyperplanes.

    For each angle theta, the extreme point of W(A) in direction e^{i theta} is
    <A v, v> where v is the top eigenvector of the Hermitian part
    H_theta = (e^{i theta} A + e^{-i theta} A^*) / 2. These points trace dW(A).
    """
    theta = np.linspace(0.0, 2.0 * np.pi, num_points, endpoint=False)
    boundary = np.empty(num_points, dtype=complex)
    for k, th in enumerate(theta):
        H = 0.5 * (np.exp(1j * th) * A + np.exp(-1j * th) * A.conj().T)
        _, eigvecs = np.linalg.eigh(H)
        v = eigvecs[:, -1]
        boundary[k] = np.vdot(v, A @ v)
    return boundary


def _crouzeix_ratio(A: np.ndarray, poly_coeffs: np.ndarray) -> float:
    p = np.poly1d(poly_coeffs)
    n = A.shape[0]

    # Evaluate p(A) via Horner in the matrix algebra.
    pA = np.zeros((n, n), dtype=complex)
    power = np.eye(n, dtype=complex)
    for coeff in reversed(poly_coeffs):
        pA = pA + coeff * power
        power = power @ A

    op_norm = np.linalg.norm(pA, ord=2)

    # max |p(z)| over the convex compact W(A) is attained on its boundary
    # (maximum modulus principle), so sampling the boundary suffices.
    boundary = _numerical_range_boundary(A)
    sup_pz = float(np.max(np.abs(p(boundary))))

    if not np.isfinite(sup_pz) or sup_pz < TOL:
        raise ValueError("sup_{z in W(A)} |p(z)| is zero or non-finite; degenerate construction.")

    return float(op_norm / sup_pz)


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
            result = program.crouzeix_conjecture4()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(result, (tuple, list)) or len(result) != 2:
            raise ValueError("Constructor must return a (A, poly_coeffs) pair.")

        A, poly_coeffs = result
        A = np.asarray(A, dtype=complex)
        poly_coeffs = np.asarray(poly_coeffs, dtype=complex).ravel()

        if A.ndim != 2 or A.shape[0] != A.shape[1] or A.shape[0] < 1:
            raise ValueError(f"Invalid matrix shape: {A.shape}; expected square (n, n).")

        if poly_coeffs.ndim != 1 or poly_coeffs.size < 1:
            raise ValueError(f"Invalid poly_coeffs shape: {poly_coeffs.shape}; expected 1-D.")

        if not np.all(np.isfinite(A)):
            raise ValueError("Matrix A contains NaN or infinite values.")

        if not np.all(np.isfinite(poly_coeffs)):
            raise ValueError("Polynomial coefficients contain NaN or infinite values.")

        if np.max(np.abs(poly_coeffs)) < TOL:
            raise ValueError("Polynomial is identically zero.")

        crouzeix_ratio = _crouzeix_ratio(A, poly_coeffs)

        combined_score = crouzeix_ratio / BENCHMARK
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "crouzeix_ratio": float(crouzeix_ratio),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
