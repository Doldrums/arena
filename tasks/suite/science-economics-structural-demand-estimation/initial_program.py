"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def estimate_demand(products, instruments, model_spec, budget):
    from autoresearch_suite.science_economics_expansion import demand_baseline
    return demand_baseline(products, instruments, model_spec, budget)
# EVOLVE-BLOCK-END
