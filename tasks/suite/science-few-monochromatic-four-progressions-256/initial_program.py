"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Alternate colours in blocks of two.
    return [(i // 2) % 2 for i in range(256)]
# EVOLVE-BLOCK-END
