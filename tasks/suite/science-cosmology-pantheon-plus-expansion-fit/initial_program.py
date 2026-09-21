"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def expansion(z, theta):
    # Flat LambdaCDM: one parameter, the present matter density.
    om = theta[0]
    return np.sqrt(om * (1.0 + np.asarray(z)) ** 3 + (1.0 - om))


def initial_theta():
    return np.array([0.3])


def bounds():
    return [(0.05, 0.95)]
# EVOLVE-BLOCK-END
