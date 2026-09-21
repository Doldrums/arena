# EVOLVE-BLOCK-START
import numpy as np


def sendov_polynomial6() -> np.ndarray:
    """
    Sendov's conjecture (probing the Sendov bound). For a complex polynomial f of degree n
    with all zeros z_1,...,z_n in the closed unit disk, let w_1,...,w_{n-1} be its critical
    points (the zeros of f'). The objective is to choose the n roots so as to maximize

        max_{1<=k<=n}  min_{1<=j<=n-1}  |z_k - w_j|

    i.e. push some root as far as possible from every critical point. Sendov conjectured
    this quantity never exceeds 1; the n-th roots of unity attain exactly 1. Here n = 6.

    Returns:
        roots: np.ndarray of shape (6,), complex dtype, with every root inside the closed
            unit disk (|z_k| <= 1).
    """
    n = 6
    # Baseline construction from the upstream notebook: random roots inside the unit disk.
    np.random.seed(0)
    r = np.random.rand(n)
    theta = np.random.rand(n) * 2.0 * np.pi
    roots = r * np.exp(1j * theta)
    return roots.astype(np.complex128)


# EVOLVE-BLOCK-END
