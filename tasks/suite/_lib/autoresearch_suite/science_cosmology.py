"""Small, synthetic cosmological numerical-method benchmarks.

The background is a spatially flat matter + smooth CPL dark-energy model:
w(a)=w0+wa*(1-a), E(a)^2=Om*a^-3+(1-Om)*a^[-3*(1+w0+wa)]
*exp[-3*wa*(1-a)]. Radiation, curvature and neutrino effects are omitted.
All quantities are dimensionless; a=1 today. These are locally designed
approximation tasks based on published equations, not observational datasets.
"""
from __future__ import annotations

from arena_task_paths import data_root

from functools import lru_cache
import math

import numpy as np
from scipy.integrate import quad, solve_ivp

from .runtime import CandidateError, require


# Each tuple is (present matter fraction, w0, wa). Public evaluation models
# are disjoint from public calibration models, not a secret test set.
CALIBRATION_MODELS = (
    (0.20, -1.20, -0.20), (0.25, -1.10, 0.20),
    (0.30, -1.00, 0.00), (0.35, -0.90, -0.20),
    (0.40, -0.80, 0.20), (0.22, -0.85, 0.10),
    (0.38, -1.15, -0.10), (0.28, -1.00, 0.30),
)
VALIDATION_MODELS = (
    (0.18, -1.25, 0.15), (0.23, -0.95, -0.25),
    (0.27, -1.05, 0.25), (0.33, -0.85, -0.15),
    (0.37, -1.20, 0.05), (0.42, -0.75, 0.15),
    (0.31, -1.30, -0.30), (0.19, -0.80, 0.20),
)
CALIBRATION_REDSHIFTS = (0.01, 0.1, 0.4, 1.0, 2.0, 4.0, 8.0)
VALIDATION_REDSHIFTS = (0.025, 0.2, 0.7, 1.5, 3.0, 5.5, 10.0)
CALIBRATION_SCALE_FACTORS = tuple(np.geomspace(0.2, 1.0, 25))
VALIDATION_SCALE_FACTORS = tuple(np.geomspace(0.2, 1.0, 33))


def expansion_squared(a, omega_m, w0, wa):
    """E(a)^2 = (H(a)/H0)^2, for dimensionless scale factor a."""
    a = np.asarray(a, dtype=float)
    dark_energy = (1.0 - omega_m) * a ** (-3.0 * (1.0 + w0 + wa))
    dark_energy *= np.exp(-3.0 * wa * (1.0 - a))
    return omega_m * a ** -3.0 + dark_energy


def matter_fraction(a, omega_m, w0, wa):
    a = np.asarray(a, dtype=float)
    return omega_m * a ** -3.0 / expansion_squared(a, omega_m, w0, wa)


def _vector(value, length, name):
    """Reject malformed arrays instead of silently casting complex/text/bools."""
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as error:
        raise CandidateError(f"{name} must be a numeric vector") from error
    require(array.shape == (length,), f"{name} must have shape ({length},)")
    require(array.dtype.kind in "fiu", f"{name} must contain real numbers")
    array = array.astype(float, copy=True)
    require(np.isfinite(array).all(), f"{name} must contain finite numbers")
    return array


@lru_cache(maxsize=512)
def reference_distance(z, omega_m, w0, wa):
    """Adaptive reference for dL/(c/H0); independent of candidate quadrature."""
    integral, error = quad(
        lambda redshift: 1.0 / math.sqrt(float(expansion_squared(
            1.0 / (1.0 + redshift), omega_m, w0, wa))),
        0.0, z, epsabs=2e-12, epsrel=2e-12, limit=200,
    )
    require(math.isfinite(integral) and error < 1e-9 * max(1.0, integral),
            "distance reference failed to converge")
    return (1.0 + z) * integral


def _distance_errors(nodes, weights, models, redshifts):
    errors = []
    for omega_m, w0, wa in models:
        for z in redshifts:
            a = 1.0 / (1.0 + z * nodes)
            predicted = (1.0 + z) * z * float(np.dot(
                weights, 1.0 / np.sqrt(expansion_squared(a, omega_m, w0, wa))))
            exact = reference_distance(z, omega_m, w0, wa)
            errors.append(abs(predicted / exact - 1.0))
    return np.asarray(errors)


