"""Editable light GP/EI optimizer seed; repository baseline, not published ATRBO.

Contract: Optimizer(dim, budget)(func) -> (best_y, best_x).  func.bounds is a
2-by-d array; exactly budget objective calls are required. CPU and no model API.
"""
import numpy as np
from scipy.linalg import cho_factor, cho_solve, solve_triangular
from scipy.special import ndtr


# EVOLVE-BLOCK-START
class Optimizer:
    def __init__(self, dim, budget):
        self.dim, self.budget = dim, budget

    def __call__(self, func):
        rng = np.random.default_rng(getattr(func, "random_seed", 0))
        lower, upper = np.asarray(func.bounds)
        xs, ys = [], []
        for step in range(self.budget):
            if step < min(12, self.budget):
                point = rng.random(self.dim)
            else:
                train = np.asarray(xs)
                observations = np.asarray(ys)
                target = (observations - observations.mean()) / max(observations.std(), 1e-8)
                pool = rng.random((128, self.dim))
                # Fixed kernel avoids costly nested hyperparameter optimization.
                def kernel(a, b):
                    return np.exp(-np.sum((a[:, None, :] - b[None, :, :]) ** 2,
                                          axis=-1) / (2 * 0.3 ** 2))
                covariance = kernel(train, train) + np.eye(step) * 1e-6
                factor = cho_factor(covariance, lower=True)
                cross = kernel(train, pool)
                mean = cross.T @ cho_solve(factor, target)
                projected = solve_triangular(factor[0], cross, lower=True)
                std = np.sqrt(np.maximum(1 - (projected ** 2).sum(axis=0), 1e-12))
                improvement = target.min() - mean
                z = improvement / std
                ei = improvement * ndtr(z) + std * np.exp(-0.5 * z ** 2) / np.sqrt(2 * np.pi)
                point = pool[int(np.argmax(ei))]
            value = float(func(lower + point * (upper - lower)))
            xs.append(point)
            ys.append(value)
        best = int(np.argmin(ys))
        return ys[best], lower + xs[best] * (upper - lower)
# EVOLVE-BLOCK-END
