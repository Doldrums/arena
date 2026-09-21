"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


class Optimizer:
    """Simple evolutionary multi-objective search: random init, mutate non-dominated parents."""

    def __init__(self, budget, dim, n_obj):
        self.budget, self.dim, self.n_obj = budget, dim, n_obj

    def __call__(self, problem, bounds):
        rng = np.random.default_rng(0)
        lo = np.array([b[0] for b in bounds]); hi = np.array([b[1] for b in bounds])
        pop = int(min(20, self.budget // 4))
        X = lo + (hi - lo) * rng.random((pop, self.dim))
        F = np.array([problem(x) for x in X])
        used = pop
        while used < self.budget:
            dominated = np.array([np.any(np.all(F <= f, axis=1) & np.any(F < f, axis=1)) for f in F])
            parents = X[~dominated] if np.any(~dominated) else X
            child = parents[rng.integers(len(parents))] + 0.1 * (hi - lo) * rng.standard_normal(self.dim)
            child = np.clip(child, lo, hi)
            fc = problem(child)
            used += 1
            worst = int(np.argmax(np.sum(F, axis=1)))
            X[worst], F[worst] = child, fc
        return X
# EVOLVE-BLOCK-END
