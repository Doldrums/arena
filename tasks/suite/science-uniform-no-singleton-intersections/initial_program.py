"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
P = {'n': 16, 'r': 4}

def construct():
    return [list(range(i,i+4)) for i in range(0,16,4)]
# EVOLVE-BLOCK-END
