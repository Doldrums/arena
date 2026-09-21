# EVOLVE-BLOCK-START
import numpy as np


def squares_in_square10() -> tuple:
    """
    Erdos "squares in a square" problem. Place n squares with pairwise disjoint
    interiors inside the unit square [0,1]^2 so as to MAXIMIZE the sum of their
    side lengths. Here n = 10.

    Returns:
        centers: np.ndarray of shape (10, 2) with the (x, y) center of each square.
        sides:   np.ndarray of shape (10,) with the side length of each square.
    The i-th axis-aligned square occupies
        [cx - s/2, cx + s/2] x [cy - s/2, cy + s/2].

    Baseline construction: a simple deterministic grid packing. With
    k = ceil(sqrt(n)) columns/rows and side = 1/k, the first n grid cells each
    hold one square. This is feasible (squares only touch, never overlap, and
    stay inside the unit square) but suboptimal.
    """
    n = 10
    k = int(np.ceil(np.sqrt(n)))
    side = 1.0 / k
    idx = np.arange(n)
    cols = idx % k
    rows = idx // k
    cx = (cols + 0.5) * side
    cy = (rows + 0.5) * side
    centers = np.stack([cx, cy], axis=1).astype(np.float64)
    sides = np.full(n, side, dtype=np.float64)
    return centers, sides


# EVOLVE-BLOCK-END
