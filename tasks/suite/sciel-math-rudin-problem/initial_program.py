# EVOLVE-BLOCK-START
import numpy as np


def rudin_problem10() -> np.ndarray:
    """
    Rudin problem for polynomials on the 2-sphere. Find the real coefficients
    (c_m) for m = -k..k of a real degree-k spherical harmonic

        f = sum_{m=-k}^{k} c_m Y_k^m

    on the round unit sphere S^2 that MINIMIZE the norm ratio

        ||f||_{L^4(S^2)} / ||f||_{L^2(S^2)}

    (norms taken with the standard surface measure dOmega of total mass 4*pi).
    Here the degree is fixed to k = 10, so the returned vector has length
    2*k + 1 = 21.

    This baseline returns the all-ones coefficient vector (the same simple,
    non-degenerate construction used in the upstream notebook's verification
    cell); evolution should reshape these coefficients to flatten |f| and drive
    the L^4/L^2 ratio down.

    Returns:
        coeffs: np.ndarray of shape (21,) with the real coefficients
            c_m, ordered m = -10, -9, ..., 0, ..., 9, 10.
    """
    k = 10
    coeffs = np.ones(2 * k + 1, dtype=np.float64)
    return coeffs


# EVOLVE-BLOCK-END
