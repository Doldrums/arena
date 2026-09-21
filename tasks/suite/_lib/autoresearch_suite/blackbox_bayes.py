"""Bayesian optimization objectives and Gaussian-process acquisition scoring."""
from __future__ import annotations

from .blackbox import (
    math,
    np,
    require,
)

# ---------------------------------------------------------------------------
# Classical synthetic test functions (for BO acquisition tasks)
# ---------------------------------------------------------------------------

def _hartmann(x, alpha, A, P):
    x = np.asarray(x)
    return -float(np.sum(alpha * np.exp(-np.sum(A * (x - P) ** 2, axis=1))))


A3 = np.array([[3, 10, 30], [0.1, 10, 35], [3, 10, 30], [0.1, 10, 35]])
P3 = 1e-4 * np.array([[3689, 1170, 2673], [4699, 4387, 7470], [1091, 8732, 5547], [381, 5743, 8828]])
A6 = np.array([[10, 3, 17, 3.5, 1.7, 8], [0.05, 10, 17, 0.1, 8, 14], [3, 3.5, 1.7, 10, 17, 8], [17, 8, 0.05, 10, 0.1, 14]])
P6 = 1e-4 * np.array([[1312, 1696, 5569, 124, 8283, 5886], [2329, 4135, 8307, 3736, 1004, 9991], [2348, 1451, 3522, 2883, 3047, 6650], [4047, 8828, 8732, 5743, 1091, 381]])
ALPHA = np.array([1.0, 1.2, 3.0, 3.2])

SYNTHETIC = {
    "sphere_1d": (lambda x: float(x[0] ** 2), [(-5, 5)], 0.0),
    "styblinski_tang_1d": (lambda x: float(0.5 * (x[0] ** 4 - 16 * x[0] ** 2 + 5 * x[0])), [(-5, 5)], -39.16617),
    "weierstrass_1d": (lambda x: float(sum(0.5 ** k * math.cos(2 * math.pi * 3 ** k * (x[0] + 0.5)) for k in range(12)) - sum(0.5 ** k * math.cos(math.pi * 3 ** k) for k in range(12))), [(-0.5, 0.5)], 0.0),
    "beale_2d": (lambda x: float((1.5 - x[0] + x[0] * x[1]) ** 2 + (2.25 - x[0] + x[0] * x[1] ** 2) ** 2 + (2.625 - x[0] + x[0] * x[1] ** 3) ** 2), [(-4.5, 4.5)] * 2, 0.0),
    "branin_2d": (lambda x: float((x[1] - 5.1 / (4 * math.pi ** 2) * x[0] ** 2 + 5 / math.pi * x[0] - 6) ** 2 + 10 * (1 - 1 / (8 * math.pi)) * math.cos(x[0]) + 10), [(-5, 10), (0, 15)], 0.397887),
    "michalewicz_2d": (lambda x: float(-sum(math.sin(xi) * math.sin((i + 1) * xi ** 2 / math.pi) ** 20 for i, xi in enumerate(x))), [(0, math.pi)] * 2, -1.8013),
    "goldstein_price_2d": (lambda x: float((1 + (x[0] + x[1] + 1) ** 2 * (19 - 14 * x[0] + 3 * x[0] ** 2 - 14 * x[1] + 6 * x[0] * x[1] + 3 * x[1] ** 2)) * (30 + (2 * x[0] - 3 * x[1]) ** 2 * (18 - 32 * x[0] + 12 * x[0] ** 2 + 48 * x[1] - 36 * x[0] * x[1] + 27 * x[1] ** 2))), [(-2, 2)] * 2, 3.0),
    "hartmann_3d": (lambda x: _hartmann(x, ALPHA, A3, P3), [(0, 1)] * 3, -3.86278),
    "hartmann_6d": (lambda x: _hartmann(x, ALPHA, A6, P6), [(0, 1)] * 6, -3.32237),
    "ackley_2d": (lambda x: float(-20 * math.exp(-0.2 * math.sqrt(0.5 * (x[0] ** 2 + x[1] ** 2))) - math.exp(0.5 * (math.cos(2 * math.pi * x[0]) + math.cos(2 * math.pi * x[1]))) + 20 + math.e), [(-5, 5)] * 2, 0.0),
    "rastrigin_2d": (lambda x: float(20 + sum(xi ** 2 - 10 * math.cos(2 * math.pi * xi) for xi in x)), [(-5.12, 5.12)] * 2, 0.0),
    "griewank_2d": (lambda x: float(1 + sum(xi ** 2 for xi in x) / 4000 - math.cos(x[0]) * math.cos(x[1] / math.sqrt(2))), [(-10, 10)] * 2, 0.0),
    "rosenbrock_2d": (lambda x: float(100 * (x[1] - x[0] ** 2) ** 2 + (1 - x[0]) ** 2), [(-2, 2)] * 2, 0.0),
    "levy_2d": (lambda x: float(math.sin(math.pi * (1 + (x[0] - 1) / 4)) ** 2 + ((1 + (x[0] - 1) / 4) - 1) ** 2 * (1 + 10 * math.sin(math.pi * (1 + (x[0] - 1) / 4) + 1) ** 2) + ((1 + (x[1] - 1) / 4) - 1) ** 2 * (1 + math.sin(2 * math.pi * (1 + (x[1] - 1) / 4)) ** 2)), [(-10, 10)] * 2, 0.0),
    "three_hump_camel_2d": (lambda x: float(2 * x[0] ** 2 - 1.05 * x[0] ** 4 + x[0] ** 6 / 6 + x[0] * x[1] + x[1] ** 2), [(-5, 5)] * 2, 0.0),
    "styblinski_tang_2d": (lambda x: float(0.5 * sum(xi ** 4 - 16 * xi ** 2 + 5 * xi for xi in x)), [(-5, 5)] * 2, -78.33234),
    "powell_4d": (lambda x: float((x[0] + 10 * x[1]) ** 2 + 5 * (x[2] - x[3]) ** 2 + (x[1] - 2 * x[2]) ** 4 + 10 * (x[0] - x[3]) ** 4), [(-4, 5)] * 4, 0.0),
    "shekel_4d": (lambda x: float(-sum(1 / (sum((x[j] - C[j]) ** 2 for j in range(4)) + b) for C, b in zip(np.array([[4, 4, 4, 4], [1, 1, 1, 1], [8, 8, 8, 8], [6, 6, 6, 6], [3, 7, 3, 7], [2, 9, 2, 9], [5, 5, 3, 3], [8, 1, 8, 1], [6, 2, 6, 2], [7, 3.6, 7, 3.6]]), [0.1, 0.2, 0.2, 0.4, 0.4, 0.6, 0.3, 0.7, 0.5, 0.5]))), [(0, 10)] * 4, -10.5364),
    "cosine8_8d": (lambda x: float(-(0.1 * sum(math.cos(5 * math.pi * xi) for xi in x) - sum(xi ** 2 for xi in x))), [(-1, 1)] * 8, -0.8),
}


