"""Source-data Earth science protocols E01--E06, with no synthetic fallback."""
from __future__ import annotations

from arena_task_paths import cache_path
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import numpy as np
from .runtime import CandidateError, require

ROOT=Path(__file__).resolve().parents[3]


def finite(value,shape=None,nonnegative=False):
    raw=np.asarray(value)
    require(raw.dtype.kind in 'fiu' and not np.iscomplexobj(raw),'Expected real numerical output')
    x=raw.astype(float)
    require(np.isfinite(x).all(),'Output contains nonfinite values')
    if shape is not None:require(x.shape==tuple(shape),f'Expected shape{shape}; got{x.shape}')
    if nonnegative:require(np.all(x>=0),'Expected nonnegative values')
    return x


def load_bundle(proposal):
    directory=Path(os.environ.get('SCIEL_EARTH_DATA',str(cache_path('science-earth-data'))))
    path=directory/f'{proposal}.json';manifest=directory/f'{proposal}.manifest.json'
    if not path.exists() or not manifest.exists():raise RuntimeError(f'{proposal} requires source data; missing{path}. Run scripts/prepare_earth_data.py --proposal {proposal}; see docs/EARTH_DATA.md.')
    raw=path.read_bytes();receipt=json.loads(manifest.read_text());data=json.loads(raw)
    require(hashlib.sha256(raw).hexdigest()==receipt.get('bundle_sha256'),'Prepared source checksum mismatch')
    require(data.get('proposal_id')==proposal and data.get('schema_version')==1,'Wrong source bundle schema')
    require(data.get('source_kind') in ['measured','reanalysis','upstream_simulation','mixed'],'Test fixtures are not source benchmarks')
    require(data.get('cases') and data.get('split_description') and data.get('sources'),'Incomplete source provenance/cases')
    for source in data['sources']:require(source.get('url','').startswith('https://') and re.fullmatch('[a-f0-9]{64}',source.get('sha256','')),'Source URL and SHA256 required')
    return data


def nash_sutcliffe(truth,prediction):
    truth,prediction=finite(truth),finite(prediction,np.shape(truth),True)
    denominator=np.sum((truth-truth.mean())**2)
    require(len(truth)>=2 and denominator>0,'Streamflow reference must have variation')
    return float(1-np.sum((prediction-truth)**2)/denominator)


def runoff_score(module,cases):
    results=[]
    for c in cases:
        predictor=module.fit_runoff(copy.deepcopy(c['training_basins']))
        for basin in c['evaluation_basins']:
            forcing=finite(basin['forcing']);observed=finite(basin['discharge'])
            require(len(forcing)==len(observed),'Forcing/discharge length mismatch')
            state={'storage_mm':0.0};discharge=[];residuals=[]
            for day in range(len(forcing)):
                previous=float(state['storage_mm'])
                # Retrospective daily simulation sees current forcing and past
                # forcing only, never discharge or future meteorological forcing.
                output=predictor(forcing[max(0,day-364):day+1].copy(),copy.deepcopy(basin['attributes']),copy.deepcopy(state))
                require(isinstance(output,dict),'Runoff output must be dict discharge_mm,evapotranspiration_mm,state')
                q=float(finite([output['discharge_mm']],(1,),True)[0]);evap=float(finite([output['evapotranspiration_mm']],(1,),True)[0])
                state=copy.deepcopy(output['state']);storage=float(finite([state['storage_mm']],(1,),True)[0])
                # P is column0 in mm/day. All storage pools (snow, soil, etc.)
                # belong in total storage_mm for an auditable water balance.
                residual=previous+forcing[day,0]-q-evap-storage
                require(abs(residual)<=1e-5,'Daily catchment water balance violated')
                discharge.append(q);residuals.append(abs(residual))
            prediction=np.array(discharge)
            mask=np.array(basin['evaluation_mask'],bool)
            require(mask.shape==observed.shape and mask.any() and np.all(observed[mask]>=0),'Invalid discharge evaluation mask')
            truth=observed[mask];pred=prediction[mask];nse=nash_sutcliffe(truth,pred)
            hi=truth>=np.quantile(truth,.9);lo=truth<=np.quantile(truth,.1)
            results.append({'basin':basin['id'],'nse':nse,'rmse_mm_day':float(np.sqrt(np.mean((pred-truth)**2))),'high_flow_bias_mm_day':float(np.mean(pred[hi]-truth[hi])),'low_flow_bias_mm_day':float(np.mean(pred[lo]-truth[lo])),'cumulative_discharge_bias_mm':float(np.sum(pred-truth)),'max_daily_balance_residual_mm':max(residuals)})
    return float(np.mean([r['nse'] for r in results])),{'basins':results,'forcing_semantics':'retrospective same-day meteorology, causal state update; not a future-weather forecast'}


