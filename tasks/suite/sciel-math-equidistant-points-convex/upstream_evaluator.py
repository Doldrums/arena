# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the "equidistant points in convex polygons" problem:
# build a convex polygon with NUM_VERTEX vertices where every vertex has (at least) 4 other
# vertices approximately equidistant from it.
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
import math
import numpy as np
import sys
import os
from importlib import __import__

# AlphaEvolve record (best minimum-vertex score found) for NUM_VERTEX = 20.
# Source: upstream notebook cell, variable best_score_found_20 = 0.9994822977347143.
BENCHMARK = 0.9994822977347143
NUM_VERTEX = 20


def is_convex_polygon(polygon):
    """Return True if the polygon (sequence of 2D tuples) is strictly convex.

    Checks: enough points, no duplicates, non-zero sides, interior angles strictly
    between 0 and pi, and the polygon does not intersect itself.
    """
    try:
        if len(polygon) < 3:
            return False
        if len(set(polygon)) != len(polygon):
            return False

        old_x, old_y = polygon[-2]
        new_x, new_y = polygon[-1]
        new_direction = math.atan2(new_y - old_y, new_x - old_x)
        angle_sum = 0.0
        orientation = 0.0

        for ndx, newpoint in enumerate(polygon):
            old_x, old_y, old_direction = new_x, new_y, new_direction
            new_x, new_y = newpoint
            new_direction = math.atan2(new_y - old_y, new_x - old_x)

            if old_x == new_x and old_y == new_y:
                return False

            angle = new_direction - old_direction
            if angle <= -math.pi:
                angle += 2 * math.pi
            elif angle > math.pi:
                angle -= 2 * math.pi

            if angle == 0.0:
                return False

            if ndx == 0:
                orientation = 1.0 if angle > 0.0 else -1.0
            elif orientation * angle <= 0.0:
                return False

            angle_sum += angle

        return abs(round(angle_sum / (2 * math.pi))) == 1
    except (ArithmeticError, TypeError, ValueError, IndexError):
        return False


