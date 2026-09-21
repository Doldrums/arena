"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def construct():
    # Composite midpoint rule; evolve one universal positive quadrature.
    n = 8
    return {"nodes": (np.arange(n) + 0.5) / n, "weights": np.full(n, 1.0 / n)}
# EVOLVE-BLOCK-END
