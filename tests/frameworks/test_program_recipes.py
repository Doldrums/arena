"""Offline conformance of program-search recipes and thin library launch bridges."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

from arena.frameworks.recipes import RecipeAdapter, validate_recipe

ROOT = Path(__file__).resolve().parents[2]
RECIPES = json.loads((ROOT / "registry/framework-recipes/program-search.json").read_text())["recipes"]
BY_ID = {row["id"]: row for row in RECIPES}
EXPECTED_IDS = {
    "adaevolve", "evox", "eoh", "evolcaf", "reevo", "hsevo", "mcts-ahd", "meoh",
    "funsearch-re-implementation", "codeevolve", "base", "llm-lex", "loongflow",
    "eurekagent", "the-station", "coevo", "coral", "deliberate-evolution", "rankevolve",
}


def test_program_batch_covers_each_research_identity_once():
    assert len(RECIPES) == len(EXPECTED_IDS)
    assert {p for r in RECIPES for p in r["participant_ids"]} == EXPECTED_IDS
    assert sum(len(r["participant_ids"]) for r in RECIPES) == len(EXPECTED_IDS)
    for recipe in RECIPES:
        validate_recipe(recipe)
        assert recipe["evidence"], recipe["id"]
        for profile in recipe["profiles"]:
            assert set(profile["required_files"]) <= recipe["evidence"].keys()
            assert set(profile["config_files"]) <= recipe["evidence"].keys()
            assert profile["evaluation"]["mode"] == "native"


def test_shared_skydiscover_source_keeps_distinct_native_algorithms():
    ada, evo = BY_ID["adaevolve"], BY_ID["evox"]
    assert ada["repository"] == evo["repository"]
    for recipe in (ada, evo):
        argv = recipe["profiles"][0]["fixed_args"]
        assert argv[argv.index("--search") + 1] == recipe["id"]


def test_unavailable_artifact_is_not_misrepresented_as_a_search_engine(tmp_path):
    for identity in ("deliberate-evolution",):
        recipe = BY_ID[identity]
        assert recipe["status"] == "blocked"
        assert not recipe["profiles"]
        with pytest.raises(ValueError, match=recipe["blocked_reason"][:15]):
            RecipeAdapter(recipe).prepare(tmp_path, {"python": sys.executable}, tmp_path / "out")


def _inert_source(tmp_path, recipe):
    """No downloaded packages are needed: prepare must never import its source."""
    source = tmp_path / "source"
    source.mkdir()
    recipe = deepcopy(recipe)
    for relative in recipe["evidence"]:
        file = source / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        payload = b"raise RuntimeError('native code must not run during preparation')\n"
        file.write_bytes(payload)
        recipe["evidence"][relative] = hashlib.sha256(payload).hexdigest()
    return recipe, source


@pytest.mark.parametrize("identity,profile_id", [(r["id"], p["id"]) for r in RECIPES for p in r["profiles"]])
def test_recipe_preparation_is_inert_and_targets_an_isolated_workspace(tmp_path, identity, profile_id):
    recipe, source = _inert_source(tmp_path, BY_ID[identity])
    output = tmp_path / "run"
    profile = next(p for p in recipe["profiles"] if p["id"] == profile_id)
    command = RecipeAdapter(recipe).prepare(source, {"python": sys.executable, "profile": profile["id"],
                                            "executables": {name: sys.executable for name in profile.get("executable_args", {})}}, output)
    assert command["workspace_copy"] is True
    assert Path(command["cwd"]).is_relative_to(output / "workspace")
    assert not output.exists()
    assert command["evaluation"]["mode"] == "native"
    if profile["output"]:
        assert str(output / profile["output"]["path"]) in command["argv"]
    assert all(path.is_file() for path in [source / p for p in recipe["evidence"]])


def test_source_tampering_fails_before_any_launch(tmp_path):
    recipe, source = _inert_source(tmp_path, BY_ID["base"])
    (source / "run_base.py").write_text("print('changed')")
    with pytest.raises(ValueError, match="evidence mismatch"):
        RecipeAdapter(recipe).prepare(source, {"python": sys.executable, "profile": "circle-packing"}, tmp_path / "out")


def test_recipe_cannot_silently_change_the_registered_search_algorithm(tmp_path):
    recipe, source = _inert_source(tmp_path, BY_ID["adaevolve"])
    with pytest.raises(ValueError, match="fixes this option"):
        RecipeAdapter(recipe).prepare(source, {"python": sys.executable, "arguments": ["--search", "evox"]}, tmp_path / "out")


def _module(monkeypatch, name, **values):
    module = ModuleType(name)
    module.__dict__.update(values)
    monkeypatch.setitem(sys.modules, name, module)
    return module


def test_eoh_driver_delegates_once_with_native_problem_and_explicit_budgets(tmp_path, monkeypatch):
    from arena.frameworks.drivers import eoh
    calls = {}
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-key")
    cwd = tmp_path / "repo/examples/bp_online"
    cwd.mkdir(parents=True)
    monkeypatch.chdir(cwd)

    def method(**kwargs):
        calls.update(kwargs)
        return SimpleNamespace(run=lambda: calls.update(ran=calls.get("ran", 0) + 1))

    _module(monkeypatch, "eoh", EoH=method, LLMConfig=lambda **kw: kw)
    _module(monkeypatch, "prob", BPONLINE=lambda **kw: {"native_problem": kw})
    old_path = sys.path[:]
    try:
        assert eoh.main(["--endpoint", "example.invalid", "--model", "test-model",
                         "--population", "4", "--generations", "2", "--samples", "8",
                         "--output", str(tmp_path / "result")]) == 0
    finally:
        sys.path[:] = old_path
    assert calls["ran"] == 1
    assert calls["pop_size"] == 4 and calls["n_pop"] == 2 and calls["max_sample_nums"] == 8
    assert calls["problem"] == {"native_problem": {"capacity": 100, "timeout": 40}}
    assert calls["llm"]["api_key"] == "unit-test-key"
    assert not (tmp_path / "result").exists()  # only the native method owns run artifacts


def test_meoh_driver_preserves_two_objective_evaluator(tmp_path, monkeypatch):
    from arena.frameworks.drivers import meoh
    calls = {}
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-key")
    native_eval = object()

    def method(**kwargs):
        calls.update(kwargs)
        return SimpleNamespace(run=lambda: calls.update(ran=True))

    for name in ("llm4ad", "llm4ad.task", "llm4ad.task.optimization", "llm4ad.tools", "llm4ad.tools.llm", "llm4ad.method"):
        _module(monkeypatch, name)
    _module(monkeypatch, "llm4ad.task.optimization.online_bin_packing_2O", OBP_2O_Evaluation=lambda **kw: native_eval)
    class HttpsApi:
        def __init__(self, **kw):
            self._key = kw.pop("key")
            self.__dict__.update(kw)

    _module(monkeypatch, "llm4ad.tools.llm.llm_api_https", HttpsApi=HttpsApi)
    _module(monkeypatch, "llm4ad.method.meoh", MEoH=method, MEoHProfiler=lambda **kw: kw)
    assert meoh.main(["--host", "example.invalid", "--model", "test-model", "--population", "4",
                      "--generations", "2", "--samples", "8", "--output", str(tmp_path / "result")]) == 0
    assert calls["ran"] and calls["evaluation"] is native_eval and calls["num_objs"] == 2
    assert calls["max_generations"] == 2 and calls["max_sample_nums"] == 8
    assert calls["profiler"]["num_objs"] == 2
    assert calls["llm"]._key == "unit-test-key"
    assert "unit-test-key" not in str(calls["llm"].__dict__)


def test_meoh_provider_credentials_are_not_serialized_by_native_profiler(monkeypatch):
    from arena.frameworks.drivers.meoh import environment_key_provider
    monkeypatch.setenv("OPENAI_API_KEY", "secret-fixture-only")

    class NativeProvider:
        def __init__(self, key):
            self._key = key
            self._model = "test-model"

        def authorization(self):
            return "Bearer " + self._key

    provider = environment_key_provider(NativeProvider)(key="secret-fixture-only")
    assert provider.authorization() == "Bearer secret-fixture-only"
    assert provider.__dict__ == {"_model": "test-model"}
    assert provider.authorization.__func__ is NativeProvider.authorization
    monkeypatch.setenv("OPENAI_API_KEY", "rotated-fixture-only")
    assert provider.authorization() == "Bearer rotated-fixture-only"
    with pytest.raises(ValueError):
        environment_key_provider(NativeProvider)(key="unrelated-key")


@pytest.mark.parametrize("endpoint", ["https://example.invalid", "user@example.invalid", "example.invalid/path"])
def test_eoh_endpoint_matches_native_https_host_interface(endpoint, tmp_path):
    from arena.frameworks.drivers.eoh import main
    with pytest.raises(SystemExit):
        main(["--endpoint", endpoint, "--model", "test", "--population", "4", "--generations", "2",
              "--samples", "8", "--output", str(tmp_path / "out")])


@pytest.mark.parametrize("data", [{"x": [0, 1], "y": [1]}, {"x": [False, 1], "y": [1, 2]},
                                  {"x": [0, 1], "y": [1, float('nan')]},
                                  {"x": [0, 1], "y": [1, 2], "execute": "evil()"}])
def test_llmlex_data_boundary_rejects_ambiguous_or_nonfinite_inputs(tmp_path, data):
    from arena.frameworks.drivers.llm_lex import read_xy
    path = tmp_path / "data.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        read_xy(path)


def test_llmlex_driver_keeps_native_scores_and_formulae_as_data(tmp_path, monkeypatch):
    from arena.frameworks.drivers import llm_lex
    data = tmp_path / "input.json"
    data.write_text('{"x":[0,1],"y":[1,2]}')
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-key")
    sentinel = tmp_path / "must-not-exist"
    formula = f"__import__('pathlib').Path({str(sentinel)!r}).touch()"
    populations = [[{"ansatz": formula, "score": -2.5, "params": [1.0]}, {"score": float('-inf')}]]
    calls = {}
    _module(monkeypatch, "numpy", asarray=lambda v, **kw: v)
    _module(monkeypatch, "matplotlib", use=lambda _: None)
    _module(monkeypatch, "matplotlib.pyplot", subplots=lambda: (object(), SimpleNamespace(scatter=lambda *a: None)), close=lambda _: None)
    _module(monkeypatch, "openai", OpenAI=lambda **kw: SimpleNamespace(**kw))

    def genetic(*args, **kwargs):
        calls.update(kwargs)
        return populations

    _module(monkeypatch, "llmlex", run_genetic=genetic,
            images=SimpleNamespace(generate_base64_image=lambda *a: "image-data"))
    output = tmp_path / "result"
    assert llm_lex.main(["--data", str(data), "--model", "test-model", "--population", "4",
                         "--generations", "2", "--output", str(output)]) == 0
    result = json.loads((output / "native-populations.json").read_text())
    assert result["canonical_evaluation"] is False
    assert result["native"]["populations"][0][0]["score"] == -2.5
    assert result["native"]["populations"][0][0]["ansatz"] == formula
    assert result["native"]["populations"][0][1]["score"] == {"nonfinite": "-inf"}
    assert calls["population_size"] == 4 and calls["num_of_generations"] == 2
    assert not sentinel.exists()


@pytest.mark.parametrize("module_name", ["eoh", "meoh", "llm_lex"])
def test_driver_rejects_unbounded_population_before_import_or_credentials(module_name, monkeypatch):
    module = importlib.import_module("arena.frameworks.drivers." + module_name)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        module.main(["--population", "0"])
    assert exc.value.code == 2


def test_evolcaf_pins_the_actual_historical_implementation_separately():
    recipe = BY_ID["evolcaf"]
    assert recipe["repository"]["url"] == BY_ID["eoh"]["repository"]["url"]
    assert recipe["repository"]["commit"] == "4b2338fc2317c743cec50c5c7a2e4684707af973"
    assert recipe["repository"]["commit"] != BY_ID["eoh"]["repository"]["commit"]
    assert "examples/user_bo_caf/instance/botorch_problem.pkl" in recipe["evidence"]
    assert recipe["profiles"][0]["cwd"] == "examples/user_bo_caf"


def test_evolcaf_driver_calls_original_loop_with_original_evaluator(tmp_path, monkeypatch):
    from arena.frameworks.drivers import evolcaf
    calls = {}
    problem = object()
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-key")
    cwd = tmp_path / "repo/examples/user_bo_caf"
    cwd.mkdir(parents=True)
    monkeypatch.chdir(cwd)

    class Parameters:
        def set_paras(self, **kwargs):
            calls.update(kwargs)

    _module(monkeypatch, "eoh", eoh=SimpleNamespace(EVOL=lambda params: SimpleNamespace(run=lambda: calls.update(ran=True))))
    _module(monkeypatch, "eoh.utils")
    _module(monkeypatch, "eoh.utils.getParas", Paras=Parameters)
    _module(monkeypatch, "prob", Evaluation=lambda: problem)
    old_path = sys.path[:]
    try:
        assert evolcaf.main(["--endpoint", "example.invalid", "--model", "test-model", "--population", "4",
                             "--generations", "2", "--output", str(tmp_path / "result")]) == 0
    finally:
        sys.path[:] = old_path
    assert calls["ran"] and calls["problem"] is problem
    assert calls["method"] == "eoh" and calls["ec_pop_size"] == 4 and calls["ec_n_pop"] == 2
    assert calls["llm_api_key"] == "unit-test-key"
    assert not (tmp_path / "result").exists()


def test_coevo_removes_only_evidence_hashed_credential_template():
    recipe = BY_ID["coevo"]
    profile = recipe["profiles"][0]
    assert profile["remove_files"] == ["model_config.json"]
    assert "model_config.json" in recipe["evidence"]
    assert "model_config.json" not in profile["config_files"]
