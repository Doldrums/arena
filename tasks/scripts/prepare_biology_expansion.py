#!/usr/bin/env python3
"""Prepare pinned real/source-generated biology subsets; never fabricate data.

Automatic sources: B01, B02, B04, B07, B09, B10, B11, B12.
Other adapters accept a reviewed source-derived bundle via --import-bundle,
which must contain provenance, group-disjoint split description and cases.
Use --h5ad for B03/B04 conversion of officially obtained scRNA data.
"""
from __future__ import annotations

import sys as _task_sys
from pathlib import Path as _TaskPath
_task_sys.path.insert(0, str(_TaskPath(__file__).resolve().parents[1] / "suite" / "_lib"))
from arena_task_paths import cache_path
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'suite/_lib'))
import numpy as np
from autoresearch_suite.science_biology_expansion import RESIDUE_MASS, PROTON, peptide_mass

MANIFEST = ROOT/'data/science/biology_expansion/sources.json'
CACHE = cache_path('biology-sources')
DEFAULT_OUTPUT = cache_path('science-biology')
AUTOMATIC = ('B01','B02','B04','B07','B09','B10','B11','B12')


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source(name, offline=False):
    item = json.loads(MANIFEST.read_text())[name]
    path = CACHE/name
    if not path.exists():
        if offline: raise FileNotFoundError(f'Pinned source not cached: {path}')
        CACHE.mkdir(parents=True,exist_ok=True)
        temporary = path.with_suffix(path.suffix+'.download')
        request = urllib.request.Request(item['url'],headers={'User-Agent':'SCIEL-benchmark-preparation/1.0'})
        with urllib.request.urlopen(request,timeout=60) as response, temporary.open('wb') as output:
            total=0
            while block:=response.read(1024*1024):
                total+=len(block)
                if total > item['max_bytes']: raise ValueError('Source exceeds declared size limit')
                output.write(block)
        if sha(temporary) != item['sha256']:
            temporary.unlink(); raise ValueError('Downloaded source checksum mismatch: '+name)
        temporary.replace(path)
    if sha(path) != item['sha256']: raise ValueError('Cached source checksum mismatch: '+name)
    return path, {'url':item['url'],'sha256':item['sha256'],'name':name}


def rows(path):
    return list(csv.DictReader(io.StringIO(Path(path).read_text()),delimiter='\t'))


