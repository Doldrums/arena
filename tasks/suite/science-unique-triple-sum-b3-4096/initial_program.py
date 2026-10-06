"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
from itertools import combinations_with_replacement

def construct():
    selected=[]
    for x in range(1,513):
        candidate=selected+[x]
        sums=[sum(t) for t in combinations_with_replacement(candidate,3)]
        if len(sums)==len(set(sums)):
            selected.append(x)
    return selected
# EVOLVE-BLOCK-END
