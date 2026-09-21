"""PromptAgent transport/provenance bounds, with separate real-native SDK CLI."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from arena.frameworks.drivers import promptagent_gateway_transport as transport
from arena.frameworks.drivers import promptagent_penguins_gateway as pilot
from arena.frameworks.recipes import load_recipes, validate_recipe


def make_gateway(tmp_path,model,callback=None):
    calls=[]
    def complete(**kwargs):
        calls.append(kwargs)
        if callback:
            return callback(**kwargs)
        return SimpleNamespace(model=model,choices=[SimpleNamespace(message=SimpleNamespace(content=' <answer>A</answer> '))],usage=None)
    client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=complete)))
    gateway=transport.GatewayTransport(model,tmp_path,client=client)
    task=SimpleNamespace(dataset={name:[{'question':name+' question'}] for name in ('train','eval','test')},answer_format_prompt='ANSWER_FORMAT')
    gateway.bind_task(task)
    return gateway,calls


def arguments(model,role='base',split='eval'):
    return {'model':model,'temperature':0.0 if role=='base' else 1.0,
            'messages':[{'role':'user','content':'native prompt\n'+split+' question\nANSWER_FORMAT'}]}


@pytest.mark.parametrize('model',pilot.MODELS)
def test_exact_model_both_native_roles_and_phase(tmp_path,model):
    gateway,calls=make_gateway(tmp_path,model)
    transport.install_transport(gateway)
    for role,split in [('base','train'),('base','eval'),('optim','train'),('base','test')]:
        client=transport.OpenAI(api_key='environment:'+role)
        response=client.chat.completions.create(**arguments(model,role,split))
        assert response.model==model
    assert all(call['model']==model and call['stream'] is False and 'temperature' not in call for call in calls)
    usage=json.loads((tmp_path/'gateway-usage.json').read_text())
    assert [r['phase'] for r in usage['records']]==['training','reward','optimization','heldout']
    assert usage['requests_attempted']==4 and usage['cost_usd'] is None
    assert 'native prompt' not in (tmp_path/'gateway-usage.json').read_text()


def test_provider_failure_allows_one_sanitized_native_retry_then_stops(tmp_path):
    def fail(**kwargs):
        raise RuntimeError('private-credential private provider response')
    gateway,calls=make_gateway(tmp_path,pilot.MODELS[0],fail)
    with pytest.raises(transport.RetryableProviderError,match='one native retry'):
        gateway.complete('base',**arguments(gateway.model))
    with pytest.raises(transport.PromptAgentStopped,match='failed twice'):
        gateway.complete('base',**arguments(gateway.model))
    assert len(calls)==2
    raw=(tmp_path/'gateway-usage.json').read_text()
    assert 'private-credential' not in raw and 'private provider' not in raw
    assert all(r['outcome']=='unknown' for r in json.loads(raw)['records'])


def test_success_resets_native_call_retry_count(tmp_path):
    sequence=[False,True,False,True]
    def respond(**kwargs):
        if not sequence.pop(0):
            raise RuntimeError('fixture')
        return SimpleNamespace(model=pilot.MODELS[0],choices=[SimpleNamespace(message=SimpleNamespace(content='answer'))],usage=None)
    gateway,calls=make_gateway(tmp_path,pilot.MODELS[0],respond)
    for _ in range(2):
        with pytest.raises(transport.RetryableProviderError):
            gateway.complete('base',**arguments(gateway.model))
        assert gateway.complete('base',**arguments(gateway.model)).model==gateway.model
    assert len(calls)==4


def test_global_request_budget_covers_native_retries(tmp_path):
    gateway,calls=make_gateway(tmp_path,pilot.MODELS[0])
    for _ in range(transport.REQUEST_LIMIT):
        gateway.complete('base',**arguments(gateway.model))
    with pytest.raises(transport.PromptAgentStopped,match='budget'):
        gateway.complete('base',**arguments(gateway.model))
    assert len(calls)==96


@pytest.mark.parametrize('model,count',[('wrong-model',1),(pilot.MODELS[0],0),(pilot.MODELS[0],2)])
def test_response_identity_and_cardinality_are_terminal(tmp_path,model,count):
    def respond(**kwargs):
        return SimpleNamespace(model=model,choices=[SimpleNamespace(message=SimpleNamespace(content='answer')) for _ in range(count)],usage=None)
    gateway,calls=make_gateway(tmp_path,pilot.MODELS[0],respond)
    with pytest.raises(transport.PromptAgentStopped,match='identity/protocol'):
        gateway.complete('base',**arguments(gateway.model))
    assert len(calls)==1


@pytest.mark.parametrize('change',[{'model':'gpt-4'},{'api_key':'forbidden'},{'temperature':0.2}])
def test_no_alias_or_unreviewed_provider_control(tmp_path,change):
    gateway,calls=make_gateway(tmp_path,pilot.MODELS[0])
    with pytest.raises(transport.PromptAgentStopped):
        gateway.complete('base',**(arguments(gateway.model)|change))
    assert not calls


def test_split_manifest_rejects_overlap_and_wrong_sizes():
    task=SimpleNamespace(dataset={name:[{'question':f'{name}{i}','answer':'A'} for i in range(count)] for name,count in [('train',8),('eval',4),('test',4)]})
    assert pilot.split_manifest(task)['disjoint']
    task.dataset['test'][0]=task.dataset['train'][0]
    with pytest.raises(ValueError,match='overlap'):
        pilot.split_manifest(task)


def test_frozen_state_allows_only_test_metric_updates():
    row={'id':0,'prompt':'p','reward':0.5,'visited':1,'test_metric':-1}
    node=SimpleNamespace(to_dict=lambda:dict(row),cum_rewards=[0.5])
    search=SimpleNamespace(nodes=[node])
    before=pilot.frozen_state(search)
    row['test_metric']=1
    assert pilot.frozen_state(search)==before
    row['reward']=1
    assert pilot.frozen_state(search)!=before


def test_versioned_recipe_and_seven_blocked_templates():
    root=Path(__file__).resolve().parents[2]
    new=json.loads((root/'registry/framework-recipes/promptagent-penguins-gateway.json').read_text())['recipes'][0]
    assert validate_recipe(new)['id']==pilot.ENGINE
    old = load_recipes(root / "registry")["promptagent"]
    assert new['repository']==old['repository'] and new['id']!=old['id']
    spec=importlib.util.spec_from_file_location('prepare_promptagent',root/'scripts/deployment/prepare_promptagent_pilots.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rows=[module.template(Path('/srv/arena'),model,Path('/srv/arena/configs/promptagent')) for model in pilot.MODELS]
    assert len({r['id'] for r in rows})==7
    for row,model in zip(rows,pilot.MODELS):
        assert row['status']=='blocked' and row['blocked_reason']
        assert row['spec']['request']['arguments']==['--model',model]
        assert row['spec']['timeout_seconds']==2400 and row['resources']['evaluation_slots']==1
        assert row['spec']['source_dir']=='/srv/arena/sources/promptagent'
        assert row['spec']['environment_names']==['OPENAI_API_KEY']


def test_provider_port_checks_native_hash(tmp_path):
    path=tmp_path/next(iter(pilot.PORT_FILES));path.parent.mkdir(parents=True);path.write_text('changed provider')
    with pytest.raises(ValueError,match='reviewed pin'):
        pilot.ports(tmp_path)


def test_default_sdk_has_no_retries_redirects_or_ambient_proxy(tmp_path,monkeypatch):
    import sys
    captured={}
    def http_client(**kwargs):
        captured['http']=kwargs
        return 'fixture-http-client'
    def sdk_client(**kwargs):
        captured['sdk']=kwargs
        return 'fixture-sdk-client'
    monkeypatch.setitem(sys.modules,'httpx',SimpleNamespace(Client=http_client))
    monkeypatch.setitem(sys.modules,'openai',SimpleNamespace(OpenAI=sdk_client))
    monkeypatch.setenv('OPENAI_API_KEY','private-fixture-key')
    gateway=transport.GatewayTransport(pilot.MODELS[0],tmp_path)
    assert gateway.client=='fixture-sdk-client'
    assert captured['http']=={'follow_redirects':False,'trust_env':False,'timeout':330}
    assert captured['sdk']['max_retries']==0 and captured['sdk']['base_url']==transport.ENDPOINT
    gateway.save()
    assert 'private-fixture-key' not in (tmp_path/'gateway-usage.json').read_text()
