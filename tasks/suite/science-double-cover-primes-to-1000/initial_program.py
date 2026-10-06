"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # The i-th prime covers the integer ceil(i/2), so every integer up to 84 is hit twice.
    primes = [p for p in range(2, 1001) if all(p % q for q in range(2, int(p ** 0.5) + 1))]
    return [((i + 2) // 2) % p for i, p in enumerate(primes)]
# EVOLVE-BLOCK-END
