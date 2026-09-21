# EVOLVE-BLOCK-START
import numpy as np
import itertools


def no_5_on_a_sphere8() -> np.ndarray:
    """
    The "no 5 on a sphere" problem. Select as many points as possible from the
    n x n x n integer grid {0,...,n-1}^3 such that no five of the selected points
    are co-spherical (lie on a common sphere, which also forbids five co-planar
    points). Five points p_i = (x_i, y_i, z_i) are co-spherical iff the 5x5
    determinant of rows [x_i, y_i, z_i, x_i^2 + y_i^2 + z_i^2, 1] vanishes.

    Here n = 8. The objective is to MAXIMIZE the number of selected points.

    Baseline construction (mirrors the notebook's randomized greedy search,
    translated to pure numpy): run a fixed number of seeded random-order greedy
    passes over the grid, adding a point whenever it keeps the set sphere-free,
    and keep the largest set found. Deterministic via np.random.seed(0).

    Returns:
        points: np.ndarray of shape (k, 3) of integer grid coordinates in
            [0, n-1], no five of which are co-spherical.
    """
    n = 8
    num_restarts = 6

    grid = np.array(list(itertools.product(range(n), range(n), range(n))), dtype=np.int64)

    def can_add(arr: np.ndarray, p: np.ndarray) -> bool:
        m = len(arr)
        if m < 4:
            return True
        # Lift each existing point to a 4-vector relative to the candidate p.
        # The candidate together with four existing points is co-spherical iff
        # the corresponding four lifted vectors are linearly dependent (4x4
        # determinant == 0). Coordinates are integers, so determinants are
        # integers and a nonzero one has |det| >= 1.
        w = np.empty((m, 4), dtype=np.float64)
        w[:, 0:3] = arr - p
        w[:, 3] = (arr ** 2).sum(axis=1) - (p ** 2).sum()
        combos = np.array(list(itertools.combinations(range(m), 4)))
        sub = w[combos]  # (C, 4, 4)
        return not np.any(np.abs(np.linalg.det(sub)) < 0.5)

    np.random.seed(0)
    best = None
    for _ in range(num_restarts):
        order = grid[np.random.permutation(len(grid))]
        arr = np.empty((0, 3), dtype=np.int64)
        for p in order:
            if can_add(arr, p):
                arr = np.vstack([arr, p]) if len(arr) else p[None, :]
        if best is None or len(arr) > len(best):
            best = arr

    return best.astype(np.int64)


# EVOLVE-BLOCK-END
