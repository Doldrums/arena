"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    from random import Random
    def instance(n, p, seed):
        rng = Random(seed)
        return [(u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < p]
    return [[list(e) for e in instance(n, p, seed)] for n, p, seed in ((32, 0.6, 601), (64, 0.55, 602))]
# EVOLVE-BLOCK-END
