"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Every edge as its own piece; the instance generator is copied from the verifier.
    from random import Random
    def instance(n, p, seed):
        rng = Random(seed)
        order = list(range(n))
        rng.shuffle(order)
        edges = {tuple(sorted(e)) for e in zip(order, order[1:])}
        edges |= {(u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < p}
        return sorted(edges)
    return [[list(e) for e in instance(*spec)] for spec in ((20, 0.4, 11), (25, 0.35, 12), (30, 0.3, 13))]
# EVOLVE-BLOCK-END
