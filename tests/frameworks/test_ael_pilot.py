"""AEL transport/config tests; real native offline conformance is a separate CLI."""
import csv
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from arena.frameworks.drivers import ael_gateway_transport as transport
from arena.frameworks.drivers import ael_portfolio_gateway as pilot
from arena.frameworks.recipes import load_recipes, validate_recipe


def client(callback):
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=callback)))


@pytest.mark.parametrize("model", pilot.MODELS)
def test_exact_model_all_roles_and_native_response_shape(tmp_path, model):
    calls = []
    response = SimpleNamespace(model=model, choices=[SimpleNamespace(message=SimpleNamespace(content='{"AAPL":0.6,"MSFT":0.4}'))], usage=None)
    gateway = transport.GatewayTransport(model, tmp_path, client=client(lambda **kwargs: calls.append(kwargs) or response))
    transport.install_transport(gateway)
    for _ in range(3):  # allocation, reflection and generated-planner interfaces share llm_call
        assert transport.llm_call(model, [{"role":"user", "content":"fixture"}],
            temperature=0.4, max_tokens=512, response_format={"type":"json_object"}) is response
    assert all(c["model"] == model and c["stream"] is False for c in calls)
    assert all("temperature" not in c and "max_tokens" not in c for c in calls)
    usage = json.loads((tmp_path / "gateway-usage.json").read_text())
    assert usage["requests_attempted"] == 3 and usage["cost_usd"] is None
    assert usage["provider_controls_unenforced"] == ["temperature", "max_tokens"]
    assert "fixture" not in json.dumps(usage)


def test_provider_failure_escapes_native_exception_fallback_and_redacts_details(tmp_path):
    def fail(**kwargs):
        raise RuntimeError("private-token-value and private provider response")
    gateway = transport.GatewayTransport(pilot.MODELS[0], tmp_path, client=client(fail))
    fallback = False
    with pytest.raises(transport.AELGatewayStopped):
        try:
            gateway.complete(pilot.MODELS[0], [{"role":"user", "content":"prompt"}])
        except Exception:
            fallback = True
    assert not fallback
    raw = (tmp_path / "gateway-usage.json").read_text()
    assert "private-token" not in raw and "private provider" not in raw
    assert json.loads(raw)["records"][0]["outcome"] == "unknown"


def test_budget_is_actual_sdk_admission_with_no_retry(tmp_path):
    calls = []
    response = SimpleNamespace(model=pilot.MODELS[0], choices=[SimpleNamespace(message=SimpleNamespace(content="fixture"))], usage=None)
    gateway = transport.GatewayTransport(pilot.MODELS[0], tmp_path, client=client(lambda **kw: calls.append(kw) or response))
    for _ in range(transport.REQUEST_LIMIT):
        gateway.complete(pilot.MODELS[0], [])
    with pytest.raises(transport.AELGatewayStopped, match="budget"):
        gateway.complete(pilot.MODELS[0], [])
    assert len(calls) == transport.REQUEST_LIMIT == 64


@pytest.mark.parametrize("change", [{"model":"openai/gpt-5.6-sol"}, {"api_key":"forbidden"}, {"response_format":{"type":"json_schema"}}])
def test_no_model_alias_credential_or_unreviewed_controls(tmp_path, change):
    gateway = transport.GatewayTransport(pilot.MODELS[0], tmp_path,
        client=client(lambda **kw: pytest.fail("Must fail before SDK dispatch")))
    with pytest.raises(transport.AELGatewayStopped):
        gateway.complete(**({"model":pilot.MODELS[0], "messages":[]} | change))


def test_missing_native_cached_returns_fail_before_evaluation(tmp_path):
    bars = [day + f" {hour}:30:00-05:00" for day in pilot.DAYS for hour in ("09","11","13","15")]
    for ticker in pilot.TICKERS:
        for folder, fieldnames, records in [
            ('prices_1h', ['Datetime'], [{"Datetime":bar} for bar in bars]),
            ('returns_1h', ['datetime','direction_1bar','return_1bar'],
             [{"datetime":bar,"direction_1bar":"flat","return_1bar":0.001} for bar in bars])]:
            path = tmp_path / f'data/{folder}/{ticker}.csv'
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('w') as stream:
                writer=csv.DictWriter(stream, fieldnames=fieldnames);writer.writeheader();writer.writerows(records)
        for category in ('fundamentals','analyst','options','earnings'):
            path=tmp_path/f'data/{category}/{ticker}.json';path.parent.mkdir(parents=True, exist_ok=True);path.write_text('{}')
    assert pilot.data_schedule(tmp_path) == bars
    path = tmp_path / 'data/returns_1h/MSFT.csv'
    path.write_text(path.read_text().replace('0.001','nan',1))
    with pytest.raises(ValueError, match="realized return"):
        pilot.data_schedule(tmp_path)


