"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def dispatch(ready_operations, time):
    # Most work remaining first.
    return int(np.argmax([op["remaining_work"] for op in ready_operations]))
# EVOLVE-BLOCK-END
