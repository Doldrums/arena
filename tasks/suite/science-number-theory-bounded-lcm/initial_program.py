"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    from math import isqrt
    return list(range(1, isqrt(512) + 1))
# EVOLVE-BLOCK-END
