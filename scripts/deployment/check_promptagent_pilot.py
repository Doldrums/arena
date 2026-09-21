#!/usr/bin/env python3
"""Actual native PromptAgent + SDK mock fixtures; no model/network calls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import socket
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from arena.frameworks.drivers.promptagent_penguins_gateway import MODELS, DATA, run, preparation, sha
from arena.frameworks.drivers.promptagent_gateway_transport import PromptAgentStopped, write_json


def check(source,destination,freeze,model,scenario='normal'):
    import httpx
    from openai import OpenAI
    if destination.exists():
        raise ValueError('Conformance destination must be new')
    destination.mkdir(parents=True)
    workspace=destination/'workspace'
    shutil.copytree(source,workspace,ignore=shutil.ignore_patterns('.git','__pycache__'))
    write_json(destination/'preparation.json',preparation(workspace,freeze))
    data=json.loads((source/DATA).read_text())
    questions={}
    for row in data['examples']:
        keys=list(row['target_scores'])
        answer=next(chr(65+i) for i,key in enumerate(keys) if row['target_scores'][key]==1)
        question=data['task_prefix'].strip()+'\n'+row['input']+'\nOptions:\n'+'\n'.join(f'({chr(65+i)}) {key}' for i,key in enumerate(keys))+'\n'
        questions[question]=answer
    calls=[]
    optimization_count=0
    def respond(request):
        nonlocal optimization_count
        body=json.loads(request.content)
        assert request.url.path=='/v1/chat/completions' and body['model']==model
        assert set(body)=={'model','messages','stream'} and body['stream'] is False
        prompt=body['messages'][0]['content']
        calls.append({'model':model})
        if scenario=='failure' or (scenario=='retry' and len(calls)==1):
            return httpx.Response(429,json={'error':{'type':'fixture','message':'private-fixture-provider-error'}})
        if prompt.startswith("I'm writing prompts for a language model"):
            if 'The new prompts is:' in prompt:
                optimization_count+=1
                content=f'<START>Fixture optimized prompt {optimization_count}. Read the penguin table carefully.<END>'
                calls[-1]['kind']='optimization'
            else:
                content='Offline fixture gradient: inspect the specified table attributes and option labels.'
                calls[-1]['kind']='gradient'
        else:
            match=[answer for question,answer in questions.items() if prompt.endswith('\n'+question+'\nAt the end show the answer option bracketed between <answer> and </answer>.')]
            assert len(match)==1, f'fixture question matches: {len(match)}'
            # Deliberately wrong initial answers; native optimizer-generated
            # marker enables correct fixture answers. No real inference occurs.
            answer=match[0] if prompt.startswith('Fixture optimized prompt') else ('B' if match[0]=='A' else 'A')
            content=f'<answer>({answer})</answer>'
            calls[-1]['kind']='forward'
        return httpx.Response(200,json={'id':'inert-promptagent-fixture','object':'chat.completion','created':0,
            'model':model,'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':content}}],
            'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}})
    respond_impl=respond
    def respond(request):
        try:
            return respond_impl(request)
        except Exception as error:
            print('Offline fixture transport error:',type(error).__name__,str(error),flush=True)
            raise
    client=OpenAI(api_key='offline-fixture',base_url='http://127.0.0.1:1/v1',max_retries=0,
                  http_client=httpx.Client(transport=httpx.MockTransport(respond)))
    def blocked_network(*args,**kwargs):
        raise AssertionError('Offline PromptAgent fixture must not connect')
    socket.socket.connect=blocked_network
    socket.create_connection=blocked_network
    try:
        receipt=run(workspace,model,destination/'output',destination/'preparation.json',freeze,client=client)
    except PromptAgentStopped:
        assert scenario=='failure'
        assert len(calls)==2
        receipt=json.loads((destination/'output/pilot-receipt.json').read_text())
        assert receipt['status']=='stopped' and not (destination/'output/native-result.json').exists()
    else:
        assert scenario!='failure' and receipt['status']=='completed' and receipt['heldout_frozen']
        assert receipt['iterations_completed']==2 and receipt['native_nodes']>=5
        result=json.loads((destination/'output/native-result.json').read_text())
        assert result['all_nodes'][0]['reward']==0
        assert receipt['selected_node']['reward']==receipt['selected_node']['heldout_accuracy']==1
        assert all(node['visited']>0 for path in result['all_paths'] for node in path)
        assert optimization_count>=4
        from prompt_optim_agent.world_model.gradient_descent import GradientDescent
        assert GradientDescent._clean_optim_response(None,'missing prompt tags')==[]
    usage=json.loads((destination/'output/gateway-usage.json').read_text())
    assert len(calls)==usage['requests_attempted']
    phases=[record['phase'] for record in usage['records']]
    if scenario!='failure':
        first_test=phases.index('heldout')
        assert set(phases[first_test:])=={'heldout'}
        assert {'training','reward','optimization'} <= set(phases[:first_test])
    proof={'schema':'arena.promptagent-offline-conformance/1','model':model,'scenario':scenario,
        'actual_sdk_calls':len(calls),'model_calls':0,'network_connections':0,'fixture_result_not_research':True,
        'native_status':receipt['status'],'native_nodes':receipt.get('native_nodes'),
        'native_iterations':receipt.get('iterations_completed'),'heldout_frozen':receipt.get('heldout_frozen',False),
        'phase_attempts':{phase:phases.count(phase) for phase in set(phases)},
        'dependency_freeze_sha256':sha(freeze),'preparation_sha256':sha(destination/'preparation.json'),
        'pilot_receipt_sha256':sha(destination/'output/pilot-receipt.json')}
    write_json(destination/'conformance.json',proof)
    return proof


def main():
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--dependencies',type=Path,required=True)
    parser.add_argument('--model',choices=MODELS,required=True)
    parser.add_argument('--scenario',choices=('normal','retry','failure'),default='normal')
    args=parser.parse_args()
    print(json.dumps(check(args.source,args.destination,args.dependencies,args.model,args.scenario)))


if __name__=='__main__':
    main()
