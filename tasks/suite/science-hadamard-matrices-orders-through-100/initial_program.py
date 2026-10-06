"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Independently coded classical Sylvester doubling construction.
    matrices={};h=[[1]]
    while len(h)<64:
        h=[r+r for r in h]+[r+[-x for x in r] for r in h]
        if len(h)>=4:matrices[len(h)]=h
    return [matrices.get(n) for n in range(4,101,4)]
# EVOLVE-BLOCK-END
