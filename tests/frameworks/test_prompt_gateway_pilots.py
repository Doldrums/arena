"""Dataset integrity, exact scoring and bounded provider transport regressions."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest

from arena.frameworks.drivers import _gsm8k_pilot as common
from arena.frameworks.recipes import load_recipes

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "registry/datasets/gsm8k-prompt-pilot-v1.json"


def test_driver_imports_do_not_import_frameworks_or_sdk():
    subprocess.run([sys.executable, "-c", "import sys; from arena.frameworks.drivers import gepa_gateway_pilot, mipro_gateway_pilot; assert not {'openai','gepa','dspy'}.intersection(sys.modules)"], check=True)


def test_dataset_has_exact_genuine_rows_and_disjoint_explicit_source_splits(tmp_path):
    data = common.load_dataset(DATASET)
    rows = data["selected_records"]
    assert data["license"]["spdx"] == "MIT" and "Copyright (c) 2021 OpenAI" in data["license"]["text"]
    assert data["selection"]["uses_answers_for_selection"] is False
    for name in ("train", "validation", "heldout"):
        assert len(rows[name]) == 8
        assert all(r["source_split"] == ("test" if name == "heldout" else "train") for r in rows[name])
        assert all(hashlib.sha256(r["question"].encode()).hexdigest() == r["question_sha256"] for r in rows[name])
    assert len({r["question"] for split in rows.values() for r in split}) == 24
    changed = tmp_path / "altered.json"
    data["selected_records"]["train"][0]["answer"] = "#### 999"
    changed.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="hash"):
        common.load_dataset(changed)


@pytest.mark.parametrize("prediction,expected", [
    ("#### 1,234", "1234"), ("reasoning #### -12", "-12"),
    ("#### 1 then #### 2", "1"), ("#### 2.0", "2.0"),
    ("2", "[invalid]"), ("####\t2", "[invalid]"), ("no number", "[invalid]"),
])
def test_official_first_marker_string_metric_is_not_numeric_normalization(prediction, expected):
    assert common.extract_answer(prediction) == expected
    assert common.is_correct("#### 2.0", {"answer": "#### 2"}) is False
    assert common.is_correct("garbage", {"answer": "#### 0"}) is False


class Response(SimpleNamespace):
    def model_copy(self, update):
        return Response(**{**self.__dict__, **update})


def fake_client(calls, model="gpt-6-astra", fail=False):
    def create(**kwargs):
        calls.append(kwargs)
        if fail:
            raise RuntimeError("fixture failure")
        choice = Response(index=0, message=SimpleNamespace(content="choice-" + str(len(calls))))
        return Response(id=str(len(calls)), model=model, choices=[choice], usage=None)
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def test_ordered_draws_preserve_exact_model_and_unknown_usage_and_budget(tmp_path):
    calls = []
    ledger = tmp_path / "usage.json"
    transport = common.GatewayTransport("gpt-6-astra", ledger, limit=2, client=fake_client(calls))
    response = transport.complete([{"role": "user", "content": "fixture"}], n=2, temperature=.4)
    assert [c.message.content for c in response.choices] == ["choice-1", "choice-2"]
    assert [c.index for c in response.choices] == [0, 1] and response.usage is None
    assert all(c["n"] == 1 and c["model"] == "gpt-6-astra" for c in calls)
    assert copy.deepcopy(transport) is transport
    with pytest.raises(common.GatewayCallBudgetExhausted):
        transport.text("must not reach gateway")
    assert len(calls) == 2
    proof = json.loads(ledger.read_text())
    assert proof["gateway_requests_attempted"] == 2 and proof["cost_usd"] is None
    assert all(r["usage"] is None for r in proof["records"])


def test_failed_requests_consume_budget_and_response_identity_mismatch_fails_closed(tmp_path):
    calls = []
    transport = common.GatewayTransport("gpt-6-astra", tmp_path / "failed.json", limit=1, client=fake_client(calls, fail=True))
    with pytest.raises(RuntimeError): transport.text("fixture")
    with pytest.raises(common.GatewayCallBudgetExhausted): transport.text("no retry")
    assert len(calls) == 1
    assert json.loads((tmp_path / "failed.json").read_text())["records"][0]["error_type"] == "RuntimeError"
    wrong = common.GatewayTransport("gpt-6-astra", client=fake_client([], model="different-model"))
    with pytest.raises(ValueError, match="identity"):
        wrong.text("fixture")


def test_unreviewed_fields_and_invalid_draw_counts_fail_before_provider_call():
    calls = []
    transport = common.GatewayTransport("gpt-6-astra", client=fake_client(calls))
    for bad in (0, True, 9, 1.5):
        with pytest.raises(ValueError): transport.complete([], n=bad)
    with pytest.raises(ValueError): transport.complete([], api_key="must-not-send")
    assert not calls


def test_heldout_reports_raw_predictions_and_exact_denominator():
    rows = common.load_dataset(DATASET)["selected_records"]["heldout"]
    answers = {r["question"]: r["answer"] for r in rows}
    report = common.heldout_report(rows, lambda question: answers[question])
    assert report["correct"] == report["total"] == 8 and report["accuracy"] == 1
    assert all(r["source_split"] == "test" and r["prediction"] for r in report["records"])


def test_interrupted_heldout_preserves_completed_predictions_without_partial_accuracy(tmp_path):
    rows = common.load_dataset(DATASET)["selected_records"]["heldout"]
    calls = []
    def predict(question):
        calls.append(question)
        if len(calls) == 3:
            raise common.GatewayCallBudgetExhausted("fixture")
        return "#### -1"
    output = tmp_path / "heldout-partial.json"
    with pytest.raises(common.GatewayCallBudgetExhausted):
        common.heldout_report(rows, predict, output)
    proof = json.loads(output.read_text())
    assert proof["status"] == "partial" and proof["expected_total"] == 8
    assert proof["completed_count"] == len(proof["records"]) == 2
    assert proof["accuracy"] is None


def test_fourteen_templates_use_new_variants_and_hashed_dataset_inputs():
    recipes = load_recipes()
    for variant, original in (("gepa-gateway-gsm8k", "gepa"), ("miprov2-gateway-gsm8k", "mipro")):
        assert recipes[variant]["repository"] == recipes[original]["repository"]
        assert recipes[variant]["participant_ids"] == recipes[original]["participant_ids"]
    path = ROOT / "scripts/deployment/prepare_prompt_gateway_pilots.py"
    spec = importlib.util.spec_from_file_location("prompt_preparation_fixture", path)
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    records = [module.template(Path("/srv/arena"), framework, model, Path("/pinned-data.json"))
               for framework in module.ENGINES for model in module.MODELS]
    assert len({r["id"] for r in records}) == 14
    for row in records:
        assert row["resources"]["evaluation_slots"] == 1 and row["spec"]["timeout_seconds"] == 2400
        assert row["spec"]["request"]["arguments"] == ["--model", row["model"]]
        assert row["spec"]["request"]["inputs"] == {"arena-inputs/gsm8k-prompt-pilot-v1.json": "/pinned-data.json"}


@pytest.mark.parametrize("interrupt_heldout", [False, True])
def test_gepa_driver_freezes_selection_before_heldout_and_retains_stage_on_failure(monkeypatch, tmp_path, interrupt_heldout):
    from arena.frameworks.drivers import gepa_gateway_pilot as driver
    data = common.load_dataset(DATASET)
    answers = {r["question"]: r["answer"] for r in data["selected_records"]["heldout"]}
    events = []
    class Adapter:
        def __init__(self, **kwargs): self.kwargs = kwargs
    adapter_module = ModuleType("gepa.adapters.default_adapter.default_adapter")
    adapter_module.DefaultAdapter = Adapter
    adapter_module.EvaluationResult = lambda score, feedback: SimpleNamespace(score=score, feedback=feedback)
    monkeypatch.setitem(sys.modules, adapter_module.__name__, adapter_module)
    class Transport:
        def __init__(self, model, ledger): self.model, self.phase = model, "optimization"
        def text(self, messages):
            assert events[0] == "optimizer_returned"
            events.append(self.phase)
            if interrupt_heldout and self.phase == "heldout_selected" and events.count(self.phase) == 3:
                raise common.GatewayCallBudgetExhausted("fixture")
            return answers[messages[-1]["content"]]
        def save(self): pass
    monkeypatch.setattr(driver, "GatewayTransport", Transport)
    def optimize(**kwargs):
        assert kwargs["max_metric_calls"] == 24 and kwargs["reflection_minibatch_size"] == 3
        assert len(kwargs["trainset"]) == len(kwargs["valset"]) == 8
        assert not set(answers).intersection(r["input"] for r in kwargs["trainset"] + kwargs["valset"])
        assert "heldout" not in kwargs
        events.append("optimizer_returned")
        return SimpleNamespace(best_candidate={"instructions": "selected fixture"}, to_dict=lambda: {"fixture": True})
    monkeypatch.setitem(sys.modules, "gepa", SimpleNamespace(optimize=optimize))
    output = tmp_path / "output"
    code = driver.main(["--model", "gpt-6-astra", "--dataset", str(DATASET), "--output", str(output)])
    status = json.loads((output / "status.json").read_text())
    assert status["native_completed"] is True
    assert events[1:9] == ["heldout_seed"] * 8
    if interrupt_heldout:
        assert code == 75 and status["heldout_completed"] is False
        partial = json.loads((output / "heldout-selected.json").read_text())
        assert partial["completed_count"] == 2 and partial["accuracy"] is None
    else:
        assert code == 0 and status["heldout_completed"] is True
        assert events[9:] == ["heldout_selected"] * 8
