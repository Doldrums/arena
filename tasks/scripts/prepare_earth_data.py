#!/usr/bin/env python3
"""Prepare genuine compact Earth science source protocols, never fake datasets.

Automatic: E01 CAMELS measured source subset, E03 WeatherBench ensemble/ERA5,
E05 ClimateBench complete scenarios, E06 independent OceanBench satellites.
E02/E04 accept reviewed source bundles after acquisition/forward-model setup.
"""

import sys as _task_sys
from pathlib import Path as _TaskPath
_task_sys.path.insert(0, str(_TaskPath(__file__).resolve().parents[1] / "suite" / "_lib"))
from arena_task_paths import cache_path
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
CACHE=cache_path('earth-sources')
MANIFEST=ROOT/'data/science/earth_data/sources.json'
OUTPUT=cache_path('science-earth-data')
AUTOMATIC=('E01','E03','E05','E06')


def checksum(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def acquire(names,offline=False):
    spec=json.loads(MANIFEST.read_text());sources=[];groups={}
    CACHE.mkdir(exist_ok=True,parents=True)
    for name in names:
        p=CACHE/name;r=spec[name]
        if p.exists():
            if checksum(p)!=r['sha256']:raise ValueError('Modified source '+name)
        elif offline:raise FileNotFoundError('Missing pinned source '+str(p))
        elif r.get('member'):groups.setdefault(r['url'],[]).append(name)
        else:
            tmp=p.with_suffix(p.suffix+'.download')
            with urllib.request.urlopen(r['url'],timeout=60) as response,tmp.open('wb') as output:
                total=0
                while chunk:=response.read(1024*1024):
                    total+=len(chunk)
                    if total>r['bytes']+1:raise ValueError('Unexpected source size '+name)
                    output.write(chunk)
            if checksum(tmp)!=r['sha256']:tmp.unlink();raise ValueError('Source checksum mismatch '+name)
            tmp.replace(p)
        sources.append({'url':r['url'],'sha256':r['sha256'],'name':name,**({'archive_member':r['member'],'sha256_scope':'extracted_member'} if r.get('member') else {})})
    for url,missing in groups.items():
        wanted={spec[n]['member']:n for n in missing}
        with urllib.request.urlopen(url,timeout=60) as response,tarfile.open(fileobj=response,mode='r|gz') as archive:
            for entry in archive:
                if entry.name not in wanted:continue
                name=wanted.pop(entry.name);target=CACHE/name;tmp=target.with_suffix('.download')
                if entry.size != spec[name]['bytes']:raise ValueError('Unexpected archive member size')
                with archive.extractfile(entry) as source,tmp.open('wb') as output:
                    while chunk:=source.read(1024*1024):output.write(chunk)
                if checksum(tmp)!=spec[name]['sha256']:tmp.unlink();raise ValueError('Archive member checksum mismatch')
                tmp.replace(target)
                if not wanted:break
        if wanted:raise ValueError('Missing archive entries '+str(wanted))
    return sources


def prepare_camels(offline):
    sources=acquire(['camels.zip'],offline);basins=[]
    with zipfile.ZipFile(CACHE/'camels.zip') as z:
        prefix=next(x for x in z.namelist() if x.endswith('test/test_data/camels_us/'))
        tops={r['gauge_id']:r for r in csv.DictReader(io.StringIO(z.read(prefix+'camels_attributes_v2.0/camels_topo.txt').decode()),delimiter=';')}
        for identifier in ['01022500','01547700','02064000','03015500']:
            text=z.read(prefix+'basin_mean_forcing/daymet/'+identifier+'_lump_cida_forcing_leap.txt').decode().splitlines();area=float(text[2]);forcing=np.loadtxt(io.StringIO('\n'.join(text[4:])))
            qrows=[line.split() for line in z.read(prefix+'usgs_streamflow/'+identifier+'_streamflow_qc.txt').decode().splitlines() if line.strip()]
            q_by_date={(int(r[1]),int(r[2]),int(r[3])):(float(r[4]),r[5]) for r in qrows}
            dates=[tuple(map(int,row[:3])) for row in forcing];valid=[i for i,d in enumerate(dates) if d in q_by_date]
            q=np.array([q_by_date[dates[i]][0] for i in valid])*0.028316846592*86400/area*1000
            attributes={k:float(v) for k,v in tops[identifier].items() if k!='gauge_id'}
            x=forcing[valid];features=np.column_stack([x[:,5],(x[:,8]+x[:,9])/2,x[:,6]])
            years=x[:,0].astype(int);observed=np.maximum(q,0)
            # Explicit source estimated-flow values are excluded from scoring.
            good=np.array([q_by_date[dates[i]][0]>=0 and q_by_date[dates[i]][1]=='A' for i in valid])
            basins.append({'id':identifier,'forcing':features.tolist(),'discharge':observed.tolist(),'attributes':attributes,'dates':['%04d-%02d-%02d'%dates[i] for i in valid],'evaluation_mask':((years==2002)&good).tolist(),'training_mask':((years<=2001)&good).tolist()})
    training=[]
    for basin in basins[:2]:
        indices=[i for i,d in enumerate(basin['dates']) if d<'2002-01-01']
        training.append({'id':basin['id'],'forcing':[basin['forcing'][i] for i in indices],'discharge':[basin['discharge'][i] for i in indices],'quality_mask':[basin['training_mask'][i] for i in indices],'attributes':basin['attributes'],'dates':[basin['dates'][i] for i in indices]})
    cases=[{'training_basins':training,'evaluation_basins':basins[2:]}]
    return package('E01','measured',sources,cases,'Official NeuralHydrology distribution of measured CAMELS-US/Daymet subset. Training basins01022500/01547700 years2000–2001; unseen basins02064000/03015500 evaluated only in2002 after full2000–2001 forcing warmup. Only unestimated USGSA discharge observations score. No hydro/runoff-derived attributes provided.')


def weather_sources():
    return [n for n in json.loads(MANIFEST.read_text()) if n.startswith('wb_') or n in ['ifs-zmetadata.json','era-zmetadata.json']]


def prepare_weather(offline):
    sources=acquire(weather_sources(),offline)
    from numcodecs import get_codec
    metadata={k:json.loads((CACHE/(k+'-zmetadata.json')).read_text())['metadata'] for k in ['ifs','era']}
    memo={}
    def chunk(dataset,var,index):
        key=(dataset,var,tuple(index))
        if key not in memo:
            name='wb_'+dataset+'_'+var+'__'+'.'.join(map(str,index))+'.bin';spec=metadata[dataset][var+'/.zarray'];raw=(CACHE/name).read_bytes();raw=get_codec(spec['compressor']).decode(raw) if spec['compressor'] else raw;memo[key]=np.frombuffer(raw,dtype=spec['dtype']).reshape(spec['chunks'])
        return memo[key]
    ifstime=chunk('ifs','time',[0]);leads=chunk('ifs','prediction_timedelta',[0]);leadindex=int(np.flatnonzero(leads==24)[0]);lat=chunk('ifs','latitude',[0]);lon=chunk('ifs','longitude',[0])
    if not np.allclose(lat,chunk('era','latitude',[0])) or not np.allclose(lon,chunk('era','longitude',[0])):raise ValueError('Forecast/reanalysis coordinates differ')
    lon_index=np.arange(0,64,8);lat_index=np.arange(2,32,4);locations=np.array([[lat[j],lon[i]] for i in lon_index for j in lat_index]);weights=np.cos(np.deg2rad(locations[:,0]));groups={}
    for year in [2018,2019]:
        forecasts=[];truths=[];valid_dates=[]
        for month in range(1,13):
            date=dt.datetime(year,month,1);ih=int((date-dt.datetime(2018,1,1)).total_seconds()/3600);i=int(np.flatnonzero(ifstime==ih)[0]);valid=date+dt.timedelta(days=1);eh=int((valid-dt.datetime(1959,1,1)).total_seconds()/3600);e=eh//6
            if chunk('era','time',[e//23386])[e%23386] != eh:raise ValueError('Reanalysis valid-time alignment mismatch')
            forecast=chunk('ifs','2m_temperature',[i//4,0,leadindex,0,0])[i%4,:,0]
            truth=chunk('era','2m_temperature',[e//100,0,0])[e%100]
            forecasts.append(forecast[:,lon_index][:,:,lat_index].reshape(50,-1).T);truths.append(truth[np.ix_(lon_index,lat_index)].ravel());valid_dates.extend([valid.isoformat()]*len(locations))
        groups[year]={'forecast':np.concatenate(forecasts).tolist(),'truth':np.concatenate(truths).tolist(),'valid_dates':valid_dates}
    n=len(groups[2019]['truth']);c={'id':'IFS50 t2m24h monthly2019 lowres global sample','forecast':groups[2019]['forecast'],'truth':groups[2019]['truth'],'lead_hours':[24]*n,'locations':np.tile(locations,(12,1)).tolist(),'sample_weights':np.tile(weights,12).tolist(),'training_history':groups[2018],'evaluation_valid_dates':groups[2019]['valid_dates'],'training_extreme_threshold':float(np.quantile(groups[2018]['truth'],.95))}
    return package('E03','reanalysis',sources,[c],'WeatherBench2 IFS50-member2m-temperature forecasts at24h on64×32 grid. One initialization/month in2018 for calibration; corresponding months in2019 for evaluation, eight longitudes×eight latitudes. Valid times are explicitly matched to ERA5. Training-only95th-percentile threshold. Small chronological source subset, not full leaderboard/reliability claim. TIGGE research-use restrictions apply.')


def prepare_climate(offline):
    names=[f'{prefix}_{scenario}.nc' for scenario in ['historical','ssp126','ssp370','ssp585','ssp245'] for prefix in ['inputs','outputs']]
    sources=acquire(names,offline)
    import netCDF4
    scenarios={};grid=None
    for scenario in ['historical','ssp126','ssp370','ssp585','ssp245']:
        with netCDF4.Dataset(CACHE/f'inputs_{scenario}.nc') as d:
            lat=np.array(d['latitude'][:]);lon=np.array(d['longitude'][:]);weights=np.cos(np.deg2rad(lat));years=np.array(d['time'][:],int)
            aerosol=[np.sum(np.asarray(d[k][:])*weights[None,:,None],axis=(1,2))/(weights.sum()*len(lon)) for k in ['SO2','BC']]
            forcing=np.column_stack([d['CO2'][:],d['CH4'][:],*aerosol]);fields={}
        w=weights.reshape(8,12)
        with netCDF4.Dataset(CACHE/f'outputs_{scenario}.nc') as d:
            if not np.array_equal(d['time'][:],years):raise ValueError('Climate input/output time mismatch')
            if not np.allclose(d['lat'][:],lat) or not np.allclose(d['lon'][:],lon):raise ValueError('Climate input/output grid mismatch')
            for variable in ['tas','pr']:
                full=np.nanmean(np.asarray(d[variable][:],float),axis=0)
                if not np.isfinite(full).all():raise ValueError('No available climate member at a required grid/time point')
                coarsened=np.einsum('tiajb,ia->tij',full.reshape(len(years),8,12,12,12),w)/(w.sum(axis=1)[None,:,None]*12)
                fields[variable]=(coarsened*(86400 if variable=='pr' else 1)).tolist()
        scenarios[scenario]={'id':scenario,'forcing':{'values':forcing.tolist(),'years':years.tolist(),'columns':['cumulative_CO2_GtCO2','CH4_GtCH4_per_year','SO2_source_global_mean','BC_source_global_mean']},'fields':fields,'evaluation_mask':((years>=2080)&(years<=2100)).tolist()}
        grid={'latitudes':(np.sum(lat.reshape(8,12)*w,axis=1)/w.sum(axis=1)).tolist(),'longitudes':lon.reshape(12,12).mean(axis=1).tolist(),'latitude_weights':w.sum(axis=1).tolist(),'shape':[8,12],'variables':{'tas':'temperature anomalyK','pr':'precipitation anomalymm/day'}}
    cases=[{'training_scenarios':[scenarios[x] for x in ['historical','ssp126','ssp370','ssp585']],'evaluation_scenarios':[scenarios['ssp245']],'grid':grid}]
    return package('E05','upstream_simulation',sources,cases,'Complete SSP245 withheld; historical,SSP126,SSP370,SSP585 train. Available-source-member mean (SSP370 has missing members after2054), cos-latitude area-weighted12×12 block coarsening to8×12; tas/pr anomalies only. Evaluate2080–2100 with published spatialNRMSE+5globalNRMSE definitions. Independent simulations, not observations or full-resolution four-variable leaderboard.')


def prepare_ocean(offline):
    names=['gf_2017_l3_j2n.nc','gf_2017_l3_j3.nc'];sources=acquire(names,offline)
    import netCDF4
    data=[]
    for name in names:
        with netCDF4.Dataset(CACHE/name) as d:
            dates=netCDF4.num2date(d['time'][:],units=d['time'].units,only_use_cftime_datetimes=False)
            epoch=dt.datetime(2017,1,1);time=np.array([(x-epoch).total_seconds()/86400 for x in dates]);lat=np.asarray(d['latitude'][:]);lon=np.asarray(d['longitude'][:]);sla=np.asarray(d['sla_filtered'][:]);track=np.asarray(d['track'][:]);cycle=np.asarray(d['cycle'][:])
            valid=(time>=0)&(time<31)&np.isfinite(sla)&(np.abs(sla)<10)&np.isfinite(lat)&np.isfinite(lon)
            indices=np.flatnonzero(valid)[::4] # source-ordered decimation, no target-value ranking
            data.append({'time':time[indices],'coords':np.column_stack([lat[indices],lon[indices]]),'sla':sla[indices],'track':track[indices],'cycle':cycle[indices]})
    train,test=data
    if not len(train['time']) or not len(test['time']):raise ValueError('No declared January2017 tracks')
    c={'id':'GulfStream January2017 Jason2N toJason3','observations':train['sla'].tolist(),'times':train['time'].tolist(),'coordinates':train['coords'].tolist(),'grid':{'times':test['time'].tolist(),'coordinates':test['coords'].tolist(),'epoch':'2017-01-01','datum':'source filteredSLA meters'},'truth':test['sla'].tolist(),'verification_regime':'OSE measured entire independentJason3 satellite withheld'}
    return package('E06','measured',sources,[c],'Real GulfStream OceanBenchOSE: source Jason2N observations reconstruct source Jason3 points for January2017. Whole satellite withheld, source-order decimation every4 samples. Retrospective same-time independent-track validation; no full-field/OSSE truth, held-out-year transfer or resolved spectral-scale claim. FilteredSLA meters, not absolute dynamic topography.')


def package(proposal,kind,sources,cases,split):return {'schema_version':1,'proposal_id':proposal,'source_kind':kind,'sources':sources,'cases':cases,'split_description':split}


def write_bundle(data,output):
    proposal=data['proposal_id']
    if proposal not in [f'E{i:02}' for i in range(1,7)] or data.get('source_kind') not in ['measured','reanalysis','upstream_simulation','mixed']:raise ValueError('Unknown proposal or non-source dataset')
    if not data.get('cases') or not data.get('sources') or not data.get('split_description'):raise ValueError('Incomplete source provenance')
    output.mkdir(exist_ok=True,parents=True);raw=(json.dumps(data,indent=2,allow_nan=False)+'\n').encode();(output/f'{proposal}.json').write_bytes(raw)
    receipt={'proposal_id':proposal,'bundle_sha256':hashlib.sha256(raw).hexdigest(),'source_kind':data['source_kind'],'sources':data['sources'],'preparation_script':'scripts/prepare_earth_data.py','source_validation':'pending actual evaluator run'}
    (output/f'{proposal}.manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return {'proposal_id':proposal,'bytes':len(raw),'cases':len(data['cases']),'sha256':receipt['bundle_sha256']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--proposal',choices=[f'E{i:02}' for i in range(1,7)]);p.add_argument('--all',action='store_true');p.add_argument('--offline',action='store_true');p.add_argument('--import-bundle',type=Path);p.add_argument('--output',type=Path,default=OUTPUT);args=p.parse_args()
    if args.import_bundle:print(json.dumps(write_bundle(json.loads(args.import_bundle.read_text()),args.output)));return
    targets=AUTOMATIC if args.all else [args.proposal] if args.proposal else []
    if not targets:p.error('Choose --proposal, --all, or --import-bundle')
    methods={'E01':prepare_camels,'E03':prepare_weather,'E05':prepare_climate,'E06':prepare_ocean}
    for proposal in targets:
        if proposal not in methods:raise SystemExit(f'{proposal} needs reviewed source data/forward setup; see docs/EARTH_DATA.md and --import-bundle.')
        print(json.dumps(write_bundle(methods[proposal](args.offline),args.output)))

if __name__=='__main__':main()
