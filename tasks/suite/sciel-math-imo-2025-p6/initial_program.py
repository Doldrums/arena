# EVOLVE-BLOCK-START
import numpy as np


def grid_tiling_imo2025_p6_n36() -> np.ndarray:
    """
    IMO 2025 Problem 6 (grid tiling). On an n x n grid of unit squares, place
    non-overlapping axis-aligned rectangular tiles (sides on grid lines) so that
    every row and every column has exactly one uncovered unit square. Minimize the
    number of tiles. Here n = 36 (optimal tile count is n + 2*sqrt(n) - 3 = 45).

    Baseline construction: leave the main diagonal uncovered (one uncovered cell
    per row and per column), then greedily cover the rest with maximal rectangles
    (extend right, then down). This is a valid but non-optimal tiling, so there is
    plenty of room to improve toward the optimum.

    Returns:
        tiles: np.ndarray of shape (T, 4) with integer rows (r0, c0, r1, c1). Each
            tile covers grid rows r0 <= r < r1 and columns c0 <= c < c1 (top-left
            corner inclusive, bottom-right corner exclusive).
    """
    n = 36
    # Uncovered cell in row r sits at column perm[r]; here the main diagonal.
    perm = np.arange(n)

    covered = np.zeros((n, n), dtype=bool)
    covered[np.arange(n), perm] = True

    tiles = []
    for r in range(n):
        for c in range(n):
            if covered[r, c]:
                continue
            # Extend the tile as far right as possible within this row.
            w = 0
            while c + w < n and not covered[r, c + w]:
                w += 1
            # Extend downward while the full width stays clear.
            h = 1
            while r + h < n and not covered[r + h, c:c + w].any():
                h += 1
            tiles.append((r, c, r + h, c + w))
            covered[r:r + h, c:c + w] = True

    return np.array(tiles, dtype=np.int64)


# EVOLVE-BLOCK-END