def test_new_recipe_and_seven_templates_preserve_legacy_identity():
    root = Path(__file__).resolve().parents[2]
    new = json.loads((root / "registry/framework-recipes/ael-portfolio-gateway.json").read_text())["recipes"][0]
    assert validate_recipe(new)["id"] == pilot.ENGINE
    old = load_recipes(root / "registry")["ael-harness"]
    assert old["profiles"][0]["id"] == 'portfolio'
    assert new["repository"] == old["repository"]
    path = root / 'scripts/deployment/prepare_ael_pilots.py'
    spec = importlib.util.spec_from_file_location('prepare_ael_pilots', path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rows=[module.template(Path('/srv/arena'), model, Path('/srv/arena/configs/ael')) for model in pilot.MODELS]
    assert len({r['id'] for r in rows}) == 7
    for row,model in zip(rows,pilot.MODELS):
        assert row['model'] == model and row['spec']['request']['arguments'] == ['--model',model]
        assert row['status'] == 'blocked' and row['blocked_reason']
        assert row['spec']['timeout_seconds'] == 2400
        assert row['resources']['evaluation_slots'] == 1
        assert row['spec']['environment_names'] == ['OPENAI_API_KEY']
        assert set(row['spec']['request']['inputs']) == {'arena-inputs/ael-preparation.json','arena-inputs/ael-dependencies.txt'}


def test_native_full_config_keeps_evolution_and_sets_all_model_roles(tmp_path, monkeypatch):
    # Core Arena tests do not install native dependencies. Real YAML parsing is
    # exercised by the separate pinned-environment native conformance CLI.
    monkeypatch.setitem(sys.modules, "yaml", SimpleNamespace(safe_load=json.loads))
    original = {"planner":{"evolve":True,"enabled_planners":["sequential","adaptive"]},
                "tools":{"evolve":True}, "memory":{"evolve":True,"backend":"local"},
                "credit":{"method":"fcc","use_shapley":True},
                "benchmark":{"tickers":["unused"],"frequency":"1d"}}
    path=tmp_path/pilot.CONFIG_PATH;path.parent.mkdir(parents=True);path.write_text(json.dumps(original))
    config=pilot.native_config(tmp_path,pilot.MODELS[-1],tmp_path/'result')
    for key in ('planner','tools','memory','credit'):
        assert config[key] == original[key]
    assert config['llm_model'] == config['reflection']['llm_model'] == config['reflection']['meta_llm_model'] == config['cold_start']['llm_model'] == pilot.MODELS[-1]
    assert config['benchmark']['frequency'] == '1h'
    assert config['benchmark']['train_end_date'] == pilot.DAYS[1]
    assert config['benchmark']['val_end_date'] == pilot.DAYS[2]
    assert config['benchmark']['end_date'] == pilot.DAYS[-1]
    assert config['num_episodes'] == 16 and config['warm_up_episodes'] == 0


@pytest.mark.parametrize("response_model,count", [("another-model",1),(pilot.MODELS[0],0),(pilot.MODELS[0],2)])
def test_response_identity_and_choice_count_fail_closed(tmp_path, response_model, count):
    response=SimpleNamespace(model=response_model, choices=[SimpleNamespace(message=SimpleNamespace(content="fixture")) for _ in range(count)], usage=None)
    gateway=transport.GatewayTransport(pilot.MODELS[0], tmp_path, client=client(lambda **kw: response))
    with pytest.raises(transport.AELGatewayStopped):
        gateway.complete(pilot.MODELS[0], [])
    usage=json.loads((tmp_path/'gateway-usage.json').read_text())
    assert usage['records'][0]['status'] == 'error'
    assert usage['records'][0]['outcome'] == 'unknown'
