"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def assign(demands, capacities, open_cost, assign_cost):
    # Largest demand first, cheapest feasible facility.
    result = np.zeros(len(demands), dtype=int)
    load = np.zeros(len(capacities))
    for i in np.argsort(-demands):
        for f in np.argsort(assign_cost[i]):
            if load[f] + demands[i] <= capacities[f]:
                load[f] += demands[i]
                result[i] = f
                break
    return result
# EVOLVE-BLOCK-END
