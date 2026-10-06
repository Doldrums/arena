"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # The first 68 pairs in lexicographic order.
    pairs = [[i, j] for i in range(16) for j in range(i + 1, 16)]
    return pairs[:68]
# EVOLVE-BLOCK-END
