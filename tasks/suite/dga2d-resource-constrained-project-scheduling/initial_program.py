"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def priority(instance):
    # Longest duration first.
    return np.asarray(instance["durations"], dtype=float)
# EVOLVE-BLOCK-END
