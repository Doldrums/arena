"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def heuristics(demands, capacity):
    n = len(demands)
    pair = demands[:, None] + demands[None, :]
    return np.where(pair <= capacity, pair / capacity, 1e-9)
# EVOLVE-BLOCK-END
