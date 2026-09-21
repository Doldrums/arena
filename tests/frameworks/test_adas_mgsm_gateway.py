"""ADAS provenance, budget and native delegation checks; no paid requests."""
import hashlib
import importlib.util
import json
from pathlib import Path
import random
from types import SimpleNamespace

import pytest

from arena.frameworks.drivers import adas_mgsm_gateway as pilot
from arena.frameworks.recipes import load_recipes, validate_recipe

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "registry/datasets/mgsm-adas-pilot-v1.json"


def test_dataset_is_official_and_parallel_problem_groups_are_disjoint(tmp_path):
    data = pilot.load_dataset(DATASET)
    assert data["commit"] == "452a21ad3dae5668c06ceeac21ff073e1e40f9be"
    assert data["license"] == "CC-BY-4.0"
    assert data["selection"]["optimization"] == [["en", 0], ["es", 1]]
    assert data["selection"]["heldout"] == [["en", 2], ["es", 3]]
    for row in sum(data["splits"].values(), []):
        assert pilot.digest(row["question"] + "\t" + row["answer"]) == row["source_line_sha256"]
    tampered = tmp_path / "data.json"
    tampered.write_bytes(DATASET.read_bytes() + b" ")
    with pytest.raises(ValueError, match="immutable"):
        pilot.load_dataset(tampered)


def test_shuffle_inverse_preserves_declared_native_slices():
    desired = [{"id": str(n)} for n in range(4)]
    arranged = pilot.before_native_shuffle(desired)
    random.Random(0).shuffle(arranged)
    assert arranged[:2] == desired[:2]
    assert arranged[2:] == desired[2:]


def test_original_recipe_unchanged_and_new_identity_is_explicit():
    recipes = load_recipes()
    assert hashlib.sha256(json.dumps(recipes["adas"], sort_keys=True).encode()).hexdigest() == "4da3555f4a6d2976158790f1c26fe4a337d294f5ffc3e4c08a4140854ed6102e"
    recipe = recipes[pilot.IDENTITY]
    assert validate_recipe(recipe) is recipe
    assert recipe["repository"] == recipes["adas"]["repository"]
    assert recipe["participant_ids"] == ["adas"]
    assert recipe["profiles"][0]["invocation"]["target"].endswith(".adas_mgsm_gateway")


def test_request_failure_is_not_swallowed_or_retried_or_recorded_as_zero(tmp_path):
    count = []
    def failed(**kwargs):
        count.append(kwargs)
        raise TimeoutError("credential-must-not-appear")
    session = pilot.Session(tmp_path, pilot.MODELS[0], failed)
    with pytest.raises(pilot.PilotStop, match="provider_request_failed"):
        session.call(model=pilot.MODELS[0], messages=[])
    assert len(count) == session.requests == 1
    assert session.completed_requests == 0
    events = (tmp_path / "events.jsonl").read_text()
    assert "TimeoutError" in events and '"outcome": "unknown"' in events
    assert "credential-must-not-appear" not in events and '"scores"' not in events
    assert not issubclass(pilot.PilotStop, Exception)
    with pytest.raises(pilot.PilotStop, match="provider_request_failed"):
        session.call(model=pilot.MODELS[0], messages=[])
    assert len(count) == 1  # Previously queued native executor task cannot dispatch.


def test_request_and_model_budget_reject_before_dispatch(tmp_path):
    def forbidden(**kwargs):
        pytest.fail("dispatch must not occur")
    session = pilot.Session(tmp_path, pilot.MODELS[0], forbidden)
    with pytest.raises(pilot.PilotStop, match="model_mismatch"):
        session.call(model="gpt-3.5-turbo-0125")
    assert session.requests == 0
    session = pilot.Session(tmp_path, pilot.MODELS[0], forbidden)
    session.requests = pilot.REQUESTS
    with pytest.raises(pilot.PilotStop, match="request_budget"):
        session.call(model=pilot.MODELS[0])


@pytest.mark.parametrize("response_model,contents", [
    ("different-model", ["{}"]), (pilot.MODELS[0], []),
    (pilot.MODELS[0], ["{}", "{}"]), (pilot.MODELS[0], [None]),
])
def test_invalid_response_identity_or_shape_stops_native_followups(tmp_path, response_model, contents):
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(model=response_model, choices=[
            SimpleNamespace(message=SimpleNamespace(content=content)) for content in contents
        ])
    session = pilot.Session(tmp_path, pilot.MODELS[0], create)
    for _ in range(2):
        with pytest.raises(pilot.PilotStop, match="provider_request_failed"):
            session.call(model=pilot.MODELS[0])
    assert len(calls) == session.requests == 1
    assert session.completed_requests == 0
    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert [event["type"] for event in events] == ["request_started", "request_failed"]
    assert events[-1]["error_class"] == "ValueError"