def automatic(proposal, offline=False):
    sources=[]
    def get(name):
        p,s=source(name,offline);sources.append(s);return p
    if proposal == 'B01':
        archive=get('proteingym-v1.3.zip')
        cases=[]
        names=['SDA_BACSU_Tsuboyama_2023_1PV0','RL40A_YEAST_Roscoe_2014','BLAT_ECOLX_Jacquier_2013']
        with zipfile.ZipFile(archive) as z:
            for name in names:
                table=list(csv.DictReader(io.StringIO(z.read('DMS_ProteinGym_substitutions/'+name+'.csv').decode())))
                # Single substitutions only in this initial bounded protocol.
                table=[r for r in table if ':' not in r['mutant'] and r['mutant'][1:-1].isdigit()]
                if not table:raise ValueError('No single variants found')
                first=table[0]; reference=list(first['mutated_sequence']); reference[int(first['mutant'][1:-1])-1]=first['mutant'][0];reference=''.join(reference)
                support=[r for r in table if int(r['mutant'][1:-1]) % 5 != 0]
                query=[r for r in table if int(r['mutant'][1:-1]) % 5 == 0]
                # All assays retained as one family; split entire mutation positions.
                cases.append({'id':name,'reference':reference,'support_variants':[r['mutant'] for r in support],'support_effects':[float(r['DMS_score']) for r in support],'query_variants':[r['mutant'] for r in query],'query_effects':[float(r['DMS_score']) for r in query]})
        kind='measured';split='Three public assays; complete mutation positions divisible by five held out within each assay. Initial single-substitution track; no higher-order or protein-transfer claim. Source scores are never supplied for query variants.'
    elif proposal == 'B02':
        table=rows(get('eterna.tsv'))
        selected=[r for r in table if 0 < len(r['Secondary Structure V2']) <= 100][:12]
        cases=[{'id':r['Puzzle #']+':'+r['Puzzle Name'],'structure':r['Secondary Structure V2'],'budget':64} for r in selected]
        kind='computational_targets';split='Eterna100-v2 first twelve source-ordered targets of length <=100. Published sequences/solutions deliberately stripped. Public target validation subset, no concealed-motif generalization claim; 64 oracle calls per target.'
    elif proposal == 'B04':
        import h5py
        path=get('scib-pancreas.h5ad')
        with h5py.File(path) as handle:
            names=handle['obs/_index'][:]
            selection=sorted(sorted(range(len(names)),key=lambda i:hashlib.sha256(bytes(names[i])).hexdigest())[:1000])
            # The release explicitly includes raw counts separately from its
            # normalized X matrix. Use counts so the seed normalizes only once.
            counts=np.asarray(handle['layers/counts'][selection,:],dtype=float)
            if not np.isfinite(counts).all() or np.any(counts<0):raise ValueError('Invalid source counts')
            genes=np.argsort(np.var(np.log1p(counts),axis=0))[-500:]
            def labels(key):
                categories=[x.decode() for x in handle['obs/__categories/'+key][:]]
                return [categories[int(i)] for i in handle['obs/'+key][selection]]
            cases=[{'id':'scib-human-pancreas','counts':counts[:,genes].tolist(),'batches':labels('tech'),'cell_types':labels('celltype')}]
        kind='measured';split='Public scIB pancreas: measured raw-count layer, genuine9technology batches and14source cell annotations.1000cell IDs hash-subsampled,500genes selected using transductive counts; cell-type labels evaluator-only. No synthetic batch assignment or cross-study generalization claim.'
    elif proposal == 'B09':
        from PIL import Image
        archive=get('fmd-test.tar');cases=[]
        with tarfile.open(archive) as tar:
            names=sorted(name for name in tar.getnames() if name.startswith('test_mix/raw/') and name.endswith('_1.png'))
            for name in names:
                reference=name.replace('/raw/','/gt/')
                noisy=np.asarray(Image.open(tar.extractfile(name)),float)[192:320,192:320]
                clean=np.asarray(Image.open(tar.extractfile(reference)),float)[192:320,192:320]
                if noisy.shape!=(128,128) or clean.shape!=noisy.shape:raise ValueError('Unexpected FMD image geometry')
                cases.append({'id':Path(name).stem,'noisy_image':noisy.tolist(),'reference_image':clean.tolist(),
                              'metadata':{'data_range':255.,'units':'source8bit intensity','crop':[192,320,192,320],
                                          'modality':Path(name).name.split('_')[0],'source_field':Path(name).stem}})
        kind='measured';split='Twelve official test_mix fields, one per source modality/sample/channel group, fixed central128x128crop. Raw acquired noisy image versus released averaged-exposure reference; no generated noise, fitting, or exposure-level train/test overlap. Bounded crop protocol, not full FMD leaderboard.'
    elif proposal == 'B07':
        text=get('prim.phy').read_text().splitlines()
        n,length=map(int,text[0].split());names=[];alignment={};index=0
        for line in text[1:]:
            if not line.strip(): continue
            fields=line.split()
            if len(names)<n:
                name=fields[0];names.append(name);alignment[name]=''.join(fields[1:])
            else:
                alignment[names[index % n]]+=''.join(fields);index+=1
        if len(alignment)!=n or any(len(v)!=length for v in alignment.values()):raise ValueError('Invalid interleaved PHYLIP')
        cases=[{'id':'RAxML-NG prim.phy empirical primate alignment','alignment':alignment,'budget':60}]
        kind='measured';split='Complete 12-taxon, 898-site empirical tutorial alignment. Independent JC69 objective, not RAxML GTR+Gamma likelihood or original empirical collection. Public single-alignment initial track; no held-out-clade or true-tree recovery claim.'
    elif proposal == 'B10':
        model=get('kinetics_model.xml')
        parameters=rows(get('kinetics_parameters.tsv'))
        measurements=rows(get('kinetics_measurementData.tsv'))
        observables=rows(get('kinetics_observables.tsv'))
        conditions=rows(get('kinetics_experimentalCondition.tsv'))
        problem={'model_id':'Brannmark_JBC2010','parameter_names':[r['parameterId'] for r in parameters], 'bounds':[[np.log10(float(r['lowerBound'])),np.log10(float(r['upperBound']))] for r in parameters], 'conditions':{r['conditionId']:{k:float(v) for k,v in r.items() if k not in ('conditionId','conditionName')} for r in conditions}, 'parameter_scale':'log10', 'initial_parameters':[float((np.log10(float(r['lowerBound']))+np.log10(float(r['upperBound'])))/2) for r in parameters]}
        for i,r in enumerate(measurements):r['row_id']=str(i)
        heldout={'Dose_01','Dose_10'}
        present={r['simulationConditionId'] for r in measurements}
        heldout &= present
        if not heldout:raise ValueError('No declared held-out condition in source')
        model_path=ROOT/'suite/_lib/autoresearch_suite/science_biology_petab.py'
        cases=[{'id':'Brannmark_JBC2010','problem':problem,'training_measurements':[r for r in measurements if r['simulationConditionId'] not in heldout], 'evaluation_measurements':[r for r in measurements if r['simulationConditionId'] in heldout], 'forward_model':{'path':str(model_path),'sha256':sha(model_path)},'budget':48}]
        kind='measured';split='Whole insulin-dose conditions '+','.join(sorted(heldout))+' held out; remaining dose/time-course conditions train. Source nominal fitted parameters stripped. All concentrations reequilibrated from conserved source pool totals. Independent SBML reaction transcription; source simulatedData is not benchmark truth.'
    elif proposal == 'B11':
        expression=get('beeline_expression.csv');network=get('beeline_network.csv')
        table=list(csv.reader(io.StringIO(expression.read_text())));genes=[row[0] for row in table[1:]]
        matrix=np.array([[float(x) for x in row[1:]] for row in table[1:]]).T
        edges=sorted(set((r['Gene1'],r['Gene2']) for r in csv.DictReader(io.StringIO(network.read_text())) if r['Gene1']!=r['Gene2'] and r['Gene1'] in genes and r['Gene2'] in genes))
        cases=[{'id':'BEELINE GSD example ex1','genes':genes,'regulators':genes,'expression':matrix.tolist(),'reference_edges':edges}]
        kind='upstream_simulation';split='Official BEELINE GSD curated-network simulated expression example, one complete network. No edge split exposing reference and no inferred regulator-set leakage (all genes eligible). Not measured expression or cross-network generalization.'
    elif proposal == 'B12':
        path=get('spectra.mgf');records=[];record=None
        for line in path.read_text().splitlines():
            line=line.strip()
            if line=='BEGIN IONS':record={'peaks':[]}
            elif line=='END IONS':records.append(record);record=None
            elif record is not None:
                if '=' in line:
                    key,value=line.split('=',1);record[key]=value
                elif line:
                    mass,intensity=map(float,line.split()[:2]);record['peaks'].append([mass,intensity])
        seen=set();cases=[]
        for r in records:
            peptide=r.get('SEQ','')
            if not peptide or not set(peptide)<=set(RESIDUE_MASS) or peptide.replace('I','L') in seen:continue
            charge=int(r['CHARGE'].rstrip('+'));mass=(float(r['PEPMASS'].split()[0])-PROTON)*charge
            if abs(peptide_mass(peptide)-mass)/mass*1e6 > 50:continue
            seen.add(peptide.replace('I','L'))
            cases.append({'id':r.get('SCANS',r['TITLE']),'peaks':r['peaks'],'precursor_mass':mass,'charge':charge,'peptide':peptide,'mass_tolerance_ppm':50})
            if len(cases)==12:break
        if not cases:raise ValueError('No source spectra meet declared unmodified mass protocol')
        kind='measured';split='First twelve unique unmodified peptides satisfying 50ppm precursor consistency from official measured mouse sample. Replicate peptide sequences deduplicated; labels stripped at candidate boundary. CPU classical decoding track; not the full nine-species benchmark or pretrained-model score reproduction.'
    else:raise ValueError(f'{proposal} has no automatic small-source recipe. See docs/BIOLOGY_EXPANSION.md for source acquisition and --import-bundle schema.')
    return {'schema_version':1,'proposal_id':proposal,'source_kind':kind,'sources':sources,'split_description':split,'cases':cases}


