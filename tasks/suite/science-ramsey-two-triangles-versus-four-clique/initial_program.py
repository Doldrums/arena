"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    # Blow up the 2-colouring of K5 by the pentagon and pentagram into classes of 3 vertices;
    # edges inside a class get colour 2 (a K3, hence K4-free).
    n, t = 15, 3
    colors = []
    for i in range(n):
        for j in range(i + 1, n):
            a, b = i // t, j // t
            colors.append(2 if a == b else (0 if (a - b) % 5 in (1, 4) else 1))
    return {'n': n, 'colors': colors}
# EVOLVE-BLOCK-END
