"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def equation(b: np.ndarray, s: np.ndarray, temp: np.ndarray, pH: np.ndarray, params: np.ndarray) -> np.ndarray:
    """E. coli growth rate from population density, substrate, temperature and pH."""
    return params[0] * b + params[1] * s + params[2] * temp + params[3] * pH + params[4]
# EVOLVE-BLOCK-END
