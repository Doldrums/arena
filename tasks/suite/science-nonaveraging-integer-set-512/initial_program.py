"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
from itertools import combinations

def construct():
    selected=[]
    for x in range(1,129):
        candidate=selected+[x]
        valid=True
        for a in candidate:
            others=[y for y in candidate if y!=a]
            if any(sum(t)==len(t)*a for k in range(2,len(others)+1) for t in combinations(others,k)):
                valid=False;break
        if valid:selected=candidate
    return selected
# EVOLVE-BLOCK-END
