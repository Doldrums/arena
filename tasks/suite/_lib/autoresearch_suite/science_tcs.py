"""Exact certificate checks for finite theoretical-computer-science problems.

These are independent construction evaluators, not reproductions of a paper's
search procedure. Sorting networks use the zero-one principle and exhaust all
Boolean inputs; binary codes check every pair with Python integer arithmetic.
Reported reference values are feasible constructions, not claims of optimality.
"""
from __future__ import annotations

import math
import numbers

import numpy as np

from .runtime import require


def _integer(value, name):
    require(isinstance(value, numbers.Integral) and not isinstance(value, (bool, np.bool_)),
            f"{name} must be an integer (floats and booleans are not accepted)")
    return int(value)


def _sequence(value, name, ndim):
    require(isinstance(value, (list, tuple, np.ndarray)), f"{name} must be a list, tuple or array")
    if isinstance(value, np.ndarray):
        require(value.ndim == ndim, f"{name} must have {ndim} dimensions")
    return value


def sorting_network(comparators, n, max_comparators=4096):
    """Return comparator count and verification diagnostics for an n-wire network.

    Each comparator is a pair 0 <= i < j < n, putting min on i and max on j.
    Sequential order is respected. Depth is the earliest legal parallel schedule
    consistent with the sequence of operations on every wire; it is diagnostic,
    not a second term in the score. No sampled inputs or float casts are used.
    """
    n = _integer(n, "n")
    limit = _integer(max_comparators, "max_comparators")
    require(2 <= n <= 20 and limit > 0, "verifier supports 2..20 wires and a positive comparator limit")
    comparators = _sequence(comparators, "comparators", 2)
    require(0 < len(comparators) <= limit, f"return 1..{limit} comparators")
    pairs = []
    for index, pair in enumerate(comparators):
        pair = _sequence(pair, f"comparator {index}", 1)
        require(len(pair) == 2, "each comparator must have exactly two endpoints")
        a, b = (_integer(v, "comparator endpoint") for v in pair)
        require(0 <= a < b < n, f"comparator endpoints must satisfy 0 <= i < j < {n}")
        pairs.append((a, b))

    # Wire-major layout makes each comparator operate on contiguous uint8 data.
    inputs = np.arange(1 << n, dtype=np.uint32)
    wires = np.array([(inputs >> i) & 1 for i in range(n)], dtype=np.uint8)
    depth = [0] * n
    for a, b in pairs:
        low = wires[a] & wires[b]
        high = wires[a] | wires[b]
        wires[a], wires[b] = low, high
        level = max(depth[a], depth[b]) + 1
        depth[a] = depth[b] = level

    bad = np.flatnonzero(np.any(wires[:-1] > wires[1:], axis=0))
    if len(bad):
        example = [(int(bad[0]) >> i) & 1 for i in range(n)]
        require(False, f"network does not sort all Boolean inputs; counterexample: {example}")
    return len(pairs), {"depth": max(depth), "verified_inputs": 1 << n,
                        "verification": "exhaustive_zero_one"}


