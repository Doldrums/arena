# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the 3D moving sofa problem: the largest-volume
# rigid shape that can move through a unit-cross-section 3D corridor with two 90-degree
# turns (one in the X-Y plane, one in the Y-Z plane).
#
# ===--------------------------------------------------------------------------------------===#
#
# Some of the code in this file is adapted from:
#
# google-deepmind/alphaevolve_results:
# Licensed under the Apache License v2.0.
#
# ===--------------------------------------------------------------------------------------===#
#
# DEVIATION FROM THE UPSTREAM NOTEBOOK
# ------------------------------------
# The upstream notebook (the_3d_moving_sofa.ipynb) computes the swept volume with JAX on a
# GPU/TPU using a grid spacing of grid_fineness = 0.002, which takes ~4 hours and yields the
# reported volume = 1.81. That is infeasible in a fast pure-numpy offline evaluator.
#
# This evaluator re-implements the SAME algorithm faithfully in pure numpy (corridor test,
# path smoothing, x/y/z/rotation step subdivision, translation survival, exact rotation-arc
# bounding boxes via Rodrigues' formula, and 4x4x4-neighbourhood cube counting), but runs it
# on a COARSER grid (GRID_FINENESS below) so the smoke test finishes in a few seconds. A
# coarser grid systematically UNDER-counts volume (the cube-counting erodes ~3 grid cells from
# every corridor wall), so the computed volume is a conservative lower bound that is smaller
# than the paper's 1.81. BENCHMARK is kept at the paper's reported 1.81, so combined_score is
# (coarse-grid volume) / 1.81 and is < 1.0 even for the optimal construction. Raise
# GRID_FINENESS resolution (smaller value) to approach 1.81 at the cost of runtime.
# ===--------------------------------------------------------------------------------------===#

import time
import numpy as np
import sys
import os
from importlib import __import__

# Reported swept volume of the AlphaEvolve construction at grid_fineness=0.002 (the record /
# benchmark constant taken from the notebook: "verifies the volume = 1.81 result").
BENCHMARK = 1.81

# Corridor / sofa geometry (from the notebook).
CORRIDOR_WIDTH = 1.0
MIDDLE_LENGTH = 4.0
INITIAL_SOFA_LENGTH = 4.0
START_END_DIST = 3.0

# Coarse grid + smoothing tolerances chosen so the pure-numpy sweep runs fast (see deviation
# note above). The notebook uses GRID_FINENESS=0.002, TRANSLATION_TOL=0.05, ROTATION_TOL=1.
GRID_FINENESS = 0.05
TRANSLATION_TOL = 0.05
ROTATION_TOL = 2.0


# ----------------------------------------------------------------------------------------- #
# Corridor membership
# ----------------------------------------------------------------------------------------- #
def are_points_in_corridor(points: np.ndarray) -> np.ndarray:
    """Boolean mask of which (..., 3) points lie inside the corridor."""
    x, y, z = points[..., 0], points[..., 1], points[..., 2]
    w = CORRIDOR_WIDTH
    y_turn = w + MIDDLE_LENGTH

    # X segment (travelling +x, x <= 0).
    mask1 = (x <= 0) & (y >= 0) & (y <= w) & (z >= 0) & (z <= w)
    # Y segment (travelling +y).
    mask2 = (x >= 0) & (x <= w) & (y >= 0) & (y <= y_turn) & (z >= 0) & (z <= w)
    # Z segment (travelling +z).
    mask3 = (x >= 0) & (x <= w) & (y >= y_turn) & (y <= y_turn + w) & (z >= 0)
    return mask1 | mask2 | mask3


# ----------------------------------------------------------------------------------------- #
# Rotations (pure numpy; matches scipy extrinsic 'zyx' degrees used in the notebook)
# ----------------------------------------------------------------------------------------- #
def _euler_zyx_matrix(yaw_deg: float, pitch_deg: float, roll_deg: float) -> np.ndarray:
    """Extrinsic 'zyx' rotation matrix R = Rx(roll) @ Ry(pitch) @ Rz(yaw)."""
    a, b, c = np.deg2rad([yaw_deg, pitch_deg, roll_deg])
    ca, sa = np.cos(a), np.sin(a)
    cb, sb = np.cos(b), np.sin(b)
    cc, sc = np.cos(c), np.sin(c)
    Rz = np.array([[ca, -sa, 0.0], [sa, ca, 0.0], [0.0, 0.0, 1.0]])
    Ry = np.array([[cb, 0.0, sb], [0.0, 1.0, 0.0], [-sb, 0.0, cb]])
    Rx = np.array([[1.0, 0.0, 0.0], [0.0, cc, -sc], [0.0, sc, cc]])
    return Rx @ Ry @ Rz


