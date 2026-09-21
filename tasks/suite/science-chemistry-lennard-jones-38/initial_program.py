"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
N = 38

# EVOLVE-BLOCK-START
import numpy as np


def construct():
    # Simple cubic lattice fragment at spacing 1.12 (the pair-potential minimum); a weak but valid start.
    side = int(np.ceil(N ** (1 / 3)))
    points = [(i, j, k) for i in range(side) for j in range(side) for k in range(side)]
    points.sort(key=lambda p: (p[0] - (side - 1) / 2) ** 2 + (p[1] - (side - 1) / 2) ** 2 + (p[2] - (side - 1) / 2) ** 2)
    return np.array(points[:N], dtype=float) * 1.12
# EVOLVE-BLOCK-END
