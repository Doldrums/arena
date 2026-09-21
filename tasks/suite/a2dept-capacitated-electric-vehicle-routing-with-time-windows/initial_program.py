"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def plan(instance):
    # Serve customers one per route, earliest due time first (always feasible with a full battery).
    customers = list(range(1, instance["n_customers"] + 1))
    customers.sort(key=lambda v: instance["due"][v])
    return [[v] for v in customers]
# EVOLVE-BLOCK-END
