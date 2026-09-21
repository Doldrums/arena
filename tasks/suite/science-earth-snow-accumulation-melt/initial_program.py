"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def snow_step(meteorology, snow_state, site_parameters):
    from autoresearch_suite.science_earth_expansion import snow_baseline
    return snow_baseline(meteorology, snow_state, site_parameters)
# EVOLVE-BLOCK-END
