"""Black-box optimization families (recreated protocols).

* ``BBOB-like`` single-objective functions f1-f24 with the standard function
  definitions, a random optimum shift and (where the original uses one) a random
  rotation, in a fixed dimension. These follow the COCO/BBOB definitions but are
  not COCO's official instances; scores are comparable within this suite only.
* An AOCC score (area over the convergence curve) as used by LLaMEA-BO.
* A numpy Gaussian-process Bayesian-optimization loop whose acquisition function
  is the candidate (FunBO-style), plus a cost-aware variant with a documented
  synthetic cost model (EvolCAF-style, cost model differs from the paper).
* Bi- and tri-objective test problems (ZDT1-6, DTLZ1/2/4/7) with exact 2D and
  3D hypervolume for multi-objective optimizer candidates (LLaMEA-MOBO-style).
"""
from __future__ import annotations

import math

import numpy as np

from .runtime import CandidateError, require


# ---------------------------------------------------------------------------
# BBOB-like functions
# ---------------------------------------------------------------------------

def _rotation(rng, d):
    q, r = np.linalg.qr(rng.standard_normal((d, d)))
    return q * np.sign(np.diag(r))


def _lambda(alpha, d):
    return np.diag(alpha ** (0.5 * np.arange(d) / max(d - 1, 1)))


def _tosz(x):
    xh = np.where(x != 0, np.log(np.abs(x)), 0.0)
    c1 = np.where(x > 0, 10.0, 5.5)
    c2 = np.where(x > 0, 7.9, 3.1)
    return np.sign(x) * np.exp(xh + 0.049 * (np.sin(c1 * xh) + np.sin(c2 * xh)))


def _tasy(x, beta):
    d = len(x)
    idx = np.arange(d) / max(d - 1, 1)
    out = x.copy()
    pos = x > 0
    out[pos] = x[pos] ** (1 + beta * idx[pos] * np.sqrt(x[pos]))
    return out


def _fpen(x):
    return float(np.sum(np.maximum(0, np.abs(x) - 5) ** 2))


