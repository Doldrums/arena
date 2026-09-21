"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def solve_transition(model, steady_state, aggregate_shock):
    from autoresearch_suite.science_economics_expansion import macro_baseline
    return macro_baseline(model, steady_state, aggregate_shock)
# EVOLVE-BLOCK-END
