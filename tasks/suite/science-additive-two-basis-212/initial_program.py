"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # 0..14 and the multiples of 15 up to 210: 29 elements.
    return sorted(set(range(15)) | set(range(15, 213, 15)))
# EVOLVE-BLOCK-END