class BBOBFunction:
    """One of the 24 BBOB functions, dimension d, random shift/rotation from a seed."""

    NAMES = {1: "Sphere", 2: "Ellipsoidal", 3: "Rastrigin", 4: "Büche-Rastrigin", 5: "Linear slope", 6: "Attractive sector",
             7: "Step ellipsoidal", 8: "Rosenbrock", 9: "Rosenbrock rotated", 10: "Ellipsoidal rotated", 11: "Discus", 12: "Bent cigar",
             13: "Sharp ridge", 14: "Different powers", 15: "Rastrigin rotated", 16: "Weierstrass", 17: "Schaffers F7", 18: "Schaffers F7 ill-conditioned",
             19: "Griewank-Rosenbrock", 20: "Schwefel", 21: "Gallagher 101 peaks", 22: "Gallagher 21 peaks", 23: "Katsuura", 24: "Lunacek bi-Rastrigin"}

    def __init__(self, fid, dim, instance=1):
        require(1 <= fid <= 24, "BBOB function id must be in 1..24")
        self.fid, self.dim = fid, dim
        rng = np.random.default_rng(1000 * fid + instance)
        self.xopt = rng.uniform(-4, 4, dim)
        self.fopt = float(np.round(rng.uniform(-100, 100), 2))
        self.R, self.Q = _rotation(rng, dim), _rotation(rng, dim)
        self.bounds = (-5.0, 5.0)
        if fid in (21, 22):
            n = 101 if fid == 21 else 21
            self.peaks = rng.uniform(-4.9, 4.9, (n, dim))
            self.peaks[0] = self.xopt
            self.weights = np.concatenate(([10.0], 1.1 + 8 * np.arange(1, n) / (n - 2)))
            alphas = 1000 ** (2 * np.arange(n) / (n - 1))
            rng.shuffle(alphas)
            alphas[0] = 1000.0
            self.C = [_lambda(a, dim) / a ** 0.25 for a in alphas]
        if fid == 24:
            self.xopt = 2.5 * np.sign(rng.standard_normal(dim)) * 0.5 * np.ones(dim) * np.sign(self.xopt + 1e-9)

    def __call__(self, x):
        x = np.asarray(x, dtype=float).ravel()
        require(x.shape == (self.dim,), f"expected a point of dimension {self.dim}")
        return float(self.raw(x) + self.fopt)

    def raw(self, x):  # noqa: C901 - one branch per BBOB function
        d, fid = self.dim, self.fid
        z = x - self.xopt
        if fid == 1:
            return float(np.sum(z ** 2))
        if fid == 2:
            z = _tosz(z)
            return float(np.sum(1e6 ** (np.arange(d) / max(d - 1, 1)) * z ** 2))
        if fid == 3:
            z = _lambda(10, d) @ _tasy(_tosz(z), 0.2)
            return float(10 * (d - np.sum(np.cos(2 * np.pi * z))) + np.sum(z ** 2))
        if fid == 4:
            z = _tosz(z)
            s = np.where((np.arange(d) % 2 == 0) & (z > 0), 100.0, 1.0) * 10 ** (0.5 * np.arange(d) / max(d - 1, 1))
            z = s * z
            return float(10 * (d - np.sum(np.cos(2 * np.pi * z))) + np.sum(z ** 2) + 100 * _fpen(x))
        if fid == 5:
            xo = 5 * np.sign(self.xopt + 1e-9)
            s = np.sign(xo) * 10 ** (np.arange(d) / max(d - 1, 1))
            zz = np.where(x * xo < 25, x, xo)
            return float(np.sum(5 * np.abs(s) - s * zz))
        if fid == 6:
            z = self.Q @ (_lambda(10, d) @ (self.R @ z))
            s = np.where(z * self.xopt > 0, 100.0, 1.0)
            return float(_tosz(np.array([np.sum((s * z) ** 2)]))[0] ** 0.9)
        if fid == 7:
            zh = _lambda(10, d) @ (self.R @ z)
            zt = np.where(np.abs(zh) > 0.5, np.floor(0.5 + zh), np.floor(0.5 + 10 * zh) / 10)
            zq = self.Q @ zt
            return float(0.1 * max(abs(zh[0]) / 1e4, np.sum(100 ** (np.arange(d) / max(d - 1, 1)) * zq ** 2)) + _fpen(x))
        if fid == 8:
            zz = max(1, math.sqrt(d) / 8) * z + 1
            return float(np.sum(100 * (zz[:-1] ** 2 - zz[1:]) ** 2 + (zz[:-1] - 1) ** 2))
        if fid == 9:
            zz = max(1, math.sqrt(d) / 8) * (self.R @ x) + 0.5
            return float(np.sum(100 * (zz[:-1] ** 2 - zz[1:]) ** 2 + (zz[:-1] - 1) ** 2))
        if fid == 10:
            zz = _tosz(self.R @ z)
            return float(np.sum(1e6 ** (np.arange(d) / max(d - 1, 1)) * zz ** 2))
        if fid == 11:
            zz = _tosz(self.R @ z)
            return float(1e6 * zz[0] ** 2 + np.sum(zz[1:] ** 2))
        if fid == 12:
            zz = self.R @ _tasy(self.R @ z, 0.5)
            return float(zz[0] ** 2 + 1e6 * np.sum(zz[1:] ** 2))
        if fid == 13:
            zz = self.Q @ (_lambda(10, d) @ (self.R @ z))
            return float(zz[0] ** 2 + 100 * math.sqrt(np.sum(zz[1:] ** 2)))
        if fid == 14:
            zz = self.R @ z
            return float(math.sqrt(np.sum(np.abs(zz) ** (2 + 4 * np.arange(d) / max(d - 1, 1)))))
        if fid == 15:
            zz = self.R @ (_lambda(10, d) @ (self.Q @ _tasy(_tosz(self.R @ z), 0.2)))
            return float(10 * (d - np.sum(np.cos(2 * np.pi * zz))) + np.sum(zz ** 2))
        if fid == 16:
            zz = self.R @ (_lambda(1 / 100, d) @ (self.Q @ _tosz(self.R @ z)))
            k = np.arange(12)
            f0 = np.sum(0.5 ** k * np.cos(2 * np.pi * 3 ** k * 0.5))
            total = sum(np.sum(0.5 ** k * np.cos(2 * np.pi * 3 ** k * (zi + 0.5))) for zi in zz)
            return float(10 * (total / d - f0) ** 3 + 10 / d * _fpen(x))
        if fid in (17, 18):
            cond = 10 if fid == 17 else 1000
            zz = _lambda(cond, d) @ (self.Q @ _tasy(self.R @ z, 0.5))
            s = np.sqrt(zz[:-1] ** 2 + zz[1:] ** 2)
            val = np.mean(np.sqrt(s) + np.sqrt(s) * np.sin(50 * s ** 0.2) ** 2) ** 2
            return float(val + 10 * _fpen(x))
        if fid == 19:
            zz = max(1, math.sqrt(d) / 8) * (self.R @ x) + 0.5
            s = 100 * (zz[:-1] ** 2 - zz[1:]) ** 2 + (zz[:-1] - 1) ** 2
            return float(10 / (d - 1) * np.sum(s / 4000 - np.cos(s)) + 10)
        if fid == 20:
            xh = 2 * np.sign(self.xopt + 1e-9) * x
            zh = xh.copy()
            zh[1:] = xh[1:] + 0.25 * (xh[:-1] - 2 * np.abs(self.xopt[:-1]))
            zz = 100 * (_lambda(10, d) @ (zh - 2 * np.abs(self.xopt)) + 2 * np.abs(self.xopt))
            return float(-1 / (100 * d) * np.sum(zz * np.sin(np.sqrt(np.abs(zz)))) + 4.189828872724339 + 100 * _fpen(zz / 100))
        if fid in (21, 22):
            best = 0.0
            for w, C, y in zip(self.weights, self.C, self.peaks):
                diff = self.R @ (x - y)
                best = max(best, w * math.exp(-1 / (2 * d) * float(diff @ C @ diff)))
            return float(_tosz(np.array([10 - best]))[0] ** 2 + _fpen(x))
        if fid == 23:
            zz = self.Q @ (_lambda(100, d) @ (self.R @ z))
            prod = 1.0
            for i, zi in enumerate(zz):
                total = sum(abs(2 ** j * zi - round(2 ** j * zi)) / 2 ** j for j in range(1, 33))
                prod *= (1 + (i + 1) * total) ** (10 / d ** 1.2)
            return float(10 / d ** 2 * (prod - 1) + _fpen(x))
        if fid == 24:
            mu0, s = 2.5, 1 - 1 / (2 * math.sqrt(d + 20) - 8.2)
            mu1 = -math.sqrt((mu0 ** 2 - 1) / s)
            xh = 2 * np.sign(self.xopt + 1e-9) * x
            zz = self.Q @ (_lambda(100, d) @ (self.R @ (xh - mu0)))
            return float(min(np.sum((xh - mu0) ** 2), d + s * np.sum((xh - mu1) ** 2)) + 10 * (d - np.sum(np.cos(2 * np.pi * zz))) + 1e4 * _fpen(x))
        raise CandidateError("unknown function")


