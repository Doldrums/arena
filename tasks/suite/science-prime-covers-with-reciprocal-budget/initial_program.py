"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # The i-th prime from 13 upward covers the integer i (sum of reciprocals about 0.92).
    primes = [p for p in range(13, 1001) if all(p % q for q in range(2, int(p ** 0.5) + 1))]
    return [[p, (i + 1) % p] for i, p in enumerate(primes)]
# EVOLVE-BLOCK-END
