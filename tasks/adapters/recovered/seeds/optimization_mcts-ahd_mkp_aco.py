# Extracted from the MIT-licensed official mcts-ahd repository.
# Source: prompts/mkp_aco/seed_func.txt
import numpy as np
def heuristics_v1(prize: np.ndarray, weight: np.ndarray) -> np.ndarray:
    return prize / np.sum(weight, axis=1)
