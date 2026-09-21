"""Learning-to-optimise problem families (FunL2O recreations) on locally generated instances.

FunL2O evolves optimisation algorithms and scores them on the DC3 quadratic
programs, the FSNet convex/nonconvex QP, QCQP and SOCP families, the IPM-MPNN,
PDHG-Net, learning-to-pivot and smart-initial-basis LP families, and the
predict-and-search / backdoor-branching MILP families. The papers' datasets are
not redistributed, so every family here is generated locally with a fixed seed
in the same mathematical form, with published-style sizes scaled down for CPU.

Candidate contract::

    solve(problem: dict, time_limit: float) -> x  (array of length problem["n"])

``problem`` carries the instance arrays (see ``instance``), ``kind`` and the
helper-friendly fields; ``objective(problem, x)`` and ``violation(problem, x)``
are available to candidates. Score per instance is the relative optimality gap
against an independent reference (cvxpy/Clarabel for convex problems, HiGHS for
LP and MILP, best-of-multistart SLSQP for nonconvex problems); an infeasible
solution (max violation above ``FEAS_TOL``), a non-finite one or a solve that
exceeds the time limit counts as gap 1. Lower is better.
"""
from __future__ import annotations

import math
import time
from functools import lru_cache

import numpy as np

from .runtime import CandidateError, require

FEAS_TOL = 1e-4
FAMILIES = ("dc3_qp", "dc3_nonconvex_qp", "dc3_nonsmooth_nonconvex_qp", "fsnet_qp", "fsnet_nonconvex_qp", "fsnet_nonsmooth_nonconvex_qp",
            "fsnet_qcqp", "fsnet_nonconvex_qcqp", "fsnet_nonsmooth_nonconvex_qcqp", "fsnet_socp", "fsnet_nonconvex_socp", "fsnet_nonsmooth_nonconvex_socp",
            "set_cover_lp", "independent_set_lp", "combinatorial_auction_lp", "generic_lp", "pagerank_lp", "combinatorial_auction_milp", "min_vertex_cover_milp")


# ---------------------------------------------------------------------------
# instance generators
# ---------------------------------------------------------------------------

def _qp_base(rng, n, n_eq, n_ineq, convex=True):
    a = rng.standard_normal((n, n)) / math.sqrt(n)
    if convex:
        q = a @ a.T + np.diag(rng.uniform(0.5, 2.0, n))
    else:
        eig = rng.uniform(-1.0, 2.0, n)
        basis, _ = np.linalg.qr(rng.standard_normal((n, n)))
        q = basis @ np.diag(eig) @ basis.T
    p = rng.standard_normal(n)
    x0 = rng.uniform(-1, 1, n)
    A = rng.standard_normal((n_eq, n)) / math.sqrt(n) if n_eq else np.zeros((0, n))
    b = A @ x0
    G = rng.standard_normal((n_ineq, n)) / math.sqrt(n)
    h = G @ x0 + rng.uniform(0.5, 1.5, n_ineq)
    return {"Q": q, "p": p, "A": A, "b": b, "G": G, "h": h, "lb": -np.full(n, 5.0), "ub": np.full(n, 5.0)}


