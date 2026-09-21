# Extracted from the MIT-licensed official hsevo repository.
# Source: prompts/op_aco/seed_func.txt
import numpy as np
def heuristics_v1(prize: np.ndarray, distance: np.ndarray, maxlen: float) -> np.ndarray:
    return prize[np.newaxis, :] / distance
