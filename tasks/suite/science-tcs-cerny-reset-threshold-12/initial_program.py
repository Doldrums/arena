"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
N = 12

# EVOLVE-BLOCK-START
def construct():
    # A simple synchronizing automaton: cycle plus a map to state zero.
    return [[(i + 1) % N for i in range(N)], [0] * N]
# EVOLVE-BLOCK-END
