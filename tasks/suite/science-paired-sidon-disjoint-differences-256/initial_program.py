"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
from itertools import combinations, combinations_with_replacement

def construct():
    sets=[[],[]]
    for x in range(1,129):
        for side in (0,1):
            candidate=sets[side]+[x]
            sums=[a+b for a,b in combinations_with_replacement(candidate,2)]
            differences={b-a for a,b in combinations(candidate,2)}
            other={b-a for a,b in combinations(sets[1-side],2)}
            if len(sums)==len(set(sums)) and not differences & other:
                sets[side]=candidate
    return sets
# EVOLVE-BLOCK-END
