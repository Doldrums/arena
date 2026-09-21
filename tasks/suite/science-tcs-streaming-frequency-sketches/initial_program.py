"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def update(state, item):
    from autoresearch_suite.science_tcs_expansion import sketch_baseline_update
    return sketch_baseline_update(state, item)

def query(state, item):
    from autoresearch_suite.science_tcs_expansion import sketch_baseline_query
    return sketch_baseline_query(state, item)
# EVOLVE-BLOCK-END
