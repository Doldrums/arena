from __future__ import annotations

import asyncio
from contextlib import nullcontext
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from arena.frameworks.drivers import aflow_gateway_pilot as pilot
from arena.frameworks.recipes import load_recipes

ROOT = Path(__file__).resolve().parents[2]


class FakeSDK:
    def __init__(self, model, calls, *, error=None):
        self.model, self.calls, self.error = model, calls, error
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        await asyncio.sleep(0)
        if self.error:
            raise self.error
        return SimpleNamespace(model=self.model, id="fixture", usage=SimpleNamespace(model_dump=lambda: {"total_tokens": 3}),
            choices=[SimpleNamespace(message=SimpleNamespace(content="fixture response"))])


def budget(model=pilot.MODELS[0], path=None, limit=1, response_model=None, error=None):
    calls, configurations = [], []
    def factory(**kwargs):
        configurations.append(kwargs)
        return FakeSDK(response_model or model, calls, error=error)
    return pilot.GatewayBudget(model, path, factory, limit), calls, configurations


@pytest.mark.parametrize("model", pilot.MODELS)
def test_exact_models_reach_sdk_without_credentials_in_ledger(tmp_path, model):
    bound, calls, configurations = budget(model, tmp_path / "usage.json")
    client = bound.client(api_key="inert-secret-fixture", base_url=pilot.ENDPOINT)
    result = asyncio.run(client.chat.completions.create(model=model, messages=[{"role": "user", "content": "fixture"}], temperature=1, top_p=1))
    assert result.model == model and calls[0]["model"] == model
    assert configurations[0]["timeout"] == 330 and configurations[0]["max_retries"] == 0
    serialized = bound.path.read_text()
    assert "inert-secret-fixture" not in serialized and '"content"' not in serialized
    assert json.loads(serialized)["cost_usd"] is None
    assert json.loads(serialized)["sdk_timeout_seconds"] == 330


def test_calls_across_native_round_event_loops_share_total_budget():
    bound, calls, _ = budget(limit=2)
    client = bound.client(api_key="fixture", base_url=pilot.ENDPOINT)
    for _ in range(2):
        asyncio.run(client.chat.completions.create(model=bound.model, messages=[]))
    with pytest.raises(pilot.PilotBudgetExhausted):
        asyncio.run(client.chat.completions.create(model=bound.model, messages=[]))
    assert len(calls) == 2
    assert not issubclass(pilot.PilotBudgetExhausted, Exception)


def test_parallel_graph_requests_cannot_overspend_budget():
    bound, calls, _ = budget(limit=1)
    client = bound.client(api_key="fixture", base_url=pilot.ENDPOINT)
    async def run():
        return await asyncio.gather(*(client.chat.completions.create(model=bound.model, messages=[]) for _ in range(4)), return_exceptions=True)
    results = asyncio.run(run())
    assert len(calls) == 1
    assert sum(isinstance(x, pilot.PilotBudgetExhausted) for x in results) == 3


def test_failures_still_count_and_different_models_are_rejected(tmp_path):
    bound, calls, _ = budget(path=tmp_path / "usage.json", response_model="other-model")
    client = bound.client(api_key="fixture", base_url=pilot.ENDPOINT)
    with pytest.raises(ValueError, match="identity"):
        asyncio.run(client.chat.completions.create(model=bound.model, messages=[]))
    assert len(calls) == len(bound.records) == 1
    assert bound.records[0]["status"] == "error"
    with pytest.raises(pilot.PilotBudgetExhausted):
        asyncio.run(client.chat.completions.create(model=bound.model, messages=[]))
    with pytest.raises(ValueError, match="Unreviewed"):
        asyncio.run(client.chat.completions.create(model="another-model", messages=[]))
    with pytest.raises(ValueError, match="endpoint"):
        bound.client(api_key="fixture", base_url="https://unreviewed.invalid/v1")


def test_fresh_workspace_refuses_old_results_before_any_cleanup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "workspace/GSM8K/workflows"
    (root / "round_1").mkdir(parents=True)
    for name in pilot.EMPTY_HISTORY:
        (root / name).write_bytes(b"")
    (root / "round_1/log.json").write_text("[]")
    with pytest.raises(ValueError, match="historical"):
        pilot.fresh_workspace()
    assert (root / "results.json").exists()
    (root / "round_1/log.json").write_bytes(b"")
    record = pilot.fresh_workspace()
    assert set(record) == set(pilot.EMPTY_HISTORY)
    assert all(not (root / name).exists() for name in record)


def test_materialization_separates_validation_and_heldout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    dataset = pilot.load_dataset(ROOT / "registry/datasets/gsm8k-prompt-pilot-v1.json")
    info = pilot.materialize_data(dataset, "validation")
    rows = [json.loads(x) for x in Path(info["path"]).read_text().splitlines()]
    assert len(rows) == 8 and rows[0]["question"] == dataset["selected_records"]["validation"][0]["question"]
    assert not Path("data/datasets/gsm8k_test.jsonl").exists()
    assert not {r["question"] for r in rows} & {r["question"] for r in dataset["selected_records"]["heldout"]}
    with pytest.raises(ValueError, match="replace"):
        pilot.materialize_data(dataset, "validation")


