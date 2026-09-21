# EVOLVE-BLOCK-START
import numpy as np


def szemeredi_trotter_incidences():
    """
    Szemeredi-Trotter incidence maximization. Construct a set of n points and a set of
    m lines in the plane (on the integer lattice) so as to maximize the number of
    point-line incidences (pairs (p, l) with p lying on l). Here the instance is fixed
    at n = 54 points and m = 27 lines.

    Baseline: the classical Szemeredi-Trotter extremal grid construction with k = 3.
        Points:  {1,...,k} x {1,...,2*k^2}                          -> 2*k^3 = 54 points
        Lines :  y = a*x + b  for a in {1,...,k}, b in {1,...,k^2}  ->   k^3 = 27 lines
    Each line y = a*x + b passes through exactly k of the grid points (one per column
    x in {1,...,k}, since a*x + b stays within {1,...,2*k^2}), giving k^4 = 81 total
    incidences. This matches the Szemeredi-Trotter bound n^(2/3) m^(2/3) up to a constant.

    Lines are encoded in homogeneous form (A, B, C) meaning A*x + B*y + C = 0, so the
    line y = a*x + b becomes (a, -1, b).

    Returns:
        points: np.ndarray of shape (54, 2), integer (x, y) lattice coordinates.
        lines : np.ndarray of shape (27, 3), integer (A, B, C) with A*x + B*y + C = 0.
    """
    k = 3
    # Points: {1,...,k} x {1,...,2*k^2}
    xs = np.arange(1, k + 1)
    ys = np.arange(1, 2 * k * k + 1)
    px, py = np.meshgrid(xs, ys, indexing="ij")
    points = np.stack([px.ravel(), py.ravel()], axis=1).astype(np.int64)

    # Lines: y = a*x + b  ->  a*x - y + b = 0  ->  (A, B, C) = (a, -1, b)
    rows = []
    for a in range(1, k + 1):
        for b in range(1, k * k + 1):
            rows.append((a, -1, b))
    lines = np.array(rows, dtype=np.int64)

    return points, lines


# EVOLVE-BLOCK-END