def distance_score(construction, n_nodes=8):
    """Evaluate one universal quadrature construction, not per-case answers."""
    require(isinstance(construction, dict) and set(construction) == {"nodes", "weights"},
            "construct() must return exactly {'nodes', 'weights'}")
    nodes = _vector(construction["nodes"], n_nodes, "nodes")
    weights = _vector(construction["weights"], n_nodes, "weights")
    require(np.all((nodes >= 0.0) & (nodes <= 1.0)), "nodes must lie in [0, 1]")
    require(np.all(np.diff(nodes) > 0.0), "nodes must be strictly increasing")
    require(np.all(weights > 0.0), "weights must be strictly positive")
    require(abs(float(weights.sum()) - 1.0) <= 1e-12, "weights must sum to 1")
    calibration = _distance_errors(nodes, weights, CALIBRATION_MODELS, CALIBRATION_REDSHIFTS)
    validation = _distance_errors(nodes, weights, VALIDATION_MODELS, VALIDATION_REDSHIFTS)
    score = 100.0 * float(validation.max())
    return score, {
        "metric": "worst_validation_relative_distance_error_percent",
        "calibration_error_percent": 100.0 * float(calibration.max()),
        "validation_rms_error_percent": 100.0 * float(np.sqrt(np.mean(validation ** 2))),
        "calibration_cases": len(calibration), "validation_cases": len(validation),
        "integrand_evaluations_per_distance": n_nodes,
        "reference": "adaptive scipy.integrate.quad, epsabs=epsrel=2e-12",
        "data": "local synthetic flat CPL models; public disjoint model splits",
    }


def growth_features(a, omega_m, w0, wa):
    """Six ordered features defining the restricted growth-index hypothesis."""
    a = np.asarray(a, dtype=float)
    q = 1.0 - matter_fraction(a, omega_m, w0, wa)
    u = 1.0 + w0 + wa * (1.0 - a)
    return np.stack((np.ones_like(a), q, q * q, u, wa * a, u * q), axis=-1)


@lru_cache(maxsize=128)
def _growth_solution(omega_m, w0, wa, a_initial=1e-3):
    """Solve D_xx+(2+dlnH/dx)D_x-3 Om(a)D/2=0 for x=ln(a)."""
    def rhs(x, state):
        a = math.exp(x)
        fraction = float(matter_fraction(a, omega_m, w0, wa))
        w = w0 + wa * (1.0 - a)
        dlnh = -1.5 * (1.0 + w * (1.0 - fraction))
        return (state[1], -(2.0 + dlnh) * state[1] + 1.5 * fraction * state[0])

    solution = solve_ivp(rhs, (math.log(a_initial), 0.0),
                         (a_initial, a_initial), method="DOP853", dense_output=True,
                         rtol=2e-11, atol=1e-13)
    require(solution.success, "growth reference failed to converge")
    return solution.sol


def reference_growth(a, omega_m, w0, wa, *, a_initial=1e-3):
    """Return D(a)/D(1), f(a)=dlnD/dlna with D(ai)=D_x(ai)=ai."""
    solution = _growth_solution(omega_m, w0, wa, a_initial)
    values = solution(np.log(np.asarray(a, dtype=float)))
    normalization = float(solution(0.0)[0])
    return values[0] / normalization, values[1] / values[0]


def _candidate_growth(coefficients, a, omega_m, w0, wa):
    """Integrate the fixed six-term ansatz; candidates cannot replace the solver."""
    a = np.asarray(a, dtype=float)

    def rate(locations):
        gamma = growth_features(locations, omega_m, w0, wa) @ coefficients
        require(np.isfinite(gamma).all() and np.all((gamma >= 0.1) & (gamma <= 1.2)),
                "growth index must lie in [0.1, 1.2] at all checked locations")
        return matter_fraction(locations, omega_m, w0, wa) ** gamma

    growth_rate = rate(a)
    # ln D(a)/D(1) = -integral[ln(a),0] f(exp(x)) dx. This numerical
    # quadrature computes the candidate ansatz; the reference is an ODE solve.
    nodes, weights = np.polynomial.legendre.leggauss(48)
    x0 = np.log(a)
    locations = np.exp(x0[:, None] * (1.0 - nodes[None, :]) / 2.0)
    integral = (-x0 / 2.0) * (rate(locations) @ weights)
    return np.exp(-integral), growth_rate


