"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def priority(instance):
    # Longest task first.
    return np.asarray(instance["times"], dtype=float)
# EVOLVE-BLOCK-END
