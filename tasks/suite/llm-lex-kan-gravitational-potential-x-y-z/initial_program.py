"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def equation(x: np.ndarray, y: np.ndarray, z: np.ndarray, params: np.ndarray) -> np.ndarray:
    return params[0] * x + params[1] * y + params[2] * z + params[3]
# EVOLVE-BLOCK-END
