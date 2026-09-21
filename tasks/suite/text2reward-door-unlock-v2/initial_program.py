"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def reward(observation, action, next_observation, info):
    # Dense shaping: bring the hand (obs[0:3]) to the object (obs[4:7]); bonus on success.
    distance = float(np.linalg.norm(next_observation[:3] - next_observation[4:7]))
    return -distance + 5.0 * float(info.get("success", 0.0))
# EVOLVE-BLOCK-END
