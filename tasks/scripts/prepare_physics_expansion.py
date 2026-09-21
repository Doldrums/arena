#!/usr/bin/env python3
"""Prepare pinned scientific data; no fallback benchmark generated from fixtures."""
from __future__ import annotations

import sys as _task_sys
from pathlib import Path as _TaskPath
_task_sys.path.insert(0, str(_TaskPath(__file__).resolve().parents[1] / "suite" / "_lib"))
from arena_task_paths import cache_path, data_root, receipt_path
import argparse,hashlib,json,shutil,sys,urllib.request,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
DATA=data_root() / 'physics-expansion'
sys.path.insert(0,str(ROOT/'suite/_lib'))
from autoresearch_suite import science_physics_expansion as physics


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fetch(url,path,expected=None,algorithm='sha256'):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    def valid():return path.is_file() and (expected is None or hashlib.new(algorithm,path.read_bytes()).hexdigest()==expected)
    if not valid():
        temporary=path.with_suffix(path.suffix+'.part')
        with urllib.request.urlopen(url,timeout=120) as response,temporary.open('wb') as output:shutil.copyfileobj(response,output)
        if expected and hashlib.new(algorithm,temporary.read_bytes()).hexdigest()!=expected:raise ValueError('official source checksum mismatch: '+url)
        temporary.replace(path)
    return {'url':url,'sha256':digest(path),'bytes':path.stat().st_size}


