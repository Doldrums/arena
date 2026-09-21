"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
N = 16

# EVOLVE-BLOCK-START
def construct():
    # Odd-even transposition sorting network: 120 comparators for 16 wires.
    return [(i, i + 1) for phase in range(N)
            for i in range(phase % 2, N - 1, 2)]
# EVOLVE-BLOCK-END
