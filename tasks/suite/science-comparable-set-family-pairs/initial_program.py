"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
P = {'n': 12, 'm': 40}

def construct():
    return [[b for b in range(P['n']) if (mask>>b)&1] for mask in range(P['m'])]
# EVOLVE-BLOCK-END
