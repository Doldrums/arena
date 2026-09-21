# EVOLVE-BLOCK-START
import numpy as np


def tammes_problem13() -> np.ndarray:
    """
    Place n points on the surface of the unit sphere in R^3 so as to maximize the minimum
    pairwise Euclidean distance between any two points (the Tammes problem). Here n = 13.

    Returns:
        points: np.ndarray of shape (13,3) with the x,y,z coordinates of the points,
            each lying on the unit sphere.
    """
    n = 13
    indices = np.arange(n, dtype=np.float64)
    # Golden-spiral (Fibonacci lattice) construction: deterministic, well-spread points.
    golden_angle = np.pi * (3.0 - np.sqrt(5.0))
    z = 1.0 - 2.0 * (indices + 0.5) / n
    radius = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    theta = golden_angle * indices
    x = radius * np.cos(theta)
    y = radius * np.sin(theta)
    points = np.stack([x, y, z], axis=1)
    return points


# EVOLVE-BLOCK-END
