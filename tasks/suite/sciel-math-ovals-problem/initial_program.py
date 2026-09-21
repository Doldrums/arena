# EVOLVE-BLOCK-START
import numpy as np


def ovals_problem20():
    """
    The Ovals problem. For a fixed n, propose three real 1D arrays x, y and phi
    (each of length n, viewed as samples at the equally spaced parameters
    t_k = 2*pi*k/n, k = 0..n-1). Interpolating these periodically yields smooth
    periodic functions f, g, h on [0, 2*pi]. Consider the planar curve
    t -> (f(t), g(t)), reparametrized by arc-length s, with curvature kappa(s).
    The objective is the Rayleigh quotient

        I(f, g, h) = integral_0^{2*pi} [ h'(s)^2 + (kappa(s) * h(s))^2 ] ds
                     / integral_0^{2*pi} h(s)^2 ds

    which must be made AS SMALL AS POSSIBLE, subject to the curve being convex
    (the signed curvature must stay strictly positive everywhere). Here n = 20.

    Baseline construction: the unit circle with a constant weight, i.e.
    x_k = cos(t_k), y_k = sin(t_k), phi_k = 1. For the circle the arc-length
    curvature is identically 1 and h is constant, so I = 1 exactly.

    Returns:
        (x, y, phi): a tuple of three np.ndarray each of shape (20,) giving the
            sampled values of the x-coordinate, y-coordinate and weight function.
    """
    n = 20
    theta = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    x = np.cos(theta)
    y = np.sin(theta)
    phi = np.ones(n)
    return x, y, phi


# EVOLVE-BLOCK-END
