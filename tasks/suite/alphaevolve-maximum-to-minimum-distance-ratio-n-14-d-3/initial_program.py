"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
N = 14
D = 3

# EVOLVE-BLOCK-START
import itertools
import numpy as np


def construct():
    side = int(np.ceil(N ** (1 / D)))
    grid = list(itertools.product(range(side), repeat=D))[:N]
    return np.array(grid, dtype=float)
# EVOLVE-BLOCK-END
