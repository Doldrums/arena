"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    selected=set()
    for x in range(4096,0,-1):
        if not (2*x in selected and 3*x in selected):
            selected.add(x)
    return sorted(selected)
# EVOLVE-BLOCK-END
