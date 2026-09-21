# EVOLVE-BLOCK-START
import numpy as np


def erdos_discrepancy_pattern() -> np.ndarray:
    """
    Erdos discrepancy problem. Build the longest possible sign pattern
    a_1, ..., a_N in {-1, +1} whose discrepancy is at most 2, where the
    discrepancy is the maximum value of |a_d + a_{2d} + ... + a_{kd}| taken over
    all homogeneous progressions d, 2d, ..., kd contained in {1, ..., N}.

    This baseline uses a deterministic greedy construction: it appends signs one
    at a time, at each step choosing the sign (+1 or -1) that keeps every
    homogeneous-progression partial sum within [-2, 2], breaking ties by
    minimizing the sum of squared partial sums. It stops as soon as neither sign
    can be appended without exceeding discrepancy 2.

    Returns:
        pattern: np.ndarray of shape (N,) and integer dtype, with every entry
            equal to +1 or -1. N is determined by how far the greedy
            construction can extend while keeping discrepancy <= 2.
    """
    disc_limit = 2

    partial_sums: dict[int, int] = {}  # running sum of progression with step d
    pattern: list[int] = []
    n = 0
    while True:
        n += 1
        divisors = [d for d in range(1, n + 1) if n % d == 0]

        best_sign = None
        best_cost = None
        for sign in (1, -1):
            feasible = True
            cost = 0
            for d in divisors:
                v = partial_sums.get(d, 0) + sign
                if abs(v) > disc_limit:
                    feasible = False
                    break
                cost += v * v
            if feasible and (best_cost is None or cost < best_cost):
                best_sign = sign
                best_cost = cost

        if best_sign is None:
            # Cannot extend the pattern any further within discrepancy 2.
            break

        for d in divisors:
            partial_sums[d] = partial_sums.get(d, 0) + best_sign
        pattern.append(best_sign)

    return np.array(pattern, dtype=np.int64)


# EVOLVE-BLOCK-END
