# EVOLVE-BLOCK-START
import numpy as np


def fejes_toth6() -> np.ndarray:
    """
    Fejes-Toth problem: place n points on the surface of the unit sphere in R^3 so as to
    maximize the volume of their convex hull (the largest-volume polyhedron with n vertices
    inscribed in the unit sphere). Here n = 6.

    Returns:
        points: np.ndarray of shape (6,3) with the x,y,z coordinates of the points,
            each lying on (or projected onto) the unit sphere.
    """
    n = 6
    # Baseline/search-seed construction from the upstream notebook: random points on the
    # unit sphere (deterministic via a fixed seed).
    np.random.seed(0)
    pts = np.random.normal(0.0, 1.0, (n, 3))
    pts = pts / np.linalg.norm(pts, axis=1, keepdims=True)
    return pts


# EVOLVE-BLOCK-END
