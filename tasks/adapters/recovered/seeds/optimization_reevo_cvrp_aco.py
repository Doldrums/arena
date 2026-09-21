# Extracted from the MIT-licensed official reevo repository.
# Source: prompts/cvrp_aco/seed_func.txt
import numpy as np
def heuristics_v1(distance_matrix: np.ndarray, coordinates: np.ndarray, demands: np.ndarray, capacity: int) -> np.ndarray:
    return 1 / distance_matrix
