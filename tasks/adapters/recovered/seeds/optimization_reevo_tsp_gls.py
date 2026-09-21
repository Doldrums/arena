# Extracted from the MIT-licensed official reevo repository.
# Source: prompts/tsp_gls/seed_func.txt
import numpy as np
def heuristics_v1(distance_matrix: np.ndarray) -> np.ndarray:
    # It's bad to include long edges in the solution
    return distance_matrix
