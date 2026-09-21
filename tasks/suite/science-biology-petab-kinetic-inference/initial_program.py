"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np
from scipy.optimize import minimize

def fit_kinetics(petab_problem, objective, budget):
    bounds=np.array(petab_problem["bounds"],float)
    initial=np.array(petab_problem["initial_parameters"],float)
    calls=[0];best=[initial,float("inf")]
    def loss(x):
        if calls[0] >= budget: return 1e100
        calls[0]+=1;value=objective(x)
        if value < best[1]:best[:]=[x.copy(),value]
        return value
    minimize(loss,initial,method="L-BFGS-B",bounds=bounds,options={"maxfun":max(1,budget-len(initial)-1),"maxiter":max(1,budget//(len(initial)+1)-1)})
    return {"parameters":best[0],"intervals":bounds}
# EVOLVE-BLOCK-END
