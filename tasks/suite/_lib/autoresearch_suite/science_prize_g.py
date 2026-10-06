"""Independent verifiers for discrete-geometry and analysis constructions.

Combinatorial geometry scores use exact integer or rational arithmetic. The
analytic tasks (products of distances, cosine sums, polynomial norms) use
floating point with the tolerances stated in each contract. Reference values
and sources are in catalog/science/prize_g.json.
"""
from collections import Counter
from fractions import Fraction
from itertools import combinations
from math import cos, gcd, isqrt, log, pi, sin, sqrt

from .runtime import require
from .science_prize import integer, sequence


def _report(**extra):
    return {"lean_verified": False, **extra}


def integer_points(value, n_min, n_max, bound):
    rows = sequence(value, "points", n_min, n_max)
    pts = []
    for row in rows:
        x, y = sequence(row, "point", 2, 2)
        integer(x, "coordinate", -bound, bound)
        integer(y, "coordinate", -bound, bound)
        pts.append((x, y))
    require(len(set(pts)) == len(pts), "points must be distinct")
    return pts


def _cross(o, a, b):
    return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])


def _no_three_collinear(pts):
    return all(_cross(a, b, c) != 0 for a, b, c in combinations(pts, 3))


def _lines(pts):
    """Map each line (as a frozenset of indices) determined by at least two points."""
    lines = set()
    n = len(pts)
    for i in range(n):
        for j in range(i+1, n):
            members = frozenset(k for k in range(n) if _cross(pts[i], pts[j], pts[k]) == 0)
            lines.add(members)
    return lines


# --- integral point sets ------------------------------------------------------

def _rational(pair, name, bound):
    num, den = sequence(pair, name, 2, 2)
    integer(num, name+" numerator", -bound, bound)
    integer(den, name+" denominator", 1, bound)
    return Fraction(num, den)


def _square_rational(q):
    return q >= 0 and isqrt(q.numerator)**2 == q.numerator and isqrt(q.denominator)**2 == q.denominator


def integral_point_set(value, max_points=12, bound=10**40):
    """Points (x, y*sqrt(D)) with rational x, y: rational pairwise distances, general position."""
    require(type(value) is dict and set(value) == {"D", "points"}, "return keys D and points only")
    d = integer(value["D"], "D", 1, 10**12)
    require(all(d % (p*p) for p in range(2, isqrt(d)+1)), "D must be squarefree")
    rows = sequence(value["points"], "points", 3, max_points)
    pts = [(_rational(r[0], "x", bound), _rational(r[1], "y", bound)) for r in (sequence(r, "point", 2, 2) for r in rows)]
    require(len(set(pts)) == len(pts), "points must be distinct")
    for (x1, y1), (x2, y2) in combinations(pts, 2):
        require(_square_rational((x1-x2)**2 + d*(y1-y2)**2), "some distance is irrational")
    for a, b, c in combinations(pts, 3):
        # collinearity in (x, y*sqrt(D)) coordinates only rescales the determinant by sqrt(D)
        require((b[0]-a[0])*(c[1]-a[1]) != (c[0]-a[0])*(b[1]-a[1]), "three points are collinear")
    for quad in combinations(pts, 4):
        rows4 = [(x*x + d*y*y, x, y) for x, y in quad]
        base = rows4[0]
        m = [[r[k]-base[k] for k in range(3)] for r in rows4[1:]]
        det = (m[0][0]*(m[1][1]*m[2][2]-m[1][2]*m[2][1]) - m[0][1]*(m[1][0]*m[2][2]-m[1][2]*m[2][0])
               + m[0][2]*(m[1][0]*m[2][1]-m[1][1]*m[2][0]))
        require(det != 0, "four points are concyclic")
    return len(pts), _report(points=len(pts), characteristic=d)


# --- empty convex polygons ---------------------------------------------------

def _inside(p, a, b, c):
    s1, s2, s3 = _cross(a, b, p), _cross(b, c, p), _cross(c, a, p)
    return (s1 > 0 and s2 > 0 and s3 > 0) or (s1 < 0 and s2 < 0 and s3 < 0)