def _relative_rotvec(start_ypr: np.ndarray, end_ypr: np.ndarray):
    """Axis-angle (rotvec, angle_deg) of the rotation taking start orientation to end."""
    r_start = _euler_zyx_matrix(*start_ypr)
    r_end = _euler_zyx_matrix(*end_ypr)
    r_rel = r_end @ r_start.T
    cos_angle = np.clip((np.trace(r_rel) - 1.0) / 2.0, -1.0, 1.0)
    angle = np.arccos(cos_angle)
    axis = np.array(
        [
            r_rel[2, 1] - r_rel[1, 2],
            r_rel[0, 2] - r_rel[2, 0],
            r_rel[1, 0] - r_rel[0, 1],
        ]
    )
    n = np.linalg.norm(axis)
    if n > 1e-12:
        axis = axis / n
    return axis, np.rad2deg(angle), r_start


# ----------------------------------------------------------------------------------------- #
# Grid + path utilities
# ----------------------------------------------------------------------------------------- #
def _grid_dims_and_coords(grid_fineness: float):
    num_x = int(np.ceil(INITIAL_SOFA_LENGTH / grid_fineness) + 1)
    num_y = int(np.ceil(CORRIDOR_WIDTH / grid_fineness) + 1)
    num_z = int(np.ceil(CORRIDOR_WIDTH / grid_fineness) + 1)
    x_coords = np.linspace(-INITIAL_SOFA_LENGTH, 0, num_x)
    y_coords = np.linspace(0, CORRIDOR_WIDTH, num_y)
    z_coords = np.linspace(0, CORRIDOR_WIDTH, num_z)
    return (num_x, num_y, num_z), (x_coords, y_coords, z_coords)


def _initial_points(grid_fineness: float):
    dims, (xc, yc, zc) = _grid_dims_and_coords(grid_fineness)
    ix, iy, iz = np.meshgrid(
        np.arange(dims[0]), np.arange(dims[1]), np.arange(dims[2]), indexing="ij"
    )
    pts = np.stack([xc[ix.ravel()], yc[iy.ravel()], zc[iz.ravel()]], axis=1)
    return pts, dims, (xc, yc, zc)


def _add_start_and_end_poses(path: np.ndarray) -> np.ndarray:
    start_pose = [-START_END_DIST, 0.0, 0.0, 0.0, 0.0, 0.0]
    end_y = 2 * CORRIDOR_WIDTH + MIDDLE_LENGTH
    end_z = CORRIDOR_WIDTH + START_END_DIST + INITIAL_SOFA_LENGTH
    end_pose = [0.0, end_y, end_z, 90.0, 90.0, 90.0]
    return np.vstack([start_pose, path, end_pose])


def _smooth_path(path: np.ndarray, translation_tol: float, rotation_tol: float) -> np.ndarray:
    out = [path[0].tolist()]
    for i in range(len(path) - 1):
        p1, p2 = path[i], path[i + 1]
        tdiff = np.linalg.norm(p2[:3] - p1[:3])
        rdiff = np.max(np.abs(p2[3:] - p1[3:]))
        n_t = int(np.ceil(tdiff / translation_tol)) if tdiff > translation_tol else 0
        n_r = int(np.ceil(rdiff / rotation_tol)) if rdiff > rotation_tol else 0
        n = max(1, n_t, n_r)
        for j in range(1, n):
            out.append((p1 + (j / n) * (p2 - p1)).tolist())
        out.append(list(p2))
    return np.array(out)


def _subdivide_path(path: np.ndarray) -> np.ndarray:
    """Each step -> x-translation, y-translation, z-translation, rotation substeps."""
    rows = [path[0]]
    for i in range(len(path) - 1):
        p0, p1 = path[i], path[i + 1]
        rows.append(np.hstack([p1[0], p0[1], p0[2], p0[3:]]))          # after x
        rows.append(np.hstack([p1[0], p1[1], p0[2], p0[3:]]))          # after y
        rows.append(np.hstack([p1[0], p1[1], p1[2], p0[3:]]))          # after z
        rows.append(np.hstack([p1[:3], p1[3:]]))                       # after rotation
    return np.array(rows)


# ----------------------------------------------------------------------------------------- #
# Survival
# ----------------------------------------------------------------------------------------- #
def _box_in_corridor(min_xyz: np.ndarray, max_xyz: np.ndarray) -> np.ndarray:
    """For N axis-aligned boxes (min/max shape (N,3)) whether all 8 corners are in-corridor."""
    n = min_xyz.shape[0]
    corners = np.empty((n, 8, 3))
    c = 0
    for ix in (0, 1):
        for iy in (0, 1):
            for iz in (0, 1):
                corners[:, c, 0] = max_xyz[:, 0] if ix else min_xyz[:, 0]
                corners[:, c, 1] = max_xyz[:, 1] if iy else min_xyz[:, 1]
                corners[:, c, 2] = max_xyz[:, 2] if iz else min_xyz[:, 2]
                c += 1
    return are_points_in_corridor(corners).all(axis=1)


