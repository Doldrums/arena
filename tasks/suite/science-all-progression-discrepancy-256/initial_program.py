"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import random

def construct():
    rng=random.Random(171)
    return [rng.choice((-1,1)) for _ in range(256)]
# EVOLVE-BLOCK-END
