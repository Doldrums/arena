"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import random

def construct():
    permutation=list(range(1,129))
    random.Random(184).shuffle(permutation)
    return permutation
# EVOLVE-BLOCK-END
