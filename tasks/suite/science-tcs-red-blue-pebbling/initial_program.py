"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def pebble(dag, fast_memory_budget):
    from autoresearch_suite.science_tcs_expansion import pebble_baseline
    return pebble_baseline(dag, fast_memory_budget)
# EVOLVE-BLOCK-END
