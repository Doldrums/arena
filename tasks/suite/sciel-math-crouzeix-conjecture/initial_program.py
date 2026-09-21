# EVOLVE-BLOCK-START
import numpy as np


def crouzeix_conjecture4() -> tuple[np.ndarray, np.ndarray]:
    """
    Crouzeix's conjecture probe. Find a complex n x n matrix A and a polynomial p
    (given by its complex coefficients, highest degree first, as in numpy.poly1d)
    that make the Crouzeix ratio

        R(A, p) = || p(A) ||_op  /  sup_{z in W(A)} |p(z)|

    as large as possible, where || . ||_op is the spectral (operator) norm and

        W(A) = { <A x, x> : ||x|| <= 1 }

    is the numerical range (field of values) of A. Crouzeix's conjecture states
    that R(A, p) <= 2 for every A and p; the bound 2 is approached by the
    construction below. Here the size is baked to n = 4.

    The baseline is the AlphaEvolve "optimal" tridiagonal construction: a
    nilpotent matrix with sqrt(2) on the first and last super-diagonal entries
    and 1 on the interior super-diagonal entries, paired with p(z) = z^(n-1).

    Returns:
        A: np.ndarray of shape (4, 4), complex dtype, the matrix.
        poly_coeffs: np.ndarray of shape (4,), the polynomial coefficients in
            descending-degree order (numpy.poly1d convention). Here this encodes
            p(z) = z^3.
    """
    n = 4
    A = np.zeros((n, n), dtype=complex)
    if n == 2:
        A[0, 1] = 2.0
    else:
        A[0, 1] = np.sqrt(2.0)
        for i in range(1, n - 1):
            A[i, i + 1] = 1.0
        A[n - 2, n - 1] = np.sqrt(2.0)

    # p(z) = z^(n-1), i.e. coefficients [1, 0, ..., 0] of length n.
    poly_coeffs = np.zeros(n, dtype=complex)
    poly_coeffs[0] = 1.0

    return A, poly_coeffs


# EVOLVE-BLOCK-END
