"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
from math import isqrt

def construct():
    def prime(n):return n>=2 and all(n%d for d in range(2,isqrt(n)+1))
    return [[3,n-3] if prime(n-3) else None for n in range(1000000,1000512,2)]
# EVOLVE-BLOCK-END
