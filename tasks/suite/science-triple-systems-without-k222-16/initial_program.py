"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # All triples through point 0.
    return [[0, a, b] for a in range(1, 16) for b in range(a + 1, 16)]
# EVOLVE-BLOCK-END
