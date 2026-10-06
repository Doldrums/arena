"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Five disjoint copies of K4.
    edges = []
    for k in range(5):
        edges += [[4 * k + a, 4 * k + b] for a in range(4) for b in range(a + 1, 4)]
    return edges
# EVOLVE-BLOCK-END
