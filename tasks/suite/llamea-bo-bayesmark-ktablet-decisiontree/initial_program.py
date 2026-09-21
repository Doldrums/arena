"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


class Optimizer:
    """Random search baseline."""

    def __init__(self, budget, dim):
        self.budget, self.dim = budget, dim

    def __call__(self, func):
        rng = np.random.default_rng(0)
        best_x, best = None, float("inf")
        for _ in range(self.budget):
            x = rng.random(self.dim)
            value = func(x)
            if value < best:
                best_x, best = x, value
        return best_x, best
# EVOLVE-BLOCK-END
