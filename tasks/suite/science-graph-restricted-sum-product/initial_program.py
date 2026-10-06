"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
P = {'n': 14, 'm': 35, 'maximum': 10000}

def construct():
    from itertools import combinations
    return {'values':list(range(1,P['n']+1)),'edges':[list(e) for e in list(combinations(range(P['n']),2))[:P['m']]]}
# EVOLVE-BLOCK-END
