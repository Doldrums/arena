"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Multiples of 20 with residues 0..9 are pairwise disjoint (they differ modulo 20).
    return [[20 * j, j - 1] for j in range(1, 11)]
# EVOLVE-BLOCK-END
