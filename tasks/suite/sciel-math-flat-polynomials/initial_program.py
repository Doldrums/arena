# EVOLVE-BLOCK-START
import numpy as np


def flat_polynomial() -> np.ndarray:
    """
    Construct a binary sequence a of length N = 41 with entries in {-1, +1} that maximizes the
    Littlewood merit factor F = N^2 / (2 * sum_{k=1}^{N-1} c_k^2), where c_k is the aperiodic
    autocorrelation at lag k. A higher merit factor corresponds to a "flatter" polynomial on the
    unit circle (low autocorrelation binary sequence).

    Returns:
        a: np.ndarray of shape (41,) with values in {-1, +1}.
    """
    n = 41
    a = np.ones(n)
    return a


# EVOLVE-BLOCK-END
