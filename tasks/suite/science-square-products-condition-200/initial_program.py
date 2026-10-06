"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    return [p for p in range(2, 201) if all(p % q for q in range(2, p))]
# EVOLVE-BLOCK-END
