"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np
from scipy.stats import norm


def acquisition(mu, sigma, f_best):
    # Expected improvement.
    z = (f_best - mu) / (sigma + 1e-9)
    return (f_best - mu) * norm.cdf(z) + sigma * norm.pdf(z)
# EVOLVE-BLOCK-END