def from_h5ad(proposal,path,url,batch_key='batch',label_key='cell_type'):
    try:import anndata
    except ImportError:raise RuntimeError('Install anndata to convert officially obtained h5ad source data')
    ad=anndata.read_h5ad(path)
    source_info={'url':url,'sha256':sha(path),'name':Path(path).name}
    if not url.startswith('https://'):raise ValueError('--source-url must identify official dataset source')
    def dense(value):return value.toarray() if hasattr(value,'toarray') else np.asarray(value)
    if proposal=='B04':
        if batch_key not in ad.obs or label_key not in ad.obs:raise ValueError('Declared batch/cell-type keys absent')
        selection=sorted(range(ad.n_obs),key=lambda i:hashlib.sha256(str(ad.obs_names[i]).encode()).hexdigest())[:1000]
        x=dense(ad.X[selection]);gene_order=np.argsort(np.var(np.log1p(x),axis=0))[-500:]
        cases=[{'id':Path(path).stem,'counts':x[:,gene_order].tolist(),'batches':ad.obs[batch_key].astype(str).iloc[selection].tolist(),'cell_types':ad.obs[label_key].astype(str).iloc[selection].tolist()}]
        split='Transductive full study; cell IDs hash-subsampled to1000, top500 variable genes; cell-type labels evaluator-only. No cross-study generalization claim. Supply separate studies for model selection.'
    elif proposal=='B03':
        if 'condition' not in ad.obs:raise ValueError('GEARS h5ad requires obs.condition')
        groups=ad.obs['condition'].astype(str).to_numpy();names=sorted(set(groups));control=[g for g in names if g in ('ctrl','control','ctrl+ctrl')]
        if not control:raise ValueError('No recognized GEARS control condition')
        control_mask=np.isin(groups,control);baseline=np.asarray(ad.X[control_mask].mean(axis=0)).ravel()
        perturbations=[g for g in names if g not in control]
        train=[g for g in perturbations if int(hashlib.sha256(g.encode()).hexdigest()[:8],16)%5 != 0]
        test=[g for g in perturbations if g not in train]
        if not train or not test:raise ValueError('Insufficient complete perturbation groups')
        means={g:np.asarray(ad.X[groups==g].mean(axis=0)).ravel()-baseline for g in perturbations}
        train_matrix=np.array([means[g] for g in train]);selected=np.argsort(np.var(train_matrix,axis=0))[-256:]
        parse=lambda g:[a for a in g.split('+') if a not in ('ctrl','control')]
        cases=[{'id':Path(path).stem,'training_shifts':train_matrix[:,selected].tolist(),'training_perturbations':[parse(g) for g in train], 'query_shifts':np.array([means[g][selected] for g in test]).tolist(),'query_perturbations':[parse(g) for g in test],'gene_context':{'gene_names':ad.var_names[selected].astype(str).tolist(),'representation':'source normalized pseudobulk shifts relative to controls'}}]
        split='Entire condition names hash-partitioned4:1; no cells from a perturbation cross train/evaluation. Gene panel chosen using training perturbations only. Single study pseudobulk adaptation; controls shared as declared reference; no cross-cell-type claim.'
    else:raise ValueError('--h5ad supported only for B03/B04')
    return {'schema_version':1,'proposal_id':proposal,'source_kind':'measured','sources':[source_info],'split_description':split,'cases':cases}


