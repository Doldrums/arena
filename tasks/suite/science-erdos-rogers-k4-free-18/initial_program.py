"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Complete tripartite graph K6,6,6: K4-free; two parts induce a triangle-free graph.
    parts = [range(0, 6), range(6, 12), range(12, 18)]
    return [[a, b] for i in range(3) for j in range(i + 1, 3) for a in parts[i] for b in parts[j]]
# EVOLVE-BLOCK-END
