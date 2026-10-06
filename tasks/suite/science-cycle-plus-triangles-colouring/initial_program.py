"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    from random import Random
    from itertools import combinations
    def instance(n, seed):
        rng = Random(seed)
        order = list(range(n))
        while True:
            rng.shuffle(order)
            triples = [order[i:i + 3] for i in range(0, n, 3)]
            if all((a - b) % n not in (1, n - 1) for t in triples for a, b in combinations(t, 2)):
                break
        edges = {(min(i, (i + 1) % n), max(i, (i + 1) % n)) for i in range(n)}
        edges |= {(min(a, b), max(a, b)) for t in triples for a, b in combinations(t, 2)}
        return sorted(edges)

    def greedy(n, edges, palette):
        adj = [set() for _ in range(n)]
        for u, v in edges:
            adj[u].add(v)
            adj[v].add(u)
        colour = [None] * n
        for v in sorted(range(n), key=lambda u: -len(adj[u])):
            taken = {colour[u] for u in adj[v]}
            free = [c for c in palette(v) if c not in taken]
            colour[v] = free[0] if free else palette(v)[0]
        return colour

    return [greedy(n, instance(n, seed), lambda v: [0, 1, 2]) for n, seed in ((30, 401), (60, 402), (90, 403), (150, 404), (300, 405))]
# EVOLVE-BLOCK-END
