# EVOLVE-BLOCK-START
import numpy as np


def turan_hypergraph_tetrahedron() -> tuple:
    """
    Hypergraph Turan number of the tetrahedron. Construct a weighted, blow-up
    3-uniform hypergraph pattern (vertex weights plus a multiset of size-3 edges)
    that contains no copy of the tetrahedron K4^(3), so as to maximize the Turan
    density lower bound C. The blow-up density of an edge multiset {a,b,c} over
    the (sum-normalized) vertex weights w is:
        - 6 * w[a]*w[b]*w[c]            if a,b,c are all distinct,
        - 3 * w[dup]^2 * w[other]       if exactly two coordinates coincide,
        - w[a]^3                        if a == b == c,
    and C is the sum of these contributions over all (distinct) edges.

    Baseline: the classical 5/9 construction (Turan's conjectured optimum for
    K4^(3)) on 3 weighted vertices.

    Returns:
        weights: np.ndarray of shape (V,), non-negative vertex weights.
        edges: np.ndarray of shape (E, 3) of int vertex indices in [0, V-1];
            each row is a size-3 multiset (repeats allowed) of vertices.
    """
    weights = np.array([1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0], dtype=np.float64)
    edges = np.array(
        [
            [0, 1, 2],
            [0, 0, 1],
            [1, 1, 2],
            [2, 2, 0],
        ],
        dtype=np.int64,
    )
    return weights, edges


# EVOLVE-BLOCK-END
