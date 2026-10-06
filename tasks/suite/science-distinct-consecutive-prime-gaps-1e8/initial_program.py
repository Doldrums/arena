"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Longest string of distinct gaps among primes below 10^5.
    n = 10 ** 5
    sieve = bytearray([1]) * n
    sieve[0:2] = b'\x00\x00'
    for i in range(2, int(n ** 0.5) + 1):
        if sieve[i]:
            sieve[i * i::i] = bytearray(len(range(i * i, n, i)))
    primes = [i for i in range(n) if sieve[i]]
    gaps = [b - a for a, b in zip(primes, primes[1:])]
    best = (1, 0)
    for i in range(len(gaps)):
        seen = set()
        j = i
        while j < len(gaps) and gaps[j] not in seen:
            seen.add(gaps[j])
            j += 1
        best = max(best, (j - i, i))
    return {'start': primes[best[1]], 'length': best[0]}
# EVOLVE-BLOCK-END
