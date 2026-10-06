"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # The 23-cycle: triangle-free and one deletion from bipartite.
    return [[i, (i + 1) % 23] for i in range(23)]
# EVOLVE-BLOCK-END
