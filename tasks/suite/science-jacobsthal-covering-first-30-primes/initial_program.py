"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Greedy: give each uncovered integer, in increasing order, to the smallest unused prime.
    primes = [p for p in range(2, 114) if all(p % q for q in range(2, p))]
    residue, x = {}, 1
    while len(residue) < len(primes):
        if not any((x - r) % p == 0 for p, r in residue.items()):
            p = next(q for q in primes if q not in residue)
            residue[p] = x % p
        x += 1
    return [residue[p] for p in primes]
# EVOLVE-BLOCK-END
