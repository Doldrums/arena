"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def construct(training_x, training_subgrid_tendency):
    # Linear least-squares closure embedded in the degree-five search space.
    coeff = np.zeros(6)
    coeff[:2] = np.polynomial.polynomial.polyfit(training_x, training_subgrid_tendency, 1)
    return coeff
# EVOLVE-BLOCK-END
