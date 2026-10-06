"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
P = {'n': 40, 'maximum_size': 18}

def construct():
    from math import isqrt
    return [a for a in range(2,P['n']+1) if all(a%d for d in range(2,isqrt(a)+1))]
# EVOLVE-BLOCK-END
