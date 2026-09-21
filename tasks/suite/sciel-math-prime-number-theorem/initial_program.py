# EVOLVE-BLOCK-START
import numpy as np


def prime_number_theorem_partial_function():
    """
    Construct a partial function f from a subset of the positive integers to the reals
    that maximizes a hidden number-theoretic objective related to the Prime Number Theorem.

    The function f is scored by a fixed evaluator (see evaluator.py) that:
      * subtracts a constant from f(1) so that sum_k f(k)/k == 0,
      * requires the step function M(x) = sum_k f(k) * floor(x/k) to stay <= 1 for every
        real x in [1, 10*max_key] (otherwise the construction is infeasible), and
      * returns the objective a = -sum_k f(k) * log(k) / k (to be maximized; optimum 1.0).
    The optimum is approached by the Mobius function mu(k), for which the classic identity
    sum_{k<=x} mu(k) floor(x/k) = 1 holds and -sum mu(k) log(k)/k -> 1.

    Representation:
        domain : np.ndarray, shape (m,), dtype int   -> positive integers in the domain of f
        values : np.ndarray, shape (m,), dtype float -> the corresponding real values f(k)

    Returns:
        (domain, values): a tuple of two numpy arrays of equal length describing f.
    """
    # Deterministic feasible baseline (a strong Mobius-flavoured partial function).
    domain = np.array([1, 2, 3, 5, 30], dtype=np.int64)
    values = np.array([3.47155351603266, -1.0, -1.0, -1.0, 1.0], dtype=np.float64)
    return domain, values


# EVOLVE-BLOCK-END
