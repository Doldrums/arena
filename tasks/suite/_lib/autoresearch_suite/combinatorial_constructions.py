"""Graph, SAT and additive-combinatorial construction evaluations."""
from __future__ import annotations

from .combinatorial import (
    CandidateError,
    _call,
    itertools,
    np,
    require,
    rng_for,
)

# ---------------------------------------------------------------------------
# Graph problems (MIS, max-cut)
# ---------------------------------------------------------------------------

def graph_instances(n_instances, n_nodes, seed, p=0.15):
    rng = rng_for(seed)
    out = []
    for _ in range(n_instances):
        adjacency = np.triu(rng.random((n_nodes, n_nodes)) < p, 1)
        adjacency = adjacency | adjacency.T
        out.append(adjacency)
    return out


def mis_greedy_score(priority, instances):
    """Mean independent-set size from greedy selection by ``priority(adjacency) -> scores``. Higher is better."""
    out = []
    for adjacency in instances:
        n = len(adjacency)
        scores = np.asarray(_call(priority, adjacency.copy()), dtype=float).ravel()
        require(scores.shape == (n,) and np.all(np.isfinite(scores)), "priority must return one finite score per vertex")
        chosen, blocked = [], np.zeros(n, dtype=bool)
        for v in np.argsort(-scores):
            if not blocked[v]:
                chosen.append(int(v))
                blocked[v] = True
                blocked[adjacency[v]] = True
        out.append(len(chosen))
    return float(np.mean(out))


def maxcut_score(partition, instances):
    """Mean cut size of the 0/1 partition returned by ``partition(adjacency) -> labels``. Higher is better."""
    out = []
    for adjacency in instances:
        n = len(adjacency)
        labels = np.asarray(_call(partition, adjacency.copy())).ravel()
        require(labels.shape == (n,) and set(np.unique(labels)).issubset({0, 1}), "partition must return a 0/1 label per vertex")
        cut = int(np.sum(adjacency[np.ix_(labels == 0, labels == 1)]))
        out.append(cut)
    return float(np.mean(out))


# ---------------------------------------------------------------------------
# Additive combinatorics (FunSearch cap sets, no-isosceles sets)
# ---------------------------------------------------------------------------

def cap_set_greedy(priority, n):
    """Build a cap set in Z_3^n greedily by candidate priority (FunSearch contract ``priority(vector, n) -> float``)."""
    vectors = list(itertools.product(range(3), repeat=n))
    scores = np.array([float(_call(priority, v, n)) for v in vectors])
    require(np.all(np.isfinite(scores)), "priority returned a nonfinite score")
    chosen = set()
    for idx in np.argsort(-scores, kind="stable"):
        v = vectors[idx]
        ok = True
        for u in chosen:
            third = tuple((-a - b) % 3 for a, b in zip(u, v))
            if third in chosen:
                ok = False
                break
        if ok:
            chosen.add(v)
    return len(chosen)


def verify_cap_set(vectors, n):
    pts = {tuple(int(x) for x in v) for v in vectors}
    require(len(pts) == len(vectors), "duplicate vectors")
    require(all(len(v) == n and all(x in (0, 1, 2) for x in v) for v in pts), f"vectors must lie in {{0,1,2}}^{n}")
    for a, b in itertools.combinations(pts, 2):
        require(tuple((-x - y) % 3 for x, y in zip(a, b)) not in pts, "three vectors sum to zero (line)")
    return len(pts)


def no_isosceles_size(points, n):
    """Size of a subset of the n x n grid with no isosceles triangle (any three points with two equal distances)."""
    pts = {(int(x), int(y)) for x, y in points}
    require(len(pts) == len(points), "duplicate points")
    require(all(0 <= x < n and 0 <= y < n for x, y in pts), f"points must lie in the {n} x {n} grid")
    plist = sorted(pts)
    for a, b, c in itertools.combinations(plist, 3):
        d1 = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
        d2 = (a[0] - c[0]) ** 2 + (a[1] - c[1]) ** 2
        d3 = (b[0] - c[0]) ** 2 + (b[1] - c[1]) ** 2
        require(not (d1 == d2 or d1 == d3 or d2 == d3), f"points {a}, {b}, {c} form an isosceles triangle")
    return len(pts)


def no_isosceles_maximal(points, n):
    """Size of a maximal no-isosceles set (no grid point can be added). Lower is better."""
    size = no_isosceles_size(points, n)
    pts = {(int(x), int(y)) for x, y in points}
    for x in range(n):
        for y in range(n):
            if (x, y) in pts:
                continue
            try:
                no_isosceles_size(list(pts | {(x, y)}), n)
            except CandidateError:
                continue
            raise CandidateError(f"the set is not maximal: point ({x}, {y}) can be added")
    return size


# ---------------------------------------------------------------------------
# SAT (portable reference)
# ---------------------------------------------------------------------------

def sat_instances(n_instances, n_vars, seed):
    rng = rng_for(seed)
    out = []
    for _ in range(n_instances):
        truth = rng.random(n_vars) < 0.5
        clauses = []
        for _ in range(4 * n_vars):
            variables = rng.choice(n_vars, size=3, replace=False)
            clause = [int(v + 1) * int(rng.choice([-1, 1])) for v in variables]
            if not any(truth[abs(l) - 1] == (l > 0) for l in clause):
                clause[0] *= -1
            clauses.append(clause)
        out.append({"n": n_vars, "clauses": clauses})
    return out


def sat_score(solve, instances):
    """Fraction of instances satisfied by ``solve(instance) -> list of booleans``. Higher is better."""
    solved = 0
    for instance in instances:
        assignment = _call(solve, {"n": instance["n"], "clauses": [list(c) for c in instance["clauses"]]})
        assignment = list(assignment)
        require(len(assignment) == instance["n"], "assignment must have one boolean per variable")
        if all(any(bool(assignment[abs(l) - 1]) == (l > 0) for l in clause) for clause in instance["clauses"]):
            solved += 1
    return solved / len(instances)


# ---------------------------------------------------------------------------
# Narrow admissible tuples (FunSearch)
# ---------------------------------------------------------------------------

def _primes_up_to(n):
    sieve = np.ones(n + 1, dtype=bool)
    sieve[:2] = False
    for p in range(2, int(n ** 0.5) + 1):
        if sieve[p]:
            sieve[p * p::p] = False
    return [int(p) for p in np.nonzero(sieve)[0]]


def admissible_tuple_size(values, n):
    """Size of an admissible tuple inside [0, n]: for every prime p <= k the tuple misses a residue class mod p. Higher is better."""
    try:
        points = sorted({int(v) for v in values})
    except (TypeError, ValueError) as error:
        raise CandidateError(f"the tuple must contain integers: {error}") from None
    require(points and all(0 <= v <= n for v in points), f"all elements must lie in [0, {n}]")
    k = len(points)
    for p in _primes_up_to(k):
        require(len({v % p for v in points}) < p, f"the tuple covers every residue class modulo {p}")
    return k
