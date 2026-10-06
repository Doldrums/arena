"""Independent verifiers for hypergraphs, set families, graph constructions,
arithmetic records and instance-solving tasks.

Every score is an exact integer or rational computation; reciprocal sums are
reported as floats together with their exact value. Instance-solving tasks
regenerate their fixed instances from the seeds stated in each contract.
Reference values and sources are in catalog/science/prize_i.json.
"""
from fractions import Fraction
from itertools import combinations
from math import gcd, isqrt
from random import Random

from .runtime import require
from .science_prize import integer, sequence
from .science_prize_e import _bits, graph, has_cycle, has_independent_set
from .science_prize_h import factor, int_set, primes_up_to, run_certificate


def _report(**extra):
    return {"lean_verified": False, **extra}


# --- hypergraphs and set families --------------------------------------------------

def proper_two_colouring(n, edges):
    """Backtracking with unit propagation; returns a proper 2-colouring or None."""
    incident = [[] for _ in range(n)]
    for e in edges:
        for v in e:
            incident[v].append(e)
    colour, trail = [-1]*n, []

    def assign(v, c):
        queue = [(v, c)]
        while queue:
            u, cu = queue.pop()
            if colour[u] != -1:
                if colour[u] != cu:
                    return False
                continue
            colour[u] = cu
            trail.append(u)
            for e in incident[u]:
                if all(colour[w] in (cu, -1) for w in e):
                    free = [w for w in e if colour[w] == -1]
                    if not free:
                        return False                     # monochromatic edge
                    if len(free) == 1:
                        queue.append((free[0], 1-cu))    # the last vertex is forced
        return True

    order = sorted(range(n), key=lambda v: -len(incident[v]))

    def search(first):
        v = next((u for u in order if colour[u] == -1), None)
        if v is None:
            return True
        for c in ((0,) if first else (0, 1)):           # colour symmetry: fix the first vertex
            mark = len(trail)
            if assign(v, c) and search(False):
                return True
            while len(trail) > mark:
                colour[trail.pop()] = -1
        return False

    return list(colour) if search(True) else None


def property_b(value, uniformity=5, max_vertices=26, max_edges=200):
    """A non-2-colourable uniform hypergraph (no Property B); minimize the number of edges."""
    require(type(value) is dict and set(value) == {"n", "edges"}, "return keys n and edges only")
    n = integer(value["n"], "n", uniformity, max_vertices)
    rows = sequence(value["edges"], "edges", 1, max_edges)
    edges = set()
    for row in rows:
        e = sequence(row, "edge", uniformity, uniformity)
        for v in e:
            integer(v, "vertex", 0, n-1)
        require(len(set(e)) == uniformity, "edge vertices must be distinct")
        require(frozenset(e) not in edges, "duplicate edge")
        edges.add(frozenset(e))
    require(proper_two_colouring(n, [tuple(e) for e in edges]) is None, "the hypergraph has a proper 2-colouring")
    return len(edges), _report(vertices=n, edges=len(edges), uniformity=uniformity)


def forbidden_intersection(value, n=8, r=2):
    """Distinct subsets of {1..n}; no two members meet in exactly r elements. Maximize the family."""
    rows = sequence(value, "sets", 1, 2**n)
    masks = set()
    for row in rows:
        s = sequence(row, "set", 0, n)
        for x in s:
            integer(x, "element", 1, n)
        require(len(set(s)) == len(s), "set elements must be distinct")
        mask = sum(1 << (x-1) for x in s)
        require(mask not in masks, "sets must be distinct")
        masks.add(mask)
    family = sorted(masks)
    for a, b in combinations(family, 2):
        require((a & b).bit_count() != r, f"two members intersect in exactly {r} elements")
    return len(family), _report(ground_set=n, forbidden_intersection=r, size=len(family))


# --- graph constructions -----------------------------------------------------------

def cycle_clique_ramsey(value, cycle=5, independent=9, max_vertices=35):
    n, adj = graph(value, max_vertices)
    require(not has_cycle(adj, cycle), f"the graph contains a {cycle}-cycle")
    require(not has_independent_set(adj, independent), f"the graph has an independent set of size {independent}")
    return n, _report(vertices=n, forbidden_cycle=cycle, independence_bound=independent-1)


