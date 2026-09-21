# Recreated feasible value-density baseline for the exact official KP contract.
# The released prompts/kp_constructive/seed_func.txt always selects item zero,
# which eventually becomes infeasible and raises in the original evaluator.
import numpy as np
def select_next_item(remaining_capacity: int, weights: np.ndarray, values: np.ndarray) -> int:
    feasible = np.flatnonzero(weights <= remaining_capacity)
    if not len(feasible):
        # Match the upstream 1e-3 boundary tolerance when no strict fit remains.
        feasible = np.flatnonzero(weights < remaining_capacity + 1e-3)
    return int(feasible[np.argmax(values[feasible] / weights[feasible])])
