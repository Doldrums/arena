"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def select_next_node(current_node, depot, unvisited_nodes, rest_capacity, demands, distance_matrix):
    # Nearest feasible customer.
    return int(unvisited_nodes[np.argmin(distance_matrix[current_node, unvisited_nodes])])
# EVOLVE-BLOCK-END
