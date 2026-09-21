#!/usr/bin/env python3
"""Reproduce the P08 source-model check; a mismatch never becomes a benchmark pass.

Run in a separate environment with taurex==3.2.4, numpy==1.26.4,
numba==0.61.2. --download verifies both original Zenodo archive MD5s.
--check compares the actual Planet_0 source spectrum with forward predictions
at the released generating parameters. It writes a diagnostic, not a task pack.
"""
from __future__ import annotations

import sys as _task_sys
from pathlib import Path as _TaskPath
_task_sys.path.insert(0, str(_TaskPath(__file__).resolve().parents[1] / "suite" / "_lib"))
from arena_task_paths import cache_path, data_root, receipt_path
import argparse,concurrent.futures,csv,hashlib,json,os,shutil,sys,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CACHE=cache_path('physics-source')
ARCHIVES=[('NeurIPS taurex tutorial.zip',67603780,'123f98a8db9f2192c51d05407689ea61'),
          ('Level2Data.zip',3190290370,'72c11cb47f80f1d9b300435fc1b7533d')]


def hash_file(path,algorithm='sha256'):
    digest=hashlib.new(algorithm)
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(2**20),b''):digest.update(chunk)
    return digest.hexdigest()


def download():
    from urllib.parse import quote
    CACHE.mkdir(parents=True,exist_ok=True);receipts=[]
    for name,size,checksum in ARCHIVES:
        destination=CACHE/name.replace(' ','_');url='https://zenodo.org/api/records/6770103/files/'+quote(name)+'/content'
        if not destination.exists() or hash_file(destination,'md5')!=checksum:
            width=64*1024*1024
            def fetch_part(index):
                first=index*width;last=min(size,(index+1)*width)-1;path=destination.with_suffix(destination.suffix+f'.part{index}')
                if not path.exists() or path.stat().st_size!=last-first+1:
                    request=urllib.request.Request(url,headers={'Range':f'bytes={first}-{last}'})
                    with urllib.request.urlopen(request,timeout=180) as response,path.open('wb') as output:
                        if response.status!=206:raise RuntimeError('Source server did not honor Range')
                        shutil.copyfileobj(response,output)
                if path.stat().st_size!=last-first+1:raise RuntimeError('Incomplete source range')
                return path
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:parts=list(pool.map(fetch_part,range((size+width-1)//width)))
            with destination.open('wb') as output:
                for part in parts:
                    with part.open('rb') as stream:shutil.copyfileobj(stream,output)
                    part.unlink()
        if hash_file(destination,'md5')!=checksum:raise ValueError('Official source MD5 mismatch')
        with zipfile.ZipFile(destination) as archive:
            for member in archive.infolist():
                if member.is_dir() or member.filename.startswith('__MACOSX') or '/.ipynb_checkpoints/' in member.filename or '.DS_Store' in member.filename:continue
                relative=Path(member.filename)
                if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe source member path')
                path=CACHE/'ariel'/relative
                if not path.exists():
                    path.parent.mkdir(parents=True,exist_ok=True)
                    with archive.open(member) as source,path.open('wb') as output:shutil.copyfileobj(source,output)
        receipts.append({'url':url,'bytes':size,'md5':checksum,'sha256':hash_file(destination)})
    return receipts


def check():
    os.environ.setdefault('MPLCONFIGDIR',str(cache_path('atmosphere-env', 'matplotlib-cache')))
    import importlib.metadata
    import h5py
    import numpy as np
    import taurex.log
    from taurex.cache import OpacityCache,CIACache
    from taurex.planet import Planet
    from taurex.stellar import BlackbodyStar
    from taurex.temperature import Isothermal
    from taurex.chemistry import TaurexChemistry,ConstantGas
    from taurex.model import TransmissionModel
    from taurex.contributions import AbsorptionContribution,CIAContribution,RayleighContribution
    from taurex.binning import FluxBinner
    from taurex.constants import RJUP,MJUP,RSOL,MSOL,G
    taurex.log.disableLogging()
    directory=CACHE/'ariel';opacity=directory/'NeurIPS taurex tutorial/inputs';data_root=directory/'Level2Data'
    OpacityCache().set_opacity_path(str(opacity/'xsec'));CIACache().set_cia_path(str(opacity/'cia'))
    with (data_root/'AuxillaryTable.csv').open() as stream:aux=next(csv.DictReader(stream))
    with (data_root/'Ground Truth Package/FM_Parameter_Table.csv').open() as stream:truth=next(csv.DictReader(stream))
    if aux['planet_ID']!='0' or truth['planet_ID']!='0':raise ValueError('Source row identity changed')
    with h5py.File(data_root/'SpectralData.hdf5') as file:
        group=file['Planet_0'];data={key:group[key][:] for key in group}
    wl=data['instrument_wlgrid'];width=data['instrument_width'];wn=10000/wl
    wnwidth=10000*width/(wl**2-(width/2)**2);order=np.argsort(wn);binner=FluxBinner(wn[order],wnwidth[order])
    outcomes=[]
    for convention,radius_unit in [('literal_released_meters',RJUP),('mean_Jupiter_to_equatorial_Jupiter_diagnostic',69911000.)]:
        chemistry=TaurexChemistry(fill_gases=['H2','He'],ratio=[.17])
        for gas in ['H2O','CO2','CH4','CO','NH3']:chemistry.addGas(ConstantGas(gas,mix_ratio=10**float(truth['log_'+gas])))
        planet=Planet(planet_radius=float(aux['planet_radius_m'])/radius_unit,planet_mass=float(aux['planet_mass_kg'])/MJUP)
        star=BlackbodyStar(radius=float(aux['star_radius_m'])/RSOL,mass=float(aux['star_mass_kg'])/MSOL,temperature=float(aux['star_temperature']))
        model=TransmissionModel(planet=planet,star=star,chemistry=chemistry,temperature_profile=Isothermal(T=float(truth['planet_temp'])),
            nlayers=100,atm_min_pressure=1e-5,atm_max_pressure=1e6)
        model.add_contribution(AbsorptionContribution());model.add_contribution(CIAContribution(cia_pairs=['H2-H2','H2-He']));model.add_contribution(RayleighContribution());model.build()
        native=model.model();binned=binner.bin_model(native);prediction=np.empty(len(wl));prediction[order]=binned[1]
        residual=(prediction-data['instrument_spectrum'])/data['instrument_noise']
        outcomes.append({'radius_convention':convention,'radius_conversion_unit_m':radius_unit,'chi2_per_bin':float(np.mean(residual**2)),
            'max_absolute_sigma_discrepancy':float(np.max(np.abs(residual))),'native_grid_points':len(native[0]),
            'effective_native_resolving_power':float(np.median(native[0][:-1]/np.diff(native[0]))),
            'source_wavelength_um':wl.tolist(),'source_spectrum':data['instrument_spectrum'].tolist(),'prediction':prediction.tolist(),
            'source_noise':data['instrument_noise'].tolist()})
    matched=all(item['chi2_per_bin']<2 for item in outcomes)
    files=[data_root/'AuxillaryTable.csv',data_root/'Ground Truth Package/FM_Parameter_Table.csv',data_root/'SpectralData.hdf5']
    files+=sorted((opacity/'xsec').glob('*.dat'))+sorted((opacity/'cia').glob('*.db'))
    report={'proposal_id':'P08','kind':'source_forward_consistency_diagnostic','status':'consistent' if matched else 'blocked',
        'counts_as_seed_execution':False,'planet_id':'Planet_0','cases':outcomes,
        'source_radius_mass_gravity_ratio':float(np.sqrt(G*float(aux['planet_mass_kg'])/float(aux['planet_radius_m'])**2/float(aux['planet_surface_gravity']))),
        'interpretation':'Both tested conventions fail. The fixed radius/gravity discrepancy suggests a unit-convention mismatch; this is an inference, not a confirmed source correction. Tutorial opacity resolving power is about1000, whereas the ABC paper specifies10000. Obtain source-matched opacity tables/model conventions and validate before a posterior benchmark pass.',
        'reference':'https://academic.oup.com/rasti/article/2/1/45/6998590',
        'libraries':{name:importlib.metadata.version(name) for name in ['taurex','numpy','scipy','numba']},
        'source_files':[{'path':str(path.relative_to(ROOT)),'sha256':hash_file(path),'bytes':path.stat().st_size} for path in files],
        'source_archives':[{'name':name,'md5':checksum,'bytes':size,'sha256':hash_file(CACHE/name.replace(' ','_'))} for name,size,checksum in ARCHIVES]}
    output=receipt_path('physics-atmosphere-forward-check.json');output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'proposal_id':'P08','status':report['status'],'chi2_per_bin':[c['chi2_per_bin'] for c in outcomes],
        'counts_as_seed_execution':False,'report':str(output)},indent=2))
    return matched


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--download',action='store_true');parser.add_argument('--check',action='store_true');args=parser.parse_args()
    if not args.download and not args.check:parser.error('select --download and/or --check')
    if args.download:print(json.dumps(download(),indent=2))
    if args.check:return 0 if check() else 1
    return 0


if __name__=='__main__':raise SystemExit(main())
