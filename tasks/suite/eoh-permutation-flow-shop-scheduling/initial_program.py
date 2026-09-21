"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def order_jobs(processing_times):
    # Longest total processing time first (a Palmer/NEH-style ordering rule).
    return list(np.argsort(-processing_times.sum(axis=1)))
# EVOLVE-BLOCK-END
