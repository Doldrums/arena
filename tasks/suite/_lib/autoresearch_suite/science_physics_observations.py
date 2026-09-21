"""Observation-based physics evaluation: lensing, detectors and interferometry."""
from __future__ import annotations

from .science_physics_expansion import (
    array,
    copy,
    disjoint,
    gaussian_filter,
    math,
    np,
    require,
    time,
    wasserstein_distance,
)

def shear_bias(prediction, truth):
    truth = array(truth, name='true shear')
    prediction = array(prediction, truth.shape, 'estimated shear')
    require(truth.ndim == 2 and truth.shape[1] == 2 and len(truth) >= 6, 'at least six two-component subfields required')
    values = []
    for component in range(2):
        x = np.column_stack((truth[:, component], np.ones(len(truth))))
        require(np.linalg.matrix_rank(x) == 2, 'shear calibration requires distinct true shears')
        slope, additive = np.linalg.lstsq(x, prediction[:, component], rcond=None)[0]
        values.append((float(slope - 1), float(additive)))
    # GREAT3 constant-shear ground branch targets; report biases explicitly.
    m = np.asarray([v[0] for v in values]); c = np.asarray([v[1] for v in values])
    loss = float(np.sum((m / .002)**2 + (c / .0002)**2))
    return 2000 * 1.232 / math.sqrt(4 + loss), {'multiplicative_bias': m.tolist(), 'additive_bias': c.tolist(),
        'metric': 'GREAT3_constant_ground_Qc', 'sigma_min_squared': 4.0, 'adaptation': 'constant ground branch; no variable-shear metric'}


def weak_lensing(candidate, data, metadata):
    images = array(data['images'], name='galaxy images')
    psf = array(data['psf'], name='PSF images')
    require(images.ndim == 4 and len(psf) == len(images), 'images must be subfield, galaxy, y, x and have matching PSFs')
    disjoint(data['development_group_ids'], data['group_ids'], 'noise-cancellation groups')
    output = []
    for i, group in enumerate(data['group_ids']):
        estimate = candidate.estimate_shear(images[i].copy(), psf[i].copy(), {'group_id': str(group),
            'pixel_scale_arcsec': metadata['pixel_scale_arcsec']})
        output.append(array(estimate, (2,), 'subfield shear'))
    angle = array(data['psf_rotation_radians'], (len(output),), 'PSF rotation')
    rotation = np.exp(-2j*angle)
    def rotate(values):
        values=np.asarray(values); z=(values[:,0]+1j*values[:,1])*rotation
        return np.column_stack([z.real,z.imag])
    return shear_bias(rotate(output), rotate(data['true_shear']))


def detection_metrics(background, foreground, injection_times, weights, *, background_seconds, max_far, tolerance):
    """Unique injection association and an independent finite-background FAR cut."""
    background = array(background, name='background detections')
    foreground = array(foreground, name='foreground detections')
    for events in (background, foreground):
        require(events.ndim == 2 and events.shape[1] == 2, 'detections must be (time_seconds, ranking_statistic) rows')
    require(background_seconds * max_far >= 10, 'background is too short: at least 10 expected false alarms at the declared FAR are needed')
    allowed = int(math.floor(max_far * background_seconds))
    ranks = np.sort(background[:, 1])
    threshold = float(ranks[-allowed-1]) if len(ranks) > allowed else -np.inf
    injections = array(injection_times, name='injection times')
    weights = array(weights, injections.shape, 'injection volume weights')
    require(np.all(weights >= 0) and weights.sum() > 0, 'invalid volume weights')
    found = np.zeros(len(injections), dtype=bool)
    for event in foreground[np.argsort(-foreground[:, 1])]:
        if event[1] <= threshold:
            continue
        separation = np.abs(injections - event[0])
        eligible = np.flatnonzero((separation <= tolerance) & ~found)
        if len(eligible):
            found[eligible[np.argmin(separation[eligible])]] = True
    volume = float(weights[found].sum())
    distance = (3 * volume / (4 * np.pi)) ** (1/3)
    return distance, {'sensitive_volume_mpc3': volume, 'recovered_injections': int(found.sum()),
        'injections': len(injections), 'false_alarms': int(np.sum(background[:, 1] > threshold)),
        'background_seconds': float(background_seconds), 'far_resolution_hz': 1/background_seconds,
        'false_alarm_rate_hz': float(np.sum(background[:, 1] > threshold)/background_seconds),
        'ranking_threshold': threshold if np.isfinite(threshold) else None, 'metric': 'sensitive_distance_at_declared_FAR'}