def write_bundle(data,output):
    proposal=data['proposal_id']
    if proposal not in [f'B{i:02}' for i in range(1,13)]:raise ValueError('Unknown proposal')
    if data.get('source_kind') not in ('measured','upstream_simulation','computational_targets','mixed'):raise ValueError('Fixture data cannot be staged as benchmark data')
    if not data.get('cases') or not data.get('sources') or not data.get('split_description'):raise ValueError('Incomplete provenance/cases')
    output.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(data,indent=2,allow_nan=False)+'\n').encode();path=output/f'{proposal}.json';path.write_bytes(raw)
    receipt={'schema_version':1,'proposal_id':proposal,'bundle_sha256':hashlib.sha256(raw).hexdigest(),'source_kind':data['source_kind'],'source_files':data['sources'],'preparation_script':'scripts/prepare_biology_expansion.py','cases':len(data['cases']),'benchmark_validation':'pending actual evaluator run'}
    (output/f'{proposal}.manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return {'proposal':proposal,'cases':len(data['cases']),'path':str(path),'bytes':len(raw),'sha256':receipt['bundle_sha256']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--proposal',choices=[f'B{i:02}' for i in range(1,13)])
    p.add_argument('--all',action='store_true',help='Prepare the eight automatically available source protocols')
    p.add_argument('--offline',action='store_true')
    p.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    p.add_argument('--import-bundle',type=Path)
    p.add_argument('--h5ad',type=Path)
    p.add_argument('--source-url')
    p.add_argument('--batch-key',default='batch');p.add_argument('--label-key',default='cell_type')
    args=p.parse_args()
    if args.import_bundle:
        data=json.loads(args.import_bundle.read_text());print(json.dumps(write_bundle(data,args.output)));return
    if args.h5ad:
        if not args.proposal or not args.source_url:p.error('--h5ad requires --proposal and --source-url')
        data=from_h5ad(args.proposal,args.h5ad,args.source_url,args.batch_key,args.label_key);print(json.dumps(write_bundle(data,args.output)));return
    targets=AUTOMATIC if args.all else [args.proposal] if args.proposal else []
    if not targets:p.error('choose --proposal or --all or --import-bundle')
    for proposal in targets:print(json.dumps(write_bundle(automatic(proposal,args.offline),args.output)))

if __name__=='__main__':main()
