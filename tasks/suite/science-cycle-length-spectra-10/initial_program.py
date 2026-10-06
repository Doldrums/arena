"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    graphs = [[]]
    for k in range(3, 11):
        graphs.append([[i, (i + 1) % k] for i in range(k)])
    graphs.append([[u, v] for u in range(10) for v in range(u + 1, 10)])
    return graphs
# EVOLVE-BLOCK-END