def test_wall_budget_prevents_late_request(tmp_path, monkeypatch):
    session = pilot.Session(tmp_path, pilot.MODELS[0], lambda **kw: pytest.fail("late dispatch"))
    monkeypatch.setattr(pilot.time, "monotonic", lambda: session.started + pilot.WALL_SECONDS)
    with pytest.raises(pilot.PilotStop, match="wall_budget"):
        session.call(model=pilot.MODELS[0])


def test_selection_excludes_native_debug_code_with_stale_fitness():
    archive = [{"code": "evaluated", "fitness": "rounded native string"},
               {"code": "new-debug-code", "fitness": "99.9%"},
               {"code": "tied", "fitness": "other"}]
    records = [{"phase": "optimization", "code_sha256": pilot.digest(code), "mean": mean}
               for code, mean in [("evaluated", 0.5), ("tied", 0.5)]]
    selected, record = pilot.select_observed(archive, records)
    assert selected is archive[0] and record["mean"] == 0.5
    with pytest.raises(pilot.PilotStop, match="no_evaluated"):
        pilot.select_observed([archive[1]], records)


def fake_native(output, observations):
    class Agent:
        def __init__(self, fields, name, role, model, temperature):
            self.model = model
    native = SimpleNamespace(LLMAgentBase=Agent, get_prompt=lambda archive: ("system", "model='gpt-3.5-turbo-0125'"))
    def api(*args, **kwargs):
        pass
    native.get_json_response_from_gpt = SimpleNamespace(__wrapped__=api)
    native.get_json_response_from_gpt_reflect = SimpleNamespace(__wrapped__=api)
    def evaluate(args, code):
        examples = native.get_all_examples()
        random.Random(args.shuffle_seed).shuffle(examples)
        if native.SEARCHING_MODE:
            assert len(examples) == 2
            observations.append("optimization")
        else:
            assert len(examples) == 4
            assert (output / "selection.json").exists()
            observations.append("heldout")
        return [1, 0]
    native.evaluate_forward_fn = evaluate
    def search(args):
        native.evaluate_forward_fn(args, "native-code")
        pilot.write_json(output / "mgsm_run_archive.json", [{"code": "native-code", "generation": "initial"}])
    native.search = search
    utils = SimpleNamespace(LANG_TO_INSTRUCTIONS={"en": "EN {input}", "es": "ES {input}"})
    return native, utils


def test_delegation_freezes_selection_before_heldout_and_binds_all_roles(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "inert-key")
    output = tmp_path / "results"
    observed = []
    pair = fake_native(output, observed)
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: None)))
    args = SimpleNamespace(model=pilot.MODELS[2], output=output, dataset=DATASET)
    assert pilot.run(args, native_pair=pair, client=client) == 0
    assert observed == ["optimization", "heldout"]
    assert pair[0].LLMAgentBase([], "agent").model == pilot.MODELS[2]
    with pytest.raises(pilot.PilotStop, match="model_mismatch"):
        pair[0].LLMAgentBase([], "agent", model="gpt-3.5-turbo-0125")
    assert pilot.MODELS[2] in pair[0].get_prompt([])[1]
    proof = json.loads((output / "heldout.json").read_text())
    assert proof["scores"] == [1, 0] and not proof["canonical_evaluation"]
    assert proof["selection_sha256"] == pilot.digest((output / "selection.json").read_bytes())
    assert "inert-key" not in (output / "provider-seam.json").read_text()
    with pytest.raises(ValueError, match="empty"):
        pilot.run(args, native_pair=pair, client=client)


def test_evaluation_budget_stops_before_native_code(tmp_path):
    observations = []
    native, utils = fake_native(tmp_path, observations)
    session = pilot.Session(tmp_path, pilot.MODELS[0], lambda **kwargs: None)
    session.evaluations = pilot.EVALUATIONS
    pilot.bind_native(native, utils, session, pilot.load_dataset(DATASET))
    with pytest.raises(pilot.PilotStop, match="evaluation_budget"):
        native.evaluate_forward_fn(SimpleNamespace(), "code")
    assert observations == []


@pytest.mark.parametrize("option", ["--request-budget", "--n-generation", "--timeout"])
def test_cannot_override_fixed_pilot_budgets(option):
    with pytest.raises(SystemExit):
        pilot.main(["--model", pilot.MODELS[0], "--output", "/not-created", option, "999"])


def test_seven_pure_templates_require_dataset_and_exact_source():
    spec = importlib.util.spec_from_file_location("adas_preparation_test", ROOT / "scripts/deployment/prepare_adas_mgsm_pilot.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    items = module.templates(Path("/srv/arena"), Path("/fixture/data.json"))
    assert len(items) == 7 and {item["model"] for item in items} == set(pilot.MODELS)
    for item in items:
        assert item["spec"]["request"]["arguments"] == ["--model", item["model"]]
        assert item["spec"]["request"]["inputs"] == {"arena-inputs/mgsm-adas-pilot-v1.json": "/fixture/data.json"}
        assert item["spec"]["source_dir"] == "/srv/arena/sources/adas"
        assert item["spec"]["timeout_seconds"] == 3600
        assert item["resources"]["evaluation_slots"] == 1
