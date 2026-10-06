"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # K9 split by circular distance: distances 1, 2 and 4 give nonagons, distance 3 gives three triangles.
    n = 9
    return {'n': n, 'colors': [min(j - i, n - j + i) - 1 for i in range(n) for j in range(i + 1, n)]}
# EVOLVE-BLOCK-END
