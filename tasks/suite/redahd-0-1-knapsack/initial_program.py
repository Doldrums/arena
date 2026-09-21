"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def select_next_item(remaining_capacity, remaining_weights, remaining_values):
    # Highest value density first.
    return int(np.argmax(remaining_values / remaining_weights))
# EVOLVE-BLOCK-END