def instance(kind, seed):
    """Deterministic instance of ``kind`` (see FAMILIES) as a dict of NumPy arrays."""
    require(kind in FAMILIES, f"unknown problem family {kind}")
    rng = np.random.default_rng(1000 + seed)
    nonconvex = "nonconvex" in kind
    nonsmooth = "nonsmooth" in kind
    prob = {"kind": kind, "seed": seed, "nonconvex": nonconvex, "nonsmooth": nonsmooth, "sin_weight": 1.0 if nonconvex else 0.0, "l1_weight": 0.5 if nonsmooth else 0.0}
    if kind.startswith("dc3"):
        n = 50
        prob.update(_qp_base(rng, n, 25, 25, convex=True), n=n, form="qp")  # DC3: convex Q, sin term for the nonconvex variant
    elif kind.startswith("fsnet_qp") or kind.startswith("fsnet_nonconvex_qp") or kind.startswith("fsnet_nonsmooth_nonconvex_qp"):
        n = 60
        prob.update(_qp_base(rng, n, 10, 40, convex=not nonconvex), n=n, form="qp")
    elif "qcqp" in kind:
        n, m = 40, 12
        base = _qp_base(rng, n, 5, 0, convex=True)
        H, g, r = [], [], []
        for _ in range(m):
            low = rng.standard_normal((n, 4)) / math.sqrt(n)
            h_i = low @ low.T
            if nonconvex:
                h_i -= 0.3 * np.eye(n) * rng.uniform(0.2, 1.0)
            g_i = rng.standard_normal(n) / math.sqrt(n)
            x0 = rng.uniform(-1, 1, n)
            H.append(h_i); g.append(g_i); r.append(0.5 * x0 @ h_i @ x0 + g_i @ x0 + rng.uniform(0.5, 1.5))
        prob.update({k: base[k] for k in ("Q", "p", "A", "b", "lb", "ub")}, G=np.zeros((0, n)), h=np.zeros(0), H=np.array(H), g=np.array(g), r=np.array(r), n=n, form="qcqp")
    elif "socp" in kind:
        n, m = 40, 8
        base = _qp_base(rng, n, 5, 0, convex=True)
        cones = []
        x0 = rng.uniform(-1, 1, n)
        for _ in range(m):
            A_i = rng.standard_normal((6, n)) / math.sqrt(n)
            b_i = rng.standard_normal(6) * 0.1
            c_i = rng.standard_normal(n) / math.sqrt(n)
            d_i = float(np.linalg.norm(A_i @ x0 + b_i) - c_i @ x0 + rng.uniform(0.5, 1.5))
            cones.append((A_i, b_i, c_i, d_i))
        prob.update({k: base[k] for k in ("A", "b", "lb", "ub")}, Q=np.zeros((n, n)) if not nonconvex else base["Q"] * 0.0, p=base["p"], G=np.zeros((0, n)), h=np.zeros(0),
                    cones=cones, n=n, form="socp")
    elif kind in ("set_cover_lp", "combinatorial_auction_lp", "independent_set_lp", "generic_lp", "pagerank_lp"):
        prob.update(_lp_instance(kind, rng), form="lp")
    else:  # MILP
        prob.update(_lp_instance(kind.replace("_milp", "_lp"), rng), form="milp")
        prob["integer"] = np.ones(prob["n"], dtype=bool)
    return prob


def _lp_instance(kind, rng):
    if kind == "set_cover_lp":
        m, n = 120, 240
        A = np.zeros((m, n))
        for j in range(n):
            A[rng.choice(m, rng.integers(3, 8), replace=False), j] = 1.0
        for i in np.flatnonzero(A.sum(1) == 0):
            A[i, rng.integers(n)] = 1.0
        c = rng.uniform(1, 10, n)
        return {"n": n, "c": c, "A_ub": -A, "b_ub": -np.ones(m), "A_eq": np.zeros((0, n)), "b_eq": np.zeros(0), "lb": np.zeros(n), "ub": np.ones(n)}
    if kind == "independent_set_lp":
        n, p = 120, 0.05
        edges = [(i, j) for i in range(n) for j in range(i + 1, n) if rng.random() < p]
        A = np.zeros((len(edges), n))
        for row, (i, j) in enumerate(edges):
            A[row, i] = A[row, j] = 1.0
        return {"n": n, "c": -np.ones(n), "A_ub": A, "b_ub": np.ones(len(edges)), "A_eq": np.zeros((0, n)), "b_eq": np.zeros(0), "lb": np.zeros(n), "ub": np.ones(n), "edges": np.array(edges)}
    if kind == "combinatorial_auction_lp":
        items, bids = 60, 150
        A = np.zeros((items, bids))
        prices = np.zeros(bids)
        for j in range(bids):
            bundle = rng.choice(items, rng.integers(2, 6), replace=False)
            A[bundle, j] = 1.0
            prices[j] = len(bundle) * rng.uniform(0.8, 1.2) + rng.uniform(0, 1)
        return {"n": bids, "c": -prices, "A_ub": A, "b_ub": np.ones(items), "A_eq": np.zeros((0, bids)), "b_eq": np.zeros(0), "lb": np.zeros(bids), "ub": np.ones(bids)}
    if kind == "generic_lp":
        m, n = 60, 120
        A = rng.standard_normal((m, n))
        x0 = rng.uniform(0, 1, n)
        return {"n": n, "c": rng.uniform(0, 1, n), "A_ub": np.zeros((0, n)), "b_ub": np.zeros(0), "A_eq": A, "b_eq": A @ x0, "lb": np.zeros(n), "ub": np.full(n, 10.0)}
    if kind == "min_vertex_cover_lp":
        n, p = 100, 0.06
        edges = [(i, j) for i in range(n) for j in range(i + 1, n) if rng.random() < p]
        A = np.zeros((len(edges), n))
        for row, (i, j) in enumerate(edges):
            A[row, i] = A[row, j] = 1.0
        return {"n": n, "c": np.ones(n), "A_ub": -A, "b_ub": -np.ones(len(edges)), "A_eq": np.zeros((0, n)), "b_eq": np.zeros(0), "lb": np.zeros(n), "ub": np.ones(n), "edges": np.array(edges)}
    if kind == "pagerank_lp":
        n, alpha = 150, 0.85
        adj = (rng.random((n, n)) < 0.05).astype(float)
        np.fill_diagonal(adj, 0)
        adj[adj.sum(1) == 0, rng.integers(n)] = 1.0
        P = adj / adj.sum(1, keepdims=True)
        A = np.eye(n) - alpha * P.T
        A = np.vstack([A, np.ones((1, n))])
        b = np.concatenate([np.full(n, (1 - alpha) / n), [1.0]])
        return {"n": n, "c": np.zeros(n), "A_ub": np.zeros((0, n)), "b_ub": np.zeros(0), "A_eq": A, "b_eq": b, "lb": np.zeros(n), "ub": np.ones(n)}
    raise CandidateError(kind)


