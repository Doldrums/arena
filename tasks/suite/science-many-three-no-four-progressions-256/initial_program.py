"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    selected=set()
    for x in range(1,257):
        if all(not all(x-j*d in selected for j in (1,2,3)) for d in range(1,(x-1)//3+1)):
            selected.add(x)
    return sorted(selected)
# EVOLVE-BLOCK-END