def _gp_sample(seed=0, n_centers=25, length=0.15):
    """A fixed random RBF mixture standing in for a Gaussian-process prior sample on [0, 1]^2 (FunBO)."""
    rng = np.random.default_rng(seed)
    centers, weights = rng.random((n_centers, 2)), rng.standard_normal(n_centers)

    def f(x):
        x = np.asarray(x, dtype=float)
        return float(np.sum(weights * np.exp(-np.sum((centers - x) ** 2, axis=1) / (2 * length ** 2))))
    grid = np.stack(np.meshgrid(np.linspace(0, 1, 201), np.linspace(0, 1, 201)), -1).reshape(-1, 2)
    fmin = min(f(g) for g in grid)
    return f, [(0.0, 1.0)] * 2, fmin


SYNTHETIC["gp_sample_2d"] = _gp_sample()


# ---------------------------------------------------------------------------
# Gaussian-process Bayesian optimization with a candidate acquisition function
# ---------------------------------------------------------------------------

def _matern52(X, Y, length):
    d = np.sqrt(np.maximum(np.sum((X[:, None, :] - Y[None, :, :]) ** 2, axis=2), 0)) / length
    s = math.sqrt(5) * d
    return (1 + s + s ** 2 / 3) * np.exp(-s)


def gp_posterior(X, y, Xs, length=0.2, noise=1e-6):
    mean, std = y.mean(), y.std() + 1e-12
    yn = (y - mean) / std
    K = _matern52(X, X, length) + noise * np.eye(len(X))
    L = np.linalg.cholesky(K)
    alpha = np.linalg.solve(L.T, np.linalg.solve(L, yn))
    Ks = _matern52(X, Xs, length)
    mu = Ks.T @ alpha
    v = np.linalg.solve(L, Ks)
    var = np.maximum(1 - np.sum(v * v, axis=0), 1e-12)
    return mu * std + mean, np.sqrt(var) * std


def bo_regret_score(acquisition, function_name, budget=30, n_init=5, n_candidates=2000, seeds=(0, 1, 2), cost_model=None):
    """Mean simple regret after ``budget`` evaluations of GP-BO driven by the candidate acquisition function.

    Contract (FunBO style): ``acquisition(mu, sigma, f_best) -> scores``; the
    point with the highest score among ``n_candidates`` uniformly sampled
    candidates is evaluated next. With ``cost_model`` (EvolCAF style) the
    contract is ``acquisition(mu, sigma, f_best, cost)`` and the loop stops when
    the accumulated cost exceeds ``budget``; the cost model is
    ``cost(x) = 1 + mean over coordinates of the normalized coordinate value``,
    a documented stand-in for the paper's cost functions.
    """
    f, bounds, fmin = SYNTHETIC[function_name]
    lo = np.array([b[0] for b in bounds], dtype=float)
    hi = np.array([b[1] for b in bounds], dtype=float)
    regrets = []
    for seed in seeds:
        rng = np.random.default_rng(seed)
        X = lo + (hi - lo) * rng.random((n_init, len(bounds)))
        y = np.array([f(x) for x in X])
        spent = float(n_init) if cost_model is None else float(np.sum(1 + np.mean((X - lo) / (hi - lo), axis=1)))
        while (len(y) < budget if cost_model is None else spent < budget):
            Xs = lo + (hi - lo) * rng.random((n_candidates, len(bounds)))
            mu, sigma = gp_posterior((X - lo) / (hi - lo), y, (Xs - lo) / (hi - lo))
            if cost_model is None:
                scores = np.asarray(acquisition(mu, sigma, float(y.min())), dtype=float).ravel()
            else:
                cost = 1 + np.mean((Xs - lo) / (hi - lo), axis=1)
                scores = np.asarray(acquisition(mu, sigma, float(y.min()), cost), dtype=float).ravel()
            require(scores.shape == (n_candidates,) and np.all(np.isfinite(scores)), "acquisition must return one finite score per candidate point")
            x = Xs[int(np.argmax(scores))]
            X = np.vstack([X, x])
            y = np.append(y, f(x))
            spent += 1.0 if cost_model is None else float(1 + np.mean((x - lo) / (hi - lo)))
            require(len(y) <= 10 * budget + n_init, "cost-aware loop did not terminate")
        regrets.append(float(y.min() - fmin))
    return float(np.mean(regrets))
