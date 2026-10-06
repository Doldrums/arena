"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # K20,20 plus one edge inside a part.
    return [[a, b] for a in range(20) for b in range(20, 40)] + [[0, 1]]
# EVOLVE-BLOCK-END
