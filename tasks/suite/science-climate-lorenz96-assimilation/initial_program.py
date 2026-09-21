"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def analyze(ensemble, observations, observed_indices, observation_variance):
    # Naive observation nudging; learn covariance, localization and inflation.
    result = ensemble.copy()
    result[:, observed_indices] += 0.6 * (observations - result[:, observed_indices])
    return result
# EVOLVE-BLOCK-END
