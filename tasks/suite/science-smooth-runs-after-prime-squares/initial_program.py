"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    def largest_factor(v):
        f, d = 1, 2
        while d * d <= v:
            while v % d == 0:
                f, v = d, v // d
            d += 1
        return max(f, v)
    best = (0, 2)
    for p in range(3, 2000, 2):
        if all(p % q for q in range(3, int(p ** 0.5) + 1, 2)):
            k = 0
            while largest_factor(p * p + k + 1) <= p:
                k += 1
            best = max(best, (k, p))
    return {'p': best[1], 'k': best[0]}
# EVOLVE-BLOCK-END
