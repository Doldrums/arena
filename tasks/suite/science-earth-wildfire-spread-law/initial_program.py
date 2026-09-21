"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def fit_spread(training_features, training_rates, metadata):
    from autoresearch_suite.science_earth_expansion import fire_baseline
    return fire_baseline(training_features, training_rates, metadata)
# EVOLVE-BLOCK-END