# ---------------------------------------------------------------------------
# objective, feasibility, references
# ---------------------------------------------------------------------------

def objective(problem, x):
    x = np.asarray(x, dtype=float)
    if problem["form"] in ("lp", "milp"):
        return float(problem["c"] @ x)
    value = 0.5 * x @ problem["Q"] @ x + problem["p"] @ x
    value += problem["sin_weight"] * float(np.sum(np.sin(x)))
    value += problem["l1_weight"] * float(np.sum(np.abs(x)))
    return float(value)


def violation(problem, x):
    """Maximum constraint violation (absolute, in the instance's own units)."""
    x = np.asarray(x, dtype=float)
    worst = max(float(np.max(problem["lb"] - x, initial=0.0)), float(np.max(x - problem["ub"], initial=0.0)))
    if problem["form"] in ("lp", "milp"):
        if len(problem["b_ub"]):
            worst = max(worst, float(np.max(problem["A_ub"] @ x - problem["b_ub"], initial=0.0)))
        if len(problem["b_eq"]):
            worst = max(worst, float(np.max(np.abs(problem["A_eq"] @ x - problem["b_eq"]), initial=0.0)))
        if problem["form"] == "milp":
            worst = max(worst, float(np.max(np.abs(x - np.round(x)), initial=0.0)))
        return worst
    if len(problem["b"]):
        worst = max(worst, float(np.max(np.abs(problem["A"] @ x - problem["b"]), initial=0.0)))
    if len(problem["h"]):
        worst = max(worst, float(np.max(problem["G"] @ x - problem["h"], initial=0.0)))
    if problem["form"] == "qcqp":
        for h_i, g_i, r_i in zip(problem["H"], problem["g"], problem["r"]):
            worst = max(worst, float(0.5 * x @ h_i @ x + g_i @ x - r_i))
    if problem["form"] == "socp":
        for A_i, b_i, c_i, d_i in problem["cones"]:
            worst = max(worst, float(np.linalg.norm(A_i @ x + b_i) - c_i @ x - d_i))
    return worst


def scipy_constraints(problem):
    """Constraint dictionaries for scipy.optimize.minimize (SLSQP style) plus bounds."""
    cons = []
    if problem["form"] in ("lp", "milp"):
        if len(problem["b_ub"]):
            cons.append({"type": "ineq", "fun": lambda x: problem["b_ub"] - problem["A_ub"] @ x})
        if len(problem["b_eq"]):
            cons.append({"type": "eq", "fun": lambda x: problem["A_eq"] @ x - problem["b_eq"]})
    else:
        if len(problem["b"]):
            cons.append({"type": "eq", "fun": lambda x: problem["A"] @ x - problem["b"]})
        if len(problem["h"]):
            cons.append({"type": "ineq", "fun": lambda x: problem["h"] - problem["G"] @ x})
        if problem["form"] == "qcqp":
            for h_i, g_i, r_i in zip(problem["H"], problem["g"], problem["r"]):
                cons.append({"type": "ineq", "fun": (lambda x, h_i=h_i, g_i=g_i, r_i=r_i: r_i - 0.5 * x @ h_i @ x - g_i @ x)})
        if problem["form"] == "socp":
            for A_i, b_i, c_i, d_i in problem["cones"]:
                cons.append({"type": "ineq", "fun": (lambda x, A_i=A_i, b_i=b_i, c_i=c_i, d_i=d_i: c_i @ x + d_i - np.linalg.norm(A_i @ x + b_i))})
    return cons, list(zip(problem["lb"], problem["ub"]))


