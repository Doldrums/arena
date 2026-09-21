"""Economic-model tasks with independently recomputed objectives.

F01, F02, F04, F05 are explicitly model-based. F03 uses the public BLP
automobile tables shipped by a pinned PyBLP distribution. No trading claims.
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.metadata
import io
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

from .runtime import CandidateError, require


def utility(c, gamma):
    c = np.maximum(c, 1e-12)
    return np.log(c) if gamma == 1 else c ** (1 - gamma) / (1 - gamma)


def consumption_model(beta=.95, gamma=2., horizon=6):
    return {"beta": beta, "gamma": gamma, "R": 1.02, "income": np.array([.5, 1.5]),
            "transition": np.array([[.85, .15], [.15, .85]]), "horizon": horizon}


def consumption_baseline(model, resource_grid, budget):
    """Finite-horizon backward induction with a bounded consumption grid."""
    m = np.asarray(resource_grid)
    horizon, nz = model['horizon'], len(model['income'])
    policy = np.zeros((horizon, nz, len(m)))
    value = np.zeros((nz, len(m)))
    fractions = np.linspace(.002, 1., int(budget))
    for t in range(horizon - 1, -1, -1):
        choices = m[:, None] * fractions
        if t == horizon - 1:
            policy[t] = m
            value[:] = utility(m, model['gamma'])
            continue
        updated = np.empty_like(value)
        for z in range(nz):
            continuation = np.zeros_like(choices)
            for zp, income in enumerate(model['income']):
                next_m = model['R'] * (m[:, None] - choices) + income
                continuation += model['transition'][z, zp] * np.interp(next_m, m, value[zp])
            total = utility(choices, model['gamma']) + model['beta'] * continuation
            which = total.argmax(axis=1)
            policy[t, z] = choices[np.arange(len(m)), which]
            updated[z] = total[np.arange(len(m)), which]
        value = updated
    return policy


def consumption_residual(model, grid, policy):
    """Policy evaluation followed by independent dense one-step deviations."""
    c = np.asarray(policy, float)
    horizon, nz = model['horizon'], len(model['income'])
    require(c.shape == (horizon, nz, len(grid)) and np.all(np.isfinite(c)), "consumption policy has invalid shape or values")
    require(np.all(c > 0) and np.all(c <= grid[None, None, :] + 1e-10), "consumption must be positive and cannot exceed resources")
    require(np.allclose(c[-1], grid, atol=1e-9, rtol=0), "terminal household must consume all remaining wealth")
    # Finer, shifted points prevent copying a candidate-reported Bellman value.
    fine = np.geomspace(grid[0], grid[-1], 251)
    value = np.zeros((nz, len(fine)))
    residuals = []
    for t in range(horizon - 1, -1, -1):
        new_value = np.zeros_like(value)
        for z in range(nz):
            chosen = np.interp(fine, grid, c[t, z])
            objective = utility(chosen, model['gamma'])
            alternatives = fine[:, None] * np.linspace(.001, 1, 301)
            all_objectives = utility(alternatives, model['gamma'])
            if t < horizon - 1:
                for zp, income in enumerate(model['income']):
                    weight = model['beta'] * model['transition'][z, zp]
                    objective += weight * np.interp(model['R'] * (fine - chosen) + income, fine, value[zp])
                    all_objectives += weight * np.interp(model['R'] * (fine[:, None] - alternatives) + income, fine, value[zp])
            new_value[z] = objective
            # The truncated upper boundary is deliberately excluded from scoring.
            selected = (fine >= .2) & (fine <= 8)
            gain = np.maximum(all_objectives.max(axis=1) - objective, 0)
            residuals.extend((gain[selected] / (1 + np.abs(objective[selected]))).tolist())
        value = new_value
    return float(np.mean(residuals))


def consumption_score(solve):
    grid = np.geomspace(.001, 40, 101)
    rows = []
    for beta, gamma in ((.94, 1.), (.97, 2.), (.98, 3.)):
        model = consumption_model(beta, gamma)
        result = solve({k: v.copy() if isinstance(v, np.ndarray) else v for k, v in model.items()}, grid.copy(), 48)
        rows.append({"beta": beta, "gamma": gamma, "bellman_gain": consumption_residual(model, grid, result)})
    return float(np.mean([r['bellman_gain'] for r in rows])), {"instances": rows, "reference": "independent dense one-step deviations under same finite-horizon model"}


def macro_baseline(model, steady_state, aggregate_shock):
    answer = model.solve_impulse_linear(steady_state, ['K'], ['asset_mkt'], {'Z': aggregate_shock}, outputs=['K'])
    return np.asarray(answer['K'])


def macro_score(solve):
    from sequence_jacobian.examples import krusell_smith
    _, ss, model, _, _, _ = krusell_smith.dag()
    rows = []
    for amplitude, persistence in ((.005, .8), (-.008, .7), (.01, .9)):
        shock = np.r_[ss['Z'] * amplitude * persistence ** np.arange(24), np.zeros(16)]
        # dag() reuses global firm/market blocks; copying the whole pair also
        # isolates candidate workspace mutations from the verifier's model.
        _, candidate_ss, candidate_model, _, _, _ = krusell_smith.dag()
        candidate_model, candidate_ss = copy.deepcopy((candidate_model, candidate_ss))
        capital = np.asarray(solve(candidate_model, candidate_ss, shock.copy()), float)
        require(capital.shape == shock.shape and np.all(np.isfinite(capital)), "return a finite length40 capital deviation path")
        require(np.all(capital + ss['K'] > 0), "capital levels must be positive")
        result = model.impulse_nonlinear(ss, {'Z': shock, 'K': capital}, outputs=['asset_mkt', 'goods_mkt'], internals={'hh': ['D', 'a', 'c']})
        micro = result.internals['hh']
        for key in ('D', 'a', 'c'):
            require(np.all(np.isfinite(micro[key])), "nonfinite household solution")
        distribution = micro['D'] + ss.internals['hh']['D']
        assets = micro['a'] + ss.internals['hh']['a']
        consumption = micro['c'] + ss.internals['hh']['c']
        require(np.all(distribution >= -1e-10) and np.allclose(distribution.sum(axis=(1, 2)), 1, atol=1e-8), "invalid household distribution")
        require(np.all(assets >= -1e-9) and np.all(consumption > 0), "infeasible household policy")
        require(np.max(assets) <= ss.internals['hh']['a_grid'][-1] + 1e-8, "asset policy leaves fixed grid")
        error = float(np.max(np.abs(result['asset_mkt'])) / ss['K'])
        rows.append({"amplitude": amplitude, "persistence": persistence, "asset_market_residual": error,
                     "goods_market_residual": float(np.max(np.abs(result['goods_mkt'])))})
    return float(np.mean([r['asset_market_residual'] for r in rows])), {"instances": rows, "terminal_condition": "fixed source steady-state continuation after40periods"}


def blp_problem(products, integration_size=9):
    import pyblp
    from scipy.linalg import qr
    pyblp.options.verbose = False
    products = products.copy(deep=True)
    columns = [c for c in products if c.startswith('demand_instruments')]
    # Three-year blocks can make full-release instrument columns redundant.
    # Fix a full-rank instrument span once from inputs, independent of sigma.
    exogenous = np.c_[np.ones(len(products)), products[['hpwt','air','mpd','space']].to_numpy()]
    z = np.c_[exogenous, products[columns].to_numpy()]
    norms = np.sqrt((z*z).sum(axis=0))
    z = z[:,norms>0] / norms[norms>0]
    _, r, pivot = qr(z, mode='economic', pivoting=True)
    rank = int(np.sum(np.abs(np.diag(r)) > abs(r[0,0])*1e-10))
    z = z[:,sorted(pivot[:rank])]
    products = products.drop(columns=columns)
    for index in range(z.shape[1]):products['demand_instruments'+str(index)] = z[:,index]
    return pyblp.Problem((pyblp.Formulation('1 + prices + hpwt + air + mpd + space'),
                          pyblp.Formulation('0 + hpwt')), products,
                         integration=pyblp.Integration('product', size=integration_size), add_exogenous=False)


def demand_baseline(products, instruments, model_spec, budget):
    import pyblp
    problem = blp_problem(products, model_spec['integration_size'])
    result = problem.solve(sigma=np.array([[.3]]), sigma_bounds=(np.array([[0.]]), np.array([[3.]])),
                           optimization=pyblp.Optimization('l-bfgs-b', {'maxiter': int(budget)}),
                           method='1s', iteration=pyblp.Iteration('squarem', {'atol': 1e-12}))
    return float(result.sigma[0, 0])


def demand_score(estimate):
    import pyblp
    import pandas as pd
    data_path = Path(pyblp.data.BLP_PRODUCTS_LOCATION)
    table = pd.read_csv(data_path)
    rows = []
    for years in ((1971, 1972, 1973), (1981, 1982, 1983)):
        data = table[table.market_ids.isin(years)].copy()
        instruments = [c for c in data if c.startswith('demand_instruments')]
        sigma = float(estimate(data.copy(deep=True), instruments, {'integration_size': 9, 'sigma_bounds': [0., 3.]}, 20))
        require(np.isfinite(sigma) and 0 <= sigma <= 3, "random-coefficient standard deviation outside[0,3]")
        reference = blp_problem(data, 15)
        checked = reference.solve(sigma=np.array([[sigma]]), method='1s', optimization=pyblp.Optimization('return'),
                                  iteration=pyblp.Iteration('squarem', {'atol': 1e-13}))
        shares = checked.compute_shares()
        share_error = float(np.max(np.abs(shares.ravel() - np.asarray(data.shares))))
        require(share_error < 1e-8, "share inversion did not converge")
        objective = float(np.asarray(checked.objective).item()) / len(data)
        require(np.isfinite(objective), "nonfinite GMM objective")
        rows.append({'years': years, 'products': len(data), 'gmm_objective_per_product': objective,
                     'sigma': sigma, 'share_residual': share_error, 'price_coefficient': float(checked.beta[1, 0])})
    return float(np.mean([r['gmm_objective_per_product'] for r in rows])), {'instances': rows,
        'data_sha256': hashlib.sha256(data_path.read_bytes()).hexdigest(), 'data_source': f'PyBLP {importlib.metadata.version("pyblp")} bundled BLP automobile data',
        'adaptation': 'one random coefficient(hpwt), fixed1-step moments, two complete3-year market blocks; not full BLP replication'}


def auction_support():
    return np.array([(a, b) for a in (0., 1., 2., 3.) for b in (0., 1., 2., 3.)])


def check_auction(values, probabilities, mechanism, tolerance=1e-8):
    require(isinstance(mechanism, dict), "return allocations and payments")
    allocations = np.asarray(mechanism.get('allocations'), float)
    payments = np.asarray(mechanism.get('payments'), float)
    require(allocations.shape == values.shape and payments.shape == (len(values),), "invalid mechanism dimensions")
    require(np.all(np.isfinite(allocations)) and np.all(np.isfinite(payments)), "mechanism contains nonfinite values")
    require(np.all(allocations >= -tolerance) and np.all(allocations <= 1 + tolerance) and np.all(payments >= -tolerance), "infeasible allocations or negative payments")
    utility_by_report = values @ allocations.T - payments[None, :]
    truthful = np.diag(utility_by_report)
    require(np.all(truthful >= -tolerance), "individual rationality violated")
    regret = float(np.max(utility_by_report - truthful[:, None]))
    require(regret <= tolerance, "a profitable misreport violates incentive compatibility")
    return float(probabilities @ payments), {'maximum_regret': regret, 'minimum_truthful_utility': float(truthful.min())}


def auction_baseline(distribution_spec, support, constraints):
    probs = np.asarray(distribution_spec['probabilities'])
    sums = support.sum(axis=1)
    prices = np.unique(sums)
    price = max(prices, key=lambda p: p * probs[sums >= p].sum())
    purchases = sums >= price
    return {'allocations': np.repeat(purchases[:, None], support.shape[1], axis=1).astype(float),
            'payments': purchases.astype(float) * price}


def auction_optimum(values, probabilities):
    # LP is only a reference; feasibility is checked independently above.
    n, d = values.shape
    cost = np.r_[np.zeros(n * d), -probabilities]
    a, b = [], []
    for i in range(n):
        row = np.zeros(n * (d + 1))
        row[i*d:(i+1)*d], row[n*d+i] = -values[i], 1
        a.append(row); b.append(0)
        for j in range(n):
            if i == j:continue
            row = np.zeros(n * (d + 1))
            row[j*d:(j+1)*d] += values[i]
            row[i*d:(i+1)*d] -= values[i]
            row[n*d+i], row[n*d+j] = 1, -1
            a.append(row); b.append(0)
    result = linprog(cost, A_ub=a, b_ub=b, bounds=[(0,1)]*(n*d)+[(0,None)]*n, method='highs')
    require(result.success, 'reference mechanism LP failed')
    mechanism = {'allocations':result.x[:n*d].reshape(n,d), 'payments':result.x[n*d:]}
    value, _ = check_auction(values, probabilities, mechanism)
    return value, mechanism


def auction_score(construct):
    values = auction_support()
    rows = []
    rng = np.random.default_rng(9124)
    for probabilities in (np.full(len(values), 1/len(values)), rng.dirichlet(np.ones(len(values))), rng.dirichlet(np.full(len(values), 3))):
        mechanism = construct({'probabilities': probabilities.copy()}, values.copy(), {'bidders':1, 'items':2, 'finite_support_only':True})
        value, detail = check_auction(values, probabilities, mechanism)
        optimum, _ = auction_optimum(values, probabilities)
        rows.append({'revenue':value, 'reference_optimum':optimum, 'ratio':value/optimum, **detail})
    return float(np.mean([r['ratio'] for r in rows])), {'instances':rows, 'scope':'one bidder,two additive items,finite16-value support; no continuous-support truthfulness claim'}


def simulate_paths(contract, n, seed):
    rng = np.random.default_rng(seed)
    dt = contract['maturity']/contract['steps']
    noise = rng.normal(size=(n//2,contract['steps']))
    noise = np.r_[noise,-noise]
    increment = (contract['rate']-.5*contract['volatility']**2)*dt + contract['volatility']*np.sqrt(dt)*noise
    return np.c_[np.full(n,contract['spot']), contract['spot']*np.exp(np.cumsum(increment,axis=1))]


class LSMPolicy:
    def __init__(self, coefficients, contract):
        self.coefficients, self.contract = coefficients, contract

    def exercise(self, current_state, time):
        intrinsic = np.maximum(self.contract['strike']-current_state,0)
        continuation = np.polynomial.polynomial.polyval(current_state/self.contract['strike'],self.coefficients[time])
        return (intrinsic > 0) & (intrinsic >= continuation)


def stopping_baseline(paths, contract):
    steps = contract['steps']
    cash = np.maximum(contract['strike']-paths[:,-1],0)
    discount = np.exp(-contract['rate']*contract['maturity']/steps)
    coefficients = np.zeros((steps+1,4))
    for time in range(steps-1,0,-1):
        cash *= discount
        intrinsic = np.maximum(contract['strike']-paths[:,time],0)
        active = intrinsic>0
        if active.sum()>=4:
            coefficient = np.polynomial.polynomial.polyfit(paths[active,time]/contract['strike'],cash[active],3)
            coefficients[time] = coefficient
            exercise = active & (intrinsic >= np.polynomial.polynomial.polyval(paths[:,time]/contract['strike'],coefficient))
            cash[exercise] = intrinsic[exercise]
        else:
            coefficients[time,0] = 1e6
    return LSMPolicy(coefficients,contract)


def stopping_payoffs(policy, paths, contract):
    n = len(paths)
    active = np.ones(n,dtype=bool)
    values = np.zeros(n)
    for time in range(1,contract['steps']+1):
        indices=np.flatnonzero(active)
        prices=paths[indices,time].copy()
        intrinsic=np.maximum(contract['strike']-prices,0)
        if time==contract['steps']:
            exercise=np.ones(len(indices),dtype=bool)
        else:
            exercise=np.asarray(policy.exercise(prices,time))
            require(exercise.shape==(len(indices),) and exercise.dtype.kind=='b', 'exercise must return boolean decisions for current states')
        chosen=indices[exercise]
        values[chosen]=intrinsic[exercise]*np.exp(-contract['rate']*time*contract['maturity']/contract['steps'])
        active[chosen]=False
    return values


def bermudan_tree(contract, subdivisions=100):
    steps=contract['steps']*subdivisions
    dt=contract['maturity']/steps
    up=np.exp(contract['volatility']*np.sqrt(dt));down=1/up
    p=(np.exp(contract['rate']*dt)-down)/(up-down)
    require(0<p<1, 'invalid reference tree probability')
    values=np.maximum(contract['strike']-contract['spot']*up**np.arange(steps+1)*down**(steps-np.arange(steps+1)),0)
    for time in range(steps-1,-1,-1):
        values=np.exp(-contract['rate']*dt)*(p*values[1:]+(1-p)*values[:-1])
        if time>0 and time%subdivisions==0:
            prices=contract['spot']*up**np.arange(time+1)*down**(time-np.arange(time+1))
            values=np.maximum(values,contract['strike']-prices)
    return float(values[0])


def stopping_score(fit):
    rows=[]
    for index,spot in enumerate((90.,100.,110.)):
        contract={'spot':spot,'strike':100.,'rate':.05,'volatility':.2,'maturity':1.,'steps':12}
        training=simulate_paths(contract,4096,173+index)
        policy=fit(training,contract.copy())
        require(callable(getattr(policy,'exercise',None)), 'fit must return an object with exercise(current_state,time)')
        evaluation=simulate_paths(contract,8192,814+index)
        payoffs=stopping_payoffs(policy,evaluation,contract)
        # Antithetic pairs are the independent sampling units.
        paired=(payoffs[:4096]+payoffs[4096:])/2
        value=float(payoffs.mean()); standard_error=float(paired.std(ddof=1)/np.sqrt(len(paired)))
        reference=bermudan_tree(contract)
        rows.append({'spot':spot,'payoff':value,'standard_error':standard_error,'tree_reference':reference,'reference_gap':reference-value})
    return float(np.mean([r['payoff'] for r in rows])), {'instances':rows,'calendar':'12 Bermudan dates,first exercise at1/12year; independent fitting/evaluation paths'}
