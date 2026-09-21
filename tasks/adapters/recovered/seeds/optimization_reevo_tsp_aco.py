# Extracted from the MIT-licensed official reevo repository.
# Source: prompts/tsp_aco/seed_func.txt
import numpy as np
def heuristics_v1(distance_matrix: np.ndarray) -> np.ndarray:
    return 1 / distance_matrix
