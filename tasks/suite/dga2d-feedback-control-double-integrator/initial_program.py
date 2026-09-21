"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def controller(state, t):
    x, v = state
    return -2.0 * x - 3.0 * v
# EVOLVE-BLOCK-END