def _growth_errors(coefficients, models, scale_factors):
    growth_errors, rate_errors = [], []
    a = np.asarray(scale_factors)
    for omega_m, w0, wa in models:
        exact_growth, exact_rate = reference_growth(a, omega_m, w0, wa)
        growth, rate = _candidate_growth(coefficients, a, omega_m, w0, wa)
        growth_errors.extend(abs(growth / exact_growth - 1.0))
        rate_errors.extend(abs(rate / exact_rate - 1.0))
    return np.asarray(growth_errors), np.asarray(rate_errors)


def growth_score(construction):
    """Minimize the worst relative error in both normalized growth and rate."""
    coefficients = _vector(construction, 6, "growth coefficients")
    require(np.all(np.abs(coefficients) <= 10.0), "growth coefficients must lie in [-10, 10]")
    calibration = _growth_errors(coefficients, CALIBRATION_MODELS, CALIBRATION_SCALE_FACTORS)
    validation_growth, validation_rate = _growth_errors(
        coefficients, VALIDATION_MODELS, VALIDATION_SCALE_FACTORS)
    score = 100.0 * max(float(validation_growth.max()), float(validation_rate.max()))
    return score, {
        "metric": "worst_validation_relative_growth_or_rate_error_percent",
        "calibration_error_percent": 100.0 * max(float(values.max()) for values in calibration),
        "validation_growth_error_percent": 100.0 * float(validation_growth.max()),
        "validation_rate_error_percent": 100.0 * float(validation_rate.max()),
        "calibration_cases": len(CALIBRATION_MODELS) * len(CALIBRATION_SCALE_FACTORS),
        "validation_cases": len(VALIDATION_MODELS) * len(VALIDATION_SCALE_FACTORS),
        "reference": "GR second-order growth ODE; DOP853 rtol=2e-11, atol=1e-13",
        "data": "local synthetic smooth-dark-energy models; public disjoint model splits",
    }


# ---------------------------------------------------------------------------
# Pantheon+ supernova expansion-history fit (real measurements)
# ---------------------------------------------------------------------------

from pathlib import Path as _Path  # noqa: E402

PANTHEON_DIR = data_root() / "pantheon-plus"
C_KM_S = 299792.458


@lru_cache(maxsize=1)
def pantheon_data(z_min=0.01):
    """Pantheon+SH0ES Hubble-diagram redshifts, corrected magnitudes and the STAT+SYS covariance (Cholesky factor).

    Rows with ``zHD > z_min`` are kept (the standard Pantheon+ cosmology cut,
    which removes the peculiar-velocity dominated nearby sample). Cepheid-host
    calibrators are excluded because no SH0ES distance anchor is used here.
    """
    table = PANTHEON_DIR / "Pantheon+SH0ES.dat"
    cov_npy = PANTHEON_DIR / "Pantheon+SH0ES_STAT+SYS.npy"
    require(table.is_file() and cov_npy.is_file(), f"Pantheon+ data missing under {PANTHEON_DIR} (run python3 scripts/prepare_science_data.py)")
    import numpy as _np
    rows = table.read_text().splitlines()
    header = rows[0].split()
    columns = {name: index for index, name in enumerate(header)}
    values = _np.array([line.split() for line in rows[1:] if line.strip()], dtype=object)
    z_hd = values[:, columns["zHD"]].astype(float)
    z_hel = values[:, columns["zHEL"]].astype(float)
    m_b = values[:, columns["m_b_corr"]].astype(float)
    calibrator = values[:, columns["IS_CALIBRATOR"]].astype(int)
    keep = (z_hd > z_min) & (calibrator == 0)
    cov = _np.load(cov_npy)[_np.ix_(keep, keep)]
    chol = _np.linalg.cholesky(cov)
    return {"z_hd": z_hd[keep], "z_hel": z_hel[keep], "m_b": m_b[keep], "cholesky": chol, "count": int(keep.sum())}


