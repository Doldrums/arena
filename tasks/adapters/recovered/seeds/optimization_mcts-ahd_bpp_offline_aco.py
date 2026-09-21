# Extracted from the MIT-licensed official mcts-ahd repository.
# Source: prompts/bpp_offline_aco/seed_func.txt
import numpy as np
def heuristics_v1(demand: np.ndarray, capacity: int) -> np.ndarray:
    return np.tile(demand/demand.max(), (demand.shape[0], 1))
