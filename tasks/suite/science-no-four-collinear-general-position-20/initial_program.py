"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Twenty points on the parabola y = x^2 (no three collinear, so the score is 20).
    return [[x, x * x] for x in range(-10, 10)]
# EVOLVE-BLOCK-END
