"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
N = 13

# EVOLVE-BLOCK-START
import random
import numpy as np


def construct():
    rng = random.Random(N)
    return np.array([[rng.random(), rng.random()] for _ in range(N)])
# EVOLVE-BLOCK-END
