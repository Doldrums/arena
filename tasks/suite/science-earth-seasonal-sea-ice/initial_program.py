"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def forecast_ice(history, past_climate_covariates, lead_months):
    from autoresearch_suite.science_earth_expansion import ice_baseline
    return ice_baseline(history, past_climate_covariates, lead_months)
# EVOLVE-BLOCK-END
