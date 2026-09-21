#!/usr/bin/env python3
"""Materialize FunSearch native pilot plans; no model or evaluator is called."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from arena.frameworks.drivers.base_gateway import MODELS


def main():
    from arena.frameworks.runtime import prepare_plan
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('/srv/arena'))
    parser.add_argument('--bubblewrap',type=Path,default=Path('/usr/bin/bwrap'))
    parser.add_argument('--destination',type=Path,required=True)
    args=parser.parse_args()
    if not args.root.is_absolute() or not args.destination.is_absolute() or args.destination.exists():
        raise ValueError('Use an absolute root and a new absolute destination')
    args.destination.mkdir(mode=0o750,parents=True)
    templates=[];records=[]
    for engine in ('funsearch-original','funsearch-re-implementation'):
        folder=args.destination/engine;folder.mkdir(mode=0o750)
        selected=[]
        for model in MODELS:
            slug=model.replace('.','-')
            spec={'schema':'arena.native-run/1','framework':engine,'source_dir':str(args.root/'sources'/engine),
                  'output_dir':str(args.root/'runs'/args.destination.name/engine/slug),'timeout_seconds':2400,
                  'environment_names':['OPENAI_API_KEY'],
                  'request':{'python':str(args.root/'envs'/engine/'bin/python'),'profile':'gateway-cpu-pilot',
                             'arguments':['--model',model,'--max-samples','6'],'executables':{'bubblewrap':str(args.bubblewrap)}}}
            plan=prepare_plan(spec)
            (folder/(slug+'.plan.json')).write_text(json.dumps(plan,indent=2)+'\n')
            template={'id':'cpu-'+engine+'-'+slug,'name':engine+' native pilot · '+model,
                      'framework':engine,'profile':'gateway-cpu-pilot','model':model,'status':'ready','blocked_reason':None,
                      'resources':{'cpus':4,'memory_mb':8192,'evaluation_slots':1,'pids':512},
                      'containment':'cgroup-v2','evaluation_concurrency_verified':True,'spec':{**spec,'output_dir':'{output_dir}'}}
            selected.append(template);templates.append(template)
            records.append({'framework':engine,'model':model,'source':plan['source'],'plan_sha256':plan['sha256'],
                            'namespace_executable':plan['command']['executables'],'research_executed':False})
        (folder/'templates.json').write_text(json.dumps(selected,indent=2)+'\n')
    (args.destination/'templates.json').write_text(json.dumps(templates,indent=2)+'\n')
    proof={'schema':'arena.funsearch-pilot-preparation/1','records':records,'model_calls':0,'research_executed':False,
           'native_evaluation':True,'canonical_evaluation':False,'sample_budgets':{'funsearch-original':6,'funsearch-re-implementation':{'generated_samples':6,'additional_connectivity_call':1}},
           'task_identity':{'funsearch-original':'Native constant-weight admissible-set specification, n=9/w=5','funsearch-re-implementation':'Native cap-set specification, n=6'},
           'concurrency_basis':'Original single-threaded native pipeline; kitft Config(num_samplers=1,num_evaluators=1). Namespace scorer waits for each child; outer cgroup constrains all descendants.',
           'provider':'Exact gateway model IDs, scoped OPENAI_API_KEY environment reference only. Sampling controls in kitft use codex-native compatibility policy and are not enforced by the provider.'}
    (args.destination/'preparation.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps({'templates':len(templates),'destination':str(args.destination),'model_calls':0}))

if __name__=='__main__':main()
