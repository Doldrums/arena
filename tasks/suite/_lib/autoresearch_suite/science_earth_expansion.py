"""Source-based wildfire, cryosphere, agriculture and inverse-model tasks.

Dataset loaders fail closed. Metric fixtures do not create benchmark evidence.
Candidate access is cooperative; these Python APIs are not security sandboxes.
"""
from __future__ import annotations

from arena_task_paths import cache_path, receipt_path

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import numpy as np
from scipy.special import logsumexp
from scipy.spatial import cKDTree
from .runtime import CandidateError, require

ROOT = Path(__file__).resolve().parents[3]


def numeric(value, shape=None):
    raw = np.asarray(value)
    require(raw.dtype.kind in 'fiu', 'Expected real numerical values')
    out = raw.astype(float)
    require(np.isfinite(out).all(), 'Nonfinite numerical values')
    if shape is not None:
        require(out.shape == tuple(shape), f'Expected shape {shape}, got {out.shape}')
    return out


def data_directory():
    return Path(os.environ.get('SCIEL_EARTH_DATA', cache_path('science-earth')))


def load_bundle(proposal):
    directory = data_directory()
    path, receipt_path = directory / f'{proposal}.json', directory / f'{proposal}.manifest.json'
    if not path.is_file() or not receipt_path.is_file():
        raise RuntimeError(f'{proposal} requires source setup: python scripts/prepare_earth_expansion.py --proposal {proposal}; see docs/EARTH_EXPANSION.md')
    raw = path.read_bytes()
    receipt, data = json.loads(receipt_path.read_text()), json.loads(raw)
    require(hashlib.sha256(raw).hexdigest() == receipt['bundle_sha256'], 'Earth source bundle checksum mismatch')
    require(data['proposal_id'] == proposal and data['schema_version'] == 1, 'Incorrect source bundle schema')
    require(data['source_kind'] in ('measured', 'upstream_simulation', 'mixed'), 'Test fixtures cannot be benchmark data')
    require(bool(data['cases']) and bool(data['split_description']) and bool(data['sources']), 'Incomplete source dataset')
    for source in data['sources']:
        require(source['url'].startswith('https://') and re.fullmatch('[0-9a-f]{64}', source['sha256']), 'Unpinned source data')
    return data


def fire_baseline(training, target, metadata):
    x = numeric(training)
    design = np.c_[np.ones(len(x)), np.log1p(np.maximum(x, 0))]
    coef = np.linalg.solve(design.T @ design + np.eye(design.shape[1]) * .1, design.T @ np.log1p(target))
    class Law:
        def spread_rate(self, features):
            features = np.asarray(features)
            return np.maximum(np.expm1(np.c_[np.ones(len(features)), np.log1p(np.maximum(features, 0))] @ coef), 0)
    return Law()


def fire_score(fit, cases):
    results = []
    for c in cases:
        model = fit(numeric(c['training_features']).copy(), numeric(c['training_rates']).copy(), copy.deepcopy(c['metadata']))
        truth = numeric(c['evaluation_rates'])
        prediction = numeric(model.spread_rate(numeric(c['evaluation_features']).copy()), truth.shape)
        require(np.all(prediction >= 0), 'Spread rate must be nonnegative m/s')
        results.append({'study': c['id'], 'rmse_m_per_s': float(np.sqrt(np.mean((prediction-truth)**2))), 'bias_m_per_s': float(np.mean(prediction-truth)), 'n': len(truth)})
    return float(np.mean([r['rmse_m_per_s'] for r in results])), {'studies': results, 'aggregation': 'equal held-out-study weight; empirical measured-input law, no unmeasured slope or wind conversion'}


def ice_metrics(probability, truth, area, mask, coordinates):
    truth = numeric(truth)
    p, area = numeric(probability, truth.shape), numeric(area, truth.shape)
    mask = np.asarray(mask, dtype=bool)
    require(mask.shape == truth.shape and mask.any(), 'Invalid sea-ice ocean mask')
    require(np.all((p >= 0) & (p <= 1)) and np.all((truth == 0) | (truth == 1)), 'Ice probabilities in [0,1] and binary presence required')
    require(np.all(area[mask] > 0), 'Positive grid-cell areas required')
    brier = float(np.average((p[mask]-truth[mask])**2, weights=area[mask]))
    predicted, actual = (p >= .5) & mask, (truth > 0) & mask
    # Symmetric contour distance, with no-edge cases explicitly undefined.
    from scipy.ndimage import binary_dilation
    # An ice edge borders open ocean, not land or the cropped domain boundary.
    pe = predicted & binary_dilation(mask & ~predicted)
    te = actual & binary_dilation(mask & ~actual)
    coords = numeric(coordinates, truth.shape + (2,))
    distance = None
    if pe.any() and te.any():
        distance = .5 * (cKDTree(coords[te]).query(coords[pe])[0].mean() + cKDTree(coords[pe]).query(coords[te])[0].mean())
    return {'brier': brier, 'symmetric_edge_distance_km': None if distance is None else float(distance)}