def calculate_single_vertex_score(vertex_index, polygon_points):
    """Per-vertex equidistance score in [0, 1] (1.0 = four neighbors perfectly equidistant)."""
    num_vertex = len(polygon_points)
    if num_vertex < 5:
        return 0.0

    v = np.array(polygon_points[vertex_index])
    distances = []
    for i, p_tuple in enumerate(polygon_points):
        if i == vertex_index:
            continue
        p = np.array(p_tuple)
        dist = np.linalg.norm(v - p)
        if dist < 5e-2:
            return 0.0
        distances.append(dist)

    if len(distances) != num_vertex - 1:
        return -1.0

    distances.sort()
    n_dist = len(distances)

    min_gap = float("inf")
    min_gap_idx = -1
    for k in range(n_dist - 1):
        gap = distances[k + 1] - distances[k]
        if gap < min_gap:
            min_gap = gap
            min_gap_idx = k

    if min_gap_idx == -1:
        return 0.0

    d_k = distances[min_gap_idx]
    d_k_plus_1 = distances[min_gap_idx + 1]
    D_v = (d_k + d_k_plus_1) / 2.0

    if D_v < 1e-1:
        return 0.0

    k = min_gap_idx
    if k == 0:
        indices = [0, 1, 2, 3]
    elif k == n_dist - 2:
        indices = [n_dist - 4, n_dist - 3, n_dist - 2, n_dist - 1]
    else:
        indices = [k - 1, k, k + 1, k + 2]

    valid_indices = [idx for idx in indices if 0 <= idx < n_dist]
    if len(valid_indices) < 4:
        center_idx = k
        num_needed = 4
        idx_range_start = max(0, center_idx - (num_needed // 2) + 1)
        idx_range_end = min(n_dist, idx_range_start + num_needed)
        idx_range_start = max(0, idx_range_end - num_needed)
        selected_indices = list(range(idx_range_start, idx_range_end))
        if len(selected_indices) < 4:
            return 0.0
    else:
        selected_indices = valid_indices

    try:
        dist_k_minus_1 = distances[selected_indices[0]]
        dist_k = distances[selected_indices[1]]
        dist_k_plus_1 = distances[selected_indices[2]]
        dist_k_plus_2 = distances[selected_indices[3]]
    except IndexError:
        return 0.0

    if dist_k_minus_1 < 1e-2 or dist_k < 1e-2:
        return 0.0

    term1 = max(D_v / dist_k_minus_1, dist_k_minus_1 / D_v)
    term2 = max(D_v / dist_k, dist_k / D_v)
    term3 = max(dist_k_plus_1 / D_v, D_v / dist_k_plus_1)
    term4 = max(dist_k_plus_2 / D_v, D_v / dist_k_plus_2)
    raw_score_v = (term1 + term2 + term3 + term4) / 4.0

    if raw_score_v < 1e-2:
        return 0.0

    final_score_v = 1.0 / raw_score_v
    return max(0.0, min(1.0, final_score_v))


def calculate_polygon_score(polygon_points, num_vertex):
    """Overall score = minimum per-vertex score, after centering and scale-normalizing.

    Returns a large negative penalty for malformed / non-convex polygons.
    """
    if not isinstance(polygon_points, list):
        return -1_000_000.0
    if len(polygon_points) != num_vertex:
        return -1_000_000.0

    current_polygon_points = [list(p) for p in polygon_points]
    for p in current_polygon_points:
        if not isinstance(p, list) or len(p) != 2:
            return -1_000_000.0
        if not all(isinstance(coord, (int, float)) for coord in p):
            return -1_000_000.0
        p_np = np.array(p, dtype=float)
        if np.isnan(p_np[0]) or np.isnan(p_np[1]) or np.isinf(p_np[0]) or np.isinf(p_np[1]):
            return -1_000_000.0

    try:
        coords = np.array(current_polygon_points, dtype=float)
        if coords.shape != (num_vertex, 2):
            return -1_000_000.0
    except ValueError:
        return -1_000_000.0

    centroid = np.mean(coords, axis=0)
    coords_centered = coords - centroid
    distances_from_origin = np.linalg.norm(coords_centered, axis=1)
    average_distance = np.mean(distances_from_origin)

    if average_distance > 1e-2:
        coords_scaled = coords_centered / average_distance
        scaled_polygon_points_tuples = [tuple(row) for row in coords_scaled]
    else:
        return 0.0

    if not is_convex_polygon(scaled_polygon_points_tuples):
        return -1_000_000.0

    if num_vertex < 5:
        return 0.0

    vertex_scores = []
    for i in range(num_vertex):
        score_v = calculate_single_vertex_score(i, scaled_polygon_points_tuples)
        if score_v < 0:
            return -500_000.0
        vertex_scores.append(score_v)

    if not vertex_scores:
        return -400_000.0
    return min(vertex_scores)


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        polygon = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            polygon = program.equidistant_points_polygon20()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(polygon, np.ndarray):
            polygon = np.array(polygon)

        if polygon.shape != (NUM_VERTEX, 2):
            raise ValueError(
                f"Invalid shape: polygon = {polygon.shape}, expected {(NUM_VERTEX, 2)}"
            )

        if not np.all(np.isfinite(polygon)):
            raise ValueError("Polygon contains NaN or infinite values.")

        # Feasibility (convexity + equidistance scoring) is handled by calculate_polygon_score,
        # which returns a negative penalty for any infeasible / non-convex configuration.
        polygon_list = [tuple(float(c) for c in row) for row in polygon]
        polygon_score = calculate_polygon_score(polygon_list, NUM_VERTEX)

        # Never reward an infeasible polygon: clamp penalties to a zero combined_score.
        if not np.isfinite(polygon_score) or polygon_score <= 0.0:
            combined_score = 0.0
            polygon_score = max(0.0, float(polygon_score)) if np.isfinite(polygon_score) else 0.0
        else:
            combined_score = polygon_score / BENCHMARK

        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "polygon_score": float(polygon_score),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
