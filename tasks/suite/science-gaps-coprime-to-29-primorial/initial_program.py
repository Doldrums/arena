"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    from math import gcd
    m = 6469693230
    units = [x for x in range(1, 20000) if gcd(x, m) == 1]
    first = {}
    for a, b in zip(units, units[1:]):
        first.setdefault(b - a, a)
    return [[x, g] for g, x in sorted(first.items())]
# EVOLVE-BLOCK-END