def gravitational_waves(candidate, data, metadata):
    disjoint(data['development_block_ids'], data['test_block_ids'], 'observing-time blocks')
    outputs = []
    for mode in ('background', 'foreground'):
        strain = array(data[mode], name=f'{mode} strain')
        require(strain.ndim == 2 and strain.shape[0] == 2, 'two detector strain channels required')
        output = candidate.search(strain[0].copy(), strain[1].copy(), {
            'sample_rate_hz': metadata['sample_rate_hz'], 'epoch': metadata[mode + '_epoch']})
        events = array(output, name='detections')
        require(events.ndim == 2 and events.shape[1] == 2, 'search returns (time, rank) pairs')
        require(np.all((events[:,0] >= metadata[mode+'_epoch']) &
                       (events[:,0] < metadata[mode+'_epoch'] + strain.shape[1]/metadata['sample_rate_hz'])), 'event time outside supplied block')
        # Collapse multiple triggers from a single local event before counting FAR.
        kept = []
        for index in np.argsort(-events[:,1]):
            if all(abs(events[index,0]-events[j,0]) > metadata['cluster_seconds'] for j in kept):
                kept.append(int(index))
        outputs.append(events[kept] if kept else np.empty((0,2)))
    return detection_metrics(*outputs, data['injection_times'], data['injection_volume_weights'],
        background_seconds=data['background'].shape[1]/metadata['sample_rate_hz'], max_far=metadata['max_far_hz'], tolerance=metadata['match_seconds'])


def decoding_metrics(predicted, truth):
    truth = np.asarray(truth)
    if truth.dtype.kind=='b':truth=truth.astype(np.uint8)
    predicted=np.asarray(predicted)
    if predicted.dtype.kind=='b':predicted=predicted.astype(np.uint8)
    truth = array(truth, name='logical observables')
    require(np.all((truth==0)|(truth==1)), 'logical truth must contain bits')
    predicted = array(predicted, truth.shape, 'logical corrections')
    require(truth.ndim == 2 and len(truth) > 0, 'logical observables require shot and observable axes')
    require(np.all((predicted == 0)|(predicted == 1)), 'logical corrections must be bits')
    failures = np.any(predicted != truth, axis=1)
    n, k = len(failures), int(failures.sum())
    z = 1.959963984540054
    center = (k/n + z*z/(2*n))/(1+z*z/n)
    half = z*math.sqrt((k/n)*(1-k/n)/n+z*z/(4*n*n))/(1+z*z/n)
    return k/n, {'logical_failures': k, 'shots': n, 'wilson_95': [center-half,center+half], 'metric': 'logical_failure_per_complete_shot'}


def surface_code(candidate, data, metadata):
    if 'cases' in metadata:
        scores=[]; records=[]
        for i,case in enumerate(metadata['cases']):
            subset={'train_batch_ids':data['train_batch_ids'],'test_batch_ids':[case['batch_id']],
                'detectors':data[f'detectors_{i}'],'logical_truth':data[f'logical_truth_{i}']}
            score,detail=surface_code(candidate,subset,case);scores.append(score)
            records.append(dict(detail,code_distance=case['code_distance'],batch_id=case['batch_id']))
        return float(np.mean(scores)),{'metric':'macro_acquisition_logical_failure_rate','acquisitions':records,
            'shots':sum(r['shots'] for r in records),'source':'complete released experimental shot batches; no synthetic shots'}
    disjoint(data['train_batch_ids'], data['test_batch_ids'], 'acquisition batches')
    syndrome = array(data['detectors'], name='detector events')
    require(np.all((syndrome == 0)|(syndrome == 1)), 'detector events must be bits')
    start = time.perf_counter()
    prediction = candidate.decode(syndrome.copy(), {'detector_error_model': metadata['detector_error_model'],
        'num_observables': data['logical_truth'].shape[1], 'code_distance': metadata['code_distance']})
    value, details = decoding_metrics(prediction, data['logical_truth'])
    details['decode_seconds'] = time.perf_counter()-start
    return value, details


