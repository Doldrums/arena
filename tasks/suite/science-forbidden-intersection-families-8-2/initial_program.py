"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # All sets with at most one or at least six elements: 9 + 37 sets.
    from itertools import combinations
    ground = range(1, 9)
    return [list(c) for k in (0, 1, 6, 7, 8) for c in combinations(ground, k)]
# EVOLVE-BLOCK-END
