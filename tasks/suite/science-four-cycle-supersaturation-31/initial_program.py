"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # The first 91 pairs in lexicographic order.
    pairs = [[i, j] for i in range(31) for j in range(i + 1, 31)]
    return pairs[:91]
# EVOLVE-BLOCK-END
