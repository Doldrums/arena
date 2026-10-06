"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Mycielski construction applied twice to the pentagon: Groetzsch graph (11) then 23 vertices.
    def mycielski(n, edges):
        out = [list(e) for e in edges]
        for u, w in edges:
            out += [[u, n + w], [w, n + u]]
        out += [[n + u, 2 * n] for u in range(n)]
        return 2 * n + 1, out
    n, edges = mycielski(5, [[i, (i + 1) % 5] for i in range(5)])
    n, edges = mycielski(n, edges)
    return {'n': n, 'edges': edges}
# EVOLVE-BLOCK-END
