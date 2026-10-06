"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Colour {i, j} by (i + j) mod 17: two disjoint edges of one K4 may share a colour,
    # but two such coincidences would force 2(b - c) = 0 mod 17.
    return [(i + j) % 17 for i in range(16) for j in range(i + 1, 16)]
# EVOLVE-BLOCK-END
