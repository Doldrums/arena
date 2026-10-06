"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    from itertools import combinations
    from math import gcd
    selected = []
    for x in range(1, 129):
        if all(len({gcd(a,b),gcd(a,x),gcd(b,x)}) > 1 for a,b in combinations(selected,2)):
            selected.append(x)
    return selected
# EVOLVE-BLOCK-END
