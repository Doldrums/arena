"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Successively partition the remaining multiples of powers of two.
    return [[(1<<k)-1,1<<(k+1)] for k in range(7)]
# EVOLVE-BLOCK-END
