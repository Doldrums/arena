"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    from math import isqrt
    values = []
    for p in range(2, 10001):
        if all(p % d for d in range(2, isqrt(p) + 1)):
            if len(values) < 2 or p - values[-1] >= values[-1] - values[-2]:
                values.append(p)
    return values
# EVOLVE-BLOCK-END
