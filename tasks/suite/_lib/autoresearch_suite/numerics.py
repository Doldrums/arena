"""Numerical-methods design families (A2DEPT / DGA2D style, recreated protocols).

* ODE integration: the candidate implements ``integrate(f, t_span, y0) -> y_end``
  for a named initial-value problem; the evaluator counts right-hand-side
  evaluations and compares with a tight scipy reference solution. Score:
  ``-log10(relative error) - lambda * log10(evaluations)`` with lambda = 0.5.
* Root finding: ``find_root(f, x0) -> x`` (scalar) or ``find_root_system(F, x0)
  -> x`` (2-D); score is the success rate on a fixed problem set, discounted by
  the mean number of function evaluations.
* Feedback control: ``controller(state, t) -> u`` for the double integrator,
  pendulum swing-up and cart-pole; score is ``-log10(1 + cumulative cost)``.

These are recreated from the papers' task descriptions; the paper's exact
instances, tolerances and weights are not public.
"""
from __future__ import annotations

import math

import numpy as np

from .runtime import CandidateError, require

LAMBDA = 0.5


# ---------------------------------------------------------------------------
# ODE problems
# ---------------------------------------------------------------------------

def _heat_matrix(n):
    A = np.zeros((n, n))
    for i in range(n):
        A[i, i] = -2
        if i:
            A[i, i - 1] = 1
        if i < n - 1:
            A[i, i + 1] = 1
    return A * (n + 1) ** 2


def _heat2d(n):
    A1 = _heat_matrix(n) / (n + 1) ** 2
    I = np.eye(n)
    return (np.kron(A1, I) + np.kron(I, A1)) * (n + 1) ** 2 / 10


ODE_PROBLEMS = {
    "harmonic_oscillator": {"f": lambda t, y: np.array([y[1], -y[0]]), "y0": [1.0, 0.0], "t_span": (0.0, 10.0), "stiff": False},
    "van_der_pol": {"f": lambda t, y: np.array([y[1], 5 * (1 - y[0] ** 2) * y[1] - y[0]]), "y0": [2.0, 0.0], "t_span": (0.0, 10.0), "stiff": True},
    "robertson": {"f": lambda t, y: np.array([-0.04 * y[0] + 1e4 * y[1] * y[2], 0.04 * y[0] - 1e4 * y[1] * y[2] - 3e7 * y[1] ** 2, 3e7 * y[1] ** 2]), "y0": [1.0, 0.0, 0.0], "t_span": (0.0, 40.0), "stiff": True},
    "heat_equation_n20": {"f": (lambda A: (lambda t, y: A @ y))(_heat_matrix(20)), "y0": list(np.sin(np.pi * np.arange(1, 21) / 21)), "t_span": (0.0, 0.1), "stiff": True},
    "lotka_volterra": {"f": lambda t, y: np.array([1.5 * y[0] - y[0] * y[1], -3 * y[1] + y[0] * y[1]]), "y0": [10.0, 5.0], "t_span": (0.0, 5.0), "stiff": False},
    "lorenz": {"f": lambda t, y: np.array([10 * (y[1] - y[0]), y[0] * (28 - y[2]) - y[1], y[0] * y[1] - 8 / 3 * y[2]]), "y0": [1.0, 1.0, 1.0], "t_span": (0.0, 2.0), "stiff": False},
    "stiff_linear_15": {"f": (lambda A: (lambda t, y: A @ y))(np.diag(-np.logspace(0, 3, 15))), "y0": list(np.ones(15)), "t_span": (0.0, 1.0), "stiff": True},
    "heat2d_10x10": {"f": (lambda A: (lambda t, y: A @ y))(_heat2d(10)), "y0": list(np.random.default_rng(0).random(100)), "t_span": (0.0, 0.05), "stiff": True},
    "convection_diffusion_100": {"f": (lambda A: (lambda t, y: A @ y))(_heat_matrix(100) / (101 ** 2) * 100 - 50 * (np.eye(100, k=1) - np.eye(100, k=-1)) * 101 / 2 / 101), "y0": list(np.exp(-100 * (np.arange(1, 101) / 101 - 0.3) ** 2)), "t_span": (0.0, 0.5), "stiff": True},
}


