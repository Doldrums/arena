"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    from itertools import combinations
    from math import lcm
    selected = []
    for x in range(1, 129):
        if all(not (lcm(a,b)==lcm(a,x)==lcm(b,x)) for a,b in combinations(selected,2)):
            selected.append(x)
    return selected
# EVOLVE-BLOCK-END
