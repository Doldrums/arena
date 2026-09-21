"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def infer_aquifer(head_observations, geometry, forward_oracle, budget):
    from autoresearch_suite.science_earth_expansion import groundwater_baseline
    return groundwater_baseline(head_observations, geometry, forward_oracle, budget)
# EVOLVE-BLOCK-END
