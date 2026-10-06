"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Complete bipartite graph K25,25: triangle-free with diameter two.
    return [[a, b] for a in range(25) for b in range(25, 50)]
# EVOLVE-BLOCK-END
