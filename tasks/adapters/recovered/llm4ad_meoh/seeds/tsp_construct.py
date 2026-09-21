# Original LLM4AD template program for this task, extracted from the pinned template module.
import numpy as np
def select_next_node(current_node: int, destination_node: int, unvisited_nodes: np.ndarray, distance_matrix: np.ndarray) -> int: 
    """
    Design a novel algorithm to select the next node in each step.

    Args:
    current_node: ID of the current node.
    destination_node: ID of the destination node.
    unvisited_nodes: Array of IDs of unvisited nodes.
    distance_matrix: Distance matrix of nodes.

    Return:
    ID of the next node to visit.
    """
    next_node = unvisited_nodes[0]

    return next_node
