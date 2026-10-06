"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # K_{8,8} plus one edge inside a part.
    edges = [[u, v] for u in range(8) for v in range(8, 16)] + [[0, 1]]
    return {'n': 16, 'edges': edges}
# EVOLVE-BLOCK-END
