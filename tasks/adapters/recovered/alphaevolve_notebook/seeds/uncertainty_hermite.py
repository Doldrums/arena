# Independently written trivial seed for the AlphaEvolve notebook task; a valid but weak
# construction. It is not the published construction and not a reproduction of the paper.
# Contract: construct() -> numpy array of three Hermite-combination coefficients (degrees 0, 4, 8 pattern of the notebook)
import numpy as np


def construct():
    # The prior state of the art of Goncalves et al. (2017), as listed in the notebook, is the weak seed.
    return np.array([-113 / 100, 1 / 25, 1 / 3240])
