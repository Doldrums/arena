# EVOLVE-BLOCK-START
import numpy as np


def kakeya_set() -> np.ndarray:
    """
    Construct a Kakeya set in the finite plane F_p^2 with p = 7. A Kakeya set must
    contain a full line in every direction. There are p + 1 = 8 directions: the p = 7
    directions of slope m = 0, 1, ..., 6 (non-vertical lines y = m*x + b), and the 1
    vertical direction (lines x = c). For each direction we choose the intercept. The
    returned array of length 8 encodes those choices: entries[m] = b for the line of
    slope m (m = 0..6), and entries[7] = c for the vertical line. The Kakeya set is the
    union of these 8 chosen lines; the objective is to minimize the number of points in
    the union.

    Returns:
        entries: np.ndarray of shape (8,) integer intercepts (entries in [0,7)).
    """
    entries = np.zeros(8, dtype=int)
    return entries


# EVOLVE-BLOCK-END
