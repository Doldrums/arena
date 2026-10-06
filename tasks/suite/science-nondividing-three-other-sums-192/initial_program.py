"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
from itertools import combinations

def construct():
    selected=[]
    for x in range(192,0,-1):
        candidate=selected+[x]
        if all(sum(t)%a for a in candidate for t in combinations([v for v in candidate if v!=a],3)):
            selected.append(x)
    return selected
# EVOLVE-BLOCK-END
