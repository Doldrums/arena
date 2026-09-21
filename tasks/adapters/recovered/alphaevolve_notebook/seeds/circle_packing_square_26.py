# Independently written trivial seed for the AlphaEvolve notebook task; a valid but weak
# construction. It is not the published construction and not a reproduction of the paper.
# Contract: construct() -> numpy array of shape (26, 3) rows (x, y, radius)
import numpy as np


def construct():
    cells = [((i + 0.5) / 6, (j + 0.5) / 6, 0.083) for i in range(6) for j in range(6)]
    return np.array(cells[:26])
