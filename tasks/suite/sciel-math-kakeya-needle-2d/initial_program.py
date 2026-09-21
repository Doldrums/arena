# EVOLVE-BLOCK-START
import numpy as np


def kakeya_needle_2d_positions64() -> np.ndarray:
    """
    Two-dimensional Kakeya-needle area-minimization problem. For a fixed n, choose
    base positions x = (x_0, ..., x_{n-1}). For position index i (0-based) let
    a_i = (i + 1) / n and define the triangle R_i with vertices
        (x_i, 0), (x_i + 1/n, 0), (x_i + a_i, 1).
    Every triangle has base width 1/n on the line y = 0 and its apex on the line
    y = 1. The objective is to choose x so that the AREA of the union of the n
    triangles R_i is as small as possible. Here n = 64.

    This baseline uses the classical Keich construction (valid for n a power of 2):
    expand a_i = i/n in binary as a_i = sum_j eps_j 2^{-j} and set
        x_i = sum_{j=1}^{k} ((1 - j) / k) * eps_j * 2^{-j},   k = log2(n).

    Returns:
        positions: np.ndarray of shape (64,) with the base x-coordinates x_i.
    """
    n = 64
    k = int(np.log2(n))
    j = np.arange(1, k + 1)
    positions = []
    for i in range(n):
        eps = np.array(list(str(bin(i))[2:]), dtype=int)
        eps = np.pad(eps, (k - len(eps), 0), "constant")
        positions.append(np.sum((1 - j) * eps * (2.0 ** -j) / k))
    return np.array(positions, dtype=np.float64)


# EVOLVE-BLOCK-END
