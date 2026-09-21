# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the Ovals problem: minimizing a curvature
# Rayleigh quotient over convex planar curves with a periodic weight function.
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
# DEVIATION FROM UPSTREAM (documented per task instructions):
#   The upstream notebook builds f, g, h with periodic cubic B-splines
#   (scipy.interpolate.make_interp_spline, k=4) and integrates with
#   scipy.integrate.quad / Gaussian quadrature. To stay pure-numpy we replace the
#   B-spline interpolation with the closest faithful smooth-periodic alternative:
#   trigonometric (Fourier) interpolation of the sampled values, which yields
#   smooth periodic functions with analytic (spectral) derivatives. Integrals are
#   computed on a dense uniform grid (rectangle rule, exact for band-limited
#   integrands). For the circle + constant-weight baseline both formulations give
#   exactly I = 1, and the objective/constraints (convexity via positive signed
#   curvature, arc-length reparametrization, Rayleigh quotient) are preserved.
#
# ===--------------------------------------------------------------------------------------===#

import time
import numpy as np
import sys
import os
from importlib import __import__

# Baseline construction (unit circle, constant weight) scores I = 1 exactly. The
# upstream notebook provides no published optimal/record constant, so BENCHMARK is
# set to the baseline's own objective value (combined_score starts at ~1.0).
BENCHMARK = 1.0

NUM_SAMPLES = 2000
SPEED_DEGENERACY_THRESHOLD = 1e-4
PHI_DEGENERACY_THRESHOLD = 1e-3
MAX_VALUE = 1e6


def _fourier_eval(values, t):
    """Trigonometric (Fourier) interpolant of `values` (samples at 2*pi*k/n) and
    its first two derivatives, evaluated at parameters `t`.

    Returns (f, f', f'') as real arrays of the same length as `t`.
    """
    values = np.asarray(values, dtype=np.float64)
    n = values.size
    coeffs = np.fft.fft(values) / n
    freqs = np.fft.fftfreq(n, d=1.0 / n)  # integer frequencies as floats

    modes = freqs
    amps = coeffs
    if n % 2 == 0:
        # Symmetrize the Nyquist mode (-n/2) so the interpolant and its
        # derivatives are real and well defined.
        ny = n // 2
        amps = amps.copy()
        amps[ny] = coeffs[ny] / 2.0
        modes = np.append(modes, float(ny))
        amps = np.append(amps, coeffs[ny] / 2.0)

    phase = np.exp(1j * np.outer(t, modes))  # (len(t), num_modes)
    f = (phase @ amps).real
    fp = (phase @ (1j * modes * amps)).real
    fpp = (phase @ (-(modes ** 2) * amps)).real
    return f, fp, fpp


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
            result = program.ovals_problem20()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        # The construction returns (x, y, phi).
        if not (isinstance(result, (tuple, list)) and len(result) == 3):
            raise ValueError("Constructor must return a tuple/list of three arrays (x, y, phi).")
        x = np.asarray(result[0], dtype=np.float64)
        y = np.asarray(result[1], dtype=np.float64)
        phi = np.asarray(result[2], dtype=np.float64)

        if x.ndim != 1 or y.ndim != 1 or phi.ndim != 1:
            raise ValueError("x, y and phi must each be one-dimensional arrays.")
        if not (x.size == y.size == phi.size) or x.size < 3:
            raise ValueError("x, y and phi must have equal length >= 3.")

        if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y)) and np.all(np.isfinite(phi))):
            raise ValueError("Inputs contain NaN or infinite values.")

        if (np.max(np.abs(x)) > MAX_VALUE or np.max(np.abs(y)) > MAX_VALUE
                or np.max(np.abs(phi)) > MAX_VALUE):
            raise ValueError("Inputs are too large; functions are not tame.")

        # Dense parameter grid over [0, 2*pi).
        t = np.linspace(0.0, 2.0 * np.pi, NUM_SAMPLES, endpoint=False)
        dt = 2.0 * np.pi / NUM_SAMPLES

        # Curve c(t) = (f(t), g(t)) and its derivatives.
        fx, dfx, ddfx = _fourier_eval(x, t)
        fy, dfy, ddfy = _fourier_eval(y, t)

        speed = np.sqrt(dfx ** 2 + dfy ** 2)
        if np.min(speed) < SPEED_DEGENERACY_THRESHOLD:
            raise ValueError("Degenerate curve speed (near-zero velocity).")

        # Total arc length and rescaling factor so arc length becomes 2*pi.
        total_arc_length = float(np.sum(speed) * dt)
        if total_arc_length < SPEED_DEGENERACY_THRESHOLD:
            raise ValueError("Degenerate curve length.")
        scale = 2.0 * np.pi / total_arc_length

        # Signed geometric curvature (parametrization invariant).
        signed_kappa = (dfx * ddfy - dfy * ddfx) / (speed ** 3)
        # Convexity constraint: signed curvature must stay strictly positive.
        if np.min(signed_kappa) <= 0.0:
            raise ValueError("Curve is not convex (signed curvature not positive).")

        # Arc-length curvature for the rescaled (length 2*pi) curve.
        kappa_arc = signed_kappa / scale  # = signed_kappa * total_arc_length / (2*pi)

        # Arc-length coordinate s(t) rescaled to [0, 2*pi).
        s_of_t = np.concatenate(([0.0], np.cumsum(speed * dt * scale)[:-1]))

        # Weight h parametrized directly by arc length s on [0, 2*pi).
        s_grid = np.linspace(0.0, 2.0 * np.pi, NUM_SAMPLES, endpoint=False)
        ds = 2.0 * np.pi / NUM_SAMPLES
        h, dh, _ = _fourier_eval(phi, s_grid)

        denom = float(np.sum(h ** 2) * ds)
        if denom < PHI_DEGENERACY_THRESHOLD:
            raise ValueError("Degenerate weight function (near-zero L2 norm).")

        # Curvature as a function of arc length, on the uniform s grid.
        kappa_s = np.interp(s_grid, s_of_t, kappa_arc, period=2.0 * np.pi)

        numer = float(np.sum(dh ** 2 + (kappa_s * h) ** 2) * ds)

        rayleigh_quotient = numer / denom
        if not np.isfinite(rayleigh_quotient) or rayleigh_quotient <= 0.0:
            raise ValueError("Non-finite or non-positive Rayleigh quotient.")

        # Minimization problem: convert to higher-is-better via BENCHMARK / value.
        combined_score = BENCHMARK / rayleigh_quotient
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "rayleigh_quotient": float(rayleigh_quotient),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