def save_pack(proposal,arrays,metadata):
    directory=DATA/proposal;directory.mkdir(parents=True,exist_ok=True)
    path=directory/'benchmark.npz';np.savez_compressed(path,**arrays)
    metadata=dict(metadata,proposal_id=proposal,fixture_only=False,sha256=digest(path),schema='sciel-physics-source-v1')
    (directory/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    physics.load_pack(proposal,directory)
    return {'proposal_id':proposal,'manifest':str(directory/'manifest.json'),'sha256':metadata['sha256'],'sources':metadata['sources']}


def prepare_calo():
    import h5py
    raw=cache_path('physics-source');sources=[];arrays={}
    for part,(split,count,checksum) in enumerate([('train',384,'005d2adeda7db034b388112661265656'),('test',128,'4767715ed56e99565fd9c67340661e70')],1):
        name=f'dataset_1_photons_{part}.hdf5';url=f'https://zenodo.org/api/records/8099322/files/{name}/content'
        sources.append(fetch(url,raw/name,checksum,'md5'))
        with h5py.File(raw/name) as file:
            energy=file['incident_energies'][:].ravel();selected=[]
            for value in np.unique(energy):
                indices=np.flatnonzero(energy==value)
                # Deterministic label-independent selection in source file order.
                selected.extend(indices[:count])
            selected=np.sort(selected)
            arrays[split+'_energy']=energy[selected];arrays[split+'_showers']=file['showers'][selected]
            arrays[split+'_event_ids']=np.asarray([f'{part}:{i}' for i in selected])
    xmlurl='https://raw.githubusercontent.com/CaloChallenge/homepage/main/code/binning_dataset_1_photons.xml'
    xmlpath=raw/'binning_dataset_1_photons.xml';sources.append(fetch(xmlurl,xmlpath,'30786d54defff3d45dada4f4ecb2a4600a1622b3ca2004d40dae01774589a92f'))
    geometry={'layer':[],'x':[],'y':[]}
    for layer in ET.parse(xmlpath).getroot().findall('.//Layer'):
        radii=np.array([float(x) for x in layer.get('r_edges').split(',')]);angles=int(layer.get('n_bin_alpha'))
        if len(radii)<2:continue
        centers=.5*(radii[:-1]+radii[1:])
        for alpha in (np.arange(angles)+.5)*2*np.pi/angles-np.pi:
            for r in centers:
                geometry['layer'].append(int(layer.get('id')));geometry['x'].append(float(r*np.cos(alpha)));geometry['y'].append(float(r*np.sin(alpha)))
    if len(geometry['layer'])!=368:raise ValueError('source photon geometry is not 368 voxels')
    return save_pack('P04',arrays,{'source_kind':'source_simulation','sources':sources,'license':'CaloChallenge Zenodo 8099322 CC BY 4.0; author source XML attributed',
        'geometry':geometry,'selection':'First 384 training and 128 evaluation events at each of 15 released energies; disjoint source files.',
        'adaptation':'5760 training/1920 evaluation GEANT4 showers; CPU distribution task, not full leaderboard.'})


def prepare_refnx():
    commit='02b9bd11b439e8db8b319e6c25c7ee94b5033451';base=f'https://raw.githubusercontent.com/refnx/refnx/{commit}/examples/global_fitting_motofit/'
    arrays={};sources=[];contrasts={'e361r':6.3024,'e365r':3.374,'e366r':-.56}
    for name in contrasts:
        path=DATA/'P13'/'raw'/(name+'.txt');sources.append(fetch(base+name+'.txt',path));arrays[name]=np.loadtxt(path)
        pilot=path.with_name(name+'_pilot.txt');sources.append(fetch(base+pilot.name,pilot))
    globalpath=DATA/'P13'/'raw'/'global_pilot';sources.append(fetch(base+'global_pilot',globalpath))
    bounds=[[0,30],[50,420],[0,1.3],[0,.5],[.5,20],[0,6e-5]]
    cases=[{'track':'experimental','sample_id':'refnx_motofit_shared_sample','train':[s for s in contrasts if s!=name],'test':name} for name in contrasts]
    # Separate and explicitly labelled inverse-problem calibration track from
    # the same physical Parratt model, never substituted for measured curves.
    rng=np.random.default_rng(41981)
    for i in range(3):
        truth=[rng.uniform(5,18),rng.uniform(120,330),rng.uniform(.15,.8),rng.uniform(.01,.14),rng.uniform(2,7),rng.uniform(.7e-5,2e-5)]
        names=[]
        for j,(name,sld) in enumerate(list(contrasts.items())):
            if name.startswith('sim_'):continue
            key=f'sim_{i}_{j}';names.append(key);q=arrays[name][:,0];errors=arrays[name][:,2];dq=arrays[name][:,3]
            reflect=physics.parratt(q,truth,sld,dq)+rng.normal(0,errors)
            arrays[key]=np.column_stack([q,reflect,errors,dq]);contrasts[key]=sld
        cases.append({'track':'specified_model_simulation','sample_id':f'independent_simulated_sample_{i}','train':names[:2],'test':names[2],'truth_parameters':truth})
    return save_pack('P13',arrays,{'source_kind':'experimental','sources':sources,'license':'refnx BSD-3-Clause repository; measurement attribution retained',
        'bounds':bounds,'contrasts':contrasts,'cases':cases,'split_unit':'complete_contrast',
        'q_resolution':'source fourth column is FWHM Q resolution, integrated by 15-point Gauss-Hermite',
        'adaptation':'One source measured sample, three solvent contrasts; shared Si/SiO2/solvated-film geometry. Fitted contrast SLDs taken as source calibration, not exact film truth. Three separately labelled simulated calibration samples.',
        'measurement_provenance_limit':'Source repository supplies contrast curves and global-refinement pilot; sample identity/instrument run metadata are incomplete. No claim of a diverse experimental cohort.'})


def prepare_xy():
    cases=[{'temperature':.88,'size':8,'sweeps':384,'warmup':96,'chains':6},
           {'temperature':.96,'size':12,'sweeps':384,'warmup':96,'chains':6},
           {'temperature':1.1,'size':8,'sweeps':384,'warmup':96,'chains':6}]
    means=[];errors=[];scales=[];chainmeans=[]
    for i,case in enumerate(cases):
        references=[];variances=[]
        for chain in range(8):
            values=physics.xy_chain(case['temperature'],case['size'],['wolff','metropolis','overrelax'],8192,1024,74113+100*i+chain)
            references.append(values.mean(axis=0));variances.append(values.var(axis=0,ddof=1))
        references=np.asarray(references);error=references.std(axis=0,ddof=1)/np.sqrt(len(references));scale=np.sqrt(np.mean(variances,axis=0))
        if np.any(error/scale>=.08):raise ValueError('Long XY reference has insufficient precision; increase independent reference chains.')
        means.append(references.mean(axis=0));errors.append(error);scales.append(scale);chainmeans.append(references)
        print('XY reference',case['temperature'],case['size'],'mean',means[-1],'SE',error,flush=True)
    return save_pack('P14',{'reference_means':means,'reference_standard_errors':errors,'observable_scales':scales,'reference_chain_means':chainmeans},
        {'source_kind':'source_model','sources':[{'url':'https://doi.org/10.1103/PhysRevLett.62.361','locator':'O(2) Wolff detailed-balance cluster update'},
            {'url':'https://alps.comp-phys.org/tutorials/mcs/','locator':'Classical XY equilibrium Monte Carlo methodology'}],
         'cases':cases,'reference_sweeps_per_chain':8192,'reference_warmup':1024,'reference_chains':8,'coupling_J':1,'boundary':'periodic',
         'adaptation':'Fixed work charged N site units per cluster/sweep. Numerical reference uncertainty explicitly bounded; no exact-distribution claim.'})


def prepare_coils():
    arrays={};cases=[]
    for i,(ip,rout) in enumerate([(2e5,1.22),(1.8e5,1.2)]):
        profile={'Ip':ip,'alpha':58213.6*ip/2e5,'beta':.582136*ip/2e5};target={'x_radius':.8,'x_height':.35,'outer_radius':rout}
        case={'profile':profile,'target':target,'coarse_grid':33,'fine_grid':65}
        coarse,_,_=physics.coil_inverse(profile,target,33);currents=physics.coil_currents(coarse)
        fine,_,_=physics.coil_inverse(profile,target,65)
        arrays[f'coarse_initial_psi_{i}']=coarse.plasma_psi;arrays[f'fine_initial_psi_{i}']=fine.plasma_psi
        # The target is source-model inverse-equilibrium geometry, not a copied
        # solution exposed to the candidate. Exact coil reference stays private.
        arrays[f'boundary_{i}']=np.asarray(fine.separatrix())[::6,:2]
        arrays[f'axis_{i}']=np.asarray(fine.magneticAxis())[:2];arrays[f'reference_currents_{i}']=currents
        cases.append(case);print('Coil reference',i,'currents',currents.tolist(),flush=True)
    return save_pack('P10',arrays,{'source_kind':'source_model','sources':[{'url':'https://github.com/FusionComputingLab/freegsnke/tree/d755538c0f849e46f0e2407c0dad535eb9a1e228','locator':'examples/example07a_-_Anamak.ipynb geometry, Lao85 source profile; two declared adaptations'}],
        'freegsnke_version':'3.1.0','cases':cases,'adaptation':'33x65 and 65x129 meshes; second profile/outer-radius perturbation. Static simulated equilibria.'})


def validate_external(proposal,directory):
    # Semantic scientific checks still run on candidate evaluation; this only
    # validates source identity, declared provenance and content checksum.
    data,manifest=physics.load_pack(proposal,directory)
    if not manifest.get('license'):raise ValueError('Source permission/license must be documented')
    destination=DATA/proposal
    if Path(directory).resolve()!=destination.resolve():
        destination.mkdir(parents=True,exist_ok=True)
        shutil.copy2(Path(directory)/'benchmark.npz',destination/'benchmark.npz');shutil.copy2(Path(directory)/'manifest.json',destination/'manifest.json')
    return {'proposal_id':proposal,'sha256':manifest['sha256'],'arrays':sorted(data),'semantic_validation':'pending candidate source execution'}


class RemoteZipReader:
    """Seekable byte-range source; refuses a server that ignores Range."""
    def __init__(self,url,size):self.url=url;self.size=size;self.position=0;self.cache={}
    def seekable(self):return True
    def readable(self):return True
    def tell(self):return self.position
    def seek(self,offset,whence=0):
        self.position=offset+(0 if whence==0 else self.position if whence==1 else self.size);return self.position
    def read(self,count=-1):
        if count<0:count=self.size-self.position
        count=min(count,self.size-self.position)
        if count<=0:return b''
        key=(self.position,count)
        if key in self.cache:payload=self.cache[key]
        else:
            request=urllib.request.Request(self.url,headers={'Range':f'bytes={self.position}-{self.position+count-1}'})
            with urllib.request.urlopen(request,timeout=120) as response:
                if response.status!=206:raise RuntimeError('Source server did not honor Range')
                payload=response.read()
            if len(payload)!=count:raise ValueError('Incomplete source byte range')
            if count<2**20:self.cache[key]=payload
        self.position+=count;return payload


def prepare_qec():
    import zipfile
    try:import stim
    except ImportError:raise RuntimeError('Run this preparation with .cache/physics-env/bin/python after --setup-environment')
    archive='google_105Q_surface_code_d3_d5_d7.zip'
    url='https://zenodo.org/api/records/13273331/files/'+archive+'/content'
    raw=cache_path('physics-source', 'qec');arrays={'train_batch_ids':np.array([],dtype='U1')};cases=[];sources=[]
    folders=['d3_at_q10_7','d5_at_q4_7','d7_at_q6_7']
    names=['metadata.json','circuit_noisy_si1000.stim','circuit_ideal.stim','detection_events.b8','obs_flips_actual.b8']
    expected_member_hashes={'google_105Q_surface_code_d3_d5_d7/d3_at_q10_7/X/r13/metadata.json': '1a41a0abb021e9c278848d156ca46517b81620ea7e299470c23191bd6488da8f', 'google_105Q_surface_code_d3_d5_d7/d3_at_q10_7/X/r13/circuit_noisy_si1000.stim': '610e311c22ee82865c75f83e95c2cd67f83c3fd8aabdbc6d07b562e2bc2b7f79', 'google_105Q_surface_code_d3_d5_d7/d3_at_q10_7/X/r13/circuit_ideal.stim': '386e4dc3106e56fd96514289e215c204a2b99f8c25e09f0ebc438df5fdc73c71', 'google_105Q_surface_code_d3_d5_d7/d3_at_q10_7/X/r13/detection_events.b8': '61b14c09531d1be6e30dc3fc0b9454270d5e13aff7c5a833d44a71687945e95a', 'google_105Q_surface_code_d3_d5_d7/d3_at_q10_7/X/r13/obs_flips_actual.b8': '90de8ac85bc23c8792f9c54fa595225d50477b031632acc6993b4c82b706573f', 'google_105Q_surface_code_d3_d5_d7/d5_at_q4_7/X/r13/metadata.json': '2f199ca2024e8cf5baf9fc229c8dc7541f5c1b43db7310a9d965d8cb447e608e', 'google_105Q_surface_code_d3_d5_d7/d5_at_q4_7/X/r13/circuit_noisy_si1000.stim': 'c5560ecd78af20a552568f2455e651d48f9bd45680f882ca72cb327ebf7b428b', 'google_105Q_surface_code_d3_d5_d7/d5_at_q4_7/X/r13/circuit_ideal.stim': '7623a21a72f64d8564ad944e32a0609110dabc3f2fdaf1f7393b8e15e5b452bf', 'google_105Q_surface_code_d3_d5_d7/d5_at_q4_7/X/r13/detection_events.b8': '399fc15e16c2d53f0f039218f3dd3f9ec576bbc0c369b74b0916515ff1ab3cb2', 'google_105Q_surface_code_d3_d5_d7/d5_at_q4_7/X/r13/obs_flips_actual.b8': '0e9abd8d3364f347119877f063166fe98a1fb051aaace5682c6aa96c756fdfe9', 'google_105Q_surface_code_d3_d5_d7/d7_at_q6_7/X/r13/metadata.json': 'a9a9f1754d952c15b662bab3f2236fccbc878912f67955875edec751194c2cf8', 'google_105Q_surface_code_d3_d5_d7/d7_at_q6_7/X/r13/circuit_noisy_si1000.stim': '06d8462c252641cbcc110ca3f2d4174a6e036623526fb3b4e0c6c23b093f55ef', 'google_105Q_surface_code_d3_d5_d7/d7_at_q6_7/X/r13/circuit_ideal.stim': '3a1cb5a1b952ee92623862f17ad3d5d688c706f1365ba2be8f25bf5f6e8ec8ae', 'google_105Q_surface_code_d3_d5_d7/d7_at_q6_7/X/r13/detection_events.b8': '75fb18c1ae9c8abf40fce2a6cb8f4d703673e09dc02c6d8d4fe7e011ea15ccef', 'google_105Q_surface_code_d3_d5_d7/d7_at_q6_7/X/r13/obs_flips_actual.b8': '05a694d889256198fcb05b1b137fcc7552902f2e9006e5f6cb8d3c156a57151d'}
    missing=any(not (raw/archive[:-4]/folder/'X/r13'/name).is_file() for folder in folders for name in names)
    opened=zipfile.ZipFile(RemoteZipReader(url,5716907033)) if missing else None
    try:
        for i,folder in enumerate(folders):
            prefix=archive[:-4]+'/'+folder+'/X/r13';directory=raw/prefix;directory.mkdir(parents=True,exist_ok=True)
            for name in names:
                path=directory/name
                if not path.exists():path.write_bytes(opened.read(prefix+'/'+name)) # ZIP CRC verified by zipfile.
                if digest(path)!=expected_member_hashes[prefix+'/'+name]:raise ValueError('QEC source member differs from reviewed SHA-256')
                sources.append({'url':'https://zenodo.org/records/13273331','archive_member':prefix+'/'+name,'sha256':digest(path),'bytes':path.stat().st_size})
            metadata=json.loads((directory/'metadata.json').read_text());ideal=stim.Circuit((directory/'circuit_ideal.stim').read_text())
            noisy=stim.Circuit((directory/'circuit_noisy_si1000.stim').read_text());dem=noisy.detector_error_model(decompose_errors=True)
            detectors=stim.read_shot_data_file(path=str(directory/'detection_events.b8'),format='b8',num_detectors=ideal.num_detectors)
            truth=stim.read_shot_data_file(path=str(directory/'obs_flips_actual.b8'),format='b8',num_observables=ideal.num_observables)
            if len(detectors)!=metadata['shots'] or len(truth)!=metadata['shots']:raise ValueError('Incomplete experimental acquisition')
            arrays[f'detectors_{i}']=detectors.astype('uint8');arrays[f'logical_truth_{i}']=truth.astype('uint8')
            cases.append({'batch_id':prefix,'code_distance':metadata['distance'],'detector_error_model':str(dem),'cycles':metadata['rounds']})
    finally:
        if opened:opened.close()
    return save_pack('P03',arrays,{'source_kind':'experimental','sources':sources,'license':'Google Zenodo13273331 experimental release; retain source attribution',
        'cases':cases,'adaptation':'Three complete 50,000-shot X-basis 13-cycle acquisitions, distances3/5/7. Zero-shot prior is published SI1000 circuit, never fit to test detections. Macro acquisition failure, not per-cycle scaling reproduction.',
        'selection':'Lexicographically first released X/r13 acquisition for each distance, selected before decoding.'})


def setup_environment():
    import subprocess
    import venv
    destination=cache_path('physics-env')
    if not (destination/'bin/python').exists():venv.EnvBuilder(with_pip=True).create(destination)
    subprocess.run([str(destination/'bin/python'),'-m','pip','install','numpy==2.3.5','scipy==1.18.1','freegsnke==3.1.0','astropy>=6,<8','pymatching==2.3.1','stim==1.15.0','lenstronomy==1.13.5'],check=True)
    return {'proposal_id':'environment','python':str(destination/'bin/python'),'packages':'Pinned optional physics solvers; shared environment unchanged'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qec',action='store_true');parser.add_argument('--setup-environment',action='store_true');parser.add_argument('--calo',action='store_true');parser.add_argument('--refnx',action='store_true');parser.add_argument('--xy-reference',action='store_true');parser.add_argument('--coils',action='store_true')
    parser.add_argument('--validate-pack',nargs=2,metavar=('PXX','DIRECTORY'))
    args=parser.parse_args();receipts=[]
    for selected,function in [(args.qec,prepare_qec),(args.calo,prepare_calo),(args.refnx,prepare_refnx),(args.xy_reference,prepare_xy),(args.coils,prepare_coils)]:
        if selected:receipts.append(function())
    if args.setup_environment:receipts.append(setup_environment())
    if args.validate_pack:receipts.append(validate_external(*args.validate_pack))
    if not receipts:parser.error('select a preparation command')
    print(json.dumps(receipts,indent=2))
    path=receipt_path('physics-source-staging.json');previous=json.loads(path.read_text()) if path.exists() else {'receipts':[]}
    merged={r['proposal_id']:r for r in previous['receipts']};merged.update({r['proposal_id']:r for r in receipts});previous['receipts']=list(merged.values())
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(previous,indent=2)+'\n')


if __name__=='__main__':main()
