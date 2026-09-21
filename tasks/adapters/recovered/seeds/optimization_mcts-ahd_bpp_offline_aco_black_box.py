# Extracted from the MIT-licensed official mcts-ahd repository.
# Source: prompts/bpp_offline_aco_black_box/seed_func.txt
import numpy as np
def heuristics_v1(node_attr: np.ndarray, node_constraint: int) -> np.ndarray:
    n = node_attr.shape[0]
    return np.ones((n, n))
