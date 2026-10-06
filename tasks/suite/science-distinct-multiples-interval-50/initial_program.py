"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Largest index first, each takes its smallest free multiple above 50.
    used, b = set(), {}
    for i in range(50, 0, -1):
        x = (50 // i + 1) * i
        while x in used:
            x += i
        used.add(x)
        b[i] = x
    return [b[i] for i in range(1, 51)]
# EVOLVE-BLOCK-END
