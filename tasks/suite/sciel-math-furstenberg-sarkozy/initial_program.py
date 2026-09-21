# EVOLVE-BLOCK-START
import numpy as np


def furstenberg_sarkozy_205() -> np.ndarray:
    """
    Furstenberg-Sarkozy problem (modular formulation). Find a subset of Z/mZ of maximum
    size that does NOT contain any two elements differing by a nonzero perfect k-th power
    modulo m. Here m = 205 and k = 2 (squares), i.e. forbidden differences are the nonzero
    quadratic residues modulo 205.

    The returned subset is the AlphaEvolve search target: the larger it is (while staying
    feasible) the better. The AlphaEvolve record for this instance is a subset of size 12.

    The notebook's literal search seed is the trivial subset [0]; here we use a slightly
    stronger but still simple deterministic greedy construction as the starting point so
    evolution has something concrete to improve on.

    Returns:
        subset: np.ndarray of shape (s,), dtype int, a list of distinct residues in
            {0, ..., 204} with no two differing by a nonzero square modulo 205.
    """
    m = 205
    k = 2
    # Forbidden differences: the nonzero k-th power residues modulo m.
    forbidden = set()
    for x in range(1, m):
        forbidden.add(pow(x, k, m))
    forbidden.discard(0)

    selected = []
    for candidate in range(m):
        ok = True
        for s in selected:
            d1 = (candidate - s) % m
            d2 = (s - candidate) % m
            if d1 in forbidden or d2 in forbidden:
                ok = False
                break
        if ok:
            selected.append(candidate)

    return np.array(selected, dtype=np.int64)


# EVOLVE-BLOCK-END