def has_empty_convex(pts, k):
    """Exact search for an empty convex k-gon, anchored at its lowest vertex."""
    n = len(pts)
    for p in pts:
        above = [q for q in pts if (q[1], q[0]) > (p[1], p[0])]
        above.sort(key=lambda q: (Fraction(-(q[0]-p[0]), q[1]-p[1]) if q[1] != p[1] else Fraction(-10**18)))
        m = len(above)
        empty = [[False]*m for _ in range(m)]
        for i in range(m):
            for j in range(i+1, m):
                empty[i][j] = not any(_inside(r, p, above[i], above[j]) for r in pts if r not in (p, above[i], above[j]))
        # best[j][i] = longest convex chain p, ..., above[i], above[j] with empty fan triangles
        best = [[0]*m for _ in range(m)]
        for j in range(m):
            for i in range(j):
                if not empty[i][j]:
                    continue
                length = 3
                for h in range(i):
                    if best[i][h] and _cross(above[h], above[i], above[j]) > 0:
                        length = max(length, best[i][h]+1)
                best[j][i] = length
                if length >= k and _cross(above[i], above[j], p) > 0:
                    return True
    return False


def empty_hexagon_free(value, max_points=30, bound=10**6):
    pts = integer_points(value, 1, max_points, bound)
    require(_no_three_collinear(pts), "three points are collinear")
    require(not has_empty_convex(pts, 6), "the set contains an empty convex hexagon")
    return len(pts), _report(points=len(pts))


# --- lines -------------------------------------------------------------------

def orchard_lines(value, n=12, points_per_line=3, bound=10**12):
    pts = integer_points(value, n, n, bound)
    count = sum(len(line) == points_per_line for line in _lines(pts))
    return count, _report(points=n, lines_with_exactly=points_per_line, count=count)


def ordinary_lines(value, n=12, bound=10**9):
    pts = integer_points(value, n, n, bound)
    lines = _lines(pts)
    require(len(lines) > 1, "points must not all lie on one line")
    count = sum(len(line) == 2 for line in lines)
    return count, _report(points=n, ordinary_lines=count)


def four_point_lines(value, n=16, bound=1000):
    pts = integer_points(value, n, n, bound)
    lines = _lines(pts)
    require(max(len(line) for line in lines) <= 4, "five or more points are collinear")
    count = sum(len(line) == 4 for line in lines)
    return count, _report(points=n, four_point_lines=count)


def general_position_subset(value, n=20, bound=20):
    """No four collinear; score is the largest subset with no three collinear (minimize)."""
    pts = integer_points(value, n, n, bound)
    lines = [line for line in _lines(pts) if len(line) >= 3]
    require(all(len(line) <= 3 for line in lines), "four points are collinear")
    triples = [sum(1 << i for i in line) for line in lines]
    best = 0

    def grow(chosen, size, candidates):
        nonlocal best
        best = max(best, size)
        while candidates:
            if size + candidates.bit_count() <= best:
                return
            bit = candidates & -candidates
            candidates ^= bit
            new = chosen | bit
            if all(t & new != t for t in triples):
                grow(new, size+1, candidates)

    grow(0, 0, (1 << n)-1)
    return best, _report(points=n, collinear_triples=len(triples), largest_general_position_subset=best)


def distinct_distances(value, n=20, bound=100):
    pts = integer_points(value, n, n, bound)
    require(all(0 <= x <= bound and 0 <= y <= bound for x, y in pts), "coordinates must lie in [0, bound]")
    require(_no_three_collinear(pts), "three points are collinear")
    distances = {(a[0]-b[0])**2+(a[1]-b[1])**2 for a, b in combinations(pts, 2)}
    return len(distances), _report(points=n, distinct_distances=len(distances))


# --- lattice contact graphs --------------------------------------------------

