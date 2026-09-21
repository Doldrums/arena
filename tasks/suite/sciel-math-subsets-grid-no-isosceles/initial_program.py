# EVOLVE-BLOCK-START
import numpy as np


def grid_subset() -> np.ndarray:
    """
    Select as many points as possible from the 7x7 integer grid (x,y in {0,...,6})
    such that no three selected points form an isosceles triangle. Three distinct
    points are "isosceles" if at least two of their three pairwise squared distances
    are equal. Maximize the number of selected points.

    Returns:
        points: np.ndarray of shape (k,2) with integer x,y coordinates in {0,...,6}.
    """
    points = np.array([[0, 0], [0, 1]])
    return points


# EVOLVE-BLOCK-END
