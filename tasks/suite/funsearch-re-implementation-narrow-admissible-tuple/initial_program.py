"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
N = 5000

# EVOLVE-BLOCK-START
def _primes(limit):
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    for p in range(2, int(limit ** 0.5) + 1):
        if sieve[p]:
            for q in range(p * p, limit + 1, p):
                sieve[q] = False
    return [p for p, ok in enumerate(sieve) if ok]


def construct():
    # Start from 1 and the primes above sqrt(N); repair any prime whose residue classes are all covered
    # by deleting the least-populated class, until the tuple is admissible.
    points = [1] + [p for p in _primes(N) if p * p > N]
    changed = True
    while changed:
        changed = False
        for p in _primes(len(points)):
            classes = {}
            for v in points:
                classes.setdefault(v % p, []).append(v)
            if len(classes) == p:
                smallest = min(classes.values(), key=len)
                points = [v for v in points if v not in smallest]
                changed = True
                break
    return points
# EVOLVE-BLOCK-END
