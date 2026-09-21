"""FunBO Figure 8 expected-improvement seed interface: return a grid index.

Input arrays have shape (grid_size, 1); incumbent is the smallest observed
objective. The evaluator owns the GP and objective; only this policy evolves.
"""
import numpy as np
from scipy.special import ndtr


# EVOLVE-BLOCK-START
def acquisition_function(predictive_mean, predictive_var, incumbent):
    standard_deviation = np.sqrt(np.maximum(predictive_var, 1e-16))
    improvement = incumbent - predictive_mean
    z = improvement / standard_deviation
    expected_improvement = improvement * ndtr(z) + standard_deviation * np.exp(-z * z / 2) / np.sqrt(2 * np.pi)
    return int(np.argmax(expected_improvement))
# EVOLVE-BLOCK-END
