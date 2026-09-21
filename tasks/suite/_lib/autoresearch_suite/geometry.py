"""Geometric construction problems from the AlphaEvolve paper (Appendix B).

Independent implementations of the published verification rules, cross-checked
against the constructions in google-deepmind/alphaevolve_results
(``mathematical_results.ipynb``): every function below reproduces the printed
value of the official notebook on the official data (see
``validation/suite-crosscheck.json``). Checks are strict: no tolerance is added
to disjointness or containment beyond what the notebook itself uses.
"""
from __future__ import annotations

import itertools
import math

import numpy as np

from .runtime import CandidateError, require


def _array(value, shape_hint, dtype=float):
    try:
        arr = np.asarray(value, dtype=dtype)
    except (TypeError, ValueError) as error:
        raise CandidateError(f"expected a numeric array {shape_hint}: {error}") from None
    require(np.all(np.isfinite(arr)), "construction contains NaN or infinite values")
    return arr


# --- circle packing -------------------------------------------------------

def circles_disjoint(circles):
    for (x1, y1, r1), (x2, y2, r2) in itertools.combinations(circles, 2):
        if math.hypot(x1 - x2, y1 - y2) < r1 + r2:
            raise CandidateError(f"circles overlap: ({x1:.6f},{y1:.6f},r={r1:.6f}) and ({x2:.6f},{y2:.6f},r={r2:.6f})")


def circle_packing_unit_square(circles, n):
    """Sum of radii of ``n`` disjoint circles inside [0,1]^2 (AlphaEvolve B.12)."""
    arr = _array(circles, f"of shape ({n}, 3)")
    require(arr.shape == (n, 3), f"expected {n} circles as rows (x, y, r); got shape {arr.shape}")
    require(np.all(arr[:, 2] >= 0), "radii must be nonnegative")
    for x, y, r in arr:
        if min(x, y) - r < 0 or max(x, y) + r > 1:
            raise CandidateError(f"circle ({x:.6f},{y:.6f},r={r:.6f}) is not inside the unit square")
    circles_disjoint(arr.tolist())
    return float(np.sum(arr[:, 2]))


def circle_packing_rectangle(circles, n, perimeter=4.0):
    """Sum of radii of ``n`` disjoint circles whose bounding rectangle has perimeter <= 4 (B.13)."""
    arr = _array(circles, f"of shape ({n}, 3)")
    require(arr.shape == (n, 3), f"expected {n} circles as rows (x, y, r); got shape {arr.shape}")
    require(np.all(arr[:, 2] >= 0), "radii must be nonnegative")
    circles_disjoint(arr.tolist())
    width = float(np.max(arr[:, 0] + arr[:, 2]) - np.min(arr[:, 0] - arr[:, 2]))
    height = float(np.max(arr[:, 1] + arr[:, 2]) - np.min(arr[:, 1] - arr[:, 2]))
    require(2 * (width + height) <= perimeter, f"the circles need a rectangle of perimeter {2 * (width + height):.6f} > {perimeter}")
    return float(np.sum(arr[:, 2]))


# --- Heilbronn -----------------------------------------------------------

def triangle_area(a, b, c):
    return abs(a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1])) / 2


def min_triangle_area(points):
    return min(triangle_area(p, q, r) for p, q, r in itertools.combinations(points, 3))


TRIANGLE = (np.array([0.0, 0.0]), np.array([1.0, 0.0]), np.array([0.5, math.sqrt(3) / 2]))


def heilbronn_triangle(points, n):
    """Minimum triangle area of ``n`` points in the unit-area equilateral triangle (B.9).

    Points must lie on or inside the triangle (0,0), (1,0), (1/2, sqrt(3)/2); the
    minimum area over all triples is normalized by the triangle's area, as in the
    notebook.
    """
    pts = _array(points, f"of shape ({n}, 2)")
    require(pts.shape == (n, 2), f"expected {n} points in the plane; got shape {pts.shape}")
    for x, y in pts:
        if not (y >= 0 and math.sqrt(3) * x <= math.sqrt(3) - y and y <= math.sqrt(3) * x):
            raise CandidateError(f"point ({x:.6f},{y:.6f}) is outside the equilateral triangle")
    area = min_triangle_area(pts.tolist())
    return float(area / triangle_area(*TRIANGLE))


def heilbronn_convex(points, n):
    """Minimum triangle area of ``n`` points normalized by their convex hull area (B.10)."""
    from scipy.spatial import ConvexHull
    pts = _array(points, f"of shape ({n}, 2)")
    require(pts.shape == (n, 2), f"expected {n} points in the plane; got shape {pts.shape}")
    try:
        hull_area = ConvexHull(pts).volume
    except Exception as error:  # noqa: BLE001 - degenerate (collinear) input
        raise CandidateError(f"points do not span a convex region: {error}") from None
    require(hull_area > 0, "points are collinear")
    return float(min_triangle_area(pts.tolist()) / hull_area)


