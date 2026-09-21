"""Offline evidence, boundaries and delegation tests for the additional engines."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

from arena.frameworks.recipes import RecipeAdapter, validate_recipe

ROOT = Path(__file__).resolve().parents[2]
RECIPES = json.loads((ROOT / "registry/framework-recipes/additional.json").read_text())["recipes"]
BY_ID = {r["id"]: r for r in RECIPES}


def module(monkeypatch, name, **attrs):
    result = ModuleType(name)
    result.__dict__.update(attrs)
    monkeypatch.setitem(sys.modules, name, result)
    return result


def test_each_additional_implementation_has_native_scoring_evidence():
    assert set(BY_ID) == {"eob", "evoor-agent", "dreureka", "lasr"}
    assert [p for r in RECIPES for p in r["participant_ids"]] == list(BY_ID)
    for recipe in RECIPES:
        validate_recipe(recipe)
        assert recipe["status"] == "source_verified"
        for profile in recipe["profiles"]:
            assert set(profile["required_files"]) <= recipe["evidence"].keys()
            assert set(profile["config_files"]) <= recipe["evidence"].keys()
            assert profile["evaluation"]["mode"] == "native"
    from arena.frameworks.drivers.evoor import SOURCE_SHA256
    assert BY_ID["evoor-agent"]["evidence"]["new_utils.py"] == SOURCE_SHA256


@pytest.mark.parametrize("identity", list(BY_ID))
def test_additional_prepare_reads_source_without_import_or_execution(tmp_path, identity):
    recipe = deepcopy(BY_ID[identity])
    source = tmp_path / "source"
    for path in recipe["evidence"]:
        target = source / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"raise RuntimeError('native imports forbidden during plan')\n")
        recipe["evidence"][path] = hashlib.sha256(target.read_bytes()).hexdigest()
    request = {"python": sys.executable}
    if identity == "lasr":
        request["executables"] = {"julia": sys.executable}
    output = tmp_path / "output"
    prepared = RecipeAdapter(recipe).prepare(source, request, output)
    assert not output.exists()
    assert prepared["workspace_copy"] is True
    assert Path(prepared["cwd"]).is_relative_to(output / "workspace")
    assert prepared["evaluation"]["mode"] == "native"
    if identity == "lasr":
        assert prepared["executables"][0]["name"] == "julia"
        assert prepared["executables"][0]["sha256"]


def test_eob_calls_native_multiobjective_loop_with_original_scorer(monkeypatch):
    from arena.frameworks.drivers import eob
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-key")
    config = SimpleNamespace(N=6, generation=2, nb_size=3, nr=2, n_jobs=1,
        algo_diff_run_time=1, algo_diff_base_FES=20, task_mode="task_bbob_expand",
        dim=10, custom_data_path=None, theta=.5, seed=42, selected_optimizer=["CMAES"], target_idx=None)
    calls = {}
    scorer = object()
    module(monkeypatch, "config", get_options=lambda args: config)
    module(monkeypatch, "utils")
    module(monkeypatch, "utils.utils", LLMWrapper=lambda **kwargs: kwargs)
    module(monkeypatch, "Constructor", ConstructorAgent=lambda llm: ("constructor", llm))
    module(monkeypatch, "Reflector", ReflectorAgent=lambda llm: ("reflector", llm))
    module(monkeypatch, "Scorer", ScoreAgent=lambda llm, options: scorer)

    async def run(**kwargs):
        calls["run"] = kwargs

    def generator(reflector, native_scorer, constructor, **kwargs):
        calls.update(scorer=native_scorer, kwargs=kwargs)
        return SimpleNamespace(run=run)

    module(monkeypatch, "Generator", AgenticFunctionGenerator=generator)
    assert eob.main(["--model", "gpt-test", "--N", "6", "--generation", "2"]) == 0
    assert calls["scorer"] is scorer
    assert calls["kwargs"]["H"] == 5
    assert calls["run"] == {"iterations": 2}


def test_evoor_port_is_exact_guarded_and_contains_no_credentials(tmp_path, monkeypatch):
    from arena.frameworks.drivers import evoor
    original = "\ufeff" + "\n".join(old for old, _ in evoor.REPLACEMENTS) + "\nunchanged_score = 5\n"
    source = tmp_path / "new_utils.py"
    source.write_bytes(original.encode("utf-8"))
    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    monkeypatch.setattr(evoor, "SOURCE_SHA256", expected)
    monkeypatch.setenv("OPENAI_API_KEY", "private-key-must-not-be-serialized")
    dataset = tmp_path / "data.json"
    dataset.write_text('{"en_question":"x","en_answer":"y"}\n')
    result = evoor.configure_workspace(tmp_path, dataset, tmp_path / "results")
    assert result["source_sha256"] == expected
    assert result["configured_sha256"] != expected
    assert "unchanged_score = 5" in source.read_text()
    assert source.read_bytes().startswith(b"\xef\xbb\xbf")
    assert 'os.environ["ARENA_EVOOR_DATASET"]' in source.read_text()
    assert "private-key-must-not-be-serialized" not in (tmp_path / "results/porting-receipt.json").read_text()
    with pytest.raises(ValueError, match="hash mismatch"):
        evoor.configure_workspace(tmp_path, dataset, tmp_path / "other")
    assert not (tmp_path / "other").exists()


def test_evoor_port_refuses_missing_or_duplicate_configuration_match(tmp_path, monkeypatch):
    from arena.frameworks.drivers import evoor
    original = "\n".join(old for old, _ in evoor.REPLACEMENTS) + "\n" + evoor.REPLACEMENTS[0][0]
    source = tmp_path / "new_utils.py"
    source.write_text(original)
    monkeypatch.setattr(evoor, "SOURCE_SHA256", hashlib.sha256(source.read_bytes()).hexdigest())
    dataset = tmp_path / "data.json"
    dataset.write_text("{}")
    with pytest.raises(ValueError, match="exactly once"):
        evoor.configure_workspace(tmp_path, dataset, tmp_path / "result")
    assert source.read_text() == original
    assert not (tmp_path / "result").exists()


def test_evoor_preserves_native_initialization_and_generation_schedule(tmp_path, monkeypatch):
    from arena.frameworks.drivers import evoor
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-key")
    monkeypatch.setattr(evoor, "configure_workspace", lambda *args: None)
    calls = []
    module(monkeypatch, "initial", generate_all=lambda **kw: calls.append(("initialize", kw)))
    module(monkeypatch, "evaluate", evolve_generation=lambda **kw: calls.append(("evolve", kw)))
    assert evoor.main(["--model", "test-model", "--population", "4", "--generations", "3",
                       "--dataset", "data.json", "--output", str(tmp_path / "results")]) == 0
    assert calls[0] == ("initialize", {"num_each": 4, "model_name": "test-model"})
    assert [c[1]["dst_generation"] for c in calls[1:]] == [2, 3]
    assert [c[1]["src_generation"] for c in calls[1:]] == [1, 2]
    assert all(c[1]["total_offspring"] == 4 for c in calls[1:])


@pytest.mark.parametrize("data", [
    {"X": [[1], [2]], "y": [1]}, {"X": [[1], [2, 3]], "y": [1, 2]},
    {"X": [[True], [2]], "y": [1, 2]}, {"X": [[1], [2]], "y": [1, float("nan")]},
    {"X": [[1], [2]], "y": [1, 2], "code": "unsafe"},
])
def test_lasr_numeric_boundary_rejects_code_and_ambiguous_data(tmp_path, data):
    from arena.frameworks.drivers.lasr import read_data
    path = tmp_path / "data.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        read_data(path)


def test_lasr_subprocess_keeps_user_strings_out_of_julia_code(tmp_path, monkeypatch):
    from arena.frameworks.drivers import lasr
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    data = tmp_path / "data.json"
    data.write_text('{"X":[[1,2],[3,4]],"y":[5,6]}')
    output = tmp_path / "results"
    calls = []
    monkeypatch.setattr(lasr.subprocess, "run", lambda args, **kw: calls.append((args, kw)) or SimpleNamespace(returncode=7))
    injection = 'model\"; run(`touch not-allowed`); #'
    assert lasr.main(["--julia", sys.executable, "--data", str(data), "--model", injection,
                      "--iterations", "2", "--populations", "3", "--output", str(output)]) == 7
    assert len(calls) == 1 and calls[0][1] == {"check": False}
    assert injection in calls[0][0]
    script = (output / "native-entry.jl").read_text()
    assert injection not in script and "unit-test-key" not in script
    assert "equation_search" in script and "Pkg.instantiate" not in script
    assert "--startup-file=no" in calls[0][0]
    assert json.loads((output / "input-data.json").read_text())["X"] == [[1, 2], [3, 4]]
