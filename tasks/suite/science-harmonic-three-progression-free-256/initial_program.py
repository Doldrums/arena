"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    selected=[]
    for x in range(1,257):
        if all(2*b-a!=x for a in selected for b in selected if a<b):
            selected.append(x)
    return selected
# EVOLVE-BLOCK-END