def penny_contacts(value, n=32, bound=64):
    """Triangular-lattice points a + b*omega (omega = exp(i*pi/3)); count unit-distance pairs."""
    pts = integer_points(value, n, n, bound)
    contacts = sum((a[0]-b[0])**2 + (a[0]-b[0])*(a[1]-b[1]) + (a[1]-b[1])**2 == 1 for a, b in combinations(pts, 2))
    return contacts, _report(points=n, contacts=contacts, harborth_bound=int(3*n-sqrt(12*n-3)))


# --- analysis ----------------------------------------------------------------

def _floats(value, n, dimension):
    rows = sequence(value, "points", n, n)
    out = []
    for row in rows:
        coords = sequence(row, "coordinates", dimension, dimension)
        for c in coords:
            require(type(c) in (int, float) and type(c) is not bool, "coordinates must be numbers")
            require(c == c and abs(c) < 1e6, "coordinates must be finite and moderate")
        out.append(tuple(float(c) for c in coords))
    return out


def distance_product(value, n=8):
    """Erdős-Herzog-Piranian: product of distances normalized to diameter 2, divided by n^n."""
    pts = _floats(value, n, 2)
    distances = [sqrt((a[0]-b[0])**2+(a[1]-b[1])**2) for a, b in combinations(pts, 2)]
    require(min(distances) > 1e-9, "points must be distinct")
    diameter = max(distances)
    # Delta = prod over ordered pairs = (prod over unordered pairs)^2, scaled so the diameter is 2
    log_delta = 2*sum(log(2*d/diameter) for d in distances)
    ratio = log_delta - n*log(n)
    return round(2.718281828459045**ratio, 12), _report(points=n, log_ratio=ratio, regular_polygon_ratio=1.0)


def _refine(f, grid, step, sense):
    """Golden-section refinement around the best local grid extrema (sense=-1 minimum, +1 maximum)."""
    values = [f(t) for t in grid]
    n = len(values)
    peaks = [i for i in range(n) if sense*values[i] >= sense*values[i-1] and sense*values[i] >= sense*values[(i+1) % n]]
    peaks.sort(key=lambda i: -sense*values[i])
    best = values[peaks[0]] if peaks else values[0]
    for i in peaks[:12]:
        lo, hi = grid[i]-step, grid[i]+step
        for _ in range(80):
            m1, m2 = lo+(hi-lo)*0.382, lo+(hi-lo)*0.618
            if sense*f(m1) >= sense*f(m2):
                hi = m2
            else:
                lo = m1
        value = f((lo+hi)/2)
        best = value if sense*value > sense*best else best
    return best


def cosine_minimum(frequencies, samples):
    f = lambda t: sum(cos(a*t) for a in frequencies)
    step = 2*pi/samples
    # the cosine sum is even and 2*pi-periodic; sample the full circle so neighbours wrap around
    return _refine(f, [step*i for i in range(samples)], step, -1)


def chowla_cosine(value, k=16, maximum=200):
    """Distinct positive frequencies; score is min over theta of the cosine sum divided by sqrt(k) (maximize)."""
    freqs = sequence(value, "frequencies", k, k)
    for a in freqs:
        integer(a, "frequency", 1, maximum)
    require(len(set(freqs)) == k, "frequencies must be distinct")
    low = cosine_minimum(freqs, 128*maximum)
    return round(low/sqrt(k), 9), _report(frequencies=sorted(freqs), minimum=low)


def littlewood_sup_norm(value, n=32, samples=None):
    """Signs of a polynomial sum c_k z^k; score is max |P| on the unit circle over sqrt(n) (minimize)."""
    signs = sequence(value, "coefficients", n, n)
    for c in signs:
        require(type(c) is int and c in (-1, 1), "coefficients must be +1 or -1")
    samples = samples or 256*n

    def modulus(t):
        re = sum(c*cos(k*t) for k, c in enumerate(signs))
        im = sum(c*sin(k*t) for k, c in enumerate(signs))
        return sqrt(re*re+im*im)

    step = 2*pi/samples
    peak = _refine(modulus, [step*i for i in range(samples)], step, 1)
    return round(peak/sqrt(n), 9), _report(coefficients=n, maximum_modulus=peak)
