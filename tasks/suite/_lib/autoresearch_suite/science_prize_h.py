"""Independent exact verifiers for number-theory and additive-combinatorics constructions.

All scores are exact integer computations except the Mahler measure, which is
evaluated from polynomial roots after an exact test that the measure exceeds one.
Reference values and sources are in catalog/science/prize_h.json.
"""
from fractions import Fraction
from functools import lru_cache
from itertools import combinations
from math import factorial, gcd, isqrt, prod

from .runtime import require
from .science_prize import integer, sequence
from .science_prize_h_arithmetic import (  # noqa: F401 - re-exported for verifiers and group I
    is_prime,
    _pollard_brent,
    factor,
    divisor_count,
    primes_up_to,
    squarefree_table,
    int_set,
    run_certificate,
    _poly_divmod,
    cyclotomic,
    _roots,
)


def _report(**extra):
    return {"lean_verified": False, **extra}



def mahler_measure(value, max_degree=12, max_coefficient=3):
    coeffs = sequence(value, "coefficients (constant term first)", 2, max_degree+1)
    for c in coeffs:
        integer(c, "coefficient", -max_coefficient, max_coefficient)
    require(coeffs[-1] != 0, "leading coefficient must be nonzero")
    poly = list(coeffs)
    while poly[0] == 0:
        poly.pop(0)
    require(len(poly) >= 2, "polynomial must have a nonzero root")
    rest = list(poly)
    for m in range(1, 64):
        phi = cyclotomic(m)
        if len(phi)-1 > len(poly)-1:
            continue
        while len(rest) >= len(phi):
            q, r = _poly_divmod(rest, phi)
            if any(x != 0 for x in r) or any(Fraction(x).denominator != 1 for x in q):
                break
            rest = [int(x) for x in q]
    # Kronecker: an integer polynomial has measure one iff it is +-x^k times cyclotomic factors.
    require(not (len(rest) == 1 and abs(rest[0]) == 1), "measure equals one (product of cyclotomic polynomials)")
    measure = abs(poly[-1])*prod(max(1.0, abs(z)) for z in _roots(poly))
    return round(measure, 10), _report(degree=len(coeffs)-1, measure=measure)


# --- primes -------------------------------------------------------------------

def consecutive_prime_progression(value, bound=10**9):
    start, step, length = sequence(value, "[start prime, difference, length]", 3, 3)
    integer(start, "start", 2, bound)
    integer(step, "difference", 1, 5000)
    integer(length, "length", 2, 64)
    require(start+(length-1)*step <= bound, "progression exceeds the bound")
    terms = [start+i*step for i in range(length)]
    require(all(is_prime(t) for t in terms), "every term must be prime")
    for a, b in zip(terms, terms[1:]):
        require(not any(is_prime(x) for x in range(a+1, b)), "terms must be consecutive primes")
    return length, _report(first=start, difference=step, length=length)


def jacobsthal_cover(value, count=30):
    primes = primes_up_to(1000)[:count]
    residues = sequence(value, "one residue per prime", count, count)
    for r, p in zip(residues, primes):
        integer(r, f"residue modulo {p}", 0, p-1)
    length = 0
    while any((length+1-r) % p == 0 for r, p in zip(residues, primes)):
        length += 1
    return length, _report(primes=count, largest_prime=primes[-1], covered_length=length, jacobsthal=length+1)


def distinct_prime_gaps(value, bound=10**8):
    start, length = run_certificate(value, bound, 200)
    require(is_prime(start), "start must be prime")
    primes = [start]
    while len(primes) < length+1:
        x = primes[-1]+1
        while not is_prime(x):
            x += 1
        require(x <= bound, "primes exceed the bound")
        primes.append(x)
    gaps = [b-a for a, b in zip(primes, primes[1:])]
    require(len(set(gaps)) == len(gaps), "gaps must be pairwise distinct")
    return length, _report(first_prime=start, gaps=gaps)


def prime_cube_sums(value, bound=10**10):
    require(type(value) is dict and set(value) == {"N", "triples"}, "return keys N and triples only")
    n = integer(value["N"], "N", 1, bound)
    rows = sequence(value["triples"], "prime triples", 1, 100)
    seen = set()
    for row in rows:
        p, q, r = sequence(row, "triple", 3, 3)
        for x in (p, q, r):
            integer(x, "prime", 2, 3000)
            require(is_prime(x), "entries must be prime")
        require(p <= q <= r and p**3+q**3+r**3 == n, "triple must be sorted and sum to N")
        require((p, q, r) not in seen, "duplicate triple")
        seen.add((p, q, r))
    return len(seen), _report(N=n, representations=len(seen))


def prime_plus_power_of_two(value, bound=10**8):
    n = integer(value, "n", 3, bound)
    count = sum(1 for k in range(n.bit_length()) if n-(1 << k) >= 2 and is_prime(n-(1 << k)))
    return count, _report(n=n, representations=count)