def flux_score(module,cases):
    results=[]
    for c in cases:
        model=module.fit_flux(copy.deepcopy(c['training_sites']))
        for site in c['evaluation_sites']:
            weather=finite(site['meteorology']);truth=finite(site['flux']);quality=np.asarray(site['quality_flag'])
            prediction=finite(model.predict_flux(weather.copy(),copy.deepcopy(site['metadata']),copy.deepcopy(site.get('history',{}))),truth.shape)
            require(quality.shape==truth.shape,'Flux quality mask shape mismatch')
            # This interface accepts half-hourly FLUXNET NEE_VUT_REF_QC:
            #0 denotes measured values; gap-filled values1/2/3 never score.
            good=(quality==0) & np.asarray(site['evaluation_mask'],bool)
            require(good.any(),'No quality-controlled measured flux targets')
            scale=float(c['training_target_std']);require(scale>0,'Training target scale must be positive')
            error=prediction[good]-truth[good]
            results.append({'site':site['id'],'measured_points':int(good.sum()),'normalized_rmse':float(np.sqrt(np.mean(error**2))/scale),'bias':float(error.mean()),'mae':float(np.abs(error).mean())})
    return float(np.mean([r['normalized_rmse'] for r in results])),{'sites':results,'quality_policy':'Only half-hourlyQC0 targets; no gap-filled target credit'}


def ensemble_crps(observation,ensemble):
    y=finite(observation);x=finite(ensemble)
    require(y.ndim==1 and x.ndim==2 and x.shape[0]==len(y) and 1<=x.shape[1]<=128,'Expected n observations and n x1..128 ensemble')
    # E|X-y| - .5 E|X-X'|, exact empirical ensemble distribution.
    ordered=np.sort(x,axis=1);m=x.shape[1]
    pair_term=np.sum(ordered*(2*np.arange(m)-m+1),axis=1)/(m*m)
    return np.mean(np.abs(x-y[:,None]),axis=1)-pair_term


def weather_score(module,cases):
    results=[]
    for c in cases:
        forecast=finite(c['forecast']);truth=finite(c['truth']);n=len(truth)
        output=module.calibrate(forecast.copy(),finite(c['lead_hours']).copy(),finite(c['locations']).copy(),copy.deepcopy(c['training_history']))
        calibrated=finite(output)
        crps=ensemble_crps(truth,calibrated);raw=ensemble_crps(truth,forecast)
        weights=finite(c['sample_weights'],(n,),True);require(weights.sum()>0,'Zero weather weights')
        threshold=float(c['training_extreme_threshold'])
        probabilities=np.mean(calibrated>threshold,axis=1)
        brier=np.average((probabilities-(truth>threshold))**2,weights=weights)
        results.append({'region_lead':c['id'],'crps':float(np.average(crps,weights=weights)),'raw_crps':float(np.average(raw,weights=weights)),'extreme_brier':float(brier),'extreme_threshold_from_training':threshold})
    return float(np.mean([r['crps'] for r in results])),{'cases':results,'truth_kind':'ERA5 reanalysis, not raw independent measurements'}


def trusted_simulator(spec):
    path=Path(spec['path']).resolve()
    require(path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==spec['sha256'],'Source-specific forward simulator absent or changed')
    loader=importlib.util.spec_from_file_location('earth_trusted_'+spec['sha256'][:10],path);module=importlib.util.module_from_spec(loader);loader.loader.exec_module(module)
    return module


def seismic_score(module,cases):
    results=[]
    for c in cases:
        traces=finite(c['traces']);truth=finite(c['velocity']);geometry=copy.deepcopy(c['geometry']);budget=int(c.get('budget',16));calls=[0]
        forward=trusted_simulator(c['forward_model']).simulate
        lower,upper=map(float,c['velocity_bounds'])
        def validate(v):
            v=finite(v,truth.shape);require(np.all(v>=lower) and np.all(v<=upper),'Seismic velocity bounds violated');return v
        def oracle(v):
            calls[0]+=1;require(calls[0]<=budget,'Wave-equation call budget exhausted')
            return finite(forward(validate(v).copy(),copy.deepcopy(geometry)),traces.shape)
        velocity=validate(module.invert_seismograms(traces.copy(),copy.deepcopy(geometry),oracle,budget))
        reproduced=finite(forward(velocity.copy(),copy.deepcopy(c['geometry'])),traces.shape)
        scale=max(float(np.mean(truth**2)),1e-20);nmse=float(np.mean((velocity-truth)**2)/scale)
        gradient_error=np.mean([(a-b)**2 for a,b in zip(np.gradient(velocity),np.gradient(truth))])
        waveform_nmse=float(np.mean((reproduced-traces)**2)/max(np.mean(traces**2),1e-20))
        results.append({'geology':c['id'],'velocity_nrmse':float(np.sqrt(nmse)),'gradient_rmse':float(np.sqrt(gradient_error)),'independent_waveform_nmse':waveform_nmse,'candidate_forward_calls':calls[0]})
    return float(np.mean([r['velocity_nrmse'] for r in results])),{'models':results,'source_kind':'OpenFWI simulated survey; no field observation claim'}


