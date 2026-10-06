"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # K3,13: any Q3 would need four vertices on each side.
    return [[a, b] for a in range(3) for b in range(3, 16)]
# EVOLVE-BLOCK-END
