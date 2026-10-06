"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # A 4 x 4 grid: rows, columns and the two main diagonals.
    return [[x, y] for x in range(4) for y in range(4)]
# EVOLVE-BLOCK-END
