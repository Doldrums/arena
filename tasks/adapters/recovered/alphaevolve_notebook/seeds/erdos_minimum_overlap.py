# Independently written trivial seed for the AlphaEvolve notebook task; a valid but weak
# construction. It is not the published construction and not a reproduction of the paper.
# Contract: construct() -> numpy array of step heights in [0, 1] whose sum is exactly len/2
import numpy as np


def construct():
    return np.full(100, 0.5)