def shower_features(showers, energy, geometry):
    showers = array(showers, name='showers')
    energy = array(energy, (len(showers),), 'incident energy')
    require(np.all(showers >= 0) and np.all(energy > 0), 'energy deposits must be nonnegative; incident energies positive')
    require(showers.ndim == 2 and len(geometry['layer']) == showers.shape[1], 'voxel geometry does not match showers')
    layer = np.asarray(geometry['layer']); x = np.asarray(geometry['x']); y = np.asarray(geometry['y'])
    values = [showers.sum(axis=1)/energy, (showers == 0).mean(axis=1)]
    for level in np.unique(layer):
        mask = layer == level
        weight = showers[:,mask]; deposited = weight.sum(axis=1); safe = np.maximum(deposited, 1e-12)
        mx = weight @ x[mask]/safe; my = weight @ y[mask]/safe
        values.extend([deposited/energy, mx, my, np.sqrt(np.maximum(0,weight @ (x[mask]**2)/safe-mx**2)),
                       np.sqrt(np.maximum(0,weight @ (y[mask]**2)/safe-my**2))])
    return np.column_stack(values)


def calorimeter(candidate, data, metadata):
    disjoint(data['train_event_ids'], data['test_event_ids'], 'shower events')
    training = {'showers':data['train_showers'].copy(), 'incident_energies':data['train_energy'].copy(), 'geometry':copy.deepcopy(metadata['geometry'])}
    sampler = candidate.fit_showers(training)
    require(callable(sampler), 'fit_showers must return a callable sampler(incident_energies, rng)')
    start = time.perf_counter()
    generated = array(sampler(data['test_energy'].copy(),np.random.default_rng(14191)),data['test_showers'].shape,'generated showers')
    seconds = time.perf_counter()-start
    reference = shower_features(data['test_showers'],data['test_energy'],metadata['geometry'])
    proposed = shower_features(generated,data['test_energy'],metadata['geometry'])
    losses = []
    for energy in np.unique(data['test_energy']):
        a = reference[data['test_energy']==energy]; b = proposed[data['test_energy']==energy]
        require(len(a) >= 16, 'at least 16 reference showers per energy required')
        scales = np.maximum(np.std(a,axis=0),1e-6)
        losses.append(float(np.mean([wasserstein_distance(a[:,j],b[:,j])/scales[j] for j in range(a.shape[1])])))
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    rng = np.random.default_rng(8191); order = rng.permutation(len(reference)); split = len(order)//2
    train,test = order[:split],order[split:]
    classifier = make_pipeline(StandardScaler(),LogisticRegression(max_iter=300,C=.2,random_state=8191))
    classifier.fit(np.concatenate([reference[train],proposed[train]]),np.r_[np.zeros(len(train)),np.ones(len(train))])
    discrimination = roc_auc_score(np.r_[np.zeros(len(test)),np.ones(len(test))],
        classifier.predict_proba(np.concatenate([reference[test],proposed[test]]))[:,1])
    return float(np.mean(losses)), {'metric':'mean_per_energy_standardized_feature_Wasserstein',
        'classifier_auc_diagnostic':float(discrimination), 'sampling_seconds':seconds, 'showers':len(generated),
        'adaptation':'CPU source-data subset; independent HLF-inspired metric, not the full CaloChallenge leaderboard'}


