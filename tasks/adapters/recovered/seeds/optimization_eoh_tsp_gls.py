# Extracted from EoH MIT-licensed prob.py template_program.
import numpy as np
def update_edge_distance(edge_distance: np.ndarray, local_opt_tour: np.ndarray,
                          edge_n_used: np.ndarray) -> np.ndarray:
    """Modify the edge distance matrix to escape the current local optimum.

    Args:
        edge_distance:  n*n symmetric matrix of original pairwise distances
        local_opt_tour: length-n array of node indices forming the current
                        local-optimal tour
        edge_n_used:    n*n symmetric matrix counting how many times each
                        edge has been penalised in previous iterations
    Returns:
        updated_edge_distance: modified n*n distance matrix to be used in
                               the next local search
    """
    return edge_distance.copy()