def ice_baseline(history, climate_covariates, lead_months):
    history = np.asarray(history)
    # Persistence with a fixed probability floor/ceiling; no future covariates.
    return np.where(history[-1] >= .15, .9, .1)


def ice_score(forecast, cases):
    results = []
    for c in cases:
        history = numeric(c['history'])
        require(c['history_end'] < c['target_date'], 'Sea-ice history reaches the forecast target')
        require(history.ndim == 3 and len(history) > 0 and np.all((history >= 0) & (history <= 1)), 'Sea-ice history must be monthly concentration grids in [0,1]')
        origin_year, origin_month = map(int, c['history_end'][:7].split('-'))
        target_year, target_month = map(int, c['target_date'][:7].split('-'))
        lead = c['lead_months']
        require(isinstance(lead, int) and not isinstance(lead, bool) and lead > 0 and
                12*(target_year-origin_year)+target_month-origin_month == lead, 'Sea-ice forecast lead does not match calendar dates')
        probability = forecast(history.copy(), copy.deepcopy(c['past_covariates']), lead)
        truth = numeric(c['concentration']) >= .15
        require(history.shape[1:] == truth.shape, 'Sea-ice history and target grids differ')
        result = ice_metrics(probability, truth.astype(float), c['area_km2'], c['ocean_mask'], c['coordinates_km'])
        mask = np.asarray(c['ocean_mask'], dtype=bool)
        results.append({'period': c['id'], 'history_end': c['history_end'], 'target_date': c['target_date'],
                        'lead_months': lead, 'evaluated_cells': int(mask.sum()),
                        'evaluated_area_km2': float(numeric(c['area_km2'])[mask].sum()), **result})
    return float(np.mean([r['brier'] for r in results])), {'periods': results, 'threshold_concentration': .15}


def snow_baseline(meteorology, snow_state, site_parameters):
    available = snow_state['swe'] + meteorology['snowfall_mm']
    melt = min(available, max(meteorology['temperature_c'], 0) * 3 * meteorology['dt_hours'] / 24)
    return {'swe': available - melt, 'melt': melt, 'sublimation': 0.0}


def snow_trajectory(step, forcing, initial_swe=0.0):
    state, trajectory, balance = {'swe': float(initial_swe)}, [], []
    for row in forcing:
        result = step(copy.deepcopy(row), state.copy(), {'units': 'mm water equivalent', 'model': 'solid snow storage; melt drains immediately'})
        values = numeric([result['swe'], result['melt'], result['sublimation']], (3,))
        require(np.all(values >= 0), 'Negative snow mass or outgoing water flux')
        error = state['swe'] + row['snowfall_mm'] - values.sum()
        require(abs(error) <= 1e-6 * max(1, state['swe'] + row['snowfall_mm']), 'Snow water balance violated')
        state = {'swe': float(values[0])}
        trajectory.append(state['swe']); balance.append(abs(error))
    return np.array(trajectory), max(balance, default=0)


def snow_score(step, cases):
    results = []
    for c in cases:
        trajectory, balance = snow_trajectory(step, c['forcing'], c.get('initial_swe', 0))
        indices = np.asarray(c['observation_indices'], dtype=int)
        require(len(indices) and np.all((indices >= c['spinup_steps']) & (indices < len(trajectory))), 'Snow observation indices overlap spinup or leave trajectory')
        truth = numeric(c['swe_observations'], indices.shape)
        error = trajectory[indices] - truth
        observed_snow = np.flatnonzero(truth > 1)
        predicted_snow = np.flatnonzero(trajectory[indices] > 1)
        timing = None
        if len(observed_snow) and len(predicted_snow) and observed_snow[-1] < len(indices)-1:
            timing = abs(indices[observed_snow[-1]] - indices[predicted_snow[-1]]) / 24
        results.append({'site_winter': c['id'], 'rmse_mm': float(np.sqrt(np.mean(error**2))), 'bias_mm': float(error.mean()), 'last_snow_timing_error_days': timing, 'maximum_water_balance_residual_mm': balance, 'observations': len(indices)})
    return float(np.mean([r['rmse_mm'] for r in results])), {'sites': results, 'scope': 'solid storage mass balance; no energy conservation or complete FSM2 reproduction claim'}


