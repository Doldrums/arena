"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
N = 11

# EVOLVE-BLOCK-START
import random
import numpy as np


def construct():
    rng = random.Random(7)
    points = []
    while len(points) < N:
        u, v = rng.random(), rng.random()
        if u + v < 0.98 and u > 0.01 and v > 0.01:
            points.append([u + 0.5 * v, (3 ** 0.5) / 2 * v])
    return np.array(points)
# EVOLVE-BLOCK-END