def reference_solution(name):
    from scipy.integrate import solve_ivp
    p = ODE_PROBLEMS[name]
    sol = solve_ivp(p["f"], p["t_span"], np.array(p["y0"], dtype=float), method="Radau" if p["stiff"] else "DOP853", rtol=1e-11, atol=1e-13)
    require(sol.success, "reference integration failed")
    return sol.y[:, -1]


def ode_score(integrate, name, lam=LAMBDA):
    """Score ``-log10(rel_err) - lam*log10(n_evals)`` of the candidate integrator on one problem. Higher is better."""
    p = ODE_PROBLEMS[name]
    counter = {"n": 0}

    def f(t, y):
        counter["n"] += 1
        require(counter["n"] <= 2_000_000, "too many right-hand-side evaluations")
        return p["f"](float(t), np.asarray(y, dtype=float))

    reference = reference_solution(name)
    try:
        result = integrate(f, tuple(p["t_span"]), np.array(p["y0"], dtype=float))
    except CandidateError:
        raise
    except Exception as error:  # noqa: BLE001
        raise CandidateError(f"integrate raised {type(error).__name__}: {error}") from None
    y_end = np.asarray(result, dtype=float).ravel()
    require(y_end.shape == reference.shape and np.all(np.isfinite(y_end)), "integrate must return the finite state vector at the end of t_span")
    require(counter["n"] > 0, "integrate did not evaluate the right-hand side")
    rel = float(np.linalg.norm(y_end - reference) / max(np.linalg.norm(reference), 1e-12))
    rel = max(rel, 1e-14)
    return float(-math.log10(rel) - lam * math.log10(counter["n"]))


# ---------------------------------------------------------------------------
# Root finding
# ---------------------------------------------------------------------------

def _poly(coeffs):
    return lambda x: float(np.polyval(coeffs, x))


ROOT_PROBLEMS = {
    "smooth_polynomials": [(_poly(np.poly([1.0, -2.0, 3.5])), 0.2, 1.0), (_poly(np.poly([0.5, 4.0, -1.5, 2.0])), 0.0, 0.5), (_poly(np.poly([-3.0, 1.0, 2.0, 5.0, -0.5])), 1.5, 1.0)],
    "ill_conditioned": [(lambda x: (x - 1.0) ** 3, 0.0, 1.0), (lambda x: (x - 2.0) ** 5 * (x + 1.0), 1.0, 2.0), (lambda x: math.exp(x) - 1 - x - x * x / 2 - x ** 3 / 6, 0.5, 0.0)],
    "oscillatory": [(lambda x: math.sin(10 * x) + 0.5 * x, 0.1, 0.0), (lambda x: math.cos(5 * x) - x / 3, 0.0, 0.3096), (lambda x: x * math.sin(x) - 1, 1.0, 1.1142)],
}
SYSTEM_PROBLEMS = [
    (lambda v: np.array([v[0] ** 2 + v[1] ** 2 - 4, v[0] * v[1] - 1]), np.array([1.0, 0.5])),
    (lambda v: np.array([math.exp(v[0]) - v[1], v[0] + math.cos(v[1]) - 1.5]), np.array([0.0, 1.0])),
    (lambda v: np.array([v[0] ** 3 - v[1] - 1, v[1] ** 2 - v[0] + 0.5]), np.array([1.0, 0.0])),
]


