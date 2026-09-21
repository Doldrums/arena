# Independently written trivial seed for the AlphaEvolve notebook task; a valid but weak
# construction. It is not the published construction and not a reproduction of the paper.
# Contract: construct() -> numpy array of shape (14, 3)
import itertools
import numpy as np


def construct():
    grid = list(itertools.product(range(3), range(3), range(2)))[:14]
    return np.array(grid, dtype=float)
