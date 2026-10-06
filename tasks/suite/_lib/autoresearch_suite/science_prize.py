"""Independently written exact verifiers for three prize-listed problems.

These are finite arithmetic/combinatorial certificates, not Lean formalizations.
Mathematical sources and the precise scope changes are in catalog/science/prize.json.
"""
from collections import deque
from math import isqrt

from .runtime import require


def integer(value, name, lower, upper):
    require(type(value) is int, f"{name} must be a Python integer (not bool/float)")
    require(lower <= value <= upper, f"{name} must be in [{lower}, {upper}]")
    return value


def sequence(value, name, lower, upper):
    require(type(value) in (list, tuple), f"{name} must be a list or tuple")
    require(lower <= len(value) <= upper, f"{name} must contain {lower}..{upper} entries")
    return value


def prime(value):
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    return all(value % divisor for divisor in range(3, isqrt(value) + 1, 2))


def powerful_counterexample(certificate, maximum=10**12):
    """Certify two consecutive powerful non-squares by complete prime factors."""
    require(type(certificate) is dict, "construct() must return a certificate dictionary")
    require(set(certificate) == {"n", "factorizations"}, "expected n and factorizations only")
    n = integer(certificate["n"], "n", 2, maximum - 1)
    factors = sequence(certificate["factorizations"], "factorizations", 2, 2)
    canonical = []
    for value, entries in zip((n, n + 1), factors):
        entries = sequence(entries, "prime factorization", 1, 20)
        product, seen, row = 1, set(), []
        for entry in entries:
            p, exponent = sequence(entry, "prime/exponent pair", 2, 2)
            p = integer(p, "prime", 2, value)
            exponent = integer(exponent, "exponent", 2, value.bit_length())
            require(p not in seen, "prime factors must be distinct")
            # The upper bound limits trial division and integer arithmetic.
            require(p**exponent <= value, "factor exceeds the proposed integer")
            require(prime(p), f"factor {p} is composite")
            seen.add(p)
            product *= p**exponent
            require(product <= value, "factor product exceeds the proposed integer")
            row.append([p, exponent])
        require(product == value, "factorization is incomplete or incorrect")
        require(isqrt(value)**2 != value, "both integers must be non-squares")
        canonical.append(sorted(row))
    return 1, {"n": n, "consecutive_integer": n + 1, "factorizations": canonical,
               "verification": "exact_prime_factorization_and_integer_square_root",
               "statement_resolved": "existence of consecutive powerful non-squares",
               "lean_verified": False}


def reset_threshold(transitions, n=12):
    """Exact shortest reset word through BFS on all reachable nonempty subsets."""
    integer(n, "n", 2, 16)
    columns = sequence(transitions, "two transition columns", 2, 2)
    columns = [list(sequence(column, "transition column", n, n)) for column in columns]
    for column in columns:
        for state in column:
            integer(state, "destination state", 0, n - 1)
    initial = (1 << n) - 1
    queue, parent = deque([initial]), {initial: None}
    terminal = None
    while queue:
        subset = queue.popleft()
        if subset & (subset - 1) == 0:
            terminal = subset
            break
        for letter, column in enumerate(columns):
            image, rest = 0, subset
            while rest:
                bit = rest & -rest
                image |= 1 << column[bit.bit_length() - 1]
                rest ^= bit
            if image not in parent:
                parent[image] = (subset, letter)
                queue.append(image)
    require(terminal is not None, "automaton is not synchronizing")
    word = []
    while parent[terminal] is not None:
        terminal, letter = parent[terminal]
        word.append(letter)
    word.reverse()
    return len(word), {"shortest_reset_word": word, "reachable_subsets_discovered": len(parent),
                       "states": n, "alphabet_size": 2, "cerny_conjectured_bound": (n - 1)**2,
                       "exceeds_cerny_bound": len(word) > (n - 1)**2,
                       "verification": "exhaustive_subset_breadth_first_search",
                       "lean_verified": False}


def sidon_sums(values):
    sums = set()
    for i, a in enumerate(values):
        for b in values[i:]:
            total = a + b
            if total in sums:
                return None
            sums.add(total)
    return sums


def maximal_sidon(values, n=256):
    """Minimize cardinality subject to Sidon AND inclusion-maximal in [1,n]."""
    integer(n, "interval endpoint", 1, 4096)
    values = list(sequence(values, "Sidon set", 1, n))
    for value in values:
        integer(value, "set element", 1, n)
    require(len(set(values)) == len(values), "set elements must be distinct")
    values.sort()
    require(sidon_sums(values) is not None, "two unordered pair sums coincide (diagonals included)")
    selected = set(values)
    for value in range(1, n + 1):
        if value not in selected:
            require(sidon_sums(values + [value]) is None,
                    f"not inclusion-maximal: {value} can still be added")
    return len(values), {"interval": [1, n], "checked_extensions": n - len(values),
                         "pair_sums": len(values) * (len(values) + 1) // 2,
                         "verification": "exact_pair_sums_and_all_single_element_extensions",
                         "lean_verified": False}
