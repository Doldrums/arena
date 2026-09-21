import numpy as np


def construct_packing():
    # Independently written trivial seed: a 6x6 grid of equal circles, first 32 used.
    cells = [((i + 0.5) / 6, (j + 0.5) / 6) for i in range(6) for j in range(6)]
    centers = np.array(cells[:32])
    radii = np.full(32, 0.083)
    return centers, radii