# --- divisors, totients and powerful numbers --------------------------------

def divisor_count_run(value, bound=10**10):
    start, length = run_certificate(value, bound, 40)
    counts = [divisor_count(x) for x in range(start, start+length)]
    require(len(set(counts)) == length, "divisor counts must be pairwise distinct")
    return length, _report(start=start, divisor_counts=counts)


def powerful_between_squares(value, bound=10**9):
    k = integer(value, "k", 1, bound)
    low, high = k*k, (k+1)**2
    cube_limit = int(round(high**(1/3)))+2
    squarefree = squarefree_table(cube_limit)
    count = 0
    for b in range(1, cube_limit+1):
        c = b**3
        if c >= high:
            break
        if not squarefree[b]:
            continue
        a_min = isqrt(low//c)
        while a_min*a_min*c <= low:
            a_min += 1
        a_max = isqrt((high-1)//c)
        count += max(0, a_max-a_min+1)
    return count, _report(k=k, powerful_numbers=count)


def large_prime_factor_run(value, bound=10**4):
    start, length = run_certificate(value, bound+200, 200)
    require(start <= bound, "the run must start at most at the bound")
    for x in range(start, start+length):
        require(max(factor(x) or {1: 1}) > length, f"{x} has no prime factor larger than the run length")
    return length, _report(start=start, length=length)


def totient_preimages(m):
    divisors = [d for d in _divisors(m)]
    primes = sorted((d+1 for d in divisors if is_prime(d+1)), reverse=True)

    @lru_cache(maxsize=None)
    def count(n, i):
        total = 1 if n == 1 else 0
        for j in range(i, len(primes)):
            p = primes[j]
            if n % (p-1):
                continue
            rest = n//(p-1)
            while True:
                total += count(rest, j+1)
                if rest % p:
                    break
                rest //= p
        return total

    return count(m, 0)


def _divisors(n):
    divisors = [1]
    for p, e in factor(n).items():
        divisors = [d*p**k for d in divisors for k in range(e+1)]
    return sorted(divisors)


def inverse_totient_multiplicity(value, k=1000, maximum=10**8):
    m = integer(value, "m", 1, maximum)
    count = totient_preimages(m)
    require(count == k, f"phi(x) = m has {count} solutions, not {k}")
    return m, _report(m=m, solutions=count)


def sigma(n):
    return prod((p**(e+1)-1)//(p-1) for p, e in factor(n).items())


def k_sigma_k(value, bound=10**18, max_solutions=1000):
    """Certificate: M and distinct k with k*sigma(k) = M. Score = number of certified k (a lower bound for f(M))."""
    require(type(value) is dict and set(value) == {"M", "k"}, "return keys M and k only")
    m = integer(value["M"], "M", 1, bound)
    ks = int_set(value["k"], "k", 1, isqrt(m), 1, max_solutions)
    for k in ks:
        require(k*sigma(k) == m, f"{k}*sigma({k}) != M")
    return len(ks), _report(M=m, solutions=len(ks))


# --- factorials -----------------------------------------------------------------

def factorial_factorization_span(value, n=30):
    parts = sequence(value, "increasing factors", 2, n)
    for x in parts:
        integer(x, "factor", 1, factorial(n))
    require(all(a < b for a, b in zip(parts, parts[1:])), "factors must be strictly increasing")
    require(prod(parts) == factorial(n), f"product must equal {n}!")
    return parts[-1]-parts[0], _report(n=n, factors=len(parts), span=parts[-1]-parts[0])


# --- additive sets ------------------------------------------------------------------

def no_square_subset_sum(value, n=134):
    a = int_set(value, "set", 1, n, 1)
    reach = 1
    for x in a:
        reach |= reach << x
    squares = [s*s for s in range(1, isqrt(sum(a))+1)]
    require(not any(reach >> s & 1 for s in squares), "some nonempty subset sums to a square")
    return len(a), _report(size=len(a))


def sidon_squares(value, m=68):
    bases = int_set(value, "bases", 1, m, 1)
    sums = [x*x+y*y for i, x in enumerate(bases) for y in bases[i:]]
    require(len(sums) == len(set(sums)), "sums of two chosen squares must be distinct")
    return len(bases), _report(size=len(bases))


def squarefree_sumset(value, n=512):
    a = int_set(value, "set", 1, n, 1)
    table = squarefree_table(2*n)
    require(all(table[x+y] for i, x in enumerate(a) for y in a[i:]), "some sum a+b (a<=b) is not squarefree")
    return len(a), _report(size=len(a))


def one_repeated_sum(value, n=100):
    a = int_set(value, "set", 1, n, 1)
    counts = {}
    for i, x in enumerate(a):
        for y in a[i:]:
            counts[x+y] = counts.get(x+y, 0)+1
    repeated = [s for s, c in counts.items() if c > 1]
    require(len(repeated) <= 1, "more than one sum has several representations")
    return len(a), _report(size=len(a), repeated_sum=repeated[0] if repeated else None)


def no_divisor_of_two(value, n=44):
    a = int_set(value, "set", 1, n, 1)
    members = set(a)
    for x in a:
        require(sum(1 for y in range(2*x, n+1, x) if y in members) <= 1, f"{x} divides two other elements")
    return len(a), _report(size=len(a))


def sparse_ruler(value, n=200):
    marks = int_set(value, "marks", 0, n, 2)
    diffs = {b-a for i, a in enumerate(marks) for b in marks[i+1:]}
    require(all(d in diffs for d in range(1, n+1)), "every distance 1..n must be measured")
    return len(marks), _report(length=n, marks=len(marks))


def additive_basis(value, n=212):
    basis = int_set(value, "set", 0, n, 1)
    sums = {x+y for i, x in enumerate(basis) for y in basis[i:]}
    require(all(t in sums for t in range(n+1)), "every integer 0..n must be a sum of two elements")
    return len(basis), _report(n=n, size=len(basis))


def square_product_condition(value, n=200):
    a = int_set(value, "set", 1, n, 1)
    index = {p: i for i, p in enumerate(primes_up_to(n))}
    vectors = {}
    for x in a:
        mask = 0
        for p, e in factor(x).items():
            if e % 2:
                mask ^= 1 << index[p]
        vectors[x] = mask
    groups = {}
    for i, x in enumerate(a):
        for y in a[i:]:
            groups.setdefault(vectors[x] ^ vectors[y], []).append((x, y))
    for pairs in groups.values():
        for (x, y), (z, w) in combinations(pairs, 2):
            q = sorted((x, y, z, w))
            require(q[0]*q[3] == q[1]*q[2], f"{q} has square product but ad != bc")
        for x, y in pairs:   # the same pair used twice
            q = sorted((x, y, x, y))
            require(q[0]*q[3] == q[1]*q[2], f"{q} has square product but ad != bc")
    return len(a), _report(size=len(a))


def van_der_waerden(value, long_length=12, maximum=135):
    colours = sequence(value, "colours of 1..N", 1, maximum)
    for c in colours:
        integer(c, "colour", 0, 1)
    n = len(colours)
    for length, colour in ((3, 0), (long_length, 1)):
        for d in range(1, (n-1)//(length-1)+1):
            for a in range(n-(length-1)*d):
                require(not all(colours[a+i*d] == colour for i in range(length)),
                        f"colour {colour} contains a {length}-term progression")
    return n, _report(N=n, forbidden=[3, long_length])


def distinct_multiples(value, n=50):
    b = sequence(value, "multiples b_1..b_n", n, n)
    for i, x in enumerate(b, 1):
        integer(x, "multiple", n+1, 100*n)
        require(x % i == 0, f"b_{i} must be divisible by {i}")
    require(len(set(b)) == n, "multiples must be distinct")
    return max(b)-n+1, _report(n=n, interval_length=max(b)-n+1)


def primorial_gaps(value, count=10):
    modulus = prod(primes_up_to(100)[:count])
    rows = sequence(value, "gap certificates [x, g]", 1, 200)
    certified = set()
    for row in rows:
        x, g = sequence(row, "certificate", 2, 2)
        integer(x, "x", 1, modulus)
        integer(g, "gap", 2, 1000)
        require(gcd(x, modulus) == 1 and gcd(x+g, modulus) == 1, "endpoints must be coprime to the primorial")
        require(all(gcd(y, modulus) > 1 for y in range(x+1, x+g)), "endpoints must be consecutive reduced residues")
        certified.add(g)
    largest = 0
    while largest+2 in certified:
        largest += 2
    return largest, _report(primorial=modulus, certified_gaps=sorted(certified), largest_complete=largest)


def three_progression_differences(value, size=32, bound=512):
    a = int_set(value, "set", 1, bound, size, size)
    members = set(a)
    diffs = {d for i, x in enumerate(a) for y in a[i+1:] for d in [y-x] if y+d in members}
    return len(diffs), _report(size=size, distinct_differences=len(diffs))


def sidon_extension(value, n=284, seed=(1, 2, 5, 11)):
    a = int_set(value, "set", 1, n, len(seed))
    require(set(seed) <= set(a), "the prescribed Sidon seed must be contained")
    sums = [x+y for i, x in enumerate(a) for y in a[i:]]
    require(len(sums) == len(set(sums)), "set must be Sidon")
    return len(a), _report(size=len(a), seed=list(seed))


def unique_differences(value, covered=30, bound=10**6, maximum_size=32):
    """A finite Sidon set containing 0 whose differences include 1..covered; minimize its largest element."""
    a = int_set(value, "set", 0, bound, 2, maximum_size)
    require(a[0] == 0, "0 must be an element")
    diffs = [y-x for i, x in enumerate(a) for y in a[i+1:]]
    require(len(diffs) == len(set(diffs)), "every positive difference must occur at most once")
    present = set(diffs)
    require(all(d in present for d in range(1, covered+1)), f"every difference 1..{covered} must occur")
    return a[-1], _report(size=len(a), maximum=a[-1])


def smooth_after_prime_square(value, prime_bound=10**9, max_run=200):
    require(type(value) is dict and set(value) == {"p", "k"}, "return keys p and k only")
    p = integer(value["p"], "p", 2, prime_bound)
    k = integer(value["k"], "k", 1, max_run)
    require(is_prime(p), "p must be prime")
    for x in range(p*p+1, p*p+k+1):
        require(max(factor(x)) <= p, f"{x} has a prime factor larger than p")
    return k, _report(p=p, k=k)


# --- covering systems ---------------------------------------------------------------

def _classes(value, name, max_classes, modulus_check):
    rows = sequence(value, name, 1, max_classes)
    moduli = []
    out = []
    for row in rows:
        m, r = sequence(row, "[modulus, residue]", 2, 2)
        integer(m, "modulus", 2, 10**6)
        modulus_check(m)
        integer(r, "residue", 0, m-1)
        moduli.append(m)
        out.append((m, r))
    require(len(set(moduli)) == len(moduli), "moduli must be distinct")
    return out


def odd_covering(value, base=3**3*5**2*7*11):
    """Distinct odd moduli dividing base; score = residues modulo base left uncovered (0 = an odd covering)."""
    classes = _classes(value, "classes", 47, lambda m: require(m % 2 == 1 and base % m == 0, f"moduli must be odd divisors of {base}"))
    covered = bytearray(base)
    for m, r in classes:
        covered[r::m] = b"\x01"*len(range(r, base, m))
    uncovered = base-sum(covered)
    return uncovered, _report(classes=len(classes), uncovered=uncovered, period=base)


def _initial_run(counts, need):
    run = 0
    while run+1 < len(counts) and counts[run+1] >= need:
        run += 1
    return run


def double_prime_cover(value, largest_prime=1000, cap=100000):
    """One residue per prime up to the bound; score = longest initial interval [1, L] covered at least twice."""
    primes = primes_up_to(largest_prime)
    residues = sequence(value, "one residue per prime", len(primes), len(primes))
    counts = [0]*(cap+2)
    for r, p in zip(residues, primes):
        integer(r, f"residue modulo {p}", 0, p-1)
        for x in range(r or p, cap+2, p):
            counts[x] += 1
    length = _initial_run(counts, 2)
    return length, _report(primes=len(primes), doubly_covered_length=length, capped=length == cap)


def budget_prime_cover(value, largest_prime=1000, budget=Fraction(1), cap=100000):
    """Classes modulo distinct primes up to the bound with sum 1/p <= budget; score = covered initial length."""
    classes = _classes(value, "classes", 200, lambda m: require(m <= largest_prime and is_prime(m), "moduli must be primes up to the bound"))
    require(sum(Fraction(1, m) for m, _ in classes) <= budget, "sum of reciprocals of the moduli exceeds the budget")
    counts = bytearray(cap+2)
    for m, r in classes:
        counts[r or m::m] = b"\x01"*len(range(r or m, cap+2, m))
    length = _initial_run(counts, 1)
    return length, _report(classes=len(classes), covered_length=length, reciprocal_sum=str(sum(Fraction(1, m) for m, _ in classes)))


def disjoint_classes_mass(value, low=20, high=200):
    classes = _classes(value, "classes", high-low+1, lambda m: require(low <= m <= high, f"moduli must lie in [{low}, {high}]"))
    for (m1, r1), (m2, r2) in combinations(classes, 2):
        require((r1-r2) % gcd(m1, m2) != 0, "two residue classes intersect")
    mass = sum(Fraction(1, m) for m, _ in classes)
    return round(float(mass), 12), _report(classes=len(classes), reciprocal_sum=str(mass))


def two_cube_sums(value, bound=10**18):
    require(type(value) is dict and set(value) == {"m", "pairs"}, "return keys m and pairs only")
    m = integer(value["m"], "m", 2, bound)
    rows = sequence(value["pairs"], "pairs", 1, 100)
    seen = set()
    for row in rows:
        a, b = sequence(row, "pair", 2, 2)
        integer(a, "a", 1, 10**6)
        integer(b, "b", 1, 10**6)
        require(a <= b and a**3+b**3 == m, "pair must satisfy a <= b and a^3 + b^3 = m")
        require((a, b) not in seen, "duplicate pair")
        seen.add((a, b))
    return len(seen), _report(m=m, representations=len(seen))