def irrigation_baseline(history, soil_state, crop_stage, remaining_water):
    root = np.maximum(soil_state['root_fraction'], 0)
    depletion = np.sum(np.maximum(soil_state['field_capacity'] - soil_state['water_content'], 0) * root)
    capacity = np.sum((soil_state['field_capacity'] - soil_state['wilting_point']) * root)
    return min(20., remaining_water) if capacity > 0 and depletion > .45 * capacity else 0.


def irrigation_season(policy, year, soil_name, allowance=150.):
    from aquacrop import AquaCropModel, Soil, Crop, InitialWaterContent, IrrigationManagement
    from aquacrop.utils import get_filepath, prepare_weather
    import importlib.metadata
    require(importlib.metadata.version('aquacrop') == '3.0.12', 'AquaCrop-OSPy3.0.12 required')
    path = Path(get_filepath('tunis_climate.txt'))
    model = AquaCropModel(sim_start_time=f'{year}/10/01', sim_end_time=f'{year+1}/07/01',
                         weather_df=prepare_weather(str(path)), soil=Soil(soil_name), crop=Crop('Wheat', planting_date='10/01'),
                         initial_water_content=InitialWaterContent(value=['FC']),
                         irrigation_management=IrrigationManagement(5, depth=0, MaxIrr=25, MaxIrrSeason=allowance))
    model._initialize()
    applied, decisions = 0., 0
    while not model._clock_struct.model_is_finished:
        day = model._clock_struct.step_start_time
        profile, condition = model.soil.profile, model._init_cond
        root_fraction = np.maximum(np.minimum(profile['zBot'].to_numpy(), max(condition.z_root, .3)) - profile['z_top'].to_numpy(), 0)
        state = {'water_content': condition.th.copy(), 'field_capacity': profile['th_fc'].to_numpy().copy(),
                 'wilting_point': profile['th_wp'].to_numpy().copy(), 'root_fraction': root_fraction.copy()}
        # At start of day only previous weather is known. Future rows never cross API.
        history = model.weather_df.loc[model.weather_df.Date < day].copy(deep=True)
        amount = numeric(policy(history, state, {'date': str(day.date()), 'stage': condition.growth_stage, 'days_after_planting': condition.dap}, allowance-applied))
        require(amount.shape == () and 0 <= amount <= min(25., allowance-applied)+1e-9, 'Irrigation violates daily or seasonal allocation')
        amount = float(amount)
        before = float(condition.irr_cum)
        model._param_struct.IrrMngt.depth = amount
        model.run_model(num_steps=1, initialize_model=False)
        increment = float(model._init_cond.irr_cum) - before
        require(increment >= -1e-7 and increment <= amount+1e-6, 'Simulator irrigation accounting disagrees with requested action')
        applied += max(increment, 0); decisions += 1
        require(decisions <= 300 and applied <= allowance+1e-6, 'Season failed to terminate or exceeded water budget')
    stats = model.get_simulation_results()
    yield_tonnes = float(stats['Dry yield (tonne/ha)'].iloc[0])
    require(np.isfinite(yield_tonnes) and yield_tonnes >= 0, 'Invalid crop yield')
    return {'year': year, 'soil': soil_name, 'yield_tonnes_per_hectare': yield_tonnes, 'irrigation_mm': applied, 'days': decisions,
            'weather_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def irrigation_score(policy):
    rows = [irrigation_season(policy, year, soil) for year, soil in [(1981, 'SandyLoam'), (1983, 'ClayLoam'), (1985, 'SandyLoam')]]
    return float(np.mean([r['yield_tonnes_per_hectare'] for r in rows])), {'seasons': rows, 'seasonal_allocation_mm': 150,
        'scope': 'three fixed Tunis weather years and wheat; simulated yield, not measured agronomic benefit'}


def predictive_metrics(truth, ensemble, noise_sd):
    truth, ensemble = numeric(truth), numeric(ensemble)
    require(ensemble.ndim == 2 and ensemble.shape[1] == len(truth) and len(ensemble) >= 2, 'Predictive ensemble must be samples x observations')
    sd = np.broadcast_to(numeric(noise_sd), truth.shape)
    require(np.all(sd > 0), 'Positive observation noise required')
    log_density = -.5 * ((ensemble-truth)/sd)**2 - np.log(sd*np.sqrt(2*np.pi))
    nll = -float(np.mean(logsumexp(log_density, axis=0)-np.log(len(ensemble))))
    # Predictive intervals include declared independent observation noise.
    rng = np.random.default_rng(389)
    draws = ensemble[np.arange(4096) % len(ensemble)] + rng.normal(size=(4096,len(truth))) * sd
    low, high = np.quantile(draws, [.05,.95], axis=0)
    return {'negative_log_predictive_density': nll, 'coverage90': float(np.mean((truth >= low) & (truth <= high))), 'interval_width90': float(np.mean(high-low))}


def groundwater_forward(parameters, model_directory, binary, observations):
    """Actual MF6 Freyberg model; four positive multipliers (3 K layers, recharge)."""
    os.environ.setdefault('MPLCONFIGDIR', str(cache_path('matplotlib')))
    import flopy
    parameters = numeric(parameters, (4,))
    require(np.all((parameters >= .5) & (parameters <= 2)), 'Aquifer multipliers outside[.5,2]')
    require(Path(binary).is_file(), 'MODFLOW6 binary missing')
    with tempfile.TemporaryDirectory(prefix='sciel-mf6-') as tmp:
        shutil.copytree(model_directory, tmp, dirs_exist_ok=True)
        model = flopy.mf6.MFSimulation.load(sim_ws=tmp, exe_name=binary, verbosity_level=0)
        # Source teaching tolerances permit percent-scale balance errors. Tighten
        # the fixed reference solver before either generating or scoring heads.
        model.ims.outer_dvclose.set_data(1e-7)
        model.ims.inner_dvclose.set_data(1e-8)
        model.ims.rcloserecord.set_data([('inner_rclose', 1e-5, 'strict')])
        model.ims.outer_maximum.set_data(300)
        model.ims.inner_maximum.set_data(300)
        gwf = model.get_model()
        k = gwf.npf.k.get_data().copy()
        for layer in range(3): k[layer] *= parameters[layer]
        gwf.npf.k.set_data(k)
        recharge = gwf.rch.recharge.get_data()
        gwf.rch.recharge.set_data({period: values * parameters[3] for period,values in recharge.items()})
        model.write_simulation(silent=True)
        process = subprocess.run([str(binary)], cwd=tmp, capture_output=True, timeout=45)
        require(process.returncode == 0 and b'Normal termination' in process.stdout, 'MODFLOW forward model failed')
        heads = gwf.output.head().get_alldata()
        prediction = np.array([heads[tuple(index)] for index in observations])
        require(np.isfinite(prediction).all() and np.all(np.abs(prediction) < 1e20), 'Dry/inactive or invalid head observation')
        listing = (Path(tmp) / 'freyberg6.lst').read_text()
        errors = re.findall(r'PERCENT DISCREPANCY\s*=\s*([-+\d.Ee]+)', listing)
        balance = max((abs(float(v)) for v in errors), default=float('inf'))
        require(balance <= .01, 'Groundwater mass balance exceeds0.01percent')
        return prediction, balance


def groundwater_baseline(head_observations, geometry, oracle, budget):
    rng = np.random.default_rng(614)
    points = np.vstack([np.ones(4), rng.uniform(.85,1.2,(max(2,budget)-1,4))])
    accepted = []
    for point in points:
        try:
            loss = float(np.mean((oracle(point)-head_observations)**2))
            accepted.append((loss,point))
        except CandidateError:
            continue  # A numerically invalid trial still consumes its oracle call.
    require(bool(accepted), 'No feasible groundwater baseline trial')
    chosen = [p for _,p in sorted(accepted,key=lambda x:x[0])[:4]]
    return np.array(chosen if len(chosen)>1 else chosen*2)


def groundwater_score(infer, cases):
    rows = []
    for c in cases:
        directory = data_directory() / c['model_relative_path']
        binary = data_directory() / c['binary_relative_path']
        require(hashlib.sha256(binary.read_bytes()).hexdigest() == c['binary_sha256'], 'MODFLOW binary hash changed')
        for rel, sha in c['model_sha256'].items():
            require(hashlib.sha256((directory/rel).read_bytes()).hexdigest() == sha, 'Freyberg input hash changed: '+rel)
        train, evaluation = c['training_indices'], c['evaluation_indices']
        require(not set(train) & set(evaluation), 'Groundwater training/evaluation observations overlap')
        observations = c['observations']; truth = numeric(c['noisy_heads'])
        calls = [0]
        def oracle(x):
            calls[0] += 1
            require(calls[0] <= c['budget'], 'MODFLOW oracle budget exceeded')
            return groundwater_forward(x, directory, binary, [observations[i] for i in train])[0]
        ensemble = numeric(infer(truth[train].copy(), {'parameter_bounds': [[.5,2]]*4, 'description': '3conductivity-layer and1recharge multipliers', 'noise_sd': c['noise_sd']}, oracle, c['budget']))
        require(ensemble.ndim == 2 and ensemble.shape[1] == 4 and 2 <= len(ensemble) <= 8, 'Return2..8parameter samples of four multipliers')
        predictions, balances = [], []
        for params in ensemble:
            values, balance = groundwater_forward(params, directory, binary, [observations[i] for i in evaluation])
            predictions.append(values); balances.append(balance)
        metrics = predictive_metrics(truth[evaluation], predictions, c['noise_sd'])
        rows.append({'case': c['id'], **metrics, 'search_forward_calls': calls[0], 'verification_forward_calls': len(ensemble), 'max_mass_balance_error_percent': max(balances)})
    return float(np.mean([r['negative_log_predictive_density'] for r in rows])), {'cases': rows, 'scope': 'synthetic Freyberg teaching aquifer; predictive uncertainty under fixed observation-noise assumptions'}


def methane_baseline(columns, operator, prior, uncertainty):
    h, y, mean = np.asarray(operator), np.asarray(columns), np.asarray(prior['mean'])
    p = np.asarray(prior['covariance'])
    r = np.diag(np.asarray(uncertainty['observation_sd'])**2)
    gain = np.linalg.solve(h@p@h.T+r, h@p).T
    posterior_mean = np.maximum(mean + gain@(y-h@mean), 0)
    covariance = p - gain@h@p
    rng = np.random.default_rng(73)
    samples = rng.multivariate_normal(posterior_mean, (covariance+covariance.T)/2, size=64)
    return np.maximum(samples, 0)


def methane_score(infer, cases):
    rows = []
    for c in cases:
        h = numeric(c['transport_operator']); y = numeric(c['columns']); sd = numeric(c['observation_sd'], y.shape)
        train, test = np.asarray(c['training_indices'],int), np.asarray(c['evaluation_indices'],int)
        require(h.ndim == 2 and h.shape[0] == len(y) and not set(train)&set(test), 'Invalid methane transport or split')
        require(set(np.asarray(c['orbit_ids'])[train]).isdisjoint(np.asarray(c['orbit_ids'])[test]), 'Methane observations from the same orbit cross the split')
        require(c['averaging_kernels_applied'] is True and c['quality_mask_applied'] is True, 'IMI operator must include retrieval kernels and quality screening')
        background = numeric(c['background'], y.shape)
        ensemble = numeric(infer((y-background)[train].copy(), h[train].copy(), copy.deepcopy(c['prior']), {'observation_sd': sd[train].copy()}))
        require(ensemble.ndim == 2 and ensemble.shape[1] == h.shape[1] and 2 <= len(ensemble) <= 1024 and np.all(ensemble >= 0), 'Return2..1024nonnegative emission samples')
        metrics = predictive_metrics(y[test], ensemble@h[test].T+background[test], sd[test])
        rows.append({'case': c['id'], **metrics, 'mean_total_emissions': float(ensemble.mean(axis=0).sum()), 'truth_scope': 'held-out satellite columns; emission map has no exact measured truth'})
    return float(np.mean([r['negative_log_predictive_density'] for r in rows])), {'cases': rows, 'scope': 'fixed linearized GEOS-Chem sensitivities; no full-transport posterior-calibration claim'}


def score(proposal, module):
    if proposal == 'E10':
        return irrigation_score(module.irrigate)
    bundle = load_bundle(proposal)
    functions = {'E07': (fire_score, 'fit_spread'), 'E08': (ice_score, 'forecast_ice'), 'E09': (snow_score, 'snow_step'), 'E11': (groundwater_score, 'infer_aquifer'), 'E12': (methane_score, 'infer_emissions')}
    evaluator, name = functions[proposal]
    value, details = evaluator(getattr(module,name), bundle['cases'])
    details['source_data'] = {'sources': bundle['sources'], 'split_description': bundle['split_description'], 'bundle_sha256': hashlib.sha256((data_directory()/f'{proposal}.json').read_bytes()).hexdigest()}
    return value, details
