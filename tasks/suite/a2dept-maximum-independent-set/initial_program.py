"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def priority(adjacency):
    # Lowest degree first.
    return -adjacency.sum(axis=1).astype(float)
# EVOLVE-BLOCK-END
