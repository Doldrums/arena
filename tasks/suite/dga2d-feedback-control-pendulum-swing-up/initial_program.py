"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math


def controller(state, t):
    theta, omega = state
    # Linear feedback toward the upright position (theta = 0).
    return -5.0 * math.atan2(math.sin(theta), math.cos(theta)) - 2.0 * omega
# EVOLVE-BLOCK-END
