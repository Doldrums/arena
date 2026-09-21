"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def heuristics(distance_matrix, coordinates, demands, capacity):
    return 1.0 / (distance_matrix + 1e-9)
# EVOLVE-BLOCK-END
