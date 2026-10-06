"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # The Groetzsch graph on vertices 0..10 (Mycielski graph of the pentagon); vertices 11..15 isolated.
    cycle = [(i, (i + 1) % 5) for i in range(5)]
    edges = [list(e) for e in cycle]
    for u, w in cycle:
        edges += [[u, 5 + w], [w, 5 + u]]
    return edges + [[5 + u, 10] for u in range(5)]
# EVOLVE-BLOCK-END