# --- max/min distance ratio ------------------------------------------------

def max_min_distance_ratio_squared(points, n, d):
    """Squared ratio of maximum to minimum pairwise distance of ``n`` points in R^d (B.8)."""
    from scipy.spatial.distance import pdist
    pts = _array(points, f"of shape ({n}, {d})")
    require(pts.shape == (n, d), f"expected {n} points in {d} dimensions; got shape {pts.shape}")
    dists = pdist(pts)
    require(float(np.min(dists)) > 0, "points must be distinct")
    return float((np.max(dists) / np.min(dists)) ** 2)


# --- kissing number --------------------------------------------------------

def kissing_configuration_size(vectors, d):
    """Number of integer vectors in Z^d whose min pairwise distance >= max norm (B.11).

    Exact integer arithmetic, as in the notebook: vectors are rounded to
    integers, none may be zero, and the minimum squared pairwise distance must
    be at least the maximum squared norm.
    """
    arr = np.asarray(vectors)
    require(arr.ndim == 2 and arr.shape[1] == d, f"expected an array of shape (k, {d})")
    ints = [[int(round(float(v))) for v in row] for row in arr]
    norms = [sum(x * x for x in row) for row in ints]
    require(min(norms) > 0, "the configuration contains the zero vector")
    max_norm = max(norms)
    for a, b in itertools.combinations(ints, 2):
        if sum((x - y) ** 2 for x, y in zip(a, b)) < max_norm:
            raise CandidateError("two vectors are closer than the maximum norm (spheres overlap)")
    return len(ints)


# --- hexagon packing -------------------------------------------------------

def hexagon_vertices(cx, cy, side, angle_degrees):
    angle = math.radians(angle_degrees)
    return [(cx + side * math.cos(angle + k * math.pi / 3), cy + side * math.sin(angle + k * math.pi / 3)) for k in range(6)]


def _project(polygon, axis):
    values = [p[0] * axis[0] + p[1] * axis[1] for p in polygon]
    return min(values), max(values)


def polygons_intersect(a, b):
    """Separating-axis test for convex polygons; touching edges count as disjoint."""
    for polygon in (a, b):
        for i in range(len(polygon)):
            x1, y1 = polygon[i]
            x2, y2 = polygon[(i + 1) % len(polygon)]
            edge = (x2 - x1, y2 - y1)
            length = math.hypot(*edge)
            if length == 0:
                continue
            axis = (-edge[1] / length, edge[0] / length)
            min_a, max_a = _project(a, axis)
            min_b, max_b = _project(b, axis)
            if max_a <= min_b or max_b <= min_a:
                return False
    return True


def point_inside_polygon(point, polygon):
    """Convex polygon containment (boundary counts as inside)."""
    sign = 0
    for i in range(len(polygon)):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % len(polygon)]
        cross = (x2 - x1) * (point[1] - y1) - (y2 - y1) * (point[0] - x1)
        if abs(cross) < 1e-12:
            continue
        current = 1 if cross > 0 else -1
        if sign == 0:
            sign = current
        elif current != sign:
            return False
    return True


def hexagon_packing_outer_side(inner, outer_center, outer_side, outer_angle, n):
    """Outer hexagon side length containing ``n`` disjoint unit hexagons (B.7).

    ``inner`` rows are (x, y, angle_degrees) of unit-side hexagons; the outer
    hexagon is given by center, side length and rotation. Returns the outer side
    length (lower is better) after checking pairwise disjointness and
    containment of every inner vertex.
    """
    arr = _array(inner, f"of shape ({n}, 3)")
    require(arr.shape == (n, 3), f"expected {n} inner hexagons as rows (x, y, angle); got shape {arr.shape}")
    outer_side = float(outer_side)
    require(math.isfinite(outer_side) and outer_side > 0, "outer side length must be positive")
    outer = hexagon_vertices(float(outer_center[0]), float(outer_center[1]), outer_side, float(outer_angle))
    polys = [hexagon_vertices(x, y, 1.0, angle) for x, y, angle in arr]
    for i, j in itertools.combinations(range(n), 2):
        if polygons_intersect(polys[i], polys[j]):
            raise CandidateError(f"inner hexagons {i} and {j} overlap")
    for i, poly in enumerate(polys):
        for vertex in poly:
            if not point_inside_polygon(vertex, outer):
                raise CandidateError(f"inner hexagon {i} is not contained in the outer hexagon")
    return outer_side
