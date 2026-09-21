# Independently written trivial seed for the AlphaEvolve notebook task; a valid but weak
# construction. It is not the published construction and not a reproduction of the paper.
# Contract: construct() -> numpy array of shape (21, 3) rows (x, y, radius); minimum circumscribing rectangle must have perimeter <= 4
import numpy as np


def construct():
    cells = [((i + 0.5) / 5, (j + 0.5) / 5, 0.099) for i in range(5) for j in range(5)]
    return np.array(cells[:21])
