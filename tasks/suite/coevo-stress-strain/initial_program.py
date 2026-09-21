"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def equation(strain: np.ndarray, temp: np.ndarray, params: np.ndarray) -> np.ndarray:
    """Stress of an aluminium rod from strain and temperature."""
    return params[0] * strain + params[1] * temp + params[2]
# EVOLVE-BLOCK-END
