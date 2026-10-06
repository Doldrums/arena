"""Exact finite adaptations of independently sourced number-theory problems.

The mathematical objectives and scope restrictions are recorded per task in
catalog/science/prize_b.json. No upstream program is reused here.
"""
from fractions import Fraction
from itertools import combinations
from math import factorial, gcd, isqrt, lcm

from .runtime import require


def integer(value, name, lower, upper):
    require(type(value) is int, f"{name} must be an integer, not bool/float")
    require(lower <= value <= upper, f"{name} outside [{lower},{upper}]")
    return value


def sequence(value, name, lower, upper):
    require(type(value) in (list, tuple), f"{name} must be a list or tuple")
    require(lower <= len(value) <= upper, f"{name} has invalid length")
    return list(value)


def int_set(value, n, lower=1, max_size=None):
    values = sequence(value, "set", 1, n if max_size is None else max_size)
    for x in values:
        integer(x, "element", lower, n)
    require(len(set(values)) == len(values), "elements must be distinct")
    return sorted(values)


def rational_result(value, **details):
    return float(value), {"exact_numerator": value.numerator,
                          "exact_denominator": value.denominator, **details}


def factors(n):
    """Trial division; all public task inputs are capped at 10**7."""
    result = {}
    d = 2
    while d * d <= n:
        while n % d == 0:
            result[d] = result.get(d, 0) + 1
            n //= d
        d += 1 if d == 2 else 2
    if n > 1:
        result[n] = 1
    return result


def egyptian_long(values, threshold=4, maximum=10**7):
    values = int_set(values, maximum, threshold + 1, 256)
    require(sum((Fraction(1, x) for x in values), Fraction()) == 1,
            "unit fractions must sum exactly to one")
    return len(values), {"largest_denominator": max(values)}


