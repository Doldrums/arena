"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    from math import isqrt
    moduli = [101,103,107,109,113,127,131,137,139,149,151,157]
    def prime(x):
        return x >= 2 and all(x % d for d in range(2,isqrt(x)+1))
    roots=[]
    for p in moduli:
        for g in range(1000,1,-1):
            if prime(g) and len({pow(g,k,p) for k in range(1,p)}) == p-1 and g % p:
                roots.append(g)
                break
    return roots
# EVOLVE-BLOCK-END
