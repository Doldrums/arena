# EVOLVE-BLOCK-START
import numpy as np


def thomson_problem12() -> np.ndarray:
    """
    Place n points on the unit sphere in R^3 so as to minimize the Coulomb energy
    E = sum over i<j of 1 / ||x_i - x_j||. Here n = 12.

    Returns:
        points: np.ndarray of shape (12,3) with the x,y,z coordinates of points on
            the unit sphere, constructed via a deterministic Fibonacci/golden-spiral.
    """
    n = 12
    indices = np.arange(n)
    golden = (1 + np.sqrt(5)) / 2
    theta = 2 * np.pi * indices / golden
    z = 1 - 2 * (indices + 0.5) / n
    r = np.sqrt(np.clip(1 - z * z, 0.0, 1.0))
    points = np.stack([r * np.cos(theta), r * np.sin(theta), z], axis=1)
    return points


# EVOLVE-BLOCK-END