class BudgetedFunction:
    """Wrap a function, enforce bounds and a budget, and record the best-so-far trajectory."""

    def __init__(self, function, budget, bounds):
        self.function, self.budget, self.bounds = function, budget, bounds
        self.evaluations, self.trajectory = 0, []
        self.best = math.inf

    def __call__(self, x):
        require(self.evaluations < self.budget, f"evaluation budget of {self.budget} exhausted")
        x = np.asarray(x, dtype=float).ravel()
        require(x.shape == (self.function.dim,) and np.all(np.isfinite(x)), "point must be a finite vector of the right dimension")
        x = np.clip(x, self.bounds[0], self.bounds[1])
        value = self.function(x)
        self.evaluations += 1
        self.best = min(self.best, value)
        self.trajectory.append(self.best)
        return value


def aocc(trajectory, fopt, budget, lower=1e-8, upper=1e2):
    """Area over the log convergence curve, in [0, 1], higher is better (LLaMEA-BO style)."""
    if not trajectory:
        return 0.0
    values = np.array(trajectory[:budget], dtype=float) - fopt
    values = np.clip(values, lower, upper)
    normalized = (np.log10(values) - math.log10(lower)) / (math.log10(upper) - math.log10(lower))
    padded = np.concatenate((normalized, np.full(max(0, budget - len(normalized)), normalized[-1])))
    return float(1 - np.mean(padded))


def bbob_suite_score(optimizer_class, fids, dim=5, budget=500, instances=(1, 2)):
    """Mean AOCC over several BBOB functions (LLaMEA-HPO style aggregate)."""
    return float(np.mean([bbob_optimizer_score(optimizer_class, fid, dim=dim, budget=budget, instances=instances) for fid in fids]))


def bbob_optimizer_score(optimizer_class, fid, dim=5, budget=500, instances=(1, 2, 3)):
    """Mean AOCC of ``Optimizer(budget, dim)(function)`` over several instances of one BBOB-like function."""
    scores = []
    for instance in instances:
        f = BBOBFunction(fid, dim, instance)
        wrapped = BudgetedFunction(f, budget, f.bounds)
        try:
            optimizer = optimizer_class(budget, dim)
            optimizer(wrapped)
        except CandidateError:
            raise
        except Exception as error:  # noqa: BLE001
            if wrapped.evaluations == 0:
                raise CandidateError(f"optimizer raised before evaluating anything: {type(error).__name__}: {error}") from None
        scores.append(aocc(wrapped.trajectory, f.fopt, budget))
    return float(np.mean(scores))


from .blackbox_bayes import (
    A3,
    A6,
    ALPHA,
    P3,
    P6,
    SYNTHETIC,
    _gp_sample,
    _hartmann,
    _matern52,
    bo_regret_score,
    gp_posterior,
)


from .blackbox_multiobjective import (
    MOO_PROBLEMS,
    _hv2d,
    _wfg_b_param,
    _wfg_b_poly,
    _wfg_concave,
    _wfg_r_nonsep,
    _wfg_r_sum,
    _wfg_s_decept,
    _wfg_s_linear,
    _wfg_s_multi,
    dtlz,
    hypervolume,
    moo_optimizer_score,
    pareto_front,
    problem_bounds,
    re_problem,
    reference_hypervolume,
    wfg,
    zdt,
)