def reciprocal_subset_free(values, n=24):
    values = int_set(values, n)
    scale = lcm(*values)
    weights = [scale // x for x in values]
    for i, target in enumerate(weights):
        reached = {0}
        for j, w in enumerate(weights):
            if j != i:
                reached |= {v + w for v in reached if v + w <= target}
                require(target not in reached, "a reciprocal is a subsum of the others")
    return len(values), {"common_denominator": scale}


def reciprocal_schur_free(values, n=180):
    values = int_set(values, n)
    selected = set(values)
    for b, c in combinations(values, 2):
        product, total = b * c, b + c
        require(product % total or product // total not in selected,
                "three distinct reciprocals satisfy 1/a = 1/b + 1/c")
    return len(values), {"distinct_operands": True}


def egyptian_maximum(values, numerator=5, denominator=31, maximum=10**7):
    values = int_set(values, maximum, 1, 256)
    require(sum((Fraction(1, x) for x in values), Fraction()) == Fraction(numerator, denominator),
            "wrong rational sum")
    return max(values), {"terms": len(values)}


def unit_fraction_packing(indices, denominators=None):
    denominators = list(range(2, 49)) if denominators is None else denominators
    indices = int_set(indices, len(denominators) - 1, 0, len(denominators))
    value = sum((Fraction(1, denominators[i]) for i in indices), Fraction())
    require(value < 1, "subsum must be strictly below one")
    return rational_result(1 - value, selected_denominators=[denominators[i] for i in indices])


def signed_harmonic(coefficients, n=30):
    coefficients = sequence(coefficients, "coefficients", n, n)
    for x in coefficients:
        integer(x, "coefficient", -1, 1)
    scale = lcm(*range(1, n + 1))
    numerator = sum(x * (scale // i) for i, x in enumerate(coefficients, 1))
    require(numerator != 0, "zero is excluded from the approximation problem")
    return rational_result(Fraction(abs(numerator), scale), signed_numerator=numerator,
                           common_denominator=scale)


def dissociated_reciprocals(values, n=22):
    values = int_set(values, n)
    scale = lcm(*values)
    reached = {0}
    for x in values:
        added = {v + scale // x for v in reached}
        require(reached.isdisjoint(added), "different subsets have the same reciprocal sum")
        reached |= added
    return len(values), {"distinct_subset_sums": len(reached)}


def pair_sum_nondivisibility(values, n=256):
    values = int_set(values, n)
    require(all((a * b) % (a + b) for a, b in combinations(values, 2)),
            "the sum of a distinct pair divides its product")
    return len(values), {}


def unique_interval_sums(values, n=256):
    values = sequence(values, "increasing sequence", 1, n)
    for x in values:
        integer(x, "element", 1, n)
    require(all(a < b for a, b in zip(values, values[1:])), "sequence must increase strictly")
    seen = set()
    for i in range(len(values)):
        total = 0
        for x in values[i:]:
            total += x
            require(total not in seen, "distinct consecutive blocks have equal sums")
            seen.add(total)
    return len(values), {"distinct_interval_sums": len(seen)}


def target_subsum_free(values, n=100, target=200):
    values = int_set(values, n)
    reachable = 1
    mask = (1 << (target + 1)) - 1
    for x in values:
        reachable = (reachable | (reachable << x)) & mask
        require(not (reachable >> target) & 1, "target is a subset sum")
    return len(values), {"target": target}


def powerful_parts(n, lower=10000, upper=1000000):
    n = integer(n, "n", lower, upper)
    rows = [factors(n), factors(n + 1)]
    parts = []
    for row in rows:
        part = 1
        for p, e in row.items():
            if e >= 2:
                part *= p**e
        parts.append(part)
    return parts[0] * parts[1], {"powerful_parts": parts, "factorizations": rows}


def smooth_adjacent(n, lower=10000, upper=1000000):
    n = integer(n, "n", lower, upper)
    rows = [factors(n), factors(n + 1)]
    return max(max(row, default=1) for row in rows), {"factorizations": rows}


def factorial_valuation(values, n=32, p=2, first=2):
    values = int_set(values, n, first)
    require(values[0] == first, "smallest factorial index must be the prescribed first index")
    total = sum(factorial(x) for x in values)
    reduced, valuation = total, 0
    while reduced % p == 0:
        reduced //= p
        valuation += 1
    return valuation, {"sum": total, "prime": p, "remaining_cofactor": reduced}


def unique_block_products(values, n=128):
    values = sequence(values, "increasing sequence", 1, n - 1)
    for x in values:
        integer(x, "element", 2, n)
    require(all(a < b for a, b in zip(values, values[1:])), "sequence must increase strictly")
    seen = set()
    for i in range(len(values)):
        product = 1
        for x in values[i:]:
            product *= x
            require(product not in seen, "different consecutive blocks have the same product")
            seen.add(product)
    return len(values), {"distinct_block_products": len(seen)}


def square_sum_free(values, n=256):
    values = int_set(values, n)
    for i, a in enumerate(values):
        for b in values[i:]:
            require(isqrt(a + b)**2 != a + b, "a pair sum is a square (diagonals included)")
    return len(values), {"diagonal_pairs_included": True}


def bounded_lcm(values, n=512):
    values = int_set(values, n)
    require(all(lcm(a, b) <= n for a, b in combinations(values, 2)), "pair lcm exceeds bound")
    return len(values), {}


def convex_primes(values, n=10000):
    values = sequence(values, "prime sequence", 1, n)
    for x in values:
        integer(x, "prime", 2, n)
        require(factors(x) == {x: 1}, "sequence contains a composite")
    gaps = [b - a for a, b in zip(values, values[1:])]
    require(all(g > 0 for g in gaps), "primes must increase strictly")
    require(all(a <= b for a, b in zip(gaps, gaps[1:])), "gaps must be nondecreasing")
    return len(values), {"gaps": gaps}


def totient_multiple(n, modulus=120, maximum=1000000):
    n = integer(n, "n", 1, maximum)
    value = n
    for p in factors(n):
        value = value // p * (p - 1)
    require(value % modulus == 0, "totient not divisible by prescribed modulus")
    return n, {"totient": value, "modulus": modulus}


def smooth_parts(n, lower=1000, upper=1000000, length=24):
    n = integer(n, "n", lower, upper)
    # Source uses the prime factors STRICTLY BELOW the interval length.
    primes = [p for p in range(2, length) if factors(p) == {p: 1}]
    parts = []
    for x in range(n + 1, n + length + 1):
        rest = x
        for p in primes:
            while rest % p == 0:
                rest //= p
        parts.append(x // rest)
    return len(set(parts)), {"smooth_parts": parts, "prime_bound_exclusive": length}


def sparse_polynomial_square(coefficients, terms=12, degree=40, coefficient_bound=64):
    coefficients = sequence(coefficients, "coefficients in ascending degree", 1, degree + 1)
    for x in coefficients:
        integer(x, "coefficient", -coefficient_bound, coefficient_bound)
    require(coefficients[-1] != 0, "no trailing zero coefficient")
    require(sum(x != 0 for x in coefficients) == terms, "wrong number of nonzero input terms")
    result = [0] * (2 * len(coefficients) - 1)
    for i, a in enumerate(coefficients):
        for j, b in enumerate(coefficients):
            result[i + j] += a * b
    return sum(x != 0 for x in result), {"square_coefficients": result}


def sidon_obstruction(values, size=12, bound=128):
    values = int_set(values, bound, 0, size)
    require(len(values) == size, "ambient set has wrong cardinality")
    for k in range(size, 0, -1):
        for subset in combinations(values, k):
            sums = [a + b for i, a in enumerate(subset) for b in subset[i:]]
            if len(set(sums)) == len(sums):
                return k, {"maximum_sidon_subset": list(subset), "diagonals_included": True}
    raise AssertionError("a singleton is always Sidon")


def noncoprime_forced(values, n=255, forced=255):
    values = int_set(values, n)
    require(forced in values, "prescribed element missing")
    require(all(gcd(a, b) > 1 for a, b in combinations(values, 2)), "coprime pair exists")
    return len(values), {"forced_element": forced}


def equal_gcd_free(values, n=128, clique_size=3):
    values = int_set(values, n)
    for subset in combinations(values, clique_size):
        require(len({gcd(a, b) for a, b in combinations(subset, 2)}) > 1,
                "a prescribed-size subset has equal pairwise gcds")
    return len(values), {"forbidden_clique_size": clique_size}


def equal_lcm_free(values, n=128):
    values = int_set(values, n)
    for a, b, c in combinations(values, 3):
        require(not (lcm(a, b) == lcm(a, c) == lcm(b, c)), "equal-lcm triple exists")
    return len(values), {}


def lcm_reciprocal_weight(values, n=256):
    values = int_set(values, n, 2)
    require(all(lcm(a, b) > n for a, b in combinations(values, 2)), "pair lcm not above interval")
    return rational_result(sum((Fraction(1, x) for x in values), Fraction()),
                           cardinality=len(values))


def smooth_decomposition(values, target=123457):
    a, b = sequence(values, "two summands", 2, 2)
    integer(a, "first summand", 1, target - 1)
    integer(b, "second summand", 1, target - 1)
    require(a + b == target, "summands must equal the prescribed target")
    rows = [factors(a), factors(b)]
    return max(max(row, default=1) for row in rows), {"factorizations": rows,
                                                     "largest_prime_factor_of_one": 1}


def factorial_large_factors(values, n=12):
    target = factorial(n)
    values = int_set(values, target, n + 1, n)
    product = 1
    for x in values:
        product *= x
        require(product <= target, "product exceeds the factorial")
    require(product == target, "product is not the prescribed factorial")
    return max(values), {"factor_count": len(values), "factorial": target}


def coprime_sumset(values, n=128, size=3):
    a, b = sequence(values, "two sets", 2, 2)
    a, b = int_set(a, n, max_size=size), int_set(b, n, max_size=size)
    require(len(a) == len(b) == size, "both sets must have prescribed cardinality")
    sums = sorted({x + y for x in a for y in b})
    require(all(gcd(x, y) == 1 for x, y in combinations(sums, 2)),
            "two distinct sumset elements have a common divisor")
    return len(sums), {"sumset": sums}


def power_residue_run(certificate, p=1009, exponent=2, length=5):
    require(type(certificate) is dict and set(certificate) == {"start", "roots"},
            "expected dictionary with start and roots only")
    start = integer(certificate["start"], "start", 1, p - length)
    roots = sequence(certificate["roots"], "roots", length, length)
    for i, root in enumerate(roots):
        integer(root, "root", 1, p - 1)
        require(pow(root, exponent, p) == start + i, "root does not certify the residue")
    return start, {"modulus": p, "exponent": exponent, "run_length": length}


def inverse_free_interval(values, p=1009):
    start, length = sequence(values, "interval [start,length]", 2, 2)
    integer(start, "start", 1, p - 1)
    integer(length, "length", 1, p - 1)
    end = start + length - 1
    require(end < p, "interval must not wrap around the modulus")
    for x in range(start, end + 1):
        inverse = pow(x, -1, p)
        require(not (start <= inverse <= end), "interval contains a modular inverse pair")
    return length, {"interval": [start, end], "self_inverse_residues_excluded": True}
