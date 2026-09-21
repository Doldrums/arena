"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np
from scipy.optimize import minimize
from autoresearch_suite import l2o


def solve(problem, time_limit):
    # Generic seed: 60 SLSQP iterations from the origin; MILP rounds the relaxed solution. Evolve a real optimiser.
    cons, bounds = l2o.scipy_constraints(problem)
    x0 = np.clip(np.zeros(problem['n']), problem['lb'], problem['ub'])
    result = minimize(lambda z: l2o.objective(problem, z), x0, method='SLSQP', constraints=cons, bounds=bounds, options={'maxiter': 60, 'ftol': 1e-9})
    x = result.x
    if problem['form'] == 'milp':
        x = np.round(x)
    return x
# EVOLVE-BLOCK-END
