"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def solve_consumption(model, resource_grid, budget):
    from autoresearch_suite.science_economics_expansion import consumption_baseline
    return consumption_baseline(model, resource_grid, budget)
# EVOLVE-BLOCK-END
