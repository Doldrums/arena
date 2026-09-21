"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def controller(state, t):
    x, xdot, theta, thetadot = state
    return 1.0 * x + 2.0 * xdot + 30.0 * theta + 8.0 * thetadot
# EVOLVE-BLOCK-END
