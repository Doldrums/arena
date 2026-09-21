# EVOLVE-BLOCK-START
import numpy as np


def erdos_szekeres_problem7() -> np.ndarray:
    """
    Erdos-Szekeres "Happy Ending" problem. Place n = 2^(k-2) + 1 points in general
    position (no three collinear) inside the unit square so as to MINIMIZE the number of
    convex k-gons whose vertices are among the points. Here k = 7, so n = 2^5 + 1 = 33.
    The conjectured record is a construction with 0 convex 7-gons.

    Returns:
        points: np.ndarray of shape (33, 2) with the x,y coordinates of the points,
            each lying in the unit square [0, 1] x [0, 1].
    """
    n = 33  # = 2^(7-2) + 1
    # Baseline construction from the upstream notebook: random points in the unit square.
    # Seeded for determinism / reproducibility.
    np.random.seed(0)
    points = np.random.rand(n, 2)
    return points


# EVOLVE-BLOCK-END
