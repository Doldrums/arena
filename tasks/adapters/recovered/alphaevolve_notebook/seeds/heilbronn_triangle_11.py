# Independently written trivial seed for the AlphaEvolve notebook task; a valid but weak
# construction. It is not the published construction and not a reproduction of the paper.
# Contract: construct() -> numpy array of shape (11, 2) inside the triangle (0,0), (1,0), (1/2, sqrt(3)/2)
import random
import numpy as np


def construct():
    rng = random.Random(7)
    points = []
    while len(points) < 11:
        u, v = rng.random(), rng.random()
        if u + v < 0.98 and u > 0.01 and v > 0.01:
            points.append([u + 0.5 * v, (3 ** 0.5) / 2 * v])
    return np.array(points)
