"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # K2,40 has no odd cycle and no six-cycle (one side has only two vertices).
    return [[a, b] for a in range(2) for b in range(2, 42)]
# EVOLVE-BLOCK-END