def _rotation_step_survival(points_rot_start, translation, axis, angle_deg):
    """Which points' rotation arcs (then translated) stay in-corridor (Rodrigues bounds)."""
    angle_rad = np.deg2rad(angle_deg)
    if angle_rad < 1e-9:
        return are_points_in_corridor(points_rot_start + translation)

    p = points_rot_start                          # (N, 3)
    k = axis                                       # (3,)
    p_dot_k = p @ k                                # (N,)
    A = p - k[None, :] * p_dot_k[:, None]          # (N, 3)
    B = np.cross(np.broadcast_to(k, p.shape), p)   # (N, 3)
    C = k[None, :] * p_dot_k[:, None]              # (N, 3)

    base = np.arctan2(B, A)                         # (N, 3)
    crit1 = np.mod(base, 2 * np.pi)
    crit2 = np.mod(base + np.pi, 2 * np.pi)

    cand = np.stack(
        [np.zeros_like(crit1), np.full_like(crit1, angle_rad), crit1, crit2], axis=-1
    )                                               # (N, 3, 4)
    crit = cand[..., 2:]
    within = (crit > 1e-6) & (crit < angle_rad)
    valid = np.concatenate([np.ones(crit1.shape + (2,), dtype=bool), within], axis=-1)

    coords = A[..., None] * np.cos(cand) + B[..., None] * np.sin(cand) + C[..., None]
    coords = np.where(valid, coords, coords[..., 0:1])
    min_xyz = coords.min(axis=-1)                   # (N, 3)
    max_xyz = coords.max(axis=-1)                   # (N, 3)
    return _box_in_corridor(min_xyz + translation, max_xyz + translation)


def _sweep_survival(points: np.ndarray, subdivided_path: np.ndarray) -> np.ndarray:
    """Single sweep of the whole path that returns the surviving-point mask.

    Mirrors the notebook's translation-step + rotation-arc survival checks, but prunes dead
    points progressively (survival is monotonic under the AND of all checks), so later poses
    only process the points still alive. The rotation-arc bounding box already contains the
    rotation end pose, so that pose's plain corridor membership is implied.
    """
    n = len(points)
    survival = np.zeros(n, dtype=bool)
    alive = np.arange(n)
    pa = points  # coordinates of the still-alive initial-block points

    def keep(mask):
        nonlocal alive, pa
        alive = alive[mask]
        pa = pa[mask]
        return len(alive) > 0

    # Initial pose corridor membership.
    pose0 = subdivided_path[0]
    r0 = _euler_zyx_matrix(pose0[3], pose0[4], pose0[5])
    if not keep(are_points_in_corridor(pa @ r0.T + pose0[:3])):
        return survival

    n_steps = (len(subdivided_path) - 1) // 4
    for i in range(n_steps):
        # x / y / z translation substep endpoints.
        for j in (1, 2, 3):
            pose = subdivided_path[4 * i + j]
            R = _euler_zyx_matrix(pose[3], pose[4], pose[5])
            if not keep(are_points_in_corridor(pa @ R.T + pose[:3])):
                return survival
        # Rotation arc from the z-substep pose to the rotation pose.
        start = subdivided_path[4 * i + 3]
        end = subdivided_path[4 * i + 4]
        axis, angle_deg, r_start = _relative_rotvec(start[3:], end[3:])
        prs = pa @ r_start.T
        if not keep(_rotation_step_survival(prs, start[:3], axis, angle_deg)):
            return survival

    survival[alive] = True
    return survival


def _sofa_volume(mask_grid: np.ndarray, coords) -> float:
    """4x4x4-neighbourhood cube counting (a corridor-safe lower-bound volume)."""
    nx, ny, nz = mask_grid.shape
    if nx < 4 or ny < 4 or nz < 4:
        return 0.0
    cube = np.ones((nx - 3, ny - 3, nz - 3), dtype=bool)
    for i in range(4):
        for j in range(4):
            for k in range(4):
                cube &= mask_grid[i : nx - 3 + i, j : ny - 3 + j, k : nz - 3 + k]
    xc, yc, zc = coords
    cube_vol = (xc[1] - xc[0]) * (yc[1] - yc[0]) * (zc[1] - zc[0])
    return float(cube.sum() * cube_vol)


# ----------------------------------------------------------------------------------------- #
def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        path = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            path = program.moving_sofa_3d_path()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(path, np.ndarray):
            path = np.array(path, dtype=np.float64)
        path = path.astype(np.float64)

        if path.ndim != 2 or path.shape[1] != 6 or path.shape[0] < 1:
            raise ValueError(f"Invalid path shape {path.shape}; expected (num_poses, 6).")
        if not np.all(np.isfinite(path)):
            raise ValueError("Path contains NaN or infinite values.")

        # Build the full motion: fixed start/end, then smooth, then subdivide.
        full_path = _add_start_and_end_poses(path)
        smoothed = _smooth_path(full_path, TRANSLATION_TOL, ROTATION_TOL)
        subdivided = _subdivide_path(smoothed)

        # Sweep the initial block and keep the surviving points.
        points, dims, coords = _initial_points(GRID_FINENESS)
        survival = _sweep_survival(points, subdivided)

        mask_grid = survival.reshape(dims)
        volume = _sofa_volume(mask_grid, coords)

        combined_score = volume / BENCHMARK
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "volume": float(volume),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