def _reference_convex(problem):
    import cvxpy as cp
    n = problem["n"]
    x = cp.Variable(n)
    if problem["form"] in ("lp", "milp"):
        x = cp.Variable(n, integer=True) if problem["form"] == "milp" else x
        obj = problem["c"] @ x
        cons = [x >= problem["lb"], x <= problem["ub"]]
        if len(problem["b_ub"]):
            cons.append(problem["A_ub"] @ x <= problem["b_ub"])
        if len(problem["b_eq"]):
            cons.append(problem["A_eq"] @ x == problem["b_eq"])
        prob = cp.Problem(cp.Minimize(obj), cons)
        prob.solve(solver=cp.HIGHS if hasattr(cp, "HIGHS") else cp.SCIPY)
        return float(prob.value), "highs"
    obj = 0.5 * cp.quad_form(x, cp.psd_wrap(problem["Q"])) + problem["p"] @ x
    cons = [x >= problem["lb"], x <= problem["ub"]]
    if len(problem["b"]):
        cons.append(problem["A"] @ x == problem["b"])
    if len(problem["h"]):
        cons.append(problem["G"] @ x <= problem["h"])
    if problem["form"] == "qcqp":
        for h_i, g_i, r_i in zip(problem["H"], problem["g"], problem["r"]):
            cons.append(0.5 * cp.quad_form(x, cp.psd_wrap(h_i)) + g_i @ x <= r_i)
    if problem["form"] == "socp":
        for A_i, b_i, c_i, d_i in problem["cones"]:
            cons.append(cp.SOC(c_i @ x + d_i, A_i @ x + b_i))
    prob = cp.Problem(cp.Minimize(obj), cons)
    prob.solve(solver=cp.CLARABEL)
    return float(prob.value), "clarabel"


def _reference_nonconvex(problem, starts=8):
    from scipy.optimize import minimize
    cons, bounds = scipy_constraints(problem)
    rng = np.random.default_rng(7)
    best = math.inf
    for k in range(starts):
        x0 = np.zeros(problem["n"]) if k == 0 else rng.uniform(-1, 1, problem["n"])
        res = minimize(lambda z: objective(problem, z), x0, method="SLSQP", constraints=cons, bounds=bounds, options={"maxiter": 500, "ftol": 1e-10})
        if violation(problem, res.x) <= FEAS_TOL and res.fun < best:
            best = float(res.fun)
    require(math.isfinite(best), "no feasible reference solution found")
    return best, "slsqp-multistart (best found, not proven optimal)"


@lru_cache(maxsize=256)
def reference(kind, seed):
    problem = instance(kind, seed)
    if problem["nonconvex"] or problem["nonsmooth"]:
        return _reference_nonconvex(problem)
    return _reference_convex(problem)


def l2o_score(solve, kind, seeds=(0, 1, 2, 3, 4), time_limit=5.0):
    """Mean relative optimality gap of ``solve`` over the instances (lower is better)."""
    rows = []
    for seed in seeds:
        problem = instance(kind, seed)
        best, method = reference(kind, seed)
        start = time.perf_counter()
        try:
            x = solve({k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in problem.items()}, time_limit)
        except CandidateError:
            raise
        except Exception as error:  # noqa: BLE001
            raise CandidateError(f"solve raised {type(error).__name__}: {error}") from None
        elapsed = time.perf_counter() - start
        try:
            x = np.asarray(x, dtype=float).reshape(-1)
        except (TypeError, ValueError):
            raise CandidateError("solve must return a numeric vector") from None
        require(x.shape == (problem["n"],), f"solve must return {problem['n']} values")
        finite = bool(np.all(np.isfinite(x)))
        viol = violation(problem, x) if finite else math.inf
        value = objective(problem, x) if finite else math.inf
        feasible = finite and viol <= FEAS_TOL and elapsed <= time_limit * 1.5
        gap = min(1.0, max(0.0, (value - best) / (abs(best) + 1.0))) if feasible else 1.0
        rows.append({"seed": seed, "objective": value if finite else None, "reference": best, "violation": viol if finite else None, "seconds": round(elapsed, 4), "feasible": feasible, "gap": gap, "reference_method": method})
    return float(np.mean([r["gap"] for r in rows])), {"instances": rows, "time_limit": time_limit}
