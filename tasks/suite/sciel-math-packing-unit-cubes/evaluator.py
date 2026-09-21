# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the packing-unit-cubes problem: pack 11 unit
# cubes into the smallest axis-aligned bounding cube without overlaps.
#
# ===--------------------------------------------------------------------------------------===#
#
# Some of the code in this file is adapted from:
#
# google-deepmind/alphaevolve_results:
# Licensed under the Apache License v2.0.
#
# ===--------------------------------------------------------------------------------------===#

import time
import numpy as np
import sys
import os
from importlib import __import__
import itertools

# Side length of the smallest bounding cube for the verified baseline 11-cube packing
# taken from the upstream notebook (cell "Data and verification"). This is a record-level
# construction; combined_score ~ 1.0 means matching it, > 1.0 means beating it.
BENCHMARK = 2.894531152
NUM_CUBES = 11
ROW_WIDTH = 6
TOL = 1e-9


def _rotation_matrix_3d(rx_deg, ry_deg, rz_deg):
    """Rotation matrix from Euler angles in degrees, applied in order Z, then Y, then X."""
    rx, ry, rz = np.deg2rad([rx_deg, ry_deg, rz_deg])
    cx, sx = np.cos(rx), np.sin(rx)
    cy, sy = np.cos(ry), np.sin(ry)
    cz, sz = np.cos(rz), np.sin(rz)
    rot_x = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    rot_y = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rot_z = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rot_z @ rot_y @ rot_x


def _cube_vertices(center, rot_mat, side_length=1.0):
    """World coordinates of a unit cube's 8 vertices."""
    h = side_length / 2.0
    local = np.array([
        [-h, -h, -h], [-h, -h, h], [-h, h, -h], [-h, h, h],
        [h, -h, -h], [h, -h, h], [h, h, -h], [h, h, h],
    ])
    return (local @ rot_mat.T) + center


def _cubes_intersect(verts1, verts2, axes1, axes2):
    """Separating Axis Theorem test for two oriented cubes. True if they overlap."""
    axes_to_test = list(axes1) + list(axes2)
    for i in range(3):
        for j in range(3):
            cross = np.cross(axes1[i], axes2[j])
            if np.linalg.norm(cross) > 1e-6:
                axes_to_test.append(cross)

    for axis in axes_to_test:
        p1 = verts1 @ axis
        p2 = verts2 @ axis
        min1, max1 = np.min(p1), np.max(p1)
        min2, max2 = np.min(p2), np.max(p2)
        # A small negative tolerance: touching faces are NOT counted as intersecting.
        if max1 < min2 - TOL or max2 < min1 - TOL:
            return False  # found a separating axis
    return True


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        placements = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            placements = program.packing_unit_cubes11()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(placements, np.ndarray):
            placements = np.array(placements)
        placements = placements.astype(np.float64)

        if placements.shape != (NUM_CUBES, ROW_WIDTH):
            raise ValueError(
                f"Invalid shape: placements = {placements.shape}, expected {(NUM_CUBES, ROW_WIDTH)}"
            )

        if not np.all(np.isfinite(placements)):
            raise ValueError("Placements contain NaN or infinite values.")

        # Build the geometry of every unit cube.
        rot_mats = [_rotation_matrix_3d(p[3], p[4], p[5]) for p in placements]
        all_verts = [_cube_vertices(p[:3], r) for p, r in zip(placements, rot_mats)]
        # Face normals (== columns of the rotation matrix) used as SAT axes.
        all_axes = [np.array([rm[:, 0], rm[:, 1], rm[:, 2]]) for rm in rot_mats]

        # Feasibility: no two unit cubes may overlap.
        for i, j in itertools.combinations(range(NUM_CUBES), 2):
            if _cubes_intersect(all_verts[i], all_verts[j], all_axes[i], all_axes[j]):
                raise ValueError(f"Cubes {i} and {j} overlap; packing is infeasible.")

        # Primary metric: side length of the smallest axis-aligned bounding cube.
        stacked = np.vstack(all_verts)
        span = np.max(stacked, axis=0) - np.min(stacked, axis=0)
        bounding_side = float(np.max(span))

        if bounding_side <= 0 or not np.isfinite(bounding_side):
            raise ValueError("Non-positive or non-finite bounding side length.")

        # Minimization problem -> convert so higher is better (1.0 == matching benchmark).
        combined_score = BENCHMARK / bounding_side
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "bounding_side": bounding_side,
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
