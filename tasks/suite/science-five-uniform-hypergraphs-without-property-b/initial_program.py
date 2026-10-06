"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # The complete 5-uniform hypergraph on 9 vertices: any 2-colouring has 5 vertices of one colour.
    from itertools import combinations
    return {'n': 9, 'edges': [list(e) for e in combinations(range(9), 5)]}
# EVOLVE-BLOCK-END
