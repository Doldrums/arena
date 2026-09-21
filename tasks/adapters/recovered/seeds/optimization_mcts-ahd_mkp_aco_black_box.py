# Extracted from the MIT-licensed official mcts-ahd repository.
# Source: prompts/mkp_aco_black_box/seed_func.txt
import numpy as np
def heuristics_v1(item_attr1: np.ndarray, item_attr2: np.ndarray) -> np.ndarray:
    n, m = item_attr2.shape
    return np.ones(n,)
