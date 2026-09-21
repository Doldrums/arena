"""Multiobjective benchmark functions and hypervolume scoring."""
from __future__ import annotations

from .blackbox import (
    CandidateError,
    math,
    np,
    require,
)

# ---------------------------------------------------------------------------
# Multi-objective test problems and hypervolume
# ---------------------------------------------------------------------------

def zdt(name, x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    if name == "zdt1":
        g = 1 + 9 * np.sum(x[1:]) / (n - 1)
        return np.array([x[0], g * (1 - math.sqrt(x[0] / g))])
    if name == "zdt2":
        g = 1 + 9 * np.sum(x[1:]) / (n - 1)
        return np.array([x[0], g * (1 - (x[0] / g) ** 2)])
    if name == "zdt3":
        g = 1 + 9 * np.sum(x[1:]) / (n - 1)
        return np.array([x[0], g * (1 - math.sqrt(x[0] / g) - x[0] / g * math.sin(10 * math.pi * x[0]))])
    if name == "zdt4":
        g = 1 + 10 * (n - 1) + np.sum(x[1:] ** 2 - 10 * np.cos(4 * math.pi * x[1:]))
        return np.array([x[0], g * (1 - math.sqrt(x[0] / g))])
    if name == "zdt6":
        f1 = 1 - math.exp(-4 * x[0]) * math.sin(6 * math.pi * x[0]) ** 6
        g = 1 + 9 * (np.sum(x[1:]) / (n - 1)) ** 0.25
        return np.array([f1, g * (1 - (f1 / g) ** 2)])
    raise ValueError(name)


def dtlz(name, x, m=3):
    x = np.asarray(x, dtype=float)
    k = len(x) - m + 1
    xm = x[m - 1:]
    if name == "dtlz1":
        g = 100 * (k + np.sum((xm - 0.5) ** 2 - np.cos(20 * math.pi * (xm - 0.5))))
        f = []
        for i in range(m):
            v = 0.5 * (1 + g)
            for j in range(m - 1 - i):
                v *= x[j]
            if i > 0:
                v *= 1 - x[m - 1 - i]
            f.append(v)
        return np.array(f)
    if name in ("dtlz2", "dtlz4"):
        g = np.sum((xm - 0.5) ** 2)
        xa = x ** 100 if name == "dtlz4" else x
        f = []
        for i in range(m):
            v = 1 + g
            for j in range(m - 1 - i):
                v *= math.cos(xa[j] * math.pi / 2)
            if i > 0:
                v *= math.sin(xa[m - 1 - i] * math.pi / 2)
            f.append(v)
        return np.array(f)
    if name == "dtlz7":
        g = 1 + 9 * np.sum(xm) / k
        f = list(x[:m - 1])
        h = m - np.sum(np.array(f) / (1 + g) * (1 + np.sin(3 * math.pi * np.array(f))))
        f.append((1 + g) * h)
        return np.array(f)
    raise ValueError(name)


# --- WFG toolkit (Huband et al. 2006), ported from the published definitions --------

def _wfg_b_poly(y, a):
    return y ** a


def _wfg_b_param(y, u, a, b, c):
    v = a - (1 - 2 * u) * abs(math.floor(0.5 - u) + a)
    return y ** (b + (c - b) * v)


def _wfg_s_linear(y, a):
    return abs(y - a) / abs(math.floor(a - y) + a)


def _wfg_s_decept(y, a, b, c):
    t1 = math.floor(y - a + b) * (1 - c + (a - b) / b) / (a - b)
    t2 = math.floor(a + b - y) * (1 - c + (1 - a - b) / b) / (1 - a - b)
    return 1 + (abs(y - a) - b) * (t1 + t2 + 1 / b)


def _wfg_s_multi(y, a, b, c):
    t = abs(y - c) / (2 * (math.floor(c - y) + c))
    return (1 + math.cos((4 * a + 2) * math.pi * (0.5 - t)) + 4 * b * t ** 2) / (b + 2)


def _wfg_r_sum(y, w):
    y, w = np.asarray(y, dtype=float), np.asarray(w, dtype=float)
    return float(np.sum(w * y) / np.sum(w))


def _wfg_r_nonsep(y, a):
    y = np.asarray(y, dtype=float)
    n = len(y)
    total = 0.0
    for j in range(n):
        total += y[j]
        for k in range(a - 1):
            total += abs(y[j] - y[(1 + j + k) % n])
    return float(total / (n / a * math.ceil(a / 2) * (1 + 2 * a - 2 * math.ceil(a / 2))))


def _wfg_concave(x, m):
    f = []
    for i in range(1, m + 1):
        v = 1.0
        for j in range(1, m - i + 1):
            v *= math.sin(x[j - 1] * math.pi / 2)
        if i > 1:
            v *= math.cos(x[m - i] * math.pi / 2)
        f.append(v)
    return np.array(f)


def wfg(name, z, m=3, k=4):
    """WFG4, WFG7 and WFG9 with ``k`` position and ``len(z)-k`` distance parameters; z_i in [0, 2i]."""
    z = np.asarray(z, dtype=float)
    n = len(z)
    l = n - k
    y = z / (2 * np.arange(1, n + 1))
    if name == "wfg4":
        t1 = np.array([_wfg_s_multi(v, 30, 10, 0.35) for v in y])
        t2 = [_wfg_r_sum(t1[(i - 1) * k // (m - 1):i * k // (m - 1)], np.ones(k // (m - 1))) for i in range(1, m)]
        t2.append(_wfg_r_sum(t1[k:], np.ones(l)))
    elif name == "wfg7":
        t1 = np.array([_wfg_b_param(y[i], _wfg_r_sum(y[i + 1:], np.ones(n - i - 1)), 0.98 / 49.98, 0.02, 50) if i < k else y[i] for i in range(n)])
        t2 = np.array([t1[i] if i < k else _wfg_s_linear(t1[i], 0.35) for i in range(n)])
        t3 = [_wfg_r_sum(t2[(i - 1) * k // (m - 1):i * k // (m - 1)], np.ones(k // (m - 1))) for i in range(1, m)]
        t3.append(_wfg_r_sum(t2[k:], np.ones(l)))
        t2 = t3
    elif name == "wfg9":
        t1 = np.array([_wfg_b_param(y[i], _wfg_r_sum(y[i + 1:], np.ones(n - i - 1)), 0.98 / 49.98, 0.02, 50) if i < n - 1 else y[i] for i in range(n)])
        t2 = np.array([_wfg_s_decept(t1[i], 0.35, 0.001, 0.05) if i < k else _wfg_s_multi(t1[i], 30, 95, 0.35) for i in range(n)])
        t3 = [_wfg_r_nonsep(t2[(i - 1) * k // (m - 1):i * k // (m - 1)], k // (m - 1)) for i in range(1, m)]
        t3.append(_wfg_r_nonsep(t2[k:], l))
        t2 = t3
    else:
        raise ValueError(name)
    t = np.clip(np.asarray(t2, dtype=float), 0, 1)
    x = np.array([max(t[m - 1], 1) * (t[i] - 0.5) + 0.5 for i in range(m - 1)] + [t[m - 1]])
    h = _wfg_concave(x, m)
    return x[m - 1] + 2 * np.arange(1, m + 1) * h


def re_problem(name, x):
    """RE21 (four-bar truss), RE34 (vehicle crashworthiness), RE37 (rocket injector) from Tanabe & Ishibuchi 2020."""
    x = np.asarray(x, dtype=float)
    if name == "re21":
        F, E, L, sigma = 10.0, 2e5, 200.0, 10.0
        x1, x2, x3, x4 = x
        f1 = L * (2 * x1 + math.sqrt(2) * x2 + math.sqrt(x3) + x4)
        f2 = F * L / E * (2 / x1 + 2 * math.sqrt(2) / x2 - 2 * math.sqrt(2) / x3 + 2 / x4)
        return np.array([f1, f2])
    if name == "re34":
        x1, x2, x3, x4, x5 = x
        f1 = 1640.2823 + 2.3573285 * x1 + 2.3220035 * x2 + 4.5688768 * x3 + 7.7213633 * x4 + 4.4559504 * x5
        f2 = (6.5856 + 1.15 * x1 - 1.0427 * x2 + 0.9738 * x3 + 0.8364 * x4 - 0.3695 * x1 * x4 + 0.0861 * x1 * x5 + 0.3628 * x2 * x4
              - 0.1106 * x1 ** 2 - 0.3437 * x3 ** 2 + 0.1764 * x4 ** 2)
        f3 = (-0.0551 + 0.0181 * x1 + 0.1024 * x2 + 0.0421 * x3 - 0.0073 * x1 * x2 + 0.024 * x2 * x3 - 0.0118 * x2 * x4 - 0.0204 * x3 * x4
              - 0.008 * x3 * x5 - 0.0241 * x2 ** 2 + 0.0109 * x4 ** 2)
        return np.array([f1, f2, f3])
    if name == "re37":
        xa, xh, xo, xr = x
        f1 = (0.692 + 0.477 * xa - 0.687 * xh - 0.080 * xo - 0.0650 * xr - 0.167 * xa ** 2 - 0.0129 * xh * xa + 0.0796 * xh ** 2
              - 0.0634 * xo * xa - 0.0257 * xo * xh + 0.0877 * xo ** 2 - 0.0521 * xr * xa + 0.00156 * xr * xh + 0.00198 * xr * xo + 0.0184 * xr ** 2)
        f2 = (0.153 - 0.322 * xa + 0.396 * xh + 0.424 * xo + 0.0226 * xr + 0.175 * xa ** 2 + 0.0185 * xh * xa - 0.0701 * xh ** 2
              - 0.251 * xo * xa + 0.179 * xo * xh + 0.0150 * xo ** 2 + 0.0134 * xr * xa + 0.0296 * xr * xh + 0.0752 * xr * xo + 0.0192 * xr ** 2)
        f3 = (0.370 - 0.205 * xa + 0.0307 * xh + 0.108 * xo + 1.019 * xr - 0.135 * xa ** 2 + 0.0141 * xh * xa + 0.0998 * xh ** 2
              + 0.208 * xo * xa - 0.0301 * xo * xh - 0.226 * xo ** 2 + 0.353 * xr * xa - 0.0497 * xr * xo - 0.423 * xr ** 2 + 0.202 * xh * xa ** 2
              - 0.281 * xh ** 2 * xa - 0.342 * xh ** 2 * xo - 0.245 * xh ** 2 * xr + 0.281 * xo ** 2 * xh - 0.184 * xr ** 2 * xa + 0.281 * xr ** 2 * xh)
        return np.array([f1, f2, f3])
    raise ValueError(name)


MOO_PROBLEMS = {
    # Reference points are generous multiples of the front's nadir so that weak
    # optimizers still receive partial credit; normalization uses the same point.
    "zdt1": (lambda x: zdt("zdt1", x), 30, 2, np.array([11.0, 11.0]), (0, 1)),
    "zdt2": (lambda x: zdt("zdt2", x), 30, 2, np.array([11.0, 11.0]), (0, 1)),
    "zdt3": (lambda x: zdt("zdt3", x), 30, 2, np.array([11.0, 11.0]), (0, 1)),
    "zdt4": (lambda x: zdt("zdt4", x), 10, 2, np.array([11.0, 400.0]), (0, 1)),
    "zdt6": (lambda x: zdt("zdt6", x), 10, 2, np.array([11.0, 11.0]), (0, 1)),
    "dtlz1": (lambda x: dtlz("dtlz1", x), 7, 3, np.array([400.0, 400.0, 400.0]), (0, 1)),
    "dtlz2": (lambda x: dtlz("dtlz2", x), 12, 3, np.array([2.5, 2.5, 2.5]), (0, 1)),
    "dtlz4": (lambda x: dtlz("dtlz4", x), 12, 3, np.array([2.5, 2.5, 2.5]), (0, 1)),
    "dtlz7": (lambda x: dtlz("dtlz7", x), 22, 3, np.array([1.1, 1.1, 25.0]), (0, 1)),
    # WFG variables live in [0, 2i]; the optimizer receives per-variable bounds.
    "wfg4": (lambda x: wfg("wfg4", x), 12, 3, np.array([3.0, 5.0, 7.0]), "wfg"),
    "wfg7": (lambda x: wfg("wfg7", x), 12, 3, np.array([3.0, 5.0, 7.0]), "wfg"),
    "wfg9": (lambda x: wfg("wfg9", x), 12, 3, np.array([3.0, 5.0, 7.0]), "wfg"),
    "re21": (lambda x: re_problem("re21", x), 4, 2, np.array([3000.0, 0.06]), "re21"),
    "re34": (lambda x: re_problem("re34", x), 5, 3, np.array([1705.0, 12.0, 0.3]), (1, 3)),
    "re37": (lambda x: re_problem("re37", x), 4, 3, np.array([1.1, 1.3, 1.1]), (0, 1)),
}


def problem_bounds(name):
    f, dim, n_obj, ref, kind = MOO_PROBLEMS[name]
    if kind == "wfg":
        return [(0.0, 2.0 * (i + 1)) for i in range(dim)]
    if kind == "re21":
        a = 10.0 / 10.0
        return [(a, 3 * a), (math.sqrt(2) * a, 3 * a), (math.sqrt(2) * a, 3 * a), (a, 3 * a)]
    return [(float(kind[0]), float(kind[1]))] * dim


def pareto_front(points):
    pts = np.asarray(points, dtype=float)
    keep = np.ones(len(pts), dtype=bool)
    for i, p in enumerate(pts):
        if keep[i]:
            dominated = np.all(pts <= p, axis=1) & np.any(pts < p, axis=1)
            keep[i] = not np.any(dominated)
    return pts[keep]


def _hv2d(pts, ref):
    """Exact 2-D hypervolume by a monotone sweep (no explicit Pareto filtering needed)."""
    if len(pts) == 0:
        return 0.0
    order = pts[np.lexsort((pts[:, 1], pts[:, 0]))]
    total, prev_y = 0.0, ref[1]
    for x, y in order:
        if y < prev_y:
            total += (ref[0] - x) * (prev_y - y)
            prev_y = y
    return float(total)


def hypervolume(points, ref):
    """Exact hypervolume for 2 or 3 minimization objectives (points dominated by ref only)."""
    pts = np.asarray(points, dtype=float)
    pts = pts[np.all(pts < ref, axis=1)]
    if len(pts) == 0:
        return 0.0
    if pts.shape[1] == 2:
        return _hv2d(pts, ref)
    if pts.shape[1] == 3:
        pts = pareto_front(pts)
        levels = list(np.unique(pts[:, 2])) + [ref[2]]
        total = 0.0
        for lo, hi in zip(levels[:-1], levels[1:]):
            total += _hv2d(pts[pts[:, 2] <= lo][:, :2], ref[:2]) * (hi - lo)
        return float(total)
    raise ValueError("hypervolume supports 2 or 3 objectives")


def reference_hypervolume(name, samples=2000):
    """Hypervolume of a dense sample of the known Pareto front, for normalization."""
    ref = MOO_PROBLEMS[name][3]
    t = np.linspace(0, 1, samples)
    if name in ("zdt1", "zdt4"):
        front = np.column_stack([t, 1 - np.sqrt(t)])
    elif name in ("zdt2", "zdt6"):
        front = np.column_stack([t, 1 - t ** 2]) if name == "zdt2" else np.column_stack([t, 1 - t ** 2])
    elif name == "zdt3":
        front = pareto_front(np.column_stack([t, 1 - np.sqrt(t) - t * np.sin(10 * math.pi * t)]))
    elif name == "dtlz1":
        a = np.random.default_rng(0).random((samples, 3))
        a = a / a.sum(axis=1, keepdims=True) * 0.5
        front = a
    elif name in ("dtlz2", "dtlz4"):
        a = np.abs(np.random.default_rng(0).standard_normal((samples, 3)))
        front = a / np.linalg.norm(a, axis=1, keepdims=True)
    elif name == "dtlz7":
        g = np.random.default_rng(0).random((samples, 2))
        h = 3 - np.sum(g / 2 * (1 + np.sin(3 * math.pi * g)), axis=1)
        front = pareto_front(np.column_stack([g, 2 * h]))
    elif name.startswith("wfg"):
        # The WFG Pareto front is the concave shape h scaled by 2i (distance parameters at 0.35 => t_m = 0).
        a = np.abs(np.random.default_rng(0).standard_normal((samples, 3)))
        a = a / np.linalg.norm(a, axis=1, keepdims=True)
        front = a * np.array([2.0, 4.0, 6.0])
    elif name.startswith("re"):
        # Empirical front from a large fixed random sample of the design space (RE problems have no closed-form front).
        rng = np.random.default_rng(0)
        bounds = problem_bounds(name)
        X = np.array([[rng.uniform(lo, hi) for lo, hi in bounds] for _ in range(4000)])
        front = pareto_front(np.array([MOO_PROBLEMS[name][0](x) for x in X]))
    else:
        raise ValueError(name)
    return hypervolume(front, ref)


def moo_optimizer_score(optimizer_class, name, budget=200, seeds=(0, 1)):
    """Mean normalized hypervolume reached by ``Optimizer(budget, dim, n_obj)(problem, bounds)``.

    The candidate receives a callable ``problem(x) -> objectives`` (minimize
    all) that enforces the evaluation budget, and must return the array of
    points it evaluated (or ``None`` to use the recorded evaluations).
    """
    f, dim, n_obj, ref, _ = MOO_PROBLEMS[name]
    bounds = problem_bounds(name)
    lo = np.array([b[0] for b in bounds])
    hi = np.array([b[1] for b in bounds])
    ref_hv = reference_hypervolume(name)
    scores = []
    for seed in seeds:
        evaluated = []

        def problem(x):
            require(len(evaluated) < budget, f"evaluation budget of {budget} exhausted")
            x = np.clip(np.asarray(x, dtype=float).ravel(), lo, hi)
            require(x.shape == (dim,), f"expected points of dimension {dim}")
            value = f(x)
            evaluated.append(value)
            return value

        np.random.seed(seed)
        try:
            optimizer = optimizer_class(budget, dim, n_obj)
            optimizer(problem, list(bounds))
        except CandidateError:
            raise
        except Exception as error:  # noqa: BLE001
            if not evaluated:
                raise CandidateError(f"optimizer raised before evaluating anything: {type(error).__name__}: {error}") from None
        scores.append(hypervolume(np.array(evaluated), ref) / ref_hv if evaluated else 0.0)
    return float(np.mean(scores))
