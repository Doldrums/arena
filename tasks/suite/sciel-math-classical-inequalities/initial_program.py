# EVOLVE-BLOCK-START
import numpy as np

# Grid parameters (must match the evaluator).
R = 10.0  # f is approximated as a step function on [-R, R].
N = 2048  # number of grid cells (and step-function values).


def hausdorff_young_p32() -> np.ndarray:
    """
    Hausdorff-Young inequality, probing the Babenko-Beckner constant.

    Construct a bounded, integrable, not-identically-zero step function f of one real
    variable that maximizes the quotient

        Q(f) = ||fhat||_q / ||f||_p ,     with 1/p + 1/q = 1, p = 3/2, q = 3,

    where fhat is the Fourier transform fhat(xi) = integral f(x) exp(-2*pi*i*x*xi) dx.

    The function is represented as a step function on the interval [-R, R]: cell j
    (j = 0 .. N-1) spans [x_j, x_j + dx) with x_j = -R + j*dx and dx = 2R/N, and f takes
    the constant value returned in entry j of the array. The sharp maximizer of the
    Hausdorff-Young ratio is a Gaussian (Babenko-Beckner), so the baseline samples the
    Gaussian exp(-x^2) on the grid.

    Returns:
        values: np.ndarray of shape (N,), the step-function value of f on each grid cell.
    """
    dx = 2.0 * R / N
    x = -R + dx * np.arange(N)
    values = np.exp(-(x**2))
    return values


# EVOLVE-BLOCK-END
