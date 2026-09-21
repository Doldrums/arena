"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def equation(X: np.ndarray, params: np.ndarray) -> np.ndarray:
    """Linear baseline over the input variables (columns of X in input_vars order); 10 fitted parameters."""
    d = X.shape[1]
    return X @ params[:d] + params[d]
# EVOLVE-BLOCK-END
