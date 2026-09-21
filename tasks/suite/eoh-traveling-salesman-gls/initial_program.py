"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def update_edge_distance(edge_distance, local_opt_tour, edge_n_used):
    # Penalize edges of the current local optimum proportionally to their use.
    return edge_distance * (1.0 + 0.1 * edge_n_used / (1.0 + edge_n_used.max()))
# EVOLVE-BLOCK-END