def trackml_score(particle, weights, labels):
    """TrackML's strict two-sided majority rule, independently implemented."""
    particle = np.asarray(particle,dtype=np.int64)
    weights = array(weights,particle.shape,'truth weights')
    labels = array(labels,particle.shape,'track IDs')
    require(np.all(labels == np.floor(labels)) and np.all(labels >= 0) and np.all(labels < 2**53), 'track IDs must be nonnegative safe integers')
    require(np.all(weights >= 0) and abs(weights.sum()-1) < 1e-5, 'event truth weights must sum to one')
    _,part_idx,part_counts = np.unique(particle,return_inverse=True,return_counts=True)
    _,track_idx,track_counts = np.unique(labels.astype(np.int64),return_inverse=True,return_counts=True)
    pairs,inverse,pair_counts = np.unique(np.column_stack([part_idx,track_idx]),axis=0,return_inverse=True,return_counts=True)
    good = (2*pair_counts > part_counts[pairs[:,0]]) & (2*pair_counts > track_counts[pairs[:,1]])
    accepted = good[inverse] & (particle != 0)
    return float(weights[accepted].sum())


def tracking(candidate,data,metadata):
    disjoint(data['development_event_ids'],data['event_ids'],'TrackML events')
    scores = []
    for i,event_id in enumerate(data['event_ids']):
        hits = data[f'hits_{i}']; cells=data[f'cells_{i}']
        labels = candidate.assign_tracks(hits.copy(),cells.copy(),{'detector':data['detector'].copy(),'event_id':int(event_id),
            'hit_columns':['hit_id','x','y','z','volume_id','layer_id','module_id'],'cell_columns':['hit_id','ch0','ch1','value']})
        scores.append(trackml_score(data[f'particle_{i}'],data[f'weights_{i}'],labels))
    return float(np.mean(scores)),{'metric':'mean_official_weighted_majority_match','events':len(scores),'event_scores':scores}


def collider_metrics(truth,scores,mass):
    from sklearn.metrics import roc_auc_score
    truth = array(truth,name='truth'); scores=array(scores,truth.shape,'anomaly scores'); mass=array(mass,truth.shape,'dijet mass')
    require(np.all((truth==0)|(truth==1)) and len(np.unique(truth))==2,'both signal and background needed')
    bg=scores[truth==0]; sig=scores[truth==1]
    allowed=math.floor(.05*len(bg)); require(allowed>=1,'too few background events')
    threshold=np.sort(bg)[-allowed-1]; selected=bg>threshold
    fpr=float(selected.mean()); tpr=float(np.mean(sig>threshold))
    edges=np.quantile(mass[truth==0],np.linspace(0,1,11)); edges=np.unique(edges)
    all_hist,_=np.histogram(mass[truth==0],edges); pass_hist,_=np.histogram(mass[truth==0][selected],edges)
    expected=all_hist*fpr; sculpt=float(np.sum((pass_hist-expected)**2/(expected+1))/(max(1,len(edges)-2)))
    sic=tpr/math.sqrt(max(fpr,1/len(bg)))
    return sic/(1+sculpt),{'metric':'SIC_at_5percent_background_divided_by_1_plus_mass_sculpting',
        'signal_efficiency':tpr,'background_efficiency':fpr,'sic':sic,'mass_sculpting_chi2_per_bin':sculpt,
        'auc':float(roc_auc_score(truth,scores)),'discovery_claim':False}


def collider(candidate,data,metadata):
    disjoint(data['train_event_ids'],data['test_event_ids'],'collider events')
    disjoint(data['null_event_ids'],data['test_event_ids'],'null/test collider events')
    disjoint(data['null_event_ids'],data['train_event_ids'],'null/training collider events')
    ranker=candidate.fit(data['control_features'].copy())
    require(hasattr(ranker,'score'),'fit must return an object exposing score(events)')
    scores=ranker.score(data['test_features'].copy())
    value,details=collider_metrics(data['truth'],scores,data['mass'])
    null=array(ranker.score(data['null_features'].copy()),(len(data['null_features']),),'no-signal scores')
    # Null behavior is a distribution-shift diagnostic, never a discovery p value.
    bg=np.asarray(scores)[data['truth']==0]; threshold=np.quantile(bg,.95)
    details['null_acceptance_at_test_threshold']=float(np.mean(null>threshold))
    return value,details


