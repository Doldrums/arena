"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def partition(adjacency):
    # Greedy local improvement from an alternating start.
    n = len(adjacency)
    labels = np.arange(n) % 2
    for _ in range(3):
        for v in range(n):
            same = adjacency[v][labels == labels[v]].sum()
            other = adjacency[v][labels != labels[v]].sum()
            if same > other:
                labels[v] = 1 - labels[v]
    return labels
# EVOLVE-BLOCK-END