def _luminosity_distance(expansion, theta, z_hd, z_hel, n_grid=2048):
    """dL in Mpc for H0 = 70 (the absolute scale is marginalised with the magnitude offset)."""
    grid = np.linspace(0.0, float(np.max(z_hd)), n_grid)
    e = np.asarray(expansion(grid, theta), dtype=float)
    require(e.shape == grid.shape and bool(np.all(np.isfinite(e))) and bool(np.all(e > 0)), "expansion(z, theta) must return positive finite E(z) for every z")
    inv = 1.0 / e
    comoving = np.concatenate([[0.0], np.cumsum(0.5 * (inv[1:] + inv[:-1]) * np.diff(grid))])
    dc = np.interp(z_hd, grid, comoving) * C_KM_S / 70.0
    return (1.0 + z_hel) * dc


def _chi2(residual, chol):
    """chi^2 with the magnitude offset M analytically profiled out (constant shift in the covariance metric)."""
    from scipy.linalg import solve_triangular
    w_r = solve_triangular(chol, residual, lower=True)
    w_1 = solve_triangular(chol, np.ones_like(residual), lower=True)
    a, b, c = float(w_r @ w_r), float(w_1 @ w_r), float(w_1 @ w_1)
    return a - b * b / c


def pantheon_score(expansion, theta0, bounds, max_evaluations=400):
    """Minimum chi^2 of the candidate expansion model on Pantheon+ (lower is better).

    ``expansion(z, theta)`` returns E(z) = H(z)/H0 for an array of redshifts;
    ``theta0`` is the initial parameter vector (at most 6 parameters) and
    ``bounds`` a list of (low, high) pairs. The evaluator profiles the absolute
    magnitude analytically and minimises chi^2 over theta with Nelder-Mead
    within the bounds, from theta0. The flat LambdaCDM chi^2 (Omega_m fitted)
    is reported for comparison.
    """
    from scipy.optimize import minimize
    data = pantheon_data()
    theta0 = _vector(theta0, len(np.atleast_1d(theta0)), "theta0")
    require(1 <= theta0.size <= 6, "theta0 must have 1 to 6 parameters")
    bounds = [(float(lo), float(hi)) for lo, hi in bounds]
    require(len(bounds) == theta0.size and all(lo < hi for lo, hi in bounds), "bounds must give (low, high) with low < high for every parameter")
    lows, highs = np.array([b[0] for b in bounds]), np.array([b[1] for b in bounds])

    def chi2_of(theta):
        theta = np.clip(theta, lows, highs)
        try:
            dl = _luminosity_distance(expansion, theta, data["z_hd"], data["z_hel"])
        except CandidateError:
            raise
        except Exception as error:  # noqa: BLE001
            raise CandidateError(f"expansion raised {type(error).__name__}: {error}") from None
        mu = 5.0 * np.log10(dl) + 25.0
        return _chi2(data["m_b"] - mu, data["cholesky"])

    result = minimize(chi2_of, theta0, method="Nelder-Mead", options={"maxfev": max_evaluations, "xatol": 1e-5, "fatol": 1e-4})
    best_theta = np.clip(result.x, lows, highs)
    best = float(chi2_of(best_theta))

    def lcdm(z, om):
        return np.sqrt(om * (1 + z) ** 3 + (1 - om))
    lcdm_fit = minimize(lambda t: _chi2(data["m_b"] - (5.0 * np.log10(_luminosity_distance(lcdm, float(t[0]), data["z_hd"], data["z_hel"])) + 25.0), data["cholesky"]),
                        np.array([0.3]), method="Nelder-Mead", options={"maxfev": 100})
    return best, {"chi2": best, "theta": best_theta.tolist(), "supernovae": data["count"], "lcdm_chi2": float(lcdm_fit.fun), "lcdm_omega_m": float(lcdm_fit.x[0]),
                  "delta_chi2_vs_lcdm": best - float(lcdm_fit.fun), "evaluations": int(result.nfev)}
