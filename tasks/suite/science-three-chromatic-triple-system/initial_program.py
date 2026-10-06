"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
P = {'n': 9, 'r': 3, 'colors': 3}

def construct():
    from itertools import combinations
    return {'edges':[list(e) for e in combinations(range(5),3)],'colors':[0,0,1,1,2,0,0,0,0]}
# EVOLVE-BLOCK-END
