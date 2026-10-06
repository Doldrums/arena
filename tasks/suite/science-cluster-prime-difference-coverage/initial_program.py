"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Enumerate small primes and independently test their difference coverage.
    primes=[];best=3
    for p in range(2,101):
        if all(p%d for d in range(2,int(p**0.5)+1)):
            primes.append(p)
            differences={a-b for a in primes for b in primes if a>b}
            if p>=3 and all(d in differences for d in range(2,p-2,2)):
                best=p
    return best
# EVOLVE-BLOCK-END
