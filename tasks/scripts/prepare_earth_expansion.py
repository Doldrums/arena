#!/usr/bin/env python3
"""Prepare attributed source bundles for E07–E12; never fabricate missing data."""
from __future__ import annotations

import sys as _task_sys
from pathlib import Path as _TaskPath
_task_sys.path.insert(0, str(_TaskPath(__file__).resolve().parents[1] / "suite" / "_lib"))
from arena_task_paths import cache_path
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'suite/_lib'))
from autoresearch_suite import science_earth_expansion as earth
import numpy as np

DATA = earth.data_directory()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def download(name, url):
    path = DATA/'raw'/name
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        with urllib.request.urlopen(url, timeout=120) as response, path.open('wb') as target:
            shutil.copyfileobj(response, target)
    return path, {'url': url, 'sha256': sha(path), 'filename': name}


def unzip(path, target):
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not (target/name).resolve().is_relative_to(target.resolve()):
                raise ValueError('Unsafe source archive path')
        archive.extractall(target)


def write_bundle(proposal, kind, cases, sources, split, license_note):
    DATA.mkdir(parents=True, exist_ok=True)
    body = {'schema_version':1, 'proposal_id':proposal, 'source_kind':kind, 'sources':sources,
            'split_description':split, 'license':license_note, 'cases':cases}
    path = DATA/f'{proposal}.json'
    path.write_text(json.dumps(body, separators=(',',':'), allow_nan=False)+'\n')
    manifest = {'proposal_id':proposal, 'bundle_sha256':sha(path), 'sources':sources, 'license':license_note,
                'split_description':split, 'case_count':len(cases)}
    (DATA/f'{proposal}.manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    target = cache_path('receipts', 'source-manifests')
    target.mkdir(parents=True,exist_ok=True)
    (target/f'{proposal}.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def prepare_fire():
    import pandas as pd
    path, source = download('firebench.zip', 'https://codeload.github.com/wirc-sjsu/firebench/zip/refs/heads/main')
    unzip(path, DATA/'firebench')
    folder = DATA/'firebench/firebench-main/data/ros_model_validation/Anderson_2015'
    table = pd.read_csv(folder/'data_Table_A1.csv')
    fields = ['wspd','whgt','fmde','fueldepthm','fldry']
    good = np.all(np.isfinite(table[fields+['ros']]) & (table[fields+['ros']] >= 0),axis=1)
    table = table.loc[good].copy()
    table['wspd'] /= 3.6; table['fmde'] /= 100; table['ros'] /= 60
    cases=[]
    for country, group in table.groupby('country'):
        if len(group)<5:continue
        train=table.loc[table.country != country]
        cases.append({'id':'heldout-'+country,'training_features':train[fields].values.tolist(), 'training_rates':train.ros.tolist(),
                      'evaluation_features':group[fields].values.tolist(), 'evaluation_rates':group.ros.tolist(),
                      'metadata':{'feature_names':['measured_wind_m_per_s','wind_measurement_height_m','dead_fuel_moisture_fraction','fuel_height_m','fuel_load_kg_per_m2'],
                                  'wind_height':'measurement height supplied as input; no invented midflame conversion', 'target_units':'m/s',
                                  'training_countries':sorted(train.country.unique().tolist()), 'evaluation_country':country}})
    source['table_sha256']=sha(folder/'data_Table_A1.csv')
    return write_bundle('E07','measured',cases,[source], 'Leave one complete country out; missing/negative measured inputs excluded. No neighboring fire from that country is in training.',
                        'Anderson2015/CSIRO commercial-use permission required; local source review and scientific validation only. Data are cached, not redistributed in the task package.')


def seaice_grid_geometry(x, y, proj4text):
    """Ellipsoidal cell areas for the actual NSIDC grid, not 625 km² constants."""
    from pyproj import CRS, Transformer
    projection = CRS.from_proj4(proj4text)
    inverse = Transformer.from_crs(projection, projection.geodetic_crs, always_xy=True)
    geod = projection.get_geod()
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 2 or len(y) < 2 or not np.allclose(np.diff(x), 25000) or not np.allclose(np.diff(y), -25000):
        raise ValueError('Expected the complete native 25km NSIDC northern grid')
    xx, yy = np.meshgrid(x, y)
    corners_x = xx[..., None] + np.array([-12500, 12500, 12500, -12500])
    corners_y = yy[..., None] + np.array([-12500, -12500, 12500, 12500])
    longitude, latitude = inverse.transform(corners_x, corners_y)
    areas = np.array([abs(geod.polygon_area_perimeter(lon, lat)[0]) / 1e6
                      for lon, lat in zip(longitude.reshape(-1, 4), latitude.reshape(-1, 4))]).reshape(xx.shape)
    if not np.isfinite(areas).all() or np.any(areas <= 0):
        raise ValueError('Invalid geodesic sea-ice cell areas')
    return areas, np.stack([xx, yy], axis=-1) / 1000


def seaice_month(path, year, month):
    """Read the unedited CDR, excluding categorical flags before scaling."""
    from netCDF4 import Dataset
    with Dataset(path) as dataset:
        if dataset.product_version != 'v02r00' or dataset.id != 'G02202':
            raise ValueError('Expected pinned NOAA/NSIDC G02202 v02r00')
        if dataset.time_coverage_start[:7] != f'{year}-{month:02d}' or dataset.time_coverage_duration != 'P1M':
            raise ValueError('Sea-ice source month does not match requested calendar period')
        var = dataset['seaice_conc_monthly_cdr']
        var.set_auto_maskandscale(False)
        raw = np.asarray(var[0]).view(np.uint8)
        if raw.shape != (448, 304):
            raise ValueError('Sea-ice source does not contain the full native northern grid')
        qa = dataset['qa_of_seaice_conc_monthly_cdr']
        qa.set_auto_maskandscale(False)
        quality = np.asarray(qa[0]).view(np.uint8)
        valid = (raw <= 100) & ((quality & 8) == 0) & (np.asarray(dataset['latitude'][:]) >= 60)
        # Zeros outside validity are serialization placeholders, never targets.
        concentration = np.where(valid, raw / 100., 0.)
        return concentration, valid, np.asarray(dataset['xgrid'][:]), np.asarray(dataset['ygrid'][:]), dataset['projection'].proj4text


def prepare_ice():
    """Six monthly Arctic forecasts from observed NOAA CDR maps; no OSISAF substitution claim."""
    pins = json.loads((ROOT/'data/science/earth_expansion/seaice_sources.json').read_text())
    months, sources = {}, []
    geometry = None
    for source in pins['sources']:
        path, receipt = download(source['filename'], source['url'])
        if receipt['sha256'] != source['sha256']:
            raise ValueError('Sea-ice source differs from the reviewed SHA256: ' + source['filename'])
        year, month = source['year'], source['month']
        values, valid, x, y, projection = seaice_month(path, year, month)
        months[year, month] = values, valid
        if geometry is None:
            area, coordinates = seaice_grid_geometry(x, y, projection)
            geometry = x, y, projection
        elif not np.array_equal(x, geometry[0]) or not np.array_equal(y, geometry[1]) or projection != geometry[2]:
            raise ValueError('Sea-ice source grids are misaligned')
        sources.append({**receipt, 'dataset_id': 'G02202', 'product_version': 'v02r00', 'year': year, 'month': month})
    cases = []
    for origin_year in (2013, 2014):
        history = np.stack([months[origin_year, month][0] for month in range(7, 13)])
        history_valid = np.logical_and.reduce([months[origin_year, month][1] for month in range(7, 13)])
        # History contains only cells with an observed value in all six months.
        history[:, ~history_valid] = 0.
        for lead in (1, 3, 6):
            target, target_valid = months[origin_year + 1, lead]
            mask = history_valid & target_valid
            cases.append({'id': f'noaa-cdr-{origin_year}-12-lead{lead}',
                          'history': history.tolist(), 'history_end': f'{origin_year}-12',
                          'target_date': f'{origin_year+1}-{lead:02d}', 'lead_months': lead,
                          'past_covariates': {'history_months': [f'{origin_year}-{month:02d}' for month in range(7, 13)],
                                              'history_ocean_mask': history_valid.tolist(), 'grid_crs': 'EPSG:3411',
                                              'invalid_history_value': '0 is a placeholder outside history_ocean_mask; not an observation',
                                              'covariate_scope': 'known calendar and historical validity mask only; no future measurements'},
                          'concentration': target.tolist(), 'ocean_mask': mask.tolist(),
                          'area_km2': area.tolist(), 'coordinates_km': coordinates.tolist(),
                          'source_dataset': 'NOAA/NSIDC G02202 v02r00, unedited seaice_conc_monthly_cdr'})
    return write_bundle('E08', 'measured', cases, sources,
                        'Six chronological forecasts: July-December2013/2014 measured monthly histories predict January/March/June2014/2015 at1/3/6-month leads. No future fields cross the candidate API. Full native448x304 grid, scoring valid ocean north of60N; land, lakes, coast, pole-hole, missing and near-coast QA excluded. Finite historical placeholders are explicitly masked. Independent new years are required for generalization.',
                        'NOAA/NSIDC G02202 v02r00 files declare no constraints on data access or use. Attribute Meier, Duerr, Fetterer, Stroeve, Savoie and Mallory; NOAA CDR Program and NSIDC. This historical NOAA monthly adaptation does not reproduce IceNet OSISAF training or leaderboard scores.')


def prepare_snow():
    from netCDF4 import Dataset, date2num
    from datetime import datetime
    sources, cases = [], []
    for site,span in [('cdp','1994_2014'),('sod','2007_2014')]:
        files=[]
        for category in ['met','obs']:
            path, source=download(f'snow-{category}-{site}.nc',f'https://hs.pangaea.de/Projects/ESM-SnowMIP/{category}_insitu_{site}_{span}.nc')
            sources.append(source);files.append(path)
        with Dataset(files[0]) as met, Dataset(files[1]) as obs:
            for year in [2008,2010]:
                def selected(dataset):
                    time=dataset['time']; start=date2num(datetime(year,10,1,1),time.units);end=date2num(datetime(year+1,9,30,23),time.units)
                    return np.flatnonzero((time[:]>=start)&(time[:]<=end))
                idx,oidx=selected(met),selected(obs)
                if len(idx)!=len(oidx) or len(idx)<8000:raise ValueError('Snow forcing/observation alignment failed')
                forcing=[]
                temp=np.asarray(met['Tair'][idx])-273.15
                snow=np.asarray(met['Snowf'][idx])*3600
                rain=np.asarray(met['Rainf'][idx])*3600
                if not np.isfinite(temp).all() or np.any(snow<0):raise ValueError('Invalid meteorological forcing')
                for t,s,r in zip(temp,snow,rain):forcing.append({'temperature_c':float(t),'snowfall_mm':float(s),'rainfall_mm':float(r),'dt_hours':1.})
                auto=obs['snw_auto'][oidx].filled(np.nan);manual=obs['snw_man'][oidx].filled(np.nan)
                truth=np.where(np.isfinite(auto),auto,manual)
                mask=np.isfinite(truth)&(truth>=0)&(np.arange(len(truth))>=31*24)
                indices=np.flatnonzero(mask)
                if len(indices)<10:raise ValueError('Insufficient measured SWE')
                cases.append({'id':f'{site}-{year}', 'forcing':forcing, 'initial_swe':0., 'spinup_steps':31*24,
                              'observation_indices':indices.tolist(),'swe_observations':truth[indices].tolist()})
    return write_bundle('E09','measured',cases,sources,'Four complete site-winters: Col de Porte and Sodankyla2008/09,2010/11. First31days warm up; missing observations excluded. Development must use separate years; fixed zero-shot baseline has no fitted parameters.',
                        'Menard and Essery2019, PANGAEA897575, CC-BY-NC4.0. Cached source data for research validation; no dataset redistribution.')


def prepare_groundwater():
    path, source=download('freyberg.zip','https://codeload.github.com/pypest/pyemu_pestpp_workflow/zip/refs/heads/master')
    unzip(path, DATA/'freyberg')
    model_path=DATA/'freyberg/pyemu_pestpp_workflow-master/model_files_lowres'
    path, solver_source=download('mf6.zip','https://codeload.github.com/MODFLOW-ORG/modflow6/zip/refs/tags/6.7.0')
    binary=DATA/'modflow-src/modflow6-6.7.0/bin/mf6'
    if not binary.is_file():
        unzip(path,DATA/'modflow-src')
        with (DATA/'mf6-build.log').open('w') as log:
            subprocess.run(['make','FC=gfortran'],cwd=binary.parent.parent/'make',stdout=log,stderr=subprocess.STDOUT,check=True,timeout=900)
    observations=[[period,2,row,col] for period in [0,12,24] for row,col in [(10,10),(20,10),(30,15)]]
    cases=[]
    hashes={str(p.relative_to(model_path)):sha(p) for p in sorted(model_path.rglob('*')) if p.is_file()}
    for i,parameters in enumerate([[.8,1.1,1.3,.9],[1.2,.9,.8,1.15]]):
        truth,balance=earth.groundwater_forward(parameters,model_path,binary.resolve(),observations)
        rng=np.random.default_rng(740+i)
        cases.append({'id':f'freyberg-source-{i}', 'model_relative_path':str(model_path.relative_to(DATA)),
                      'binary_relative_path':str(binary.relative_to(DATA)), 'binary_sha256':sha(binary), 'model_sha256':hashes,
                      'observations':observations,'noisy_heads':(truth+rng.normal(0,.1,len(truth))).tolist(),
                      'training_indices':list(range(6)), 'evaluation_indices':[6,7,8], 'noise_sd':.1,'budget':8,
                      'generating_parameter_multipliers':parameters,'reference_balance_percent':balance})
    return write_bundle('E11','upstream_simulation',cases,[source,solver_source],
                        'Two source Freyberg aquifer parameter settings; first/midpoint head observations train, final stress-period observations held out. Fixed published pumping/recharge histories. Added independent Gaussian0.1m observation noise; no field-data claim.',
                        'Public USGS model and pyEMU/PEST++ teaching workflow; upstream attribution retained. Model arrays are cached separately.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proposal',required=True,choices=['E07','E08','E09','E10','E11','E12'])
    args=parser.parse_args()
    if args.proposal == 'E12':
        raise SystemExit(args.proposal+' requires a curated upstream regional data bundle; see docs/EARTH_EXPANSION.md. No fabricated fallback is generated.')
    if args.proposal=='E10':
        from aquacrop.utils import get_filepath
        print(json.dumps({'proposal_id':'E10','weather_path':get_filepath('tunis_climate.txt'),'weather_sha256':sha(get_filepath('tunis_climate.txt'))}));return
    result={'E07':prepare_fire,'E08':prepare_ice,'E09':prepare_snow,'E11':prepare_groundwater}[args.proposal]()
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
