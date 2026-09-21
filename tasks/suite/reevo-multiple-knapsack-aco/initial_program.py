"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def heuristics(prizes, weights):
    return prizes / (weights.sum(axis=0) + 1e-9)
# EVOLVE-BLOCK-END
