"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def optimize(Q, c, bounds, objective):
    # Projected gradient descent from the origin.
    lo, hi = bounds
    x = np.zeros(len(c))
    step = 1.0 / (np.linalg.norm(Q, 2) + 1e-9)
    for _ in range(500):
        x = np.clip(x - step * (Q @ x + c), lo, hi)
    return x
# EVOLVE-BLOCK-END
