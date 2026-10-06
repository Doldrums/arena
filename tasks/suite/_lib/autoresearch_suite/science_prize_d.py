"""Independent finite verifiers for bank-derived mathematical constructions.

The sources, finite restrictions and mathematical credits are recorded per task.
No function claims formal verification or optimality of the supplied object.
"""
from collections import Counter
from functools import lru_cache
from itertools import combinations, product
from math import factorial, gcd, isqrt, lcm

from .runtime import require
from .science_prize import integer, sequence, prime


def distinct_integers(values, name, lower, upper, minimum=1, maximum=None):
    values = list(sequence(values, name, minimum, upper-lower+1 if maximum is None else maximum))
    for x in values:
        integer(x, name, lower, upper)
    require(len(set(values)) == len(values), name + " must be distinct")
    return values


def points(value, n, dimension, bound, minimum=None):
    rows = sequence(value, "points", n if minimum is None else minimum, n)
    result = []
    for row in rows:
        row = tuple(sequence(row, "coordinate row", dimension, dimension))
        for x in row:
            integer(x, "coordinate", -bound, bound)
        result.append(row)
    require(len(set(result)) == len(result), "points must be distinct")
    return result


def edges(value, n):
    rows = sequence(value, "edges", 0, n*(n-1)//2)
    result = set()
    for row in rows:
        u, v = sequence(row, "edge endpoints", 2, 2)
        integer(u, "vertex", 0, n-1)
        integer(v, "vertex", 0, n-1)
        require(u != v, "self-loops are forbidden")
        e = tuple(sorted((u, v)))
        require(e not in result, "duplicate undirected edge")
        result.add(e)
    return result


def factor(n):
    out, p = {}, 2
    while p*p <= n:
        while n % p == 0:
            out[p] = out.get(p, 0) + 1
            n //= p
        p = 3 if p == 2 else p+2
    if n > 1:
        out[n] = 1
    return out


def gaussian_path(value, bound=64, target=50):
    path = points(value, (2*bound+1)**2, 2, bound, minimum=2)
    require(path[0] == (1, 1), "path must start at 1+i")
    require(max(map(abs, path[-1])) >= target, "endpoint must reach target boundary")
    for x, y in path:
        if x*y:
            ok = prime(x*x+y*y)
        else:
            p = abs(x or y)
            ok = prime(p) and p % 4 == 3
        require(ok, "every vertex must be a Gaussian prime")
    steps = [(a-c)**2+(b-d)**2 for (a,b),(c,d) in zip(path, path[1:])]
    return max(steps), {"path_length": len(path), "maximum_squared_step": max(steps), "lean_verified": False}


def jacobsthal(value, maximum=1000000, prime_count=5):
    n = integer(value, "modulus", 2, maximum)
    factors = factor(n)
    require(len(factors) == prime_count and all(e == 1 for e in factors.values()),
            "modulus must be squarefree with the specified prime-factor count")
    # Adjacent units, including the last-to-first wrap, delimit every gap.
    first = previous = None
    longest = 0
    for a in range(n):
        if gcd(a, n) == 1:
            if first is None:
                first = a
            if previous is not None:
                longest = max(longest, a-previous-1)
            previous = a
    longest = max(longest, first+n-previous-1)
    return longest, {"modulus": n, "prime_factors": sorted(factors), "jacobsthal_function": longest+1, "lean_verified": False}


def pancyclic(value, n=40):
    require(type(value) is dict and set(value) == {"edges", "cycles"}, "return edges and cycles only")
    graph = edges(value["edges"], n)
    cycles = sequence(value["cycles"], "cycle certificates ordered by length", n-2, n-2)
    for length, row in enumerate(cycles, 3):
        cycle = distinct_integers(row, "cycle vertex", 0, n-1, length, length)
        require(all(tuple(sorted((u,v))) in graph for u,v in zip(cycle, cycle[1:]+cycle[:1])),
                "cycle certificate uses an absent edge")
    return len(graph)-n, {"vertices": n, "edges": len(graph), "certified_lengths": list(range(3,n+1)), "lean_verified": False}


def equal_area(value, n=30, bound=30):
    pts = points(value, n, 2, bound)
    counts = Counter()
    for (a,b),(c,d),(e,f) in combinations(pts,3):
        determinant = abs((c-a)*(f-b)-(d-b)*(e-a))
        if determinant:
            counts[determinant] += 1
    require(bool(counts), "at least one noncollinear triple is required")
    area, count = max(counts.items(), key=lambda x: (x[1], -x[0]))
    return count, {"twice_area": area, "triangle_count": count, "lean_verified": False}


@lru_cache(maxsize=8)
def projective_plane(q):
    require(prime(q), "prime field order required")
    # Unique representatives: the first nonzero coordinate equals one.
    pts = [(1,x,y) for x in range(q) for y in range(q)] + [(0,1,x) for x in range(q)] + [(0,0,1)]
    lines = [tuple(i for i,p in enumerate(pts) if sum(a*b for a,b in zip(p,l)) % q == 0) for l in pts]
    return tuple(pts), tuple(lines)


def blocking_set(value, q=7):
    pts, lines = projective_plane(q)
    selected = set(distinct_integers(value, "projective point index", 0, len(pts)-1))
    intersections = [len(selected.intersection(line)) for line in lines]
    require(min(intersections) >= 1, "every projective line must meet the set")
    return max(intersections), {"size":len(selected), "line_intersections":intersections, "lean_verified": False}


def transitive_tournament(value, n=20):
    colors = sequence(value, "upper-triangle orientations", n*(n-1)//2, n*(n-1)//2)
    outgoing = [0]*n
    for (u,v), bit in zip(combinations(range(n),2), colors):
        integer(bit, "orientation", 0, 1)
        a,b = (u,v) if bit == 0 else (v,u)
        outgoing[a] |= 1 << b

    @lru_cache(maxsize=None)
    def best(mask):
        if not mask:
            return 0
        result, rest = 0, mask
        while rest:
            bit = rest & -rest
            v = bit.bit_length()-1
            # Every transitive tournament has a unique source. Removing it
            # leaves a transitive tournament among its out-neighbors.
            result = max(result, 1+best(mask & outgoing[v]))
            rest ^= bit
        return result

    size = best((1 << n)-1)
    return size, {"vertices":n, "largest_transitive_order":size, "subproblems":best.cache_info().currsize, "lean_verified":False}


def prime_primitive_roots(value, moduli, maximum=100000):
    roots = sequence(value, "prime roots in modulus order", len(moduli), len(moduli))
    for g,p in zip(roots,moduli):
        integer(g,"prime root",2,maximum)
        require(prime(p),"modulus must be prime")
        require(prime(g) and gcd(g,p)==1,"root must be a prime coprime to the modulus")
        require(all(pow(g,(p-1)//q,p)!=1 for q in factor(p-1)),"root has smaller multiplicative order")
    return sum(roots), {"roots":list(roots),"moduli":moduli,"lean_verified":False}


@lru_cache(maxsize=2)
def farey(order):
    out=[(0,1)]
    a,b,c,d=0,1,1,order
    while c<=order:
        out.append((c,d))
        k=(order+b)//d
        a,b,c,d=c,d,k*c-a,k*d-b
    return tuple(out)


def opposite_farey_pair(value, order=1000):
    pair=sequence(value,"two reduced Farey fractions",2,2)
    rows=[]
    for row in pair:
        a,b=sequence(row,"numerator denominator",2,2)
        integer(a,"numerator",0,order)
        integer(b,"denominator",1,order)
        require(a<=b and gcd(a,b)==1,"fractions must be reduced and in [0,1]")
        rows.append((a,b))
    (a,b),(c,d)=rows
    require(a*d<c*b,"fractions must be in increasing numerical order")
    require((c-a)*(d-b)<0,"numerator and denominator must change in opposite directions")
    series=farey(order)
    i,j=series.index((a,b)),series.index((c,d))
    return j-i, {"rank_difference":j-i,"first_rank":i,"second_rank":j,"lean_verified":False}


def rainbow_c4_avoidance(value,n=16):
    colors=sequence(value,"upper-triangle colors",n*(n-1)//2,n*(n-1)//2)
    matrix=[[0]*n for _ in range(n)]
    for (u,w),c in zip(combinations(range(n),2),colors):
        integer(c,"color",0,n*(n-1)//2-1)
        matrix[u][w]=matrix[w][u]=c
    for a,b,c,d in combinations(range(n),4):
        for cycle in [(a,b,c,d),(a,b,d,c),(a,c,b,d)]:
            palette={matrix[u][w] for u,w in zip(cycle,cycle[1:]+cycle[:1])}
            require(len(palette)<4,"a rainbow four-cycle exists")
    return len(set(colors)), {"used_colors":len(set(colors)),"lean_verified":False}


@lru_cache(maxsize=5)
def permutation_orders(n):
    counts=Counter()

    def partitions(remaining,minimum,parts):
        if remaining==0:
            multiplicities=Counter(parts)
            divisor=1
            order=1
            for length,multiplicity in multiplicities.items():
                divisor*=length**multiplicity*factorial(multiplicity)
                order=lcm(order,length)
            counts[order]+=factorial(n)//divisor
            return
        for length in range(minimum,remaining+1):
            partitions(remaining-length,length,parts+(length,))
    partitions(n,1,())
    return dict(counts)


def frequent_permutation_order(value,n=16):
    k=integer(value,"permutation order",1,factorial(n))
    count=permutation_orders(n).get(k,0)
    require(count>0,"no permutation of this degree has the proposed order")
    return count,{"order":k,"permutation_count":count,"degree":n,"lean_verified":False}


def modular_inverse_cover(value,p=101,interval=10):
    rows=sequence(value,"representations in residue order",p,p)
    lengths=[]
    for target,row in enumerate(rows):
        denominators=distinct_integers(row,"denominator",1,interval,1,interval)
        require(sum(pow(x,-1,p) for x in denominators)%p==target,"incorrect modular inverse sum")
        lengths.append(len(denominators))
    return max(lengths),{"modulus":p,"covered_residues":p,"maximum_terms":max(lengths),"lean_verified":False}
