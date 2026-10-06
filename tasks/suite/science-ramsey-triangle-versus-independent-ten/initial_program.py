"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Andrasfai graph And(9): Z_26 with i ~ j iff (j - i) mod 26 is 1 mod 3.
    # It is triangle-free and its largest independent set has 9 vertices.
    n = 26
    return {'n': n, 'edges': [[i, j] for i in range(n) for j in range(i + 1, n) if (j - i) % n % 3 == 1]}
# EVOLVE-BLOCK-END
