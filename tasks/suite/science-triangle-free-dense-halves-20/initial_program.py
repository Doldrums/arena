"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # The 20-cycle; alternate vertices form an independent half.
    return [[i, (i + 1) % 20] for i in range(20)]
# EVOLVE-BLOCK-END
