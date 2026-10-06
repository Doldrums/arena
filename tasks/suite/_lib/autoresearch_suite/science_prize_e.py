"""Independent exact verifiers for Ramsey-type and colouring constructions.

Every function checks a finite certificate: a graph, an edge colouring, a
coloured triple system or a tournament. Scores are construction sizes or exact
extremal counts. Published bounds and their sources are recorded per task in
catalog/science/prize_e.json; nothing here is a Lean proof or an optimality
proof for the supplied object.
"""
from itertools import combinations

from .runtime import require
from .science_prize import integer, sequence


# --- input parsing ----------------------------------------------------------

def graph(value, max_vertices, min_vertices=1):
    """Parse {"n": n, "edges": [[u, v], ...]} into adjacency bitmasks."""
    require(type(value) is dict and set(value) == {"n", "edges"}, "return a dictionary with keys n and edges only")
    n = integer(value["n"], "n", min_vertices, max_vertices)
    rows = sequence(value["edges"], "edges", 0, n*(n-1)//2)
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
    return n, adj


def coloring(value, colors, max_vertices, min_vertices=1):
    """Parse {"n": n, "colors": [...]} (pairs i<j in lexicographic order)."""
    require(type(value) is dict and set(value) == {"n", "colors"}, "return a dictionary with keys n and colors only")
    n = integer(value["n"], "n", min_vertices, max_vertices)
    labels = sequence(value["colors"], "edge colours", n*(n-1)//2, n*(n-1)//2)
    classes = [[0]*n for _ in range(colors)]
    for (u, v), c in zip(combinations(range(n), 2), labels):
        integer(c, "colour", 0, colors-1)
        classes[c][u] |= 1 << v
        classes[c][v] |= 1 << u
    return n, classes


def complement(adj, n):
    full = (1 << n)-1
    return [full & ~a & ~(1 << v) for v, a in enumerate(adj)]


# --- exact subgraph searches ------------------------------------------------

def _colour_order(adj, candidates):
    """Greedy colour classes; the colour of each vertex bounds any clique."""
    order, bounds, colour, rest = [], [], 0, candidates
    while rest:
        colour += 1
        queue = rest
        while queue:
            bit = queue & -queue
            v = bit.bit_length()-1
            queue &= ~adj[v] & ~bit
            rest &= ~bit
            order.append(v)
            bounds.append(colour)
    return order, bounds


def has_clique(adj, k, candidates=None):
    """Branch and bound with colouring bounds (Tomita-style)."""
    if candidates is None:
        candidates = (1 << len(adj))-1
    if k <= 0:
        return True
    if candidates.bit_count() < k:
        return False
    if k == 1:
        return True
    order, bounds = _colour_order(adj, candidates)
    for i in range(len(order)-1, -1, -1):
        if bounds[i] < k:
            return False
        v = order[i]
        if has_clique(adj, k-1, candidates & adj[v]):
            return True
        candidates &= ~(1 << v)
    return False


def has_independent_set(adj, k, candidates=None):
    """Exact branching with the standard degree-at-most-one reduction."""
    if candidates is None:
        candidates = (1 << len(adj))-1
    while True:
        if k <= 0:
            return True
        if candidates.bit_count() < k:
            return False
        low, best, best_degree, rest = -1, -1, -1, candidates
        while rest:
            bit = rest & -rest
            v = bit.bit_length()-1
            rest ^= bit
            d = (adj[v] & candidates).bit_count()
            if d <= 1:
                low = v
                break
            if d > best_degree:
                best, best_degree = v, d
        if low < 0:
            break
        # A vertex of degree at most one lies in some maximum independent set.
        candidates &= ~adj[low] & ~(1 << low)
        k -= 1
    if has_independent_set(adj, k-1, candidates & ~adj[best] & ~(1 << best)):
        return True
    return has_independent_set(adj, k, candidates & ~(1 << best))


def triangle_free(adj):
    return all(not (adj[u] & adj[v]) for u in range(len(adj)) for v in _bits(adj[u]) if v > u)


def c4_free(adj):
    n = len(adj)
    return all((adj[u] & adj[v]).bit_count() <= 1 for u in range(n) for v in range(u+1, n))


def _bits(mask):
    while mask:
        bit = mask & -mask
        yield bit.bit_length()-1
        mask ^= bit


def has_cycle(adj, length):
    """Exact search for a (not necessarily induced) cycle of the given length."""
    n = len(adj)
    for start in range(n):
        allowed = ((1 << n)-1) & ~((1 << (start+1))-1)   # vertices larger than start

        def extend(v, depth, used):
            if depth == length:
                return bool(adj[v] >> start & 1)
            for w in _bits(adj[v] & allowed & ~used):
                if extend(w, depth+1, used | (1 << w)):
                    return True
            return False

        for w in _bits(adj[start] & allowed):
            if extend(w, 2, (1 << start) | (1 << w)):
                return True
    return False


def has_octahedron(adj):
    """K_{2,2,2}: some pair {a,b} whose common neighbourhood contains a C4."""
    n = len(adj)
    for a in range(n):
        for b in range(a+1, n):
            common = adj[a] & adj[b]
            if common.bit_count() < 4:
                continue
            for c in _bits(common):
                for d in _bits(common & ~((1 << (c+1))-1)):
                    if (common & adj[c] & adj[d]).bit_count() >= 2:
                        return True
    return False


def has_cube(adj):
    """Q3: a vertex x, three neighbours, three pairwise second neighbours, one opposite vertex."""
    n = len(adj)
    for x in range(n):
        nx = list(_bits(adj[x]))
        for p, q, r in combinations(nx, 3):
            base = (1 << x) | (1 << p) | (1 << q) | (1 << r)
            pq = (adj[p] & adj[q]) & ~base
            pr = (adj[p] & adj[r]) & ~base
            qr = (adj[q] & adj[r]) & ~base
            for a in _bits(pq):
                for b in _bits(pr & ~(1 << a)):
                    for c in _bits(qr & ~(1 << a) & ~(1 << b)):
                        used = base | (1 << a) | (1 << b) | (1 << c)
                        if adj[a] & adj[b] & adj[c] & ~used:
                            return True
    return False


def _report(n, **extra):
    return {"vertices": n, "lean_verified": False, **extra}


# --- two-colour classical and graph Ramsey constructions --------------------

def ramsey_graph(value, clique, independent, max_vertices):
    """Graph with no K_clique and no independent set of size `independent`."""
    n, adj = graph(value, max_vertices)
    require(not has_clique(adj, clique), f"graph contains K{clique}")
    require(not has_independent_set(adj, independent), f"graph has an independent set of size {independent}")
    edges = sum(a.bit_count() for a in adj)//2
    return n, _report(n, edges=edges, certifies=f"R({clique},{independent}) > {n}")


def c4_clique_ramsey(value, independent=11, max_vertices=43):
    n, adj = graph(value, max_vertices)
    require(c4_free(adj), "graph contains a four-cycle")
    require(not has_independent_set(adj, independent), f"graph has an independent set of size {independent}")
    return n, _report(n, edges=sum(a.bit_count() for a in adj)//2, certifies=f"R(C4,K{independent}) > {n}")


def c4_star_ramsey(value, star=39, max_vertices=47):
    n, adj = graph(value, max_vertices)
    require(c4_free(adj), "graph contains a four-cycle")
    minimum = min(a.bit_count() for a in adj)
    # The complement avoids K_{1,star} iff every complement degree is below `star`.
    require(minimum >= n-star, f"minimum degree must be at least n-{star}")
    return n, _report(n, minimum_degree=minimum, certifies=f"R(C4,K1,{star}) > {n}")


def triangle_triangle_clique(value, clique=4, max_vertices=30):
    n, (first, second, third) = coloring(value, 3, max_vertices)
    require(triangle_free(first), "colour 0 contains a triangle")
    require(triangle_free(second), "colour 1 contains a triangle")
    require(not has_clique(third, clique), f"colour 2 contains K{clique}")
    return n, _report(n, certifies=f"R(3,3,{clique}) > {n}")


def multicolor_triangle(value, colors=4, max_vertices=62):
    n, classes = coloring(value, colors, max_vertices)
    for c, adj in enumerate(classes):
        require(triangle_free(adj), f"colour {c} contains a triangle")
    return n, _report(n, certifies=f"R_{colors}(3) > {n}")


def multicolor_cycle(value, colors, length, max_vertices):
    n, classes = coloring(value, colors, max_vertices)
    for c, adj in enumerate(classes):
        if length == 4:
            require(c4_free(adj), f"colour {c} contains a four-cycle")
        else:
            require(not has_cycle(adj, length), f"colour {c} contains C{length}")
    return n, _report(n, certifies=f"R_{colors}(C{length}) > {n}")


def octahedron_ramsey(value, max_vertices=31):
    n, (red, blue) = coloring(value, 2, max_vertices)
    require(not has_octahedron(red), "colour 0 contains K2,2,2")
    require(not has_octahedron(blue), "colour 1 contains K2,2,2")
    return n, _report(n, certifies=f"R(K2,2,2,K2,2,2) > {n}")


def cube_ramsey(value, max_vertices=13):
    n, (red, blue) = coloring(value, 2, max_vertices)
    require(not has_cube(red), "colour 0 contains Q3")
    require(not has_cube(blue), "colour 1 contains Q3")
    return n, _report(n, certifies=f"R(Q3,Q3) > {n}")


# --- hypergraph Ramsey -------------------------------------------------------

def triple_ramsey(value, red_clique=4, blue_clique=5, max_vertices=40):
    """2-colouring of all triples; no red K4^(3) and no blue K5^(3)."""
    require(type(value) is dict and set(value) == {"n", "colors"}, "return a dictionary with keys n and colors only")
    n = integer(value["n"], "n", 1, max_vertices)
    labels = sequence(value["colors"], "triple colours", n*(n-1)*(n-2)//6, n*(n-1)*(n-2)//6)
    red = [[0]*n for _ in range(n)]
    blue = [[0]*n for _ in range(n)]
    for (a, b, c), colour in zip(combinations(range(n), 3), labels):
        integer(colour, "triple colour", 0, 1)
        target = red if colour == 0 else blue
        for x, y, z in ((a, b, c), (a, c, b), (b, c, a)):
            target[x][y] |= 1 << z
            target[y][x] |= 1 << z

    def monochromatic(link, size):
        # link[x][y] = third vertices z with xyz of this colour
        def grow(chosen, candidates):
            if len(chosen) == size:
                return True
            for w in _bits(candidates):
                rest = candidates & ~((1 << (w+1))-1)
                for x in chosen:
                    rest &= link[x][w]
                if len(chosen)+1+rest.bit_count() >= size and grow(chosen+[w], rest):
                    return True
            return False

        for a in range(n):
            for b in range(a+1, n):
                if grow([a, b], link[a][b] & ~((1 << (b+1))-1)):
                    return True
        return False

    require(not monochromatic(red, red_clique), f"colour 0 contains K{red_clique}^(3)")
    require(not monochromatic(blue, blue_clique), f"colour 1 contains K{blue_clique}^(3)")
    return n, _report(n, certifies=f"R({red_clique},{blue_clique};3) > {n}")


# --- tournaments -------------------------------------------------------------

def schutte_tournament(value, k=4, max_vertices=90):
    """Tournament in which every k vertices are dominated by another vertex."""
    require(type(value) is dict and set(value) == {"n", "orientation"}, "return a dictionary with keys n and orientation only")
    n = integer(value["n"], "n", k+1, max_vertices)
    bits = sequence(value["orientation"], "pair orientations", n*(n-1)//2, n*(n-1)//2)
    dominators = [0]*n   # dominators[v] = vertices with an arc into v
    for (u, v), bit in zip(combinations(range(n), 2), bits):
        integer(bit, "orientation", 0, 1)
        if bit == 0:
            dominators[v] |= 1 << u
        else:
            dominators[u] |= 1 << v

    def covered(start, depth, common):
        if depth == k:
            return common != 0
        for v in range(start, n):
            if not covered(v+1, depth+1, common & dominators[v]):
                return False
        return True

    require(covered(0, 0, (1 << n)-1), f"some {k} vertices have no common dominator")
    return n, _report(n, property=f"S_{k}")


# --- chromatic and packing extremal problems --------------------------------

def four_colourable(adj):
    """Exact 4-colourability by DSATUR-ordered backtracking."""
    n = len(adj)
    colour = [-1]*n

    def place(coloured, used_colours):
        if coloured == n:
            return True
        # most saturated uncoloured vertex, ties broken by degree
        best, key = -1, None
        for v in range(n):
            if colour[v] < 0:
                seen = {colour[w] for w in _bits(adj[v]) if colour[w] >= 0}
                k = (len(seen), adj[v].bit_count())
                if key is None or k > key:
                    best, key, blocked = v, k, seen
        for c in range(min(4, used_colours+1)):   # a new colour only in order
            if c not in blocked:
                colour[best] = c
                if place(coloured+1, max(used_colours, c+1)):
                    return True
        colour[best] = -1
        return False

    return place(0, 0)


def triangle_free_five_chromatic(value, max_vertices=23):
    n, adj = graph(value, max_vertices)
    require(triangle_free(adj), "graph contains a triangle")
    require(not four_colourable(adj), "graph is 4-colourable")
    return n, _report(n, edges=sum(a.bit_count() for a in adj)//2, chromatic_number_at_least=5)


def triangle_packing(adj, n):
    """Maximum number of edge-disjoint triangles, by exact branch and bound.

    The bound uses that uncovered edges keep each vertex degree's parity and
    that their number is congruent to the free edge count modulo three.
    """
    edges = [(u, v) for u in range(n) for v in _bits(adj[u]) if v > u]
    index = {e: i for i, e in enumerate(edges)}
    triangles = {}
    for u, v in edges:
        for w in _bits(adj[u] & adj[v]):
            if w > v:
                mask = (1 << index[(u, v)]) | (1 << index[(u, w)]) | (1 << index[(v, w)])
                for e in ((u, v), (u, w), (v, w)):
                    triangles.setdefault(index[e], []).append(mask)
    incident = [0]*n
    for i, (u, v) in enumerate(edges):
        incident[u] |= 1 << i
        incident[v] |= 1 << i
    best = 0

    def bound(free):
        m = free.bit_count()
        odd = sum((free & incident[x]).bit_count() & 1 for x in range(n))
        leave = odd//2
        # an even-degree leave has zero or at least three edges
        while (m-leave) % 3 or (odd == 0 and leave in (1, 2)):
            leave += 1
        return (m-leave)//3

    def search(free, count):
        nonlocal best
        best = max(best, count)
        if count + bound(free) <= best:
            return
        # the lowest remaining edge lies in a chosen triangle or is left uncovered
        while free:
            bit = free & -free
            options = [m for m in triangles.get(bit.bit_length()-1, ()) if m & free == m]
            if options:
                break
            free ^= bit
        if not free:
            return
        for m in options:
            search(free & ~m, count+1)
        search(free & ~bit, count)

    search((1 << len(edges))-1, 0)
    return best


def monochromatic_triangle_packing(value, n=11):
    m, (red, blue) = coloring(value, 2, n, n)
    red_packing = triangle_packing(red, m)
    blue_packing = triangle_packing(blue, m)
    total = red_packing+blue_packing
    return total, _report(m, red_triangles=red_packing, blue_triangles=blue_packing, edge_disjoint_monochromatic_triangles=total)


def no_large_regular_induced(value, size=6, max_vertices=22):
    """Every vertex subset of at least `size` vertices must induce a non-regular graph."""
    n, adj = graph(value, max_vertices)
    for mask in range(1, 1 << n):
        if mask.bit_count() < size:
            continue
        first = (mask & -mask).bit_length()-1
        degree = (adj[first] & mask).bit_count()
        rest = mask & (mask-1)
        while rest:
            bit = rest & -rest
            if (adj[bit.bit_length()-1] & mask).bit_count() != degree:
                break
            rest ^= bit
        else:
            members = [v for v in range(n) if mask >> v & 1]
            require(False, f"vertices {members} induce a {degree}-regular subgraph")
    return n, _report(n, largest_allowed_regular_order=size-1)


def four_clique_colour_count(value, n=16):
    """Erdős–Gyárfás f(n,4,5): every K4 must see at least five colours."""
    labels = sequence(value, "edge colours", n*(n-1)//2, n*(n-1)//2)
    colour = {}
    for (u, v), c in zip(combinations(range(n), 2), labels):
        integer(c, "colour", 0, n*(n-1)//2-1)
        colour[(u, v)] = c
    for quad in combinations(range(n), 4):
        palette = {colour[p] for p in combinations(quad, 2)}
        require(len(palette) >= 5, "some K4 receives fewer than five colours")
    used = len(set(labels))
    return used, {"vertices": n, "colours": used, "lean_verified": False}


def monochromatic_progressions(value, n=256, length=4):
    bits = sequence(value, "two-colouring of 1..n", n, n)
    for b in bits:
        integer(b, "colour", 0, 1)
    count = 0
    for d in range(1, (n-1)//(length-1)+1):
        for a in range(n-(length-1)*d):
            first = bits[a]
            if all(bits[a+i*d] == first for i in range(1, length)):
                count += 1
    return count, {"n": n, "length": length, "monochromatic_progressions": count, "lean_verified": False}

