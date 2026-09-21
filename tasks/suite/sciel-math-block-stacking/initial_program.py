# EVOLVE-BLOCK-START
import numpy as np


def block_stacking30() -> np.ndarray:
    """
    Block-stacking (single-wide overhang) problem. Stack n identical rigid blocks of
    width 1 at the edge of a table (table edge at x = 0). Let x_k be the horizontal
    position of block k (its center), with 0 = x_0 <= x_1 <= ... <= x_n. Maximize the
    horizontal displacement x_n of the top (n-th) block over the table edge subject to
    the stack remaining stable, i.e. for every 0 <= i < n the center of mass of all
    blocks above block i must lie within block i's footprint (and the whole stack's
    center of mass must lie over the table). Here n = 30.

    Baseline construction: the classical harmonic ("1/2, 1/4, 1/6, ...") staircase,
    which achieves the known optimum C(n) = (1/2) * H_n, where H_n is the n-th harmonic
    number. Block k is offset so that x_k = (1/2)(H_n - H_{n-k-1}).

    Returns:
        positions: np.ndarray of shape (30,) with the horizontal center positions
            x_1, ..., x_n of the blocks, non-decreasing and positive.
    """
    n = 30
    tol = 1e-9
    harmonic = np.zeros(n + 1, dtype=np.float64)
    for j in range(1, n + 1):
        harmonic[j] = harmonic[j - 1] + 1.0 / j
    k = np.arange(n)
    # x_k = 0.5 * (H_n - H_{n-k-1}); tiny slack keeps the stack strictly stable.
    positions = 0.5 * (harmonic[n] - harmonic[n - k - 1]) - 2.0 * tol
    return positions


# EVOLVE-BLOCK-END
