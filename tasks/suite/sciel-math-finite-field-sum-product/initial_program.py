# EVOLVE-BLOCK-START
import numpy as np


def sum_product_set() -> np.ndarray:
    """
    Construct a subset A of the finite field F_31 (integers mod 31) that minimizes
    |A+A| + |A*A|, where A+A = { (a+b) mod 31 : a,b in A } and
    A*A = { (a*b) mod 31 : a,b in A }. The sum-product phenomenon guarantees that at
    least one of these sets must be large, so minimizing their combined size is a
    genuine optimization. Here A has 12 distinct elements.

    Returns:
        elements: np.ndarray of shape (12,) with distinct integer elements in [0, 31).
    """
    elements = np.arange(12)
    return elements


# EVOLVE-BLOCK-END
