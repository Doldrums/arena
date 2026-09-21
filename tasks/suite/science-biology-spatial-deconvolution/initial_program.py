"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np
from scipy.optimize import nnls

def deconvolve(spatial_counts, reference_profiles, coordinates):
    return np.array([nnls(reference_profiles, spot)[0] for spot in spatial_counts])
# EVOLVE-BLOCK-END
