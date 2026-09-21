# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for a classical-inequalities problem: the
# Hausdorff-Young inequality, probing the Babenko-Beckner constant by maximizing the
# ratio Q(f) = ||fhat||_q / ||f||_p for a bounded, integrable step function f.
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

# Conjugate exponents with 1/p + 1/q = 1.
P = 3.0 / 2.0
Q = P / (P - 1.0)  # = 3.0

# Grid parameters (must match initial_program.py).
R = 10.0
N = 2048

# Sharp Hausdorff-Young (Babenko-Beckner) constant for the Fourier transform
# fhat(xi) = integral f(x) exp(-2*pi*i*x*xi) dx and exponents (p, q):
#     Q_max = sqrt( p^(1/p) / q^(1/q) ).
# For p = 3/2, q = 3 this equals ~0.9531842929969365, the optimal ratio, attained by a
# Gaussian. We use it as BENCHMARK (known optimal constant from the literature).
BENCHMARK = float(np.sqrt(P ** (1.0 / P) / Q ** (1.0 / Q)))

# Validation bounds (mirroring the upstream notebook's failure modes).
MAX_F = 1e2  # f must be bounded.
MAX_FHAT = 1e2  # fhat must not blow up.
TOL = 1e-12


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        values = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            values = program.hausdorff_young_p32()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(values, np.ndarray):
            values = np.array(values, dtype=np.float64)
        values = values.astype(np.float64)

        if values.shape != (N,):
            raise ValueError(f"Invalid shape: values = {values.shape}, expected {(N,)}")

        if not np.all(np.isfinite(values)):
            raise ValueError("Step-function values contain NaN or infinite entries.")

        # Feasibility: f must be bounded and not identically zero.
        if np.max(np.abs(values)) > MAX_F:
            raise ValueError("Function is too large (unbounded); not admissible.")

        dx = 2.0 * R / N
        x = -R + dx * np.arange(N)

        # ||f||_p of the step function (exact for a piecewise-constant f).
        f_lp_norm = (np.sum(np.abs(values) ** P) * dx) ** (1.0 / P)
        if f_lp_norm < TOL:
            raise ValueError("Function is (numerically) identically zero.")

        # Fourier transform of the sampled function via the FFT:
        #   fhat(xi_k) = dx * exp(-2*pi*i*x0*xi_k) * FFT(values)_k,
        # evaluated on the DFT frequency grid xi_k = fftfreq(N, d=dx).
        fft_vals = np.fft.fft(values)
        xi = np.fft.fftfreq(N, d=dx)
        x0 = -R
        f_hat = dx * np.exp(-2j * np.pi * x0 * xi) * fft_vals

        if np.max(np.abs(f_hat)) > MAX_FHAT:
            raise ValueError("Fourier transform is too large; not admissible.")

        # ||fhat||_q via a Riemann sum over the frequency grid (spacing dxi = 1/(N*dx)).
        dxi = 1.0 / (N * dx)
        fhat_lq_norm = (np.sum(np.abs(f_hat) ** Q) * dxi) ** (1.0 / Q)

        quotient = fhat_lq_norm / f_lp_norm

        combined_score = quotient / BENCHMARK
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "quotient": float(quotient),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
