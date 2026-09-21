# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the Fejes-Toth problem on the unit sphere, with
# 6 points (maximize the volume of the inscribed polyhedron / convex hull).
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
# DEVIATION NOTE: the upstream notebook scores constructions with
# scipy.spatial.ConvexHull. To honor the pure-numpy + stdlib constraint of this repo, the
# convex-hull volume here is computed with a self-contained incremental 3D convex-hull
# implementation. For points in convex position on the unit sphere this yields the same
# polyhedron volume; pathological coplanar/degenerate inputs simply score low (>= 0).

import time
import numpy as np
import sys
import os
from importlib import __import__

# Known optimal for n = 6: the regular octahedron inscribed in the unit sphere, whose
# volume is exactly 4/3 (see upstream notebook, "Evolved Code" + "Data Verification" cells).
BENCHMARK = 4.0 / 3.0
TOL = 1e-6
NUM_POINTS = 6


def _convex_hull_volume(pts):
    """Volume of the convex hull of `pts` (shape (n,3)) via incremental 3D convex hull.

    Returns 0.0 for degenerate (coplanar / collinear) inputs.
    """
    pts = np.asarray(pts, dtype=np.float64)
    n = pts.shape[0]
    if n < 4:
        return 0.0

    eps = 1e-12

    # --- find an initial non-degenerate tetrahedron ---------------------------------------
    i0 = 0
    # i1: farthest from i0
    d = np.linalg.norm(pts - pts[i0], axis=1)
    i1 = int(np.argmax(d))
    if d[i1] < eps:
        return 0.0
    # i2: farthest from the line i0-i1
    line = pts[i1] - pts[i0]
    line = line / np.linalg.norm(line)
    proj = pts[i0] + np.outer((pts - pts[i0]) @ line, line)
    d = np.linalg.norm(pts - proj, axis=1)
    i2 = int(np.argmax(d))
    if d[i2] < eps:
        return 0.0
    # i3: farthest from the plane i0-i1-i2
    normal = np.cross(pts[i1] - pts[i0], pts[i2] - pts[i0])
    nn = np.linalg.norm(normal)
    if nn < eps:
        return 0.0
    normal = normal / nn
    d = np.abs((pts - pts[i0]) @ normal)
    i3 = int(np.argmax(d))
    if d[i3] < eps:
        return 0.0

    init = [i0, i1, i2, i3]
    r = pts[init].mean(axis=0)  # interior reference point (stays inside the growing hull)

    faces = []  # list of [i,j,k] with outward-pointing normals (relative to r)

    def _add_face(a, b, c):
        norm = np.cross(pts[b] - pts[a], pts[c] - pts[a])
        if np.dot(norm, pts[a] - r) < 0.0:
            b, c = c, b
        faces.append([a, b, c])

    _add_face(i0, i1, i2)
    _add_face(i0, i1, i3)
    _add_face(i0, i2, i3)
    _add_face(i1, i2, i3)

    for idx in range(n):
        if idx in init:
            continue
        p = pts[idx]
        visible = []
        for f in faces:
            a, b, c = f
            norm = np.cross(pts[b] - pts[a], pts[c] - pts[a])
            if np.dot(norm, p - pts[a]) > eps:
                visible.append(f)
        if not visible:
            continue
        # directed edges of all visible faces
        vis_edges = set()
        for f in visible:
            a, b, c = f
            vis_edges.add((a, b))
            vis_edges.add((b, c))
            vis_edges.add((c, a))
        # horizon edges: directed edges whose reverse is not also visible
        horizon = []
        for (a, b) in vis_edges:
            if (b, a) not in vis_edges:
                horizon.append((a, b))
        # drop visible faces, then cone the new point to the horizon
        faces = [f for f in faces if f not in visible]
        for (a, b) in horizon:
            _add_face(a, b, idx)

    # volume = sum of |tetra(r, face)| over the boundary triangulation
    vol = 0.0
    for f in faces:
        a, b, c = f
        vol += abs(np.dot(np.cross(pts[b] - pts[a], pts[c] - pts[a]), pts[a] - r)) / 6.0
    return float(vol)


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        points = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            points = program.fejes_toth6()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(points, np.ndarray):
            points = np.array(points)

        if points.shape != (NUM_POINTS, 3):
            raise ValueError(f"Invalid shapes: points = {points.shape}, expected {(NUM_POINTS,3)}")

        if not np.all(np.isfinite(points)):
            raise ValueError("Points contain NaN or infinite values.")

        norms = np.linalg.norm(points, axis=1)
        if np.any(norms < TOL):
            raise ValueError("Encountered a zero-norm row; cannot project onto the unit sphere.")
        points = points / norms[:, None]

        volume = _convex_hull_volume(points)
        if not np.isfinite(volume) or volume <= 0.0:
            raise ValueError("Degenerate configuration: convex hull has non-positive volume.")

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
