"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def angles(n, coupling, field, layers):
    # Product |+> state, represented in the permitted circuit.
    theta = np.zeros((layers, n))
    theta[-1] = np.pi / 2
    return theta
# EVOLVE-BLOCK-END
