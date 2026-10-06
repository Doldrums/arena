"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # All triples through point 0 (no two are disjoint).
    return [[0, a, b] for a in range(1, 12) for b in range(a + 1, 12)]
# EVOLVE-BLOCK-END
