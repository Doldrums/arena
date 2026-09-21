"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def angles(n, edges, p):
    # A feasible unevolved schedule; optimize angles and graph-dependent rules.
    return np.tile([0.35, 0.25], (p, 1))
# EVOLVE-BLOCK-END
