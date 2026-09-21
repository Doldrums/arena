"""Christmas-tree packing: the Kaggle "Santa 2025" competition metric, reimplemented.

The competition (https://www.kaggle.com/competitions/santa-2025) asks for 200
configurations: for every n from 1 to 200, place n copies of a fixed tree
polygon in the plane so that the axis-aligned bounding *square* of their union
is as small as possible. The public metric (competition metric notebook,
shapely 2.1.2) defines

* the tree: a 15-vertex polygon with a 0.15 x 0.2 trunk below y = 0, tiers of
  width 0.7, 0.4 and 0.25 at y = 0, 0.25 and 0.5, and the tip at y = 0.8; a
  placed tree is that polygon rotated by ``deg`` degrees about the origin
  (counter-clockwise) and translated to (x, y);
* the constraints: x and y within [-100, 100]; trees of one configuration may
  touch but must not overlap (shapely ``intersects`` and not ``touches``);
* the score of an n-tree configuration: the larger side of the bounding
  rectangle of the union, squared, divided by n; the total score is the sum
  over the 200 configurations. Lower is better.

Coordinates are multiplied by 1e18 before they reach shapely, exactly as in
the official code, so the overlap decision and the bounding box agree with the
competition's evaluation. Cross-checks (see ``validation/santa-2025-crosscheck.json``):
the doctest example of the official metric scores 0.877038143325303 here and
there, and the getting-started sample submission scores 176.60550959158516
with both implementations.
"""
from __future__ import annotations

from decimal import Decimal, getcontext

import numpy as np

from .runtime import CandidateError, require

getcontext().prec = 25
SCALE = Decimal("1e18")
LIMIT = 100.0

_TRUNK_W, _TRUNK_H = Decimal("0.15"), Decimal("0.2")
_BASE_W, _MID_W, _TOP_W = Decimal("0.7"), Decimal("0.4"), Decimal("0.25")
_TIP_Y, _TIER_1_Y, _TIER_2_Y, _BASE_Y = Decimal("0.8"), Decimal("0.5"), Decimal("0.25"), Decimal("0.0")
_TWO, _FOUR = Decimal("2"), Decimal("4")
TREE_VERTICES = [
    (Decimal("0.0"), _TIP_Y),
    (_TOP_W / _TWO, _TIER_1_Y), (_TOP_W / _FOUR, _TIER_1_Y),
    (_MID_W / _TWO, _TIER_2_Y), (_MID_W / _FOUR, _TIER_2_Y),
    (_BASE_W / _TWO, _BASE_Y),
    (_TRUNK_W / _TWO, _BASE_Y), (_TRUNK_W / _TWO, -_TRUNK_H),
    (-(_TRUNK_W / _TWO), -_TRUNK_H), (-(_TRUNK_W / _TWO), _BASE_Y),
    (-(_BASE_W / _TWO), _BASE_Y),
    (-(_MID_W / _FOUR), _TIER_2_Y), (-(_MID_W / _TWO), _TIER_2_Y),
    (-(_TOP_W / _FOUR), _TIER_1_Y), (-(_TOP_W / _TWO), _TIER_1_Y),
]
TREE_AREA = 0.245625  # shoelace area of the polygon above (trunk 0.03 + tiers 0.215625)


def _shapely():
    try:
        from shapely import affinity
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        from shapely.strtree import STRtree
    except ImportError as error:  # pragma: no cover - reported as a requirement by the harness
        raise RuntimeError("the tree-packing evaluator needs the shapely package (pip install shapely)") from error
    return affinity, Polygon, unary_union, STRtree


def tree_polygon(x, y, deg):
    """The placed tree in scaled coordinates, built exactly like the official ``ChristmasTree``."""
    affinity, Polygon, _, _ = _shapely()
    base = Polygon([(px * SCALE, py * SCALE) for px, py in TREE_VERTICES])
    rotated = affinity.rotate(base, float(Decimal(deg)), origin=(0, 0))
    return affinity.translate(rotated, xoff=float(Decimal(x) * SCALE), yoff=float(Decimal(y) * SCALE))


def _placements(value, n):
    try:
        arr = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as error:
        raise CandidateError(f"configuration {n}: expected rows (x, y, deg): {error}") from None
    require(arr.shape == (n, 3), f"configuration {n}: expected {n} rows (x, y, deg); got shape {arr.shape}")
    require(np.all(np.isfinite(arr)), f"configuration {n}: NaN or infinite placement")
    require(np.all(np.abs(arr[:, :2]) <= LIMIT), f"configuration {n}: x and y must lie within [-{LIMIT:g}, {LIMIT:g}]")
    return arr


def configuration_score(placements, n):
    """(bounding square area / n, side length) for one configuration; raises CandidateError on overlap."""
    _, _, unary_union, STRtree = _shapely()
    arr = _placements(placements, n)
    polygons = [tree_polygon(repr(float(x)), repr(float(y)), repr(float(deg))) for x, y, deg in arr]
    tree = STRtree(polygons)
    for i, poly in enumerate(polygons):
        for j in tree.query(poly):
            if j != i and poly.intersects(polygons[j]) and not poly.touches(polygons[j]):
                raise CandidateError(f"configuration {n}: trees {i} and {j} overlap")
    bounds = unary_union(polygons).bounds
    side_scaled = max(bounds[2] - bounds[0], bounds[3] - bounds[1])
    score = (Decimal(side_scaled) ** 2) / (SCALE ** 2) / Decimal(n)
    return score, float(Decimal(side_scaled) / SCALE)


def tree_packing_score(construct, sizes):
    """Sum over ``sizes`` of the normalized bounding-square area of ``construct(n)``.

    Returns ``(total, details)``; ``details`` reports the number of configurations,
    the mean packing density (n * tree area / square area) and the worst n.
    """
    total = Decimal("0")
    densities = []
    worst = (None, -1.0)
    for n in sizes:
        try:
            placements = construct(n)
        except CandidateError:
            raise
        except Exception as error:  # noqa: BLE001 - candidate failure is an invalid candidate
            raise CandidateError(f"construct({n}) raised {type(error).__name__}: {error}") from None
        score, side = configuration_score(placements, n)
        value = float(score)
        densities.append(n * TREE_AREA / (side * side))
        if value > worst[1]:
            worst = (n, value)
        total += score
    require(densities, "no configuration was evaluated")
    details = {"configurations": len(densities), "mean_density": round(float(np.mean(densities)), 6),
               "worst_n": worst[0], "worst_contribution": round(worst[1], 6)}
    return float(total), details


def score_submission(rows):
    """Score a competition-format submission: iterable of (id, x, y, deg) with ``id`` = ``<n>_<k>``.

    Values may carry the competition's leading ``s``. Mirrors the official metric so
    that published submissions can be checked (used by the tests).
    """
    groups = {}
    for row_id, x, y, deg in rows:
        groups.setdefault(str(row_id).split("_")[0], []).append([float(str(v).lstrip("s")) for v in (x, y, deg)])
    total = Decimal("0")
    for _, placements in sorted(groups.items()):
        score, _ = configuration_score(placements, len(placements))
        total += score
    return float(total)
