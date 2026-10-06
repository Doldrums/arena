"""Independent exact verifiers for extremal graph, hypergraph and design constructions.

Scores are exact functions of the submitted object (edge counts, cut values,
subgraph counts, independence numbers). Reference values and sources are in
catalog/science/prize_f.json. No function claims a Lean proof or optimality.
"""
from itertools import combinations
from random import Random

from .runtime import require
from .science_prize import integer, sequence


def _bits(mask):
    while mask:
        bit = mask & -mask
        yield bit.bit_length()-1
        mask ^= bit


def graph(value, n, edges=None):
    """Parse a list of [u, v] pairs on vertices 0..n-1 (optionally with an exact edge count)."""
    rows = sequence(value, "edges", 0 if edges is None else edges, n*(n-1)//2 if edges is None else edges)
    adj, seen = [0]*n, set()
    for row in rows:
        u, v = sequence(row, "edge endpoints", 2, 2)
        integer(u, "vertex", 0, n-1)
        integer(v, "vertex", 0, n-1)
        require(u != v, "self-loops are forbidden")
        e = (min(u, v), max(u, v))
        require(e not in seen, "duplicate undirected edge")
        seen.add(e)
        adj[u] |= 1 << v
        adj[v] |= 1 << u
    return adj


def triangle_free(adj):
    return all(not (adj[u] & adj[v]) for u in range(len(adj)) for v in _bits(adj[u]) if v > u)


def has_cycle(adj, length):
    """Exact search for a cycle of the given length (not necessarily induced)."""
    n = len(adj)
    if length == 3:
        return not triangle_free(adj)
    if length == 4:
        return any((adj[u] & adj[v]).bit_count() >= 2 for u in range(n) for v in range(u+1, n))
    for start in range(n):
        allowed = ((1 << n)-1) & ~((1 << (start+1))-1)

        def extend(v, depth, used):
            if depth == length:
                return bool(adj[v] >> start & 1)
            return any(extend(w, depth+1, used | (1 << w)) for w in _bits(adj[v] & allowed & ~used))

        if any(extend(w, 2, (1 << start) | (1 << w)) for w in _bits(adj[start] & allowed)):
            return True
    return False


def colourable(adj, colours):
    """Exact k-colourability by DSATUR-ordered backtracking."""
    n = len(adj)
    colour = [-1]*n

    def place(done, used):
        if done == n:
            return True
        best, key, blocked = -1, None, set()
        for v in range(n):
            if colour[v] < 0:
                seen = {colour[w] for w in _bits(adj[v]) if colour[w] >= 0}
                k = (len(seen), adj[v].bit_count())
                if key is None or k > key:
                    best, key, blocked = v, k, seen
        for c in range(min(colours, used+1)):
            if c not in blocked:
                colour[best] = c
                if place(done+1, max(used, c+1)):
                    return True
        colour[best] = -1
        return False

    return place(0, 0)


def _count(adj):
    return sum(a.bit_count() for a in adj)//2


def _report(**extra):
    return {"lean_verified": False, **extra}


# --- triangle-free graphs ---------------------------------------------------

def bipartization(value, n=23):
    """Edges that must be deleted to make a triangle-free graph bipartite (maximize)."""
    adj = graph(value, n)
    require(triangle_free(adj), "graph contains a triangle")
    m = _count(adj)
    degree = [a.bit_count() for a in adj]
    # Gray-code walk over the 2^(n-1) cuts with vertex n-1 fixed on side zero.
    side, cut, best = 0, 0, 0
    for step in range(1, 1 << (n-1)):
        v = (step & -step).bit_length()-1
        across = (adj[v] & side).bit_count() if not side >> v & 1 else (adj[v] & ~side).bit_count()
        cut += degree[v]-2*across
        side ^= 1 << v
        best = max(best, cut)
    return m-best, _report(vertices=n, edges=m, maximum_cut=best, deletions_to_bipartite=m-best)


def sparse_halves(value, n=20):
    """Triangle-free graph; score is the minimum edge count over all n/2-vertex subsets (maximize)."""
    adj = graph(value, n)
    require(triangle_free(adj), "graph contains a triangle")
    half, best = n//2, None

    def descend(start, chosen, mask, edges):
        nonlocal best
        if chosen == half:
            best = edges if best is None else min(best, edges)
            return
        for v in range(start, n-(half-chosen)+1):
            descend(v+1, chosen+1, mask | (1 << v), edges+(adj[v] & mask).bit_count())

    descend(0, 0, 0, 0)
    return best, _report(vertices=n, edges=_count(adj), minimum_half_edges=best)


def triangle_count(value, n=16, edges=68):
    adj = graph(value, n, edges)
    triangles = sum((adj[u] & adj[v] & ~((1 << (v+1))-1)).bit_count() for u in range(n) for v in _bits(adj[u]) if v > u)
    return triangles, _report(vertices=n, edges=edges, triangles=triangles)


def diameter_two_triangle_free(value, n=50):
    adj = graph(value, n)
    require(triangle_free(adj), "graph contains a triangle")
    for u in range(n):
        reach = adj[u] | (1 << u)
        for w in _bits(adj[u]):
            reach |= adj[w]
        require(reach == (1 << n)-1, "some pair of vertices is at distance greater than two")
    degree = max(a.bit_count() for a in adj)
    return degree, _report(vertices=n, edges=_count(adj), maximum_degree=degree)


def triangle_free_four_chromatic(value, n=16):
    adj = graph(value, n)
    require(triangle_free(adj), "graph contains a triangle")
    require(not colourable(adj, 3), "graph is 3-colourable")
    return _count(adj), _report(vertices=n, edges=_count(adj), chromatic_number_at_least=4)


# --- Turán-type problems ----------------------------------------------------

def cycle_free(value, n, lengths):
    adj = graph(value, n)
    for length in lengths:
        require(not has_cycle(adj, length), f"graph contains a cycle of length {length}")
    return _count(adj), _report(vertices=n, edges=_count(adj), forbidden_cycles=list(lengths))


def bipartite_free(value, n=20, s=2, t=3):
    """No K_{s,t} with s in {2,3}: no s vertices share t common neighbours."""
    adj = graph(value, n)
    for group in combinations(range(n), s):
        common = (1 << n)-1
        for v in group:
            common &= adj[v]
        require(common.bit_count() < t, f"graph contains K{s},{t}")
    return _count(adj), _report(vertices=n, edges=_count(adj), forbidden=f"K{s},{t}")


def has_cube(adj):
    n = len(adj)
    for x in range(n):
        for p, q, r in combinations(list(_bits(adj[x])), 3):
            base = (1 << x) | (1 << p) | (1 << q) | (1 << r)
            for a in _bits(adj[p] & adj[q] & ~base):
                for b in _bits(adj[p] & adj[r] & ~base & ~(1 << a)):
                    for c in _bits(adj[q] & adj[r] & ~base & ~(1 << a) & ~(1 << b)):
                        if adj[a] & adj[b] & adj[c] & ~(base | (1 << a) | (1 << b) | (1 << c)):
                            return True
    return False


def cube_free(value, n=16):
    adj = graph(value, n)
    require(not has_cube(adj), "graph contains the cube Q3")
    return _count(adj), _report(vertices=n, edges=_count(adj))


def four_cycle_count(value, n=31, edges=91):
    adj = graph(value, n, edges)
    pairs = sum((c := (adj[u] & adj[v]).bit_count())*(c-1)//2 for u in range(n) for v in range(u+1, n))
    return pairs//2, _report(vertices=n, edges=edges, four_cycles=pairs//2)


def largest_book(value, n=40, edges=401):
    adj = graph(value, n, edges)
    book = max((adj[u] & adj[v]).bit_count() for u in range(n) for v in _bits(adj[u]) if v > u)
    return book, _report(vertices=n, edges=edges, largest_book=book)


def erdos_rogers(value, n=18):
    """K4-free graph; score is its largest triangle-free induced subgraph (minimize)."""
    adj = graph(value, n)
    for u in range(n):
        for v in _bits(adj[u]):
            if v > u:
                common = adj[u] & adj[v]
                require(not any(adj[w] & common for w in _bits(common)), "graph contains K4")
    best = 0

    def grow(chosen, size, candidates):
        nonlocal best
        best = max(best, size)
        while candidates:
            if size+candidates.bit_count() <= best:
                return
            bit = candidates & -candidates
            v = bit.bit_length()-1
            candidates ^= bit
            inside = adj[v] & chosen
            # v may join if its neighbours in the set are pairwise non-adjacent
            if all(not (adj[w] & inside) for w in _bits(inside)):
                grow(chosen | bit, size+1, candidates)

    grow(0, 0, (1 << n)-1)
    return best, _report(vertices=n, edges=_count(adj), largest_triangle_free_induced=best)


# --- hypergraphs, designs and hypercubes -------------------------------------

def triples(value, n, maximum):
    rows = sequence(value, "triples", 0, maximum)
    seen = set()
    for row in rows:
        t = sequence(row, "triple", 3, 3)
        for x in t:
            integer(x, "vertex", 0, n-1)
        key = tuple(sorted(t))
        require(len(set(key)) == 3, "triple vertices must be distinct")
        require(key not in seen, "duplicate triple")
        seen.add(key)
    return seen


def bounded_matching(value, n=12, matching=2):
    edges = triples(value, n, n*(n-1)*(n-2)//6)
    masks = [sum(1 << x for x in e) for e in edges]

    def disjoint(start, used, need):
        if need == 0:
            return True
        return any(not (masks[i] & used) and disjoint(i+1, used | masks[i], need-1) for i in range(start, len(masks)))

    require(not disjoint(0, 0, matching+1), f"hypergraph has {matching+1} pairwise disjoint triples")
    return len(edges), _report(vertices=n, triples=len(edges), matching_number_at_most=matching)


def steiner_packing(value, points=12, block=6, strength=5):
    rows = sequence(value, "blocks", 0, 924)
    covered, blocks = set(), set()
    for row in rows:
        b = sequence(row, "block", block, block)
        for x in b:
            integer(x, "point", 0, points-1)
        key = tuple(sorted(b))
        require(len(set(key)) == block and key not in blocks, "blocks must be distinct sets of distinct points")
        blocks.add(key)
        for sub in combinations(key, strength):
            require(sub not in covered, f"some {strength}-subset lies in two blocks")
            covered.add(sub)
    return len(blocks), _report(points=points, block_size=block, strength=strength, blocks=len(blocks))


def hypercube_c4_free(value, dimension=7):
    rows = sequence(value, "hypercube edges", 0, dimension*2**(dimension-1))
    chosen = set()
    for row in rows:
        u, v = sequence(row, "edge endpoints", 2, 2)
        integer(u, "vertex", 0, 2**dimension-1)
        integer(v, "vertex", 0, 2**dimension-1)
        require((u ^ v).bit_count() == 1, "endpoints must differ in exactly one coordinate")
        e = (min(u, v), max(u, v))
        require(e not in chosen, "duplicate edge")
        chosen.add(e)
    # Every 4-cycle of Q_d is a 2-dimensional face.
    for i, j in combinations(range(dimension), 2):
        for x in range(2**dimension):
            if not x >> i & 1 and not x >> j & 1:
                a, b, c, d = x, x | 1 << i, x | 1 << i | 1 << j, x | 1 << j
                require(not all((min(p, q), max(p, q)) in chosen for p, q in ((a, b), (b, c), (d, c), (a, d))),
                        "edge set contains a four-cycle")
    return len(chosen), _report(dimension=dimension, edges=len(chosen), total_edges=dimension*2**(dimension-1))


def tripartite_free(value, n=16):
    """3-uniform hypergraph without K(2,2,2): three disjoint pairs with all eight transversal triples."""
    edges = triples(value, n, n*(n-1)*(n-2)//6)
    link = {}
    for a, b, c in edges:
        for x, y, z in ((a, b, c), (a, c, b), (b, c, a)):
            link[(x, y)] = link.get((x, y), 0) | 1 << z
    pairs = list(combinations(range(n), 2))
    for a1, a2 in pairs:
        for b1, b2 in pairs:
            if b1 <= a1 or len({a1, a2, b1, b2}) < 4:
                continue
            common = ((1 << n)-1) & ~(1 << a1 | 1 << a2 | 1 << b1 | 1 << b2)
            for x in (a1, a2):
                for y in (b1, b2):
                    common &= link.get((min(x, y), max(x, y)), 0)
            # any two common vertices complete the eight transversal triples
            require(common.bit_count() < 2, "hypergraph contains K(2,2,2)")
    return len(edges), _report(vertices=n, triples=len(edges))


def linear_independence(value, n=16):
    """Linear 3-graph; score is its independence number (minimize)."""
    edges = triples(value, n, n*(n-1)//6)
    pairs = set()
    for e in edges:
        for p in combinations(e, 2):
            require(p not in pairs, "two triples share two vertices")
            pairs.add(p)
    masks = [sum(1 << x for x in e) for e in edges]
    best = 0
    for subset in range(1 << n):
        size = subset.bit_count()
        if size > best and not any(m & subset == m for m in masks):
            best = size
    return best, _report(vertices=n, triples=len(edges), independence_number=best)


# --- fixed-instance decompositions ------------------------------------------

def instance_graph(n, p, seed):
    """Deterministic connected graph: a random spanning path plus random edges."""
    rng = Random(seed)
    order = list(range(n))
    rng.shuffle(order)
    edges = {tuple(sorted(e)) for e in zip(order, order[1:])}
    edges |= {(u, v) for u in range(n) for v in range(u+1, n) if rng.random() < p}
    return sorted(edges)


GALLAI_INSTANCES = ((20, 0.3, 1), (25, 0.3, 2), (30, 0.25, 3))
CYCLE_INSTANCES = ((20, 0.4, 11), (25, 0.35, 12), (30, 0.3, 13))


def _walks(value, instances, closed):
    """Check an edge decomposition into paths (closed=False) or into cycles and single edges."""
    rows = sequence(value, "decompositions, one per instance", len(instances), len(instances))
    total = 0
    for (n, p, seed), pieces in zip(instances, rows):
        remaining = set(instance_graph(n, p, seed))
        pieces = sequence(pieces, "pieces", 1, len(remaining))
        for piece in pieces:
            walk = sequence(piece, "vertex sequence", 2, n)
            for x in walk:
                integer(x, "vertex", 0, n-1)
            require(len(set(walk)) == len(walk), "pieces must not repeat vertices")
            steps = list(zip(walk, walk[1:]))
            if closed and len(walk) >= 3:
                steps.append((walk[-1], walk[0]))   # a cycle; two vertices mean a single edge
            for u, v in steps:
                e = (min(u, v), max(u, v))
                require(e in remaining, "piece uses a missing or already used edge")
                remaining.remove(e)
        require(not remaining, "pieces must cover every edge")
        total += len(pieces)
    return total


def gallai_paths(value):
    total = _walks(value, GALLAI_INSTANCES, closed=False)
    bound = sum((n+1)//2 for n, _, _ in GALLAI_INSTANCES)
    return total, _report(paths=total, gallai_bound=bound)


def cycle_edge_decomposition(value):
    total = _walks(value, CYCLE_INSTANCES, closed=True)
    return total, _report(pieces=total, instances=len(CYCLE_INSTANCES))


def instance_trees(n, seed):
    """Deterministic trees T_1..T_n with T_k on k vertices (random Prüfer sequences)."""
    rng = Random(seed)
    trees = []
    for k in range(1, n+1):
        if k <= 2:
            trees.append([] if k == 1 else [(0, 1)])
            continue
        code = [rng.randrange(k) for _ in range(k-2)]
        degree = [1]*k
        for x in code:
            degree[x] += 1
        edges = []
        for x in code:
            leaf = min(v for v in range(k) if degree[v] == 1)
            edges.append((leaf, x))
            degree[leaf] -= 1
            degree[x] -= 1
        u, w = [v for v in range(k) if degree[v] == 1]
        edges.append((u, w))
        trees.append(edges)
    return trees


def tree_packing(value, n=20, seed=611):
    trees = instance_trees(n, seed)
    rows = sequence(value, "embeddings, one per tree (None to skip)", n, n)
    used, packed = set(), 0
    for k, (edges, row) in enumerate(zip(trees, rows), 1):
        if row is None:
            continue
        image = sequence(row, "vertex images", k, k)
        for x in image:
            integer(x, "host vertex", 0, n-1)
        require(len(set(image)) == k, "embedding must be injective")
        for u, v in edges:
            e = (min(image[u], image[v]), max(image[u], image[v]))
            require(e not in used, "trees share a host edge")
            used.add(e)
        packed += len(edges)
    return packed, _report(host_vertices=n, packed_edges=packed, host_edges=n*(n-1)//2)
