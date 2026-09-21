# EVOLVE-BLOCK-START
import numpy as np


def sidorenko_graphon() -> np.ndarray:
    """
    Sidorenko's conjecture for the bipartite graph H = K_{5,5} minus a perfect
    matching (10 vertices, 20 edges, 4-regular bipartite). A graphon is a symmetric
    measurable function W: [0,1]^2 -> [0,1]; here it is represented as a step graphon,
    i.e. a symmetric n x n matrix M with entries in [0,1] whose value on block (i,j)
    equals M[i, j] (the unit square is split into n equal intervals).

    Sidorenko's conjecture states that for every graphon W,
        t(H, W) >= t(K2, W)^|E(H)|,
    i.e. the ratio  t(H, W) / t(K2, W)^|E(H)|  is at least 1. The goal is to make this
    ratio as small as possible (a value strictly below 1 would be a counterexample).
    The constant graphon W == 0.5 attains the ratio exactly 1 and is used as the seed.

    Returns:
        M: np.ndarray of shape (8, 8), symmetric, with all entries in [0, 1] -
            the step-graphon matrix.
    """
    n = 8
    M = 0.5 * np.ones((n, n), dtype=np.float64)
    M = 0.5 * (M + M.T)  # enforce symmetry
    return M


# EVOLVE-BLOCK-END
