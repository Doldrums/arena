"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def reward(observation, action, next_observation, info):
    # Seed: forward progress minus a small control cost; refine with task-specific shaping terms.
    return float(info.get('x_velocity', 0.0)) - 0.001 * float(np.sum(np.square(action)))
# EVOLVE-BLOCK-END
