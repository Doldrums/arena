"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def select_next_node(current_node, destination_node, unvisited_nodes, distance_matrix):
    # Nearest neighbour.
    return int(unvisited_nodes[np.argmin(distance_matrix[current_node, unvisited_nodes])])
# EVOLVE-BLOCK-END
