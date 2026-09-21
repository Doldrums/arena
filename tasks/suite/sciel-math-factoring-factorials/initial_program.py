# EVOLVE-BLOCK-START
import heapq

import numpy as np


def factoring_factorials100() -> np.ndarray:
    """
    Factoring N! into N factors (here N = 100). Let A034258-style C(N) be the largest
    quantity such that N! can be written as a product of exactly N integer factors that are
    all >= C(N). Equivalently, partition the multiset of prime factors of N! into N groups
    (bins) and maximize the minimum group product. The objective is to make the smallest of
    the N factors as large as possible.

    Solution representation (numpy-array form required by this template):
        The prime factors of N! are enumerated in a fixed canonical order: the sorted-ascending
        list of all prime factors of N! counted with multiplicity, e.g. [2, 2, ..., 3, 3, ...,
        5, ...]. This constructor returns a 1-D integer assignment array `assign` of that same
        length, where assign[i] in {0, ..., N-1} is the bin (factor) that the i-th canonical
        prime factor is placed into. The N factor values are then the products of the primes in
        each bin, and the score is the minimum of those N products.

    Baseline construction:
        A multiplicative longest-processing-time greedy: sort the prime factors descending and
        repeatedly assign the next largest prime to the bin that currently has the smallest
        product (balancing the bins). Deterministic.

    Returns:
        assign: np.ndarray of shape (Omega(N!),) and integer dtype, with values in [0, N-1],
            giving the bin index of each canonical prime factor. For N = 100 the length is 239.
    """
    n = 100

    # Sieve of Eratosthenes for primes <= n.
    is_prime = [True] * (n + 1)
    is_prime[0] = is_prime[1] = False
    for i in range(2, int(n**0.5) + 1):
        if is_prime[i]:
            for j in range(i * i, n + 1, i):
                is_prime[j] = False

    # Prime factors of n! with multiplicity (Legendre's formula), ascending canonical order.
    primes_asc = []
    for p in range(2, n + 1):
        if not is_prime[p]:
            continue
        exponent = 0
        pk = p
        while pk <= n:
            exponent += n // pk
            pk *= p
        primes_asc.extend([p] * exponent)
    primes_asc.sort()
    length = len(primes_asc)

    # Greedy: assign largest primes first to the currently smallest bin (by product).
    order_desc = sorted(range(length), key=lambda i: -primes_asc[i])
    assign = np.zeros(length, dtype=np.int64)
    bins = [(1, b) for b in range(n)]  # (current_product, bin_index)
    heapq.heapify(bins)
    for i in order_desc:
        prod, b = heapq.heappop(bins)
        assign[i] = b
        heapq.heappush(bins, (prod * primes_asc[i], b))

    return assign


# EVOLVE-BLOCK-END
