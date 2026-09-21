"""Transport/provenance bounds; full native fixture runs in the pinned environment."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from arena.frameworks.drivers import qdaif_gateway_transport as transport
from arena.frameworks.drivers import qdaif_poetry_gateway as pilot
from arena.frameworks.recipes import load_recipes, validate_recipe


class Response(dict):
    def __getattr__(self, key):
        return self[key]


def gateway(tmp_path, monkeypatch, model=None, response_model=None, count=1, failure=False):
    model = model or pilot.MODELS[0]
    monkeypatch.setenv('OPENAI_API_KEY', 'private-fixture-credential')
    calls = []
    class Session:
        def close(self):
            pass
        def request(self, method, url, **kwargs):
            calls.append((method, url, kwargs))
            if failure:
                raise RuntimeError('private-fixture-credential provider details')
            return SimpleNamespace(status_code=200)
    sdk=SimpleNamespace()
    def create(**kwargs):
        body={k:kwargs[k] for k in ('model','messages','stream')}
        sdk.requestssession().request('post', transport.ENDPOINT+'/chat/completions', data=json.dumps(body))
        return Response(model=response_model or model,
            choices=[SimpleNamespace(message=SimpleNamespace(content='native text')) for _ in range(count)], usage=None)
    sdk.ChatCompletion=SimpleNamespace(create=create)
    instance=transport.GatewayTransport(model,tmp_path,session=Session(),sdk=sdk)
    return instance,calls


@pytest.mark.parametrize('model', pilot.MODELS)
def test_exact_model_dual_native_interface(tmp_path, monkeypatch, model):
    instance,calls=gateway(tmp_path,monkeypatch,model=model)
    transport.install_transport(instance)
    model_fn=transport.make_model(SimpleNamespace(model_type='openai',model_path=model,logits_only=False))
    assert model_fn('native generation prompt') == 'native text'
    assert model_fn([SimpleNamespace(type='human',content='native judgment prompt')]).content == 'native text'
    assert len(calls) == 2
    assert all(json.loads(c[2]['data'])['model'] == model for c in calls)
    assert all(c[2]['timeout'] == 330 and c[2]['allow_redirects'] is False for c in calls)
    raw=(tmp_path/'gateway-usage.json').read_text()
    assert 'private-fixture-credential' not in raw and 'native generation prompt' not in raw
    assert json.loads(raw)['http_attempts'] == 2


@pytest.mark.parametrize('response_model,count',[('wrong-model',1),(None,0),(None,2)])
def test_response_identity_and_cardinality_stop(tmp_path, monkeypatch,response_model,count):
    instance,calls=gateway(tmp_path,monkeypatch,response_model=response_model,count=count)
    with pytest.raises(transport.QDAIFGatewayStopped):
        instance.complete('prompt')
    assert len(calls) == 1
    assert json.loads((tmp_path/'gateway-usage.json').read_text())['records'][0]['status'] == 'error'


def test_physical_request_budget_includes_sdk_internal_retries(tmp_path,monkeypatch):
    instance,calls=gateway(tmp_path,monkeypatch)
    body={'model':instance.model,'messages':[],'stream':False}
    # Every retry still enters the requestssession seam, independent of how many
    # ChatCompletion calls the legacy SDK made.
    for _ in range(transport.REQUEST_LIMIT):
        instance.sdk.requestssession().request('post',transport.ENDPOINT+'/chat/completions',data=json.dumps(body))
    with pytest.raises(transport.QDAIFGatewayStopped,match='budget'):
        instance.sdk.requestssession().request('post',transport.ENDPOINT+'/chat/completions',data=json.dumps(body))
    assert len(calls) == 24


def test_provider_errors_escape_quality_parse_fallback(tmp_path,monkeypatch):
    instance,calls=gateway(tmp_path,monkeypatch,failure=True)
    fallback=False
    with pytest.raises(transport.QDAIFGatewayStopped):
        try:
            instance.complete('prompt')
        except Exception:
            fallback=True
    assert not fallback
    raw=(tmp_path/'gateway-usage.json').read_text()
    assert 'private-fixture-credential' not in raw and 'provider details' not in raw
    assert json.loads(raw)['records'][0]['outcome'] == 'unknown'


@pytest.mark.parametrize('change',[{'model_type':'hf'},{'model_path':'gpt-4'},{'logits_only':True}])
def test_model_factory_rejects_old_alias_or_local_weights(tmp_path,monkeypatch,change):
    instance,calls=gateway(tmp_path,monkeypatch)
    transport.install_transport(instance)
    config={'model_type':'openai','model_path':instance.model,'logits_only':False}|change
    with pytest.raises(transport.QDAIFGatewayStopped):
        transport.make_model(SimpleNamespace(**config))
    assert not calls


def test_unreviewed_endpoint_and_controls_never_dispatch(tmp_path,monkeypatch):
    instance,calls=gateway(tmp_path,monkeypatch)
    body={'model':instance.model,'messages':[],'stream':False,'temperature':1}
    with pytest.raises(transport.QDAIFGatewayStopped):
        instance.dispatch('post',transport.ENDPOINT+'/chat/completions',data=json.dumps(body))
    with pytest.raises(transport.QDAIFGatewayStopped):
        instance.dispatch('post','https://unreviewed.invalid/v1/chat/completions',data='{}')
    assert not calls


def test_distinct_recipe_and_templates_preserve_old_qdaif_identity():
    root=Path(__file__).resolve().parents[2]
    new=json.loads((root/'registry/framework-recipes/qdaif-poetry-gateway.json').read_text())['recipes'][0]
    assert validate_recipe(new)['id'] == pilot.ENGINE
    old = load_recipes(root / "registry")["qdaif"]
    assert new['repository'] == old['repository'] and new['id'] != old['id']
    spec=importlib.util.spec_from_file_location('prepare_qdaif',root/'scripts/deployment/prepare_qdaif_pilots.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rows=[module.template(Path('/srv/arena'),model,Path('/srv/arena/configs/qdaif')) for model in pilot.MODELS]
    assert len({r['id'] for r in rows}) == 7
    for row,model in zip(rows,pilot.MODELS):
        assert row['status'] == 'blocked' and row['blocked_reason']
        assert row['spec']['request']['arguments'] == ['--model',model]
        assert row['spec']['timeout_seconds'] == 2400 and row['resources']['evaluation_slots'] == 1
        assert row['spec']['environment_names'] == ['OPENAI_API_KEY']
        assert len(row['spec']['request']['inputs']) == 3


def test_provider_port_is_source_hash_guarded(tmp_path):
    path=tmp_path/pilot.HELPER;path.parent.mkdir(parents=True);path.write_text('def get_model(config): return fake\n')
    with pytest.raises(ValueError,match='reviewed pin'):
        pilot.ported_helper(tmp_path)


def test_preexisting_sdk_session_is_rejected_before_dispatch(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','fixture')
    sdk=SimpleNamespace(api_requestor=SimpleNamespace(_thread_context=SimpleNamespace(session=object())))
    with pytest.raises(ValueError,match='fresh SDK process'):
        transport.GatewayTransport(pilot.MODELS[0],tmp_path,session=SimpleNamespace(),sdk=sdk)


def test_nonfinite_native_values_export_explicitly_without_changing_fitness():
    assert pilot.native_value({'quality':float('nan'),'values':[float('-inf'),11]}) == {
        'quality':{'nonfinite':'nan'},'values':[{'nonfinite':'-inf'},11]}
