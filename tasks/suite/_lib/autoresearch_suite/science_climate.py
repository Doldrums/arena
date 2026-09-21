"""Reduced Lorenz-96 climate-method benchmarks with independent ODE truth.

Time and state are nondimensional. No meteorological observations are used.
The two-scale convention follows Rasp (2020), Eqs. (2)-(3), including h/J
in the fast equation and -h*c*mean(Y) in the slow equation.
"""
from __future__ import annotations

from functools import lru_cache
import numpy as np
from scipy.integrate import solve_ivp

from .runtime import CandidateError


def finite(value, shape):
    raw = np.asarray(value)
    if np.iscomplexobj(raw) or raw.dtype.kind not in "fiu":
        raise CandidateError("Expected a real numeric array")
    result = np.asarray(raw, dtype=float)
    if result.shape != shape or not np.isfinite(result).all():
        raise CandidateError(f"Expected finite array of shape {shape}")
    return result


def rhs(x, forcing):
    return (np.roll(x, -1, axis=-1) - np.roll(x, 2, axis=-1)) * np.roll(x, 1, axis=-1) - x + forcing


def rk4(x, dt, forcing):
    a = rhs(x, forcing)
    b = rhs(x + dt * a / 2, forcing)
    c = rhs(x + dt * b / 2, forcing)
    d = rhs(x + dt * c, forcing)
    return x + dt * (a + 2*b + 2*c + d) / 6


def integrate(fun, initial, times):
    solution = solve_ivp(fun, (0, float(times[-1])), initial, t_eval=times,
                         method="DOP853", rtol=2e-10, atol=2e-11)
    if not solution.success or not np.isfinite(solution.y).all():
        raise RuntimeError("Reference ODE integration failed")
    return solution.y.T


@lru_cache(maxsize=12)
def assimilation_case(seed, forcing, n, members, cycles):
    rng = np.random.default_rng(seed)
    initial = forcing + rng.normal(0, 0.1, n)
    initial = integrate(lambda t, x: rhs(x, forcing), initial, np.array([0, 3.0]))[-1]
    truth = integrate(lambda t, x: rhs(x, forcing), initial, np.arange(cycles + 1) * 0.05)
    observed = np.arange(0, n, 2)
    observations = truth[1:, observed] + rng.normal(0, 0.7, (cycles, len(observed)))
    ensemble = initial + rng.normal(0, 1.0, n) + rng.normal(0, 1.0, (members, n))
    return truth, observations, ensemble, observed


def assimilation_score(analyze, parameters):
    n, members, cycles = 20, 16, parameters.get("cycles", 40)
    cases = []
    for seed, forcing in ((181, 6.0), (283, 8.0), (389, 10.0)):
        truth, observations, initial, observed = assimilation_case(seed, forcing, n, members, cycles)
        ensemble = initial.copy()
        errors = []
        for k, observation in enumerate(observations):
            for _ in range(5):
                ensemble = rk4(ensemble, 0.01, forcing)
            ensemble = finite(analyze(ensemble.copy(), observation.copy(), observed.copy(), 0.49), (members, n))
            if np.max(np.abs(ensemble)) > 100:
                raise CandidateError("Analysis ensemble leaves the allowed [-100,100] state box")
            errors.append(float(np.mean((ensemble.mean(axis=0) - truth[k + 1])**2)))
        cases.append({"forcing": forcing, "seed": seed, "rmse": float(np.sqrt(np.mean(errors)))})
    return float(np.sqrt(np.mean([c["rmse"]**2 for c in cases]))), {"per_case": cases}


def two_scale_rhs(state, forcing, k=8, j=4, h=1.0, c=10.0, b=10.0):
    x, y = state[:k], state[k:].reshape(k, j)
    dx = rhs(x, forcing) - h*c*np.mean(y, axis=1)
    # One periodic K*J ring: fast neighbours cross slow-cell boundaries.
    fast = y.ravel()
    advection = -b*np.roll(fast, -1) * (np.roll(fast, -2) - np.roll(fast, 1))
    dy = c * (advection.reshape(k, j) - y + h*x[:, None]/j)
    return np.concatenate([dx, dy.ravel()])


@lru_cache(maxsize=12)
def closure_case(seed, forcing):
    rng = np.random.default_rng(seed)
    state = np.concatenate([forcing + rng.normal(0, 0.1, 8), rng.normal(0, 0.1, 32)])
    trajectory = integrate(lambda t, z: two_scale_rhs(z, forcing), state, np.linspace(0, 8, 401))[150:]
    x = trajectory[:, :8].copy()
    tendency = -10 * trajectory[:, 8:].reshape(-1, 8, 4).mean(axis=2)
    return x, tendency


def closure_score(construct, parameters):
    training = [closure_case(seed, forcing) for seed, forcing in ((31, 6.0), (43, 8.0))]
    xtrain = np.concatenate([x.ravel() for x, _ in training])
    ytrain = np.concatenate([y.ravel() for _, y in training])
    coeff = finite(construct(xtrain.copy(), ytrain.copy()), (6,))
    cases = []
    for seed, forcing in ((107, 6.0), (211, 8.0), (307, 10.0)):
        x, truth = closure_case(seed, forcing)
        prediction = np.polynomial.polynomial.polyval(x, coeff)
        if not np.isfinite(prediction).all():
            raise CandidateError("Polynomial predictions must be finite")
        nmse = float(np.mean((prediction - truth)**2) / np.var(truth))
        cases.append({"forcing": forcing, "seed": seed, "normalized_mse": nmse})
    return float(np.mean([c["normalized_mse"] for c in cases])), {"per_case": cases, "coefficients": coeff.tolist()}
