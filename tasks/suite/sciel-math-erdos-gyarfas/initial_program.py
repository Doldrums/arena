# EVOLVE-BLOCK-START
import numpy as np


def erdos_gyarfas_graph() -> np.ndarray:
    """
    Erdős-Gyárfás counterexample search. Construct a finite simple graph G whose
    minimum degree is at least 3, trying to AVOID any cycle whose length is a power
    of two (4, 8, 16, ...). The Erdős-Gyárfás conjecture states no such graph exists;
    we search for a counterexample (or, failing that, a graph with as few power-of-two
    cycles as possible).

    The graph is represented by its adjacency matrix: a symmetric numpy array A of
    shape (n, n) with entries in {0, 1} and zero diagonal, where A[i, j] = 1 iff there
    is an edge between vertices i and j.

    Baseline construction (translated from the notebook's nx.random_regular_graph(3, n)):
    a random 3-regular graph on n vertices built with the configuration / pairing model,
    deterministically seeded for reproducibility.

    Returns:
        adjacency: np.ndarray of shape (n, n), symmetric, {0, 1}-valued, zero diagonal.
    """
    n = 200  # must be even so that a 3-regular graph exists (3 * n stubs must pair up)
    rng = np.random.RandomState(0)

    for _attempt in range(50000):
        # Three "stubs" per vertex; randomly pair them up (configuration model).
        stubs = np.repeat(np.arange(n), 3)
        rng.shuffle(stubs)
        pairs = stubs.reshape(-1, 2)

        adjacency = np.zeros((n, n), dtype=np.int64)
        ok = True
        for a, b in pairs:
            a = int(a)
            b = int(b)
            if a == b or adjacency[a, b] == 1:
                ok = False  # self-loop or parallel edge -> reject this pairing
                break
            adjacency[a, b] = 1
            adjacency[b, a] = 1
        if ok:
            return adjacency

    # Deterministic fallback: a 3-regular "cycle + antipodal matching" (Möbius-Kantor
    # style) graph, guaranteed simple for even n >= 6.
    adjacency = np.zeros((n, n), dtype=np.int64)
    for i in range(n):
        j = (i + 1) % n
        k = (i + n // 2) % n
        adjacency[i, j] = adjacency[j, i] = 1
        adjacency[i, k] = adjacency[k, i] = 1
    return adjacency


# EVOLVE-BLOCK-END
