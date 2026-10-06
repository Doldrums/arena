"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # The regular octagon, which Erdős, Herzog and Piranian asked about as a candidate maximizer.
    from math import cos, sin, pi
    return [[cos(2 * pi * k / 8), sin(2 * pi * k / 8)] for k in range(8)]
# EVOLVE-BLOCK-END