def climate_metrics(truth,prediction,latitude_weights):
    truth=finite(truth);prediction=finite(prediction,truth.shape)
    require(truth.ndim==3,'Climate field shape must be year x latitude x longitude')
    weights=finite(latitude_weights,(truth.shape[1],),True)
    require(weights.sum()>0,'Zero climate latitude weights')
    weights2=np.broadcast_to(weights[:,None],truth.shape[1:]);weights2=weights2/weights2.sum()
    truth_global=np.sum(truth*weights2,axis=(1,2));prediction_global=np.sum(prediction*weights2,axis=(1,2))
    normalization=abs(float(np.mean(truth_global)));require(normalization>1e-12,'ClimateBench normalization is zero')
    spatial=float(np.sqrt(np.sum((truth.mean(axis=0)-prediction.mean(axis=0))**2*weights2))/normalization)
    global_=float(np.sqrt(np.mean((truth_global-prediction_global)**2))/normalization)
    return {'spatial_nrmse':spatial,'global_nrmse':global_,'total_nrmse':spatial+5*global_}


def climate_score(module,cases):
    results=[]
    for c in cases:
        training=copy.deepcopy(c['training_scenarios'])
        model=module.fit_climate(training,copy.deepcopy(c['grid']))
        for scenario in c['evaluation_scenarios']:
            prediction=model.project_climate(copy.deepcopy(scenario['forcing']))
            require(isinstance(prediction,dict) and set(prediction)==set(scenario['fields']),'Return exactly declared climate variables')
            mask=np.asarray(scenario['evaluation_mask'],bool)
            for variable,truth in scenario['fields'].items():
                truth=finite(truth);pred=finite(prediction[variable],truth.shape)
                require(mask.shape==(len(truth),) and mask.any(),'Invalid climate year mask')
                metric=climate_metrics(truth[mask],pred[mask],c['grid']['latitude_weights'])
                results.append({'scenario':scenario['id'],'variable':variable,**metric})
    return float(np.mean([r['total_nrmse'] for r in results])),{'variables':results,'metric':'ClimateBench spatialNRMSE+5*globalNRMSE, mean across declared variables; source coarse-grid adaptation'}


def ocean_score(module,cases):
    results=[]
    for c in cases:
        observed=finite(c['observations']);coordinates=finite(c['coordinates']);times=finite(c['times']);grid=copy.deepcopy(c['grid']);truth=finite(c['truth'])
        require(len(observed)==len(coordinates)==len(times),'Ocean observation coordinate lengths differ')
        prediction=finite(module.reconstruct_ssh(observed.copy(),times.copy(),coordinates.copy(),grid),truth.shape)
        error=prediction-truth
        result={'region':c['id'],'rmse_m':float(np.sqrt(np.mean(error**2))),'mae_m':float(np.abs(error).mean()),'bias_m':float(error.mean()),'verification_regime':c['verification_regime']}
        if 'segments' in c:
            gradients=[]
            for segment in c['segments']:
                indices=np.asarray(segment['indices'],int);distance=finite(segment['distance_km'])
                require(np.all(np.diff(distance)>0),'Along-track distances must increase')
                gradients.extend((np.diff(prediction[indices]-truth[indices])/np.diff(distance)).tolist())
            if gradients:result['along_track_gradient_rmse_m_per_km']=float(np.sqrt(np.mean(np.array(gradients)**2)))
        results.append(result)
    return float(np.mean([r['rmse_m'] for r in results])),{'regions':results,'interpretation':'OSE measured independent-track error has incomplete truth; OSSE full-field truth must be labeled separately'}


SCORERS={'E01':runoff_score,'E02':flux_score,'E03':weather_score,'E04':seismic_score,'E05':climate_score,'E06':ocean_score}


def evaluate(proposal,module,parameters):
    data=load_bundle(proposal);score,details=SCORERS[proposal](module,data['cases'])
    return score,{**details,'source_kind':data['source_kind'],'split_description':data['split_description'],'fixture_validation':False}
