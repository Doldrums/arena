# EVOLVE-BLOCK-START
import numpy as np


def function_guessing_game_strategy() -> np.ndarray:
    """
    Offline proxy for AlphaEvolve Problem 66 ("The function guessing game").

    In the original (interactive) problem, an agent must guess a hidden function
    f: R -> R, paying 1 currency unit per evaluation f(x), and earning a reward of
    1000 currency units if it reconstructs the function accurately (L^1 error below a
    small threshold). The deterministic, offline core of that game is: decide AT WHICH
    POINTS to evaluate the hidden function so that, given only those samples, the
    function can be reconstructed exactly while paying as little as possible.

    A guessing strategy is therefore a fixed set of query locations x_1, ..., x_k in the
    domain [-1, 1]. The evaluator probes each hidden test function at these locations,
    reconstructs it by polynomial (least-squares) interpolation, and scores the strategy
    by the net reward = 1000 * (fraction reconstructed correctly) - k, i.e. reward minus
    the per-evaluation query cost.

    A polynomial of degree D is uniquely determined by D + 1 distinct samples, so the
    optimal strategy queries exactly D + 1 well-placed points. This baseline plays it
    safe with 12 equally-spaced query points: it reconstructs every degree-5 test
    function exactly, but overpays on queries, leaving headroom for evolution to reduce
    the number of queries toward the optimum of 6.

    Returns:
        query_points: np.ndarray of shape (k,) giving the x-locations (in [-1, 1]) at
            which the hidden function will be evaluated.
    """
    # Safe but query-heavy baseline: 12 equally spaced query points in [-1, 1].
    query_points = np.linspace(-1.0, 1.0, 12)
    return query_points


# EVOLVE-BLOCK-END
