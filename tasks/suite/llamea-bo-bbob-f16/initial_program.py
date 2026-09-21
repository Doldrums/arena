"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


class Optimizer:
    """(1+1)-ES with 1/5 success rule."""

    def __init__(self, budget, dim):
        self.budget, self.dim = budget, dim

    def __call__(self, func):
        rng = np.random.default_rng(0)
        x = rng.uniform(-5, 5, self.dim)
        fx = func(x)
        sigma = 2.0
        for _ in range(self.budget - 1):
            y = np.clip(x + sigma * rng.standard_normal(self.dim), -5, 5)
            fy = func(y)
            if fy < fx:
                x, fx = y, fy
                sigma *= 1.5
            else:
                sigma *= 0.87
        return x, fx
# EVOLVE-BLOCK-END
