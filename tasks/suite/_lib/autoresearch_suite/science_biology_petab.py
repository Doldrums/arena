"""Brannmark 2010 PEtab source model: independent SciPy ODE likelihood.

Equations transcribed from the pinned SBML reaction stoichiometry/kinetic laws.
Concentration units and observation scaling are those of the source model.
Parameters are represented on the PEtab log10 scale. Conservation totals are
10 for receptor, IRS and X pools, matching the source initial concentrations.
"""
import numpy as np
from scipy.integrate import solve_ivp


def rhs(t, y, p, condition):
    IR, IRins, IRp, IRiP, IRi, IRS, IRSiP, X, Xp = y
    insulin = (condition['insulin_dose_1'] if t >= condition['insulin_time_1'] else 0.) + (condition['insulin_dose_2'] if t >= condition['insulin_time_2'] else 0.)
    a = IR * (p['k1aBasic'] + insulin*p['k1a'])
    b = IRins*p['k1b']; c = IRins*p['k1c']; d = IRp*p['k1d']
    e = IRiP*(p['k1e']+Xp*p['k1f']/(Xp+1)); f = IRp*p['k1g']; g = IRi*p['k1r']
    h = IRS*p['k21']*(IRp+IRiP*p['k22']); i = IRSiP*p['km2']
    j = IRSiP*X*p['k3']; k = Xp*p['km3']
    return np.array([-a+b+f+g,a-b-c,c-d-f,d-e,e-g,-h+i,h-i,-j+k,j-k])


def equilibrium(p):
    y = np.array([10.,0,0,0,0,10,0,10,0])
    zero = dict(insulin_dose_1=0.,insulin_dose_2=0.,insulin_time_1=0.,insulin_time_2=0.)
    for horizon in [100.,1000.,10000.,100000.,1000000.]:
        sol = solve_ivp(lambda t,z:rhs(t,z,p,zero), (0,horizon), y, method='BDF', rtol=2e-7, atol=2e-9)
        if not sol.success or np.min(sol.y[:,-1]) < -1e-6:
            raise ValueError('PEtab preequilibration failed')
        y = sol.y[:,-1]
        if np.max(np.abs(rhs(0,y,p,zero))) < 1e-8:
            return y
    raise ValueError('PEtab preequilibrium did not converge')


def predict(parameters, rows, problem):
    p = dict(zip(problem['parameter_names'],10**np.asarray(parameters)))
    initial = equilibrium(p)
    outputs = {}
    for condition_id in sorted({r['simulationConditionId'] for r in rows}):
        condition = problem['conditions'][condition_id]
        relevant = [r for r in rows if r['simulationConditionId'] == condition_id]
        times = sorted(set(float(r['time']) for r in relevant))
        end = max(times)
        # Explicitly restart at insulin discontinuities; solve_ivp must not
        # extrapolate across a stimulus jump without sampling it.
        boundaries = sorted({0.,end,*[float(condition[k]) for k in ['insulin_time_1','insulin_time_2'] if 0 < condition[k] < end]})
        y = initial.copy(); states = {0.: y.copy()}
        for left,right in zip(boundaries[:-1],boundaries[1:]):
            requested = sorted(set([t for t in times if left < t <= right]+[right]))
            sol = solve_ivp(lambda t,z:rhs(t,z,p,condition), (left,right), y, t_eval=requested, method='BDF', rtol=2e-7,atol=2e-9)
            if not sol.success or not np.isfinite(sol.y).all() or np.min(sol.y) < -1e-5:
                raise ValueError('PEtab concentration integration failed')
            for t,z in zip(sol.t,sol.y.T): states[float(t)]=z
            y=sol.y[:,-1]
        for row in relevant:
            state = states[float(row['time'])]
            unscaled = state[2]+state[3] if row['observableId']=='IR1_P' else state[6]
            prediction = p[row['observableParameters']]*unscaled
            sigma = p[row['noiseParameters']]
            outputs[row['row_id']] = (prediction,sigma)
    return [outputs[r['row_id']] for r in rows]


def negative_log_likelihood(parameters, rows, problem):
    try:
        values = predict(parameters, rows, problem)
        terms = [.5*((prediction-float(r['measurement']))/sigma)**2 + np.log(sigma*np.sqrt(2*np.pi)) for r,(prediction,sigma) in zip(rows,values)]
        return float(np.mean(terms))
    except (ValueError, FloatingPointError, OverflowError):
        return 1e100
