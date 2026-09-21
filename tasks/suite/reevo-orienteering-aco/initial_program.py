"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def heuristics(prizes, distance_matrix, max_len):
    return (prizes[None, :] + 1e-9) / (distance_matrix + 1e-9)
# EVOLVE-BLOCK-END