def test_native_completion_requires_every_fresh_round_and_experience(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rows = [{"round": n, "score": 0.5} for n in (1, 2, 3)]
    optimizer = SimpleNamespace(data_utils=SimpleNamespace(load_results=lambda _: rows))
    for n in (2, 3):
        path = Path(f"workspace/GSM8K/workflows/round_{n}")
        path.mkdir(parents=True)
        (path / "experience.json").write_text("{}")
    assert pilot.completed_rounds(optimizer)
    rows.pop()
    assert not pilot.completed_rounds(optimizer)
    rows.append({"round": 3, "score": float("nan")})
    assert not pilot.completed_rounds(optimizer)


def test_selection_frozen_from_native_validation_without_heldout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = Path("workspace/GSM8K/workflows/round_2")
    path.mkdir(parents=True)
    (path / "graph.py").write_text("class Workflow: pass")
    (path / "prompt.py").write_text("PROMPT='fixture'")
    optimizer = SimpleNamespace(data_utils=SimpleNamespace(get_top_rounds=lambda n: [{"round": 2, "score": 0.75}]))
    assert pilot.freeze_selection(optimizer, tmp_path) == 2
    result = json.loads((tmp_path / "selection.json").read_text())
    assert result["heldout_seen"] is False and result["validation_score"] == 0.75
    assert set(result["files"]) == {"graph.py", "prompt.py"}


def test_recipe_and_all_seven_templates_have_native_contract():
    recipe = load_recipes()["aflow-gateway-gsm8k-v1"]
    assert recipe["repository"]["commit"] == pilot.COMMIT
    assert recipe["participant_ids"] == ["aflow"]
    assert "remove_files" not in recipe["profiles"][0]
    spec = importlib.util.spec_from_file_location("aflow_prepare_fixture", ROOT / "scripts/deployment/prepare_aflow_gateway_pilots.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    templates = [module.template(Path("/srv/arena"), model, Path("/srv/arena/configs/data.json")) for model in pilot.MODELS]
    assert len({x["id"] for x in templates}) == 7
    for item, model in zip(templates, pilot.MODELS):
        assert item["spec"]["request"]["arguments"] == ["--model", model]
        assert item["resources"]["evaluation_slots"] == 1 and item["spec"]["timeout_seconds"] == 2400
        assert item["spec"]["environment_names"] == ["OPENAI_API_KEY"]


@pytest.mark.parametrize("failure,expected_status,code", [
    (None, "native_incomplete", 76),
    (pilot.PilotBudgetExhausted("fixture"), "budget_exhausted", 75),
])
def test_incomplete_or_budget_stopped_native_search_never_touches_heldout(tmp_path, monkeypatch, failure, expected_status, code):
    phases = []
    monkeypatch.setattr(pilot, "verify_source", lambda _: None)
    monkeypatch.setattr(pilot, "fresh_workspace", lambda: {})
    monkeypatch.setattr(pilot, "load_dataset", lambda _: {})
    monkeypatch.setattr(pilot, "GatewayBudget", lambda *a, **kw: SimpleNamespace(save=lambda: None))
    monkeypatch.setattr(pilot, "configure_native", lambda _: nullcontext())
    monkeypatch.setattr(pilot, "materialize_data", lambda d, phase: phases.append(phase))
    def native(mode):
        assert mode == "Graph"
        if failure:
            raise failure
    monkeypatch.setattr(pilot, "build_native", lambda *args: SimpleNamespace(optimize=native))
    monkeypatch.setattr(pilot, "completed_rounds", lambda _: False)
    def forbidden(*args):
        raise AssertionError("Selection and heldout must follow complete native search")
    monkeypatch.setattr(pilot, "freeze_selection", forbidden)
    output = tmp_path / "result"
    assert pilot.run(SimpleNamespace(model=pilot.MODELS[0], dataset=tmp_path / "ignored", output=output)) == code
    report = json.loads((output / "pilot.json").read_text())
    assert report["status"] == expected_status and not report["native_completed"]
    assert not report["heldout_completed"] and phases == ["validation"]


def test_provider_hook_enforces_serial_native_evaluation_and_restores_on_stop(monkeypatch):
    class NativeBenchmark:
        async def evaluate_all_problems(self, data, agent, max_concurrent_tasks=50):
            return {"count": len(data), "parallelism": max_concurrent_tasks, "agent": agent}
    old_sdk = object()
    llm = SimpleNamespace(AsyncOpenAI=old_sdk)
    scripts = SimpleNamespace(async_llm=llm)
    monkeypatch.setitem(sys.modules, "scripts", scripts)
    monkeypatch.setitem(sys.modules, "scripts.async_llm", llm)
    monkeypatch.setitem(sys.modules, "benchmarks.benchmark", SimpleNamespace(BaseBenchmark=NativeBenchmark))
    original = NativeBenchmark.evaluate_all_problems
    bound, _, _ = budget()
    with pytest.raises(pilot.PilotBudgetExhausted):
        with pilot.configure_native(bound):
            result = asyncio.run(NativeBenchmark().evaluate_all_problems(list(range(8)), "unchanged-agent"))
            assert result == {"count": 8, "parallelism": 1, "agent": "unchanged-agent"}
            assert bound.evaluations == 8
            asyncio.run(NativeBenchmark().evaluate_all_problems(list(range(40)), "unchanged-agent"))
    assert bound.evaluations == 8 and llm.AsyncOpenAI is old_sdk
    assert NativeBenchmark.evaluate_all_problems is original
