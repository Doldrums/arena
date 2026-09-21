"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def priority(item: float, bins: np.ndarray) -> np.ndarray:
    # Best-fit: prefer bins that leave the least remaining capacity.
    return -(bins - item)
# EVOLVE-BLOCK-END