def crps(samples, truth):
    """Proper scalar posterior score, O(n log n), no pairwise allocation."""
    x = np.sort(array(samples, name='posterior samples'))
    require(x.ndim == 1 and len(x) >= 16, 'at least 16 posterior samples required')
    n = len(x)
    return float(np.mean(np.abs(x-truth)) - np.sum((2*np.arange(n)-n+1)*x)/(n*n))


def lens_forward(parameters, config):
    """Independent lenstronomy imaging/Fermat and dynamical forward likelihood."""
    from copy import deepcopy
    from astropy.cosmology import FlatLambdaCDM
    from lenstronomy.Data.imaging_data import ImageData
    from lenstronomy.Data.psf import PSF
    from lenstronomy.LensModel.lens_model import LensModel
    from lenstronomy.LightModel.light_model import LightModel
    from lenstronomy.PointSource.point_source import PointSource
    from lenstronomy.ImSim.image_model import ImageModel
    from lenstronomy.Analysis.kinematics_api import KinematicsAPI
    kwargs = deepcopy(config['model_parameters'])
    for value, binding in zip(parameters[1:], config['bindings']):
        group, index, key = binding
        kwargs[group][index][key] = float(value)
    cosmology = FlatLambdaCDM(H0=70, Om0=.27)
    zd,zs = config['z_lens'],config['z_source']
    dd = cosmology.angular_diameter_distance(zd).value
    ds = cosmology.angular_diameter_distance(zs).value
    dds = cosmology.angular_diameter_distance_z1z2(zd,zs).value
    ddt_reference = (1+zd)*dd*ds/dds
    cosmology = FlatLambdaCDM(H0=70*ddt_reference/parameters[0],Om0=.27)
    model = config['kwargs_model']
    lens=LensModel(model['lens_model_list'])
    image=ImageModel(ImageData(**config['kwargs_data']),PSF(**config['kwargs_psf']),lens,
        LightModel(model.get('source_light_model_list',[])),LightModel(model.get('lens_light_model_list',[])),
        PointSource(model.get('point_source_model_list',[]),lens_model=lens),kwargs_numerics=config.get('kwargs_numerics',{}))
    prediction=image.image(kwargs_lens=kwargs['lens'],kwargs_source=kwargs['source'],
                           kwargs_lens_light=kwargs['lens_light'],kwargs_ps=kwargs.get('point_source'))
    positions=np.asarray(config['image_positions'])
    fermat=lens.fermat_potential(positions[:,0],positions[:,1],kwargs['lens'])
    # Mpc/c to days, angular arcsecond squared to radians squared.
    delays=(fermat[1:]-fermat[0])*parameters[0]*3.085677581491367e19/299792.458/86400*(np.pi/(180*3600))**2
    api=KinematicsAPI(zd,zs,model,config['kwargs_aperture'],config['kwargs_seeing'],
        config.get('anisotropy_model','OM'),cosmo=cosmology,
        kwargs_numerics_galkin=config.get('kwargs_numerics_galkin',{}))
    dispersion=api.velocity_dispersion(kwargs['lens'],kwargs['lens_light'],config['kwargs_anisotropy'],
        r_eff=config['r_eff'],theta_E=kwargs['lens'][0]['theta_E'],gamma=kwargs['lens'][0].get('gamma',2))
    return {'image':np.asarray(prediction),'time_delays':np.asarray(delays),'velocity_dispersion':float(np.asarray(dispersion).mean())}


