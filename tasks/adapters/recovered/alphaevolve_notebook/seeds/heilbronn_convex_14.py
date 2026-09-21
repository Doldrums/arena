# Independently written trivial seed for the AlphaEvolve notebook task; a valid but weak
# construction. It is not the published construction and not a reproduction of the paper.
# Contract: construct() -> numpy array of shape (14, 2)
import random
import numpy as np


def construct():
    rng = random.Random(14)
    return np.array([[rng.random(), rng.random()] for _ in range(14)])
