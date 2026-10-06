"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    def squarefree(v):
        return all(v % (d * d) for d in range(2, int(v ** 0.5) + 1))
    chosen = []
    for x in range(1, 513):
        if all(squarefree(x + y) for y in chosen + [x]):
            chosen.append(x)
    return chosen
# EVOLVE-BLOCK-END