def binary_code(codewords, n, minimum_distance):
    """Return |C| for a binary (n, |C|, d) code encoded as packed integers.

    All codewords must be distinct integers in [0, 2**n). Leading zero bits are
    implicit. Linear and nonlinear codes are both allowed. Disjoint Hamming
    balls of radius floor((d-1)/2) provide an elementary size rejection before
    the exact pairwise checks; the literature's stronger bounds are not assumed.
    """
    n = _integer(n, "n")
    d = _integer(minimum_distance, "minimum_distance")
    require(1 <= n <= 24 and 1 <= d <= n, "require 1 <= minimum_distance <= n <= 24")
    codewords = _sequence(codewords, "codewords", 1)
    volume = sum(math.comb(n, radius) for radius in range((d - 1) // 2 + 1))
    hamming_bound = (1 << n) // volume
    require(1 <= len(codewords) <= hamming_bound,
            f"code must contain 1..{hamming_bound} words (elementary Hamming bound)")
    words = [_integer(word, "codeword") for word in codewords]
    require(all(0 <= word < (1 << n) for word in words), f"codewords must lie in [0, {1 << n})")
    require(len(set(words)) == len(words), "duplicate codewords are not permitted")
    observed_distance = n + 1
    checked = 0
    for i, word in enumerate(words):
        for other in words[:i]:
            distance = (word ^ other).bit_count()
            require(distance >= d, f"codeword pair has Hamming distance {distance}, below {d}")
            observed_distance = min(observed_distance, distance)
            checked += 1
    return len(words), {"minimum_distance": observed_distance if checked else None,
                        "verified_pairs": checked, "word_length": n,
                        "verification": "exact_pairwise_hamming"}


# --- snake-in-the-box -------------------------------------------------------

def snake_in_the_box(vertices, n):
    """Return the length (number of edges) of an induced path in the hypercube Q_n.

    ``vertices`` are distinct integers in [0, 2**n) listed along the path.
    Consecutive vertices must differ in exactly one bit; two non-consecutive
    vertices must differ in at least two bits (no chord), which is the snake
    condition. Every pair is checked exactly.
    """
    n = _integer(n, "n")
    require(2 <= n <= 16, "verifier supports dimensions 2..16")
    vertices = _sequence(vertices, "vertices", 1)
    words = [_integer(v, "vertex") for v in vertices]
    require(1 <= len(words) <= (1 << n), f"return 1..{1 << n} vertices")
    require(all(0 <= w < (1 << n) for w in words), f"vertices must lie in [0, {1 << n})")
    require(len(set(words)) == len(words), "vertices must be distinct")
    for i in range(1, len(words)):
        require((words[i] ^ words[i - 1]).bit_count() == 1, f"vertices {i - 1} and {i} are not adjacent in the hypercube")
    for i in range(len(words)):
        for j in range(i + 2, len(words)):
            require((words[i] ^ words[j]).bit_count() >= 2, f"chord between path positions {i} and {j}: the path is not induced")
    return len(words) - 1, {"vertices": len(words), "dimension": n, "verification": "exact_pairwise"}


# --- Ramsey graphs --------------------------------------------------------------

def _has_clique(adjacency, k):
    """True when the bitset adjacency (list of ints) contains a k-clique."""
    n = len(adjacency)

    def extend(candidates, depth):
        if depth == k:
            return True
        while candidates:
            v = (candidates & -candidates).bit_length() - 1
            candidates &= candidates - 1
            if extend(candidates & adjacency[v], depth + 1):
                return True
        return False

    return extend((1 << n) - 1, 0)


def ramsey_graph(edges, n, clique=5, independent=5, max_vertices=45):
    """Return ``n`` when the graph on n vertices has no K_clique and no independent set of size ``independent``.

    ``edges`` is an iterable of (i, j) pairs with 0 <= i < j < n. Both
    conditions are checked exactly by enumerating cliques of the graph and of
    its complement with bitsets. A larger valid ``n`` is a better lower bound on
    the Ramsey number R(clique, independent).
    """
    n = _integer(n, "n")
    require(2 <= n <= max_vertices, f"n must be between 2 and {max_vertices} (larger graphs cannot exist by the known upper bound)")
    edges = _sequence(edges, "edges", 2)
    adjacency = [0] * n
    count = 0
    for index, pair in enumerate(edges):
        pair = _sequence(pair, f"edge {index}", 1)
        require(len(pair) == 2, "each edge must have two endpoints")
        a, b = (_integer(v, "edge endpoint") for v in pair)
        require(0 <= a < b < n, f"edge endpoints must satisfy 0 <= i < j < {n}")
        if not adjacency[a] >> b & 1:
            adjacency[a] |= 1 << b
            adjacency[b] |= 1 << a
            count += 1
    complement = [((1 << n) - 1) & ~adjacency[i] & ~(1 << i) for i in range(n)]
    require(not _has_clique(adjacency, clique), f"the graph contains a clique of size {clique}")
    require(not _has_clique(complement, independent), f"the graph contains an independent set of size {independent}")
    return n, {"vertices": n, "edges": count, "verification": "exact_bitset_clique_search"}