def strong_lensing(candidate,data,metadata):
    disjoint(data['development_lens_ids'],data['lens_ids'],'whole lens systems')
    scores=[]; diagnostics=[]
    require(metadata.get('rung') in (1,2), 'Rung 3 is not accurate enough for percent-level distance validation')
    for i,config in enumerate(metadata['cases']):
        bounds=np.asarray(config['bounds']); calls=0
        def forward(values):
            nonlocal calls
            calls+=1; require(calls<=config.get('forward_budget',2000),'forward-model budget exceeded')
            p=array(values,(len(bounds),),'physical lens parameters')
            require(np.all((p>=bounds[:,0])&(p<=bounds[:,1])),'lens parameters outside specified prior')
            return lens_forward(p,config)
        public={'parameter_names':config['parameter_names'],'bounds':bounds.tolist(),'forward':forward,
                'kinematics_sigma':config['kinematics_sigma'],'delay_sigma':config['delay_sigma'],
                'image_sigma':data[f'noise_{i}'].copy()}
        samples=array(candidate.infer_distance(data[f'image_{i}'].copy(),np.array(config['kwargs_psf']['kernel_point_source'],copy=True),
            data[f'delays_{i}'].copy(),data[f'kinematics_{i}'].copy(),copy.deepcopy(public)),name='distance and nuisance posterior')
        require(samples.ndim==2 and samples.shape[1]==len(bounds) and 32<=len(samples)<=4096,'return 32..4096 joint physical posterior samples')
        require(np.all((samples>=bounds[:,0])&(samples<=bounds[:,1])),'posterior outside physical priors')
        truth=float(data['true_ddt'][i]); normalized=crps(samples[:,0],truth)/truth
        residual=[]
        for p in samples[np.linspace(0,len(samples)-1,16).astype(int)]:
            predicted=lens_forward(p,config)
            residual.append(np.mean(((predicted['image']-data[f'image_{i}'])/data[f'noise_{i}'])**2)+
                np.mean(((predicted['time_delays']-data[f'delays_{i}'])/config['delay_sigma'])**2)+
                ((predicted['velocity_dispersion']-float(data[f'kinematics_{i}']))/config['kinematics_sigma'])**2)
        low,high=np.quantile(samples[:,0],[.05,.95])
        scores.append(normalized + .01*math.log1p(float(np.mean(residual))))
        diagnostics.append({'relative_crps':normalized,'relative_bias':float(samples[:,0].mean()/truth-1),
            'relative_width_90':float((high-low)/truth),'covers_truth_90':bool(low<=truth<=high),
            'forward_chi2_sum_per_channel':float(np.mean(residual)),'candidate_forward_calls':calls})
    return float(np.mean(scores)),{'metric':'relative_distance_CRPS_plus_forward_predictive_penalty','lenses':diagnostics,
        'coverage_90':float(np.mean([d['covers_truth_90'] for d in diagnostics]))}


def exoplanets(candidate,data,metadata):
    """Explicit cached TauREx forward-grid adaptation, no interpolated toy spectra."""
    disjoint(data['train_planet_ids'],data['planet_ids'],'complete planets')
    scores=[]; details=[]
    for i,config in enumerate(metadata['cases']):
        grid=data[f'grid_parameters_{i}']; spectra=data[f'grid_spectra_{i}']; bounds=np.asarray(config['bounds'])
        require(grid.shape[0]==spectra.shape[0] and np.all(np.isfinite(spectra)),'invalid source TauREx grid')
        require(grid.ndim==2 and grid.shape[1]==len(bounds),'parameter dimensions disagree')
        require(np.all((grid>=bounds[:,0])&(grid<=bounds[:,1])),'forward grid outside prior bounds')
        require(np.all(data[f'uncertainty_{i}']>0),'spectral errors must be positive')
        public=dict(config['planet_metadata'],parameter_names=config['parameter_names'],bounds=bounds.tolist(),
                    forward_grid_parameters=grid.copy(),forward_grid_spectra=spectra.copy())
        result=candidate.retrieve(data[f'spectrum_{i}'].copy(),data[f'uncertainty_{i}'].copy(),public)
        indices=array(result,name='TauREx grid posterior indices')
        require(indices.ndim==1 and 32<=len(indices)<=4096 and np.all(indices==np.floor(indices)), 'return 32..4096 integer grid sample indices (repetition allowed)')
        require(np.all((indices>=0)&(indices<len(grid))),'posterior indices outside forward grid')
        indices=indices.astype(int); samples=grid[indices]; reference=data[f'reference_posterior_{i}']; truth=data[f'truth_{i}']
        ranges=bounds[:,1]-bounds[:,0]; require(np.all(ranges>0),'invalid prior bounds')
        calibration=np.mean([crps(samples[:,j],truth[j])/ranges[j] for j in range(len(ranges))])
        discrepancy=np.mean([wasserstein_distance(samples[:,j],reference[:,j])/ranges[j] for j in range(len(ranges))])
        chi2=np.mean(((spectra[indices]-data[f'spectrum_{i}'])/data[f'uncertainty_{i}'])**2)
        scores.append(float(calibration+discrepancy+.01*np.log1p(chi2)))
        lo,hi=np.quantile(samples,[.05,.95],axis=0)
        details.append({'parameter_coverage_90':((lo<=truth)&(truth<=hi)).tolist(),'normalized_crps':float(calibration),
                        'reference_posterior_Wasserstein':float(discrepancy),'posterior_predictive_chi2_per_bin':float(chi2)})
    return float(np.mean(scores)),{'metric':'grid_posterior_calibration_reference_agreement_and_spectral_likelihood','planets':details,
        'adaptation':'posterior resampling on source TauREx grid, not continuous atmospheric retrieval; grid/opacity versions fixed'}


