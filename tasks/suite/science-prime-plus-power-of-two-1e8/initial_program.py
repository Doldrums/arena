"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    def prime(v):
        return v > 1 and all(v % d for d in range(2, int(v ** 0.5) + 1))
    def count(n):
        return sum(prime(n - 2 ** k) for k in range(n.bit_length()) if n - 2 ** k > 1)
    return max(range(3, 5000), key=count)
# EVOLVE-BLOCK-END
