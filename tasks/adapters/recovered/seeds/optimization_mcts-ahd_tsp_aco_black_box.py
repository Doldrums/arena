# Extracted from the MIT-licensed official mcts-ahd repository.
# Source: prompts/tsp_aco_black_box/seed_func.txt
import numpy as np
def heuristics_v1(edge_attr: np.ndarray) -> np.ndarray:
    return np.ones(edge_attr.shape[0])
