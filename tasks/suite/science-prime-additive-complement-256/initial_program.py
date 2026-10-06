"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    primes={x for x in range(2,513) if all(x%d for d in range(2,int(x**0.5)+1))}
    remaining=set(range(256,513));chosen=[]
    while remaining:
        b=max((b for b in range(257) if b not in chosen),key=lambda b:sum(x-b in primes for x in remaining))
        chosen.append(b)
        remaining={x for x in remaining if x-b not in primes}
    return chosen
# EVOLVE-BLOCK-END
