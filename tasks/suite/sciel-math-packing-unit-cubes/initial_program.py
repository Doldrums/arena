# EVOLVE-BLOCK-START
import numpy as np


def packing_unit_cubes11() -> np.ndarray:
    """
    Pack n unit cubes (side length 1) into the smallest possible axis-aligned bounding
    cube, without any two unit cubes overlapping. Each cube is free to translate and
    rotate. Here n = 11.

    Each cube is described by 6 numbers: [cx, cy, cz, rx, ry, rz] where (cx, cy, cz) is
    the center and (rx, ry, rz) are intrinsic Euler rotation angles in DEGREES applied in
    the order Z, then Y, then X (R = Rz @ Ry @ Rx).

    The objective is to minimize the side length of the smallest axis-aligned cube that
    contains all 11 unit cubes. Smaller is better.

    Returns:
        placements: np.ndarray of shape (11, 6), one row [cx, cy, cz, rx, ry, rz] per
            unit cube, giving a non-overlapping packing.
    """
    # Verified non-overlapping 11-cube packing (bounding-cube side ~= 2.8945).
    placements = np.array([
        [-8.77779155e-01, -8.77126384e-01, -1.01671182e+00, 0.0, 0.0, 0.0],
        [-8.77779155e-01, -8.77126384e-01, 8.77819332e-01, 0.0, 0.0, 0.0],
        [-8.77779155e-01, 1.01740471e+00, -1.01671182e+00, 0.0, 0.0, 0.0],
        [-8.77779155e-01, 1.01740471e+00, 8.77819332e-01, 0.0, 0.0, 0.0],
        [1.01675167e+00, -8.77126384e-01, -1.01671182e+00, 0.0, 0.0, 0.0],
        [1.01675167e+00, -8.77126384e-01, 8.77819332e-01, 0.0, 0.0, 0.0],
        [1.01675167e+00, 1.01740471e+00, -1.01671182e+00, 0.0, 0.0, 0.0],
        [1.01675167e+00, 1.01740471e+00, 8.77819332e-01, 0.0, 0.0, 0.0],
        [2.01013926e-01, 1.15252160e-01, 8.77806873e-01, 6.76458206e+00, 8.99998576e+01, 1.60681931e+02],
        [1.13368230e-01, -8.77124005e-01, -2.08800374e-01, 2.07520455e+02, 3.59999904e+02, 9.00002316e+01],
        [-8.77752030e-01, 2.04448607e-01, -1.14126641e-01, 1.80000883e+02, 2.65856303e+01, 2.70001203e+02],
    ], dtype=np.float64)
    return placements


# EVOLVE-BLOCK-END