def visibility_forward(image,uv,pixel_radians):
    image=array(image,name='sky brightness'); uv=array(uv,name='uv baselines')
    require(image.ndim==2 and image.shape[0]==image.shape[1],'square image required')
    positions=(np.arange(image.shape[0])-(image.shape[0]-1)/2)*pixel_radians
    x,y=np.meshgrid(positions,positions,indexing='xy'); output=[]
    for block in np.array_split(uv,max(1,math.ceil(len(uv)/128))):
        output.extend(np.exp(-2j*np.pi*(block[:,0,None]*x.ravel()+block[:,1,None]*y.ravel()))@image.ravel())
    return np.asarray(output)


def interferometry(candidate,data,metadata):
    disjoint(data['development_source_ids'],data['source_ids'],'source models')
    disjoint(data['development_schedule_ids'],data['schedule_ids'],'observing schedules')
    losses=[]; details=[]
    for i,config in enumerate(metadata['cases']):
        public={'uv':data[f'uv_{i}'].copy(),'amplitudes':data[f'amplitude_{i}'].copy(),
            'closure_triangles':data[f'triangles_{i}'].copy(),'closure_phases':data[f'closure_phase_{i}'].copy()}
        image=array(candidate.reconstruct(public,copy.deepcopy(config),{'amplitude_sigma':data[f'amplitude_sigma_{i}'].copy(),
            'closure_sigma':data[f'closure_sigma_{i}'].copy()}),(config['pixels'],config['pixels']),'reconstructed image')
        require(np.all(image>=0),'sky brightness must be nonnegative')
        require(abs(image.sum()/config['flux_jy']-1)<.01,'image integrated flux outside 1 percent calibration constraint')
        predicted=visibility_forward(image,data[f'uv_{i}'],config['pixel_radians'])
        amp_chi2=np.mean(((np.abs(predicted)-data[f'amplitude_{i}'])/data[f'amplitude_sigma_{i}'])**2)
        # Triangles use signed one-based visibility indices, sign reverses baseline.
        triangles=data[f'triangles_{i}'].astype(int); oriented=predicted[np.abs(triangles)-1]
        oriented=np.where(triangles>0,oriented,np.conjugate(oriented))
        closure=np.angle(np.prod(oriented,axis=1)); error=np.angle(np.exp(1j*(closure-data[f'closure_phase_{i}'])))
        closure_chi2=np.mean((error/data[f'closure_sigma_{i}'])**2)
        truth=data[f'truth_image_{i}']; blur=config['resolution_fwhm_pixels']/math.sqrt(8*math.log(2))
        a=gaussian_filter(image,blur,mode='constant'); b=gaussian_filter(truth,blur,mode='constant')
        # Source-defined image centre is fixed; no candidate-dependent alignment.
        nrmse=float(np.linalg.norm(a-b)/np.linalg.norm(b))
        losses.append(nrmse+.01*np.log1p(amp_chi2+closure_chi2))
        details.append({'blurred_image_nrmse':nrmse,'amplitude_chi2_per_datum':float(amp_chi2),'closure_chi2_per_datum':float(closure_chi2)})
    return float(np.mean(losses)),{'metric':'resolution_matched_NRMSE_plus_amplitude_closure_penalty','cases':details}
