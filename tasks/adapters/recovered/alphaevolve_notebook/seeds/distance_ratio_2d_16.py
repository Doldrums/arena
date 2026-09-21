# Independently written trivial seed for the AlphaEvolve notebook task; a valid but weak
# construction. It is not the published construction and not a reproduction of the paper.
# Contract: construct() -> numpy array of shape (16, 2)
import numpy as np


def construct():
    return np.array([[float(i), float(j)] for i in range(4) for j in range(4)])
