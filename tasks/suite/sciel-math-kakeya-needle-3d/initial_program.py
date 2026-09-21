# EVOLVE-BLOCK-START
import numpy as np


def kakeya_needle_3d8() -> np.ndarray:
    """
    Three-dimensional discrete Kakeya needle problem with grid parameter N = 8.

    We build N*N = 64 "generalized tubes" indexed by (i, j), i, j in {0, ..., N-1}.
    Tube (i, j) has a base position (x, y) and, at height c in [0, 1], occupies the
    axis-aligned square
        [x + c*i/N, x + 1/N + c*i/N] x [y + c*j/N, y + 1/N + c*j/N].
    So the tube is a unit-height prism of square cross-section 1/N x 1/N that is
    sheared so its top face is offset by (i/N, j/N): the (i, j) pair selects the
    needle direction, and all N*N directions are covered. The task is to choose the
    64 base positions so that the VOLUME of the union of all tubes is as SMALL as
    possible (a Kakeya/Besicovitch-type set: needles in every direction, tiny measure).

    Because the (i, j) grid is a full product and each square is a product of an
    x-interval (a function of i) and a y-interval (a function of j), placing the base
    x only as a function of i and the base y only as a function of j makes the union a
    product of two 1-D unions. This baseline uses the Keich binary construction
    (the 2-D Kakeya analogue, here for N = 2^k = 8) independently in x and y.

    Returns:
        positions: np.ndarray of shape (64, 2). Row k = tube k in (i, j) raster order
            (i outer, j inner, i.e. numpy meshgrid indexing="ij" then flatten),
            column 0 = base x-coordinate, column 1 = base y-coordinate.
    """
    N = 8
    # Keich binary construction for n = 2^k base positions (one per grid index).
    pos = int(np.log2(N))
    j_terms = np.arange(1, pos + 1)
    keich = np.empty(N, dtype=np.float64)
    for idx in range(N):
        eps = np.array(list(str(bin(idx))[2:]), dtype=int)
        eps = np.pad(eps, (pos - len(eps), 0), "constant")
        keich[idx] = np.sum((1 - j_terms) * eps * (2.0 ** -j_terms) / pos)

    i_grid, j_grid = np.meshgrid(np.arange(N), np.arange(N), indexing="ij")
    i_flat = i_grid.flatten()
    j_flat = j_grid.flatten()

    base_x = keich[i_flat]
    base_y = keich[j_flat]
    positions = np.stack([base_x, base_y], axis=1)
    return positions


# EVOLVE-BLOCK-END
