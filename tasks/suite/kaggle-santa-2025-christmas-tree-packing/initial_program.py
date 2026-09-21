"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math


def construct(n):
    # Trivial seed: upright trees on a grid whose cell is the tree's bounding box (0.7 wide, 1.0 tall),
    # with a hair of clearance so that floating-point rounding never makes neighbours overlap.
    cols = max(1, round(math.sqrt(n / 0.7)))
    return [[(k % cols) * (0.7 + 1e-6), (k // cols) * (1.0 + 1e-6), 0.0] for k in range(n)]
# EVOLVE-BLOCK-END
