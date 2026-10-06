"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # 0..14 and the multiples of 15, plus the end mark: 29 marks.
    return sorted(set(range(15)) | set(range(15, 200, 15)) | {200})
# EVOLVE-BLOCK-END
