"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def infer_emissions(columns, transport_operator, prior, uncertainty):
    from autoresearch_suite.science_earth_expansion import methane_baseline
    return methane_baseline(columns, transport_operator, prior, uncertainty)
# EVOLVE-BLOCK-END