def root_finding_score(find_root, group, tol=1e-8, max_evals=500):
    """Success rate (|f(x)| <= tol) discounted by function evaluations. Higher is better."""
    problems = ROOT_PROBLEMS[group]
    successes, evals = 0, []
    for f, x0, _ in problems:
        counter = {"n": 0}

        def wrapped(x, f=f):
            counter["n"] += 1
            require(counter["n"] <= max_evals, "too many function evaluations")
            return f(float(x))

        try:
            x = find_root(wrapped, float(x0))
            ok = x is not None and math.isfinite(float(x)) and abs(f(float(x))) <= tol
        except CandidateError:
            ok = False
        except Exception:  # noqa: BLE001
            ok = False
        successes += int(ok)
        evals.append(counter["n"] if counter["n"] else max_evals)
    return float(successes / len(problems) * (1 - 0.5 * math.log10(max(1.0, float(np.mean(evals)))) / math.log10(max_evals)))


def root_system_score(find_root_system, tol=1e-8, max_evals=500):
    successes, evals = 0, []
    for F, x0 in SYSTEM_PROBLEMS:
        counter = {"n": 0}

        def wrapped(v, F=F):
            counter["n"] += 1
            require(counter["n"] <= max_evals, "too many function evaluations")
            return F(np.asarray(v, dtype=float))

        try:
            x = np.asarray(find_root_system(wrapped, x0.copy()), dtype=float)
            ok = x.shape == (2,) and np.all(np.isfinite(x)) and np.linalg.norm(F(x)) <= tol
        except CandidateError:
            ok = False
        except Exception:  # noqa: BLE001
            ok = False
        successes += int(ok)
        evals.append(counter["n"] if counter["n"] else max_evals)
    return float(successes / len(SYSTEM_PROBLEMS) * (1 - 0.5 * math.log10(max(1.0, float(np.mean(evals)))) / math.log10(max_evals)))


# ---------------------------------------------------------------------------
# Feedback control
# ---------------------------------------------------------------------------

def _simulate(dynamics, controller, x0, dt, horizon, u_max, cost_fn):
    x = np.array(x0, dtype=float)
    cost, t = 0.0, 0.0
    for _ in range(horizon):
        u = controller(x.copy(), t)
        u = float(np.clip(float(u), -u_max, u_max))
        k1 = dynamics(x, u)
        k2 = dynamics(x + dt / 2 * k1, u)
        k3 = dynamics(x + dt / 2 * k2, u)
        k4 = dynamics(x + dt * k3, u)
        x = x + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        require(np.all(np.isfinite(x)), "state diverged")
        cost += cost_fn(x, u) * dt
        t += dt
    return cost


def control_score(controller, name):
    """``-log10(1 + cumulative quadratic cost)`` over a fixed horizon; higher is better."""
    if name == "double_integrator":
        dyn = lambda x, u: np.array([x[1], u])
        cost = _simulate(dyn, controller, [1.0, 0.0], 0.02, 500, 2.0, lambda x, u: x[0] ** 2 + 0.1 * x[1] ** 2 + 0.01 * u ** 2)
    elif name == "pendulum_swing_up":
        g, l, m, b = 9.81, 1.0, 1.0, 0.1
        dyn = lambda x, u: np.array([x[1], (u - b * x[1] - m * g * l * math.sin(x[0])) / (m * l * l)])
        cost = _simulate(dyn, controller, [math.pi, 0.0], 0.02, 500, 5.0, lambda x, u: (1 - math.cos(x[0])) + 0.1 * x[1] ** 2 + 0.001 * u ** 2)
    elif name == "cartpole":
        mc, mp, l, g = 1.0, 0.1, 0.5, 9.81

        def dyn(x, u):
            _, xdot, th, thdot = x
            s, c = math.sin(th), math.cos(th)
            temp = (u + mp * l * thdot ** 2 * s) / (mc + mp)
            thacc = (g * s - c * temp) / (l * (4 / 3 - mp * c * c / (mc + mp)))
            xacc = temp - mp * l * thacc * c / (mc + mp)
            return np.array([xdot, xacc, thdot, thacc])
        cost = _simulate(dyn, controller, [0.0, 0.0, 0.2, 0.0], 0.02, 500, 10.0, lambda x, u: x[2] ** 2 + 0.1 * x[0] ** 2 + 0.01 * x[3] ** 2 + 0.001 * u ** 2)
    else:
        raise ValueError(name)
    return float(-math.log10(1 + cost))
