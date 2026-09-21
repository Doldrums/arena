"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np
from scipy.ndimage import gaussian_filter

def denoise(noisy_image, acquisition_metadata):
    # Variance-stabilized smooth seed; preserve physical nonnegative intensity.
    stabilized=2*np.sqrt(np.maximum(noisy_image,0)+3/8)
    smoothed=gaussian_filter(stabilized, .65)
    return np.maximum((smoothed/2)**2-3/8,0)
# EVOLVE-BLOCK-END
