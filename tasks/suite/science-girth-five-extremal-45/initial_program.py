"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Four disjoint Petersen graphs and a pentagon.
    edges = []
    for k in range(4):
        o = 10 * k
        edges += [[o + i, o + (i + 1) % 5] for i in range(5)]
        edges += [[o + 5 + i, o + 5 + (i + 2) % 5] for i in range(5)]
        edges += [[o + i, o + 5 + i] for i in range(5)]
    return edges + [[40 + i, 40 + (i + 1) % 5] for i in range(5)]
# EVOLVE-BLOCK-END
