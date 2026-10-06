"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    from math import isqrt
    limit = 20000
    powerful = sorted({a * a * b ** 3 for b in range(1, 28) for a in range(1, isqrt(limit // b ** 3) + 1)})
    members = set(powerful)
    best = max(range(2, limit + 1), key=lambda n: sum(1 for a in powerful if 2 * a <= n and n - a in members))
    return {'N': best, 'pairs': [[a, best - a] for a in powerful if 2 * a <= best and best - a in members]}
# EVOLVE-BLOCK-END
