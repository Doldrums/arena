"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    def phi(x):
        result, d, y = x, 2, x
        while d * d <= y:
            if y % d == 0:
                result -= result // d
                while y % d == 0:
                    y //= d
            d += 1
        return result - result // y if y > 1 else result
    values = [0] + [phi(x) for x in range(1, 20001)]
    best = (1, 1)
    for s in range(1, 19000):
        seen, k = set(), 0
        while s + k <= 20000 and values[s + k] not in seen:
            seen.add(values[s + k])
            k += 1
        best = max(best, (k, s))
    return {'start': best[1], 'length': best[0]}
# EVOLVE-BLOCK-END
