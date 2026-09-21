# EVOLVE-BLOCK-START
import numpy as np


def spherical_design() -> np.ndarray:
    """
    Place N = 12 points on the unit sphere S^2 so that they form a spherical 2-design:
    the empirical first and second moments should match those of the uniform sphere.

    The baseline uses a deterministic golden-spiral (Fibonacci sphere) construction,
    which spreads 12 distinct points nearly uniformly over the sphere.

    Returns:
        points: np.ndarray of shape (12,3) with the x,y,z coordinates of points on the unit sphere.
    """
    n = 12
    points = np.zeros((n, 3))
    golden_angle = np.pi * (3.0 - np.sqrt(5.0))
    for i in range(n):
        z = 1.0 - (2.0 * i + 1.0) / n
        radius = np.sqrt(max(0.0, 1.0 - z * z))
        theta = golden_angle * i
        points[i, 0] = radius * np.cos(theta)
        points[i, 1] = radius * np.sin(theta)
        points[i, 2] = z
    return points


# EVOLVE-BLOCK-END