def cycle_lengths(adj, n):
    """Bitmask of cycle lengths, by dynamic programming over paths from their smallest vertex."""
    lengths = 0
    for s in range(n):
        higher = ((1 << n)-1) & ~((1 << (s+1))-1)
        layer, size = {1 << s: 1 << s}, 1
        while layer:
            nxt = {}
            for mask, ends in layer.items():
                for v in _bits(ends):
                    for w in _bits(adj[v] & higher & ~mask):
                        m2 = mask | (1 << w)
                        nxt[m2] = nxt.get(m2, 0) | (1 << w)
            size += 1
            if size >= 3 and any(ends & adj[s] for ends in nxt.values()):
                lengths |= 1 << size
            layer = nxt
    return lengths


def cycle_spectra(value, n=10, max_graphs=500):
    """Graphs on n vertices; the score is the number of distinct sets of cycle lengths."""
    rows = sequence(value, "graphs", 1, max_graphs)
    spectra = set()
    for row in rows:
        edges = sequence(row, "edges", 0, n*(n-1)//2)
        adj, seen = [0]*n, set()
        for e in edges:
            u, v = sequence(e, "edge", 2, 2)
            integer(u, "vertex", 0, n-1)
            integer(v, "vertex", 0, n-1)
            require(u != v and (min(u, v), max(u, v)) not in seen, "graphs must be simple")
            seen.add((min(u, v), max(u, v)))
            adj[u] |= 1 << v
            adj[v] |= 1 << u
        spectra.add(cycle_lengths(adj, n))
    return len(spectra), _report(vertices=n, graphs=len(rows), distinct_cycle_sets=len(spectra))


def triangle_degree_sum(value, n=16, edges=65):
    """A graph with exactly `edges` > n^2/4 edges; the score is the largest degree sum of a triangle (minimize)."""
    count, adj = graph(value, n, min_vertices=n)
    m = sum(a.bit_count() for a in adj)//2
    require(m == edges, f"the graph must have exactly {edges} edges")
    degree = [a.bit_count() for a in adj]
    best = max(degree[u]+degree[v]+degree[w] for u in range(n) for v in _bits(adj[u] >> (u+1) << (u+1))
               for w in _bits(adj[u] & adj[v] & ~((1 << (v+1))-1)))
    return best, _report(vertices=n, edges=m, largest_triangle_degree_sum=best)


def rainbow_c4(value, n=20, colours=20):
    """Coloured edges [u, v, c]; every 4-cycle must receive four distinct colours. Maximize the edges."""
    rows = sequence(value, "coloured edges", 1, n*(n-1)//2)
    adj, colour = [0]*n, {}
    for row in rows:
        u, v, c = sequence(row, "edge [u, v, colour]", 3, 3)
        integer(u, "vertex", 0, n-1)
        integer(v, "vertex", 0, n-1)
        integer(c, "colour", 0, colours-1)
        e = (min(u, v), max(u, v))
        require(u != v and e not in colour, "graphs must be simple")
        colour[e] = c
        adj[u] |= 1 << v
        adj[v] |= 1 << u
    col = lambda a, b: colour[(min(a, b), max(a, b))]
    for u, w in combinations(range(n), 2):
        for v, x in combinations(list(_bits(adj[u] & adj[w])), 2):
            require(len({col(u, v), col(v, w), col(w, x), col(x, u)}) == 4, f"the 4-cycle {u}-{v}-{w}-{x} repeats a colour")
    return len(colour), _report(vertices=n, colours=colours, edges=len(colour))


# --- arithmetic ----------------------------------------------------------------------

def coprime_reciprocal_sum(value, n=512):
    """Pairwise coprime integers in [1, n); maximize the sum of 1/(n - a)."""
    a = int_set(value, "set", 1, n-1, 1)
    for x, y in combinations(a, 2):
        require(gcd(x, y) == 1, f"{x} and {y} are not coprime")
    total = sum(Fraction(1, n-x) for x in a)
    prime_sum = sum(Fraction(1, p) for p in primes_up_to(n-1))
    return round(float(total), 12), _report(size=len(a), exact=str(total), prime_reciprocal_sum=round(float(prime_sum), 12))


def powerful(x):
    return all(e >= 2 for e in factor(x).values())


def powerful_pairs(value, bound=10**18, max_pairs=1000):
    """Certified representations N = a + b with a <= b powerful (1 counts as powerful). Maximize the count."""
    require(type(value) is dict and set(value) == {"N", "pairs"}, "return keys N and pairs only")
    total = integer(value["N"], "N", 2, bound)
    rows = sequence(value["pairs"], "pairs", 1, max_pairs)
    seen = set()
    for row in rows:
        a, b = sequence(row, "pair", 2, 2)
        integer(a, "a", 1, total)
        integer(b, "b", 1, total)
        require(a <= b and a+b == total, "each pair must satisfy a <= b and a + b = N")
        require((a, b) not in seen, "duplicate pair")
        require(powerful(a) and powerful(b), f"{a} or {b} is not powerful")
        seen.add((a, b))
    return len(seen), _report(N=total, representations=len(seen))


def b2g_set(value, n=1000, g=2):
    """A subset of {1..n} in which every integer has at most g representations a + b with a <= b. Maximize."""
    a = int_set(value, "set", 1, n, 1)
    counts = {}
    for i, x in enumerate(a):
        for y in a[i:]:
            counts[x+y] = counts.get(x+y, 0)+1
    worst = max(counts.values())
    require(worst <= g, f"some integer has {worst} representations")
    return len(a), _report(size=len(a), largest_multiplicity=worst)


def totient(x):
    result = x
    for p in factor(x):
        result = result//p*(p-1)
    return result


def distinct_totient_run(value, bound=10**12, max_length=200):
    start, length = run_certificate(value, bound, max_length)
    values = [totient(x) for x in range(start, start+length)]
    require(len(set(values)) == length, "totient values must be pairwise distinct")
    return length, _report(start=start, length=length)


def coprime_adjacent_divisors(value, bound=10**18):
    """tau_perp(n): consecutive divisors d_i < d_{i+1} of n with gcd 1. Maximize."""
    n = integer(value, "n", 2, bound)
    divisors = [1]
    for p, e in factor(n).items():
        divisors = [d*p**k for d in divisors for k in range(e+1)]
    divisors.sort()
    count = sum(1 for a, b in zip(divisors, divisors[1:]) if gcd(a, b) == 1)
    return count, _report(n=n, divisors=len(divisors), coprime_adjacent_pairs=count)


# --- instance generators for method tasks ---------------------------------------------

def bounded_degree_graph(n, d, seed):
    rng = Random(seed)
    degree, edges = [0]*n, set()
    for _ in range(4*n*d):
        u, v = rng.randrange(n), rng.randrange(n)
        e = (min(u, v), max(u, v))
        if u != v and degree[u] < d and degree[v] < d and e not in edges:
            edges.add(e)
            degree[u] += 1
            degree[v] += 1
    return sorted(edges)


def random_graph(n, p, seed):
    rng = Random(seed)
    return [(u, v) for u in range(n) for v in range(u+1, n) if rng.random() < p]


def split_graph(n, k, p, seed):
    """A split graph (hence chordal): a clique on 0..k-1, an independent set on k..n-1, cross pairs with probability p."""
    rng = Random(seed)
    edges = [(u, v) for u in range(k) for v in range(u+1, k)]
    edges += [(u, v) for v in range(k, n) for u in range(k) if rng.random() < p]
    return sorted(edges)


def cycle_plus_triangles(n, seed):
    """Hamiltonian cycle 0-1-...-(n-1)-0 plus vertex-disjoint triangles using no cycle edge."""
    rng = Random(seed)
    order = list(range(n))
    while True:
        rng.shuffle(order)
        triples = [order[i:i+3] for i in range(0, n, 3)]
        if all((a-b) % n not in (1, n-1) for t in triples for a, b in combinations(t, 2)):
            break
    edges = {(min(i, (i+1) % n), max(i, (i+1) % n)) for i in range(n)}
    edges |= {(min(a, b), max(a, b)) for t in triples for a, b in combinations(t, 2)}
    return sorted(edges)


def planar_bipartite_lists(faces_to_split, seed, palette=5):
    """A bipartite quadrangulation grown from the cube by inserting a smaller square into random faces,
    with a random list of three colours per vertex."""
    rng = Random(seed)
    faces = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    edges = {(min(a, b), max(a, b)) for f in faces for a, b in zip(f, f[1:]+f[:1])}
    n = 8
    for _ in range(faces_to_split):
        face = faces.pop(rng.randrange(len(faces)))
        inner = list(range(n, n+4))
        n += 4
        for i in range(4):
            a, b = face[i], face[(i+1) % 4]
            edges.add((min(a, inner[i]), max(a, inner[i])))
            edges.add((inner[i], inner[(i+1) % 4]) if inner[i] < inner[(i+1) % 4] else (inner[(i+1) % 4], inner[i]))
            faces.append([a, b, inner[(i+1) % 4], inner[i]])
        faces.append(inner)
    lists = [sorted(rng.sample(range(palette), 3)) for _ in range(n)]
    return n, sorted(edges), lists


def sum_free_instance(size, seed, limit=10000):
    rng = Random(seed)
    values = set()
    while len(values) < size:
        x = rng.randint(-limit, limit)
        if x:
            values.add(x)
    return sorted(values)


STRONG_INSTANCES = ((40, 4, 101), (60, 5, 102), (80, 6, 103))
TRANSVERSAL_INSTANCES = ((30, 0.3, 201), (35, 0.25, 202), (40, 0.2, 203))
CHORDAL_INSTANCES = ((30, 10, 0.7, 301), (60, 20, 0.7, 302), (90, 30, 0.7, 303))
TRIANGLE_CYCLE_INSTANCES = ((30, 401), (60, 402), (90, 403), (150, 404), (300, 405))
DENSE_INSTANCES = ((32, 0.6, 601), (64, 0.55, 602))
LIST_INSTANCES = ((20, 701), (40, 702), (60, 703), (100, 704))
SUM_FREE_INSTANCES = ((60, 801), (120, 802), (240, 803))


def _per_instance(value, count):
    return sequence(value, "one answer per instance", count, count)


def _colouring(row, n, colours):
    row = sequence(row, "colour per vertex", n, n)
    for c in row:
        integer(c, "colour", 0, colours-1)
    return row


def strong_edge_colouring(value, instances=STRONG_INSTANCES):
    """Colour per edge (sorted edge order) with each colour class an induced matching; minimize the colours used."""
    total, used = 0, []
    for (n, d, seed), row in zip(instances, _per_instance(value, len(instances))):
        edges = bounded_degree_graph(n, d, seed)
        colours = sequence(row, "colour per edge", len(edges), len(edges))
        for c in colours:
            integer(c, "colour", 0, len(edges)-1)
        adj = [set() for _ in range(n)]
        for u, v in edges:
            adj[u].add(v)
            adj[v].add(u)
        classes = {}
        for e, c in zip(edges, colours):
            classes.setdefault(c, []).append(e)
        for members in classes.values():
            for (a, b), (x, y) in combinations(members, 2):
                require(not {a, b} & {x, y} and not ({x, y} & (adj[a] | adj[b])), "two edges of one colour share or join vertices")
        used.append(len(classes))
        total += len(classes)
    return total, _report(colours_per_instance=used, erdos_nesetril_bounds=[5*d*d//4 for _, d, _ in instances])


def maximal_cliques(adj, n):
    """Bron-Kerbosch with pivoting over bitmasks."""
    out = []

    def expand(r, p, x):
        if not p and not x:
            out.append(r)
            return
        pivot = max(_bits(p | x), key=lambda u: (adj[u] & p).bit_count())
        for v in list(_bits(p & ~adj[pivot])):
            expand(r | (1 << v), p & adj[v], x & adj[v])
            p &= ~(1 << v)
            x |= 1 << v
    expand(0, (1 << n)-1, 0)
    return [c for c in out if c.bit_count() >= 2]


def clique_transversal(value, instances=TRANSVERSAL_INSTANCES):
    """A vertex set meeting every maximal clique with at least two vertices; minimize the total size."""
    total, sizes = 0, []
    for (n, p, seed), row in zip(instances, _per_instance(value, len(instances))):
        adj = [0]*n
        for u, v in random_graph(n, p, seed):
            adj[u] |= 1 << v
            adj[v] |= 1 << u
        chosen = int_set(row, "transversal", 0, n-1, 0)
        mask = sum(1 << v for v in chosen)
        require(all(c & mask for c in maximal_cliques(adj, n)), "some maximal clique is missed")
        sizes.append(len(chosen))
        total += len(chosen)
    return total, _report(sizes=sizes)


def _clique_partition(rows, n, edges):
    edge_set = set(edges)
    covered = set()
    for clique in sequence(rows, "cliques", 1, len(edges)):
        vs = sequence(clique, "clique", 2, n)
        for v in vs:
            integer(v, "vertex", 0, n-1)
        require(len(set(vs)) == len(vs), "clique vertices must be distinct")
        for a, b in combinations(vs, 2):
            e = (min(a, b), max(a, b))
            require(e in edge_set, "a listed clique uses a non-edge")
            require(e not in covered, "an edge is covered twice")
            covered.add(e)
    require(len(covered) == len(edge_set), "some edge is not covered")
    return len(rows)


def chordal_clique_partition(value, instances=CHORDAL_INSTANCES):
    total, counts = 0, []
    for (n, k, p, seed), rows in zip(instances, _per_instance(value, len(instances))):
        counts.append(_clique_partition(rows, n, split_graph(n, k, p, seed)))
        total += counts[-1]
    return total, _report(cliques=counts, conjectured_bound=[round(n*n/6, 1) for n, *_ in instances])


def dense_clique_partition(value, instances=DENSE_INSTANCES):
    total, counts = 0, []
    for (n, p, seed), rows in zip(instances, _per_instance(value, len(instances))):
        edges = random_graph(n, p, seed)
        counts.append(_clique_partition(rows, n, edges))
        total += counts[-1]
    return total, _report(cliques=counts, edges=[len(random_graph(n, p, s)) for n, p, s in instances])


def _proper(edges, colours):
    return all(colours[u] != colours[v] for u, v in edges)


def triangle_cycle_colouring(value, instances=TRIANGLE_CYCLE_INSTANCES):
    """3-colourings of cycle-plus-triangles graphs; the score counts properly coloured instances."""
    solved = []
    for (n, seed), row in zip(instances, _per_instance(value, len(instances))):
        solved.append(_proper(cycle_plus_triangles(n, seed), _colouring(row, n, 3)))
    return sum(solved), _report(solved=solved)


def list_colouring(value, instances=LIST_INSTANCES):
    """Colourings of planar bipartite quadrangulations from lists of three colours; counts solved instances."""
    solved = []
    for (splits, seed), row in zip(instances, _per_instance(value, len(instances))):
        n, edges, lists = planar_bipartite_lists(splits, seed)
        colours = _colouring(row, n, 5)
        solved.append(all(c in l for c, l in zip(colours, lists)) and _proper(edges, colours))
    return sum(solved), _report(solved=solved)


def sum_free_subsets(value, instances=SUM_FREE_INSTANCES):
    """Sum-free subsets (no a + b = c, a = b allowed) of fixed integer sets; maximize the total size."""
    total, sizes = 0, []
    for (size, seed), row in zip(instances, _per_instance(value, len(instances))):
        allowed = set(sum_free_instance(size, seed))
        chosen = int_set(row, "subset", -10000, 10000, 0, size)
        require(set(chosen) <= allowed, "the subset must come from the instance")
        members = set(chosen)
        require(not any(a+b in members for i, a in enumerate(chosen) for b in chosen[i:]), "the subset is not sum-free")
        sizes.append(len(chosen))
        total += len(chosen)
    return total, _report(sizes=sizes, one_third=[round(s/3, 2) for s, _ in instances])
