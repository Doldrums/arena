"""Original FunSearch source provenance and provider-boundary conformance."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest

from arena.frameworks.drivers import funsearch_original as driver
from arena.frameworks.recipes import RecipeAdapter, validate_recipe

ROOT = Path(__file__).resolve().parents[2]
RECIPE = json.loads((ROOT / "registry/framework-recipes/funsearch-original.json").read_text())["recipes"][0]


def native_fixture():
    """Small native-interface stand-in; no candidate code or real models run."""
    native = SimpleNamespace()

    class LLM:
        def __init__(self, samples_per_prompt):
            self._samples_per_prompt = samples_per_prompt

        def draw_samples(self, prompt):
            native.batch_sizes.append(self._samples_per_prompt)
            return [self._draw_sample(prompt) for _ in range(self._samples_per_prompt)]

    class Database:
        def __init__(self):
            self._best_program_per_island = [None]
            self._best_score_per_island = [-float("inf")]
            self._best_scores_per_test_per_island = [None]

        def get_prompt(self):
            return SimpleNamespace(code="native prompt", island_id=0, version_generated=2)

        def _register_program_in_island(self, program, island_id, scores_per_test):
            score = list(scores_per_test.values())[-1]
            if score > self._best_score_per_island[island_id]:
                self._best_program_per_island[island_id] = program
                self._best_score_per_island[island_id] = score
                self._best_scores_per_test_per_island[island_id] = scores_per_test

    def main(specification, inputs, config):
        native.main_calls.append((specification, inputs, config))
        database = native.programs_database.ProgramsDatabase()
        sandbox = native.evaluator.Sandbox()

        def analyse(program):
            scores = {}
            for item in inputs:
                score, runs_ok = sandbox.run(program, "evaluate", item, 30)
                if runs_ok and score is not None:
                    scores[item] = score
            if scores:
                database._register_program_in_island(program, 0, scores)

        analyse("seed")
        llm = native.sampler.LLM(config.samples_per_prompt)
        while True:
            prompt = database.get_prompt()
            for continuation in llm.draw_samples(prompt.code):
                analyse(continuation)

    native.sampler = SimpleNamespace(LLM=LLM)
    native.evaluator = SimpleNamespace(Sandbox=object)
    native.programs_database = SimpleNamespace(ProgramsDatabase=Database)
    native.main_calls = []
    native.batch_sizes = []
    native.main = main
    return native


def test_recipe_distinguishes_original_author_paper_from_community_paper():
    assert validate_recipe(RECIPE) is RECIPE
    assert RECIPE["participant_ids"] == []
    assert RECIPE["repository"]["url"] == "https://github.com/google-deepmind/funsearch"
    assert RECIPE["repository"]["commit"] == "cc53f274237d7ab05c19df939edbc1f9616a7c19"
    assert RECIPE["profiles"][0]["evaluation"]["mode"] == "native"


def test_optional_exact_pinned_source_and_nonexecuting_plan(tmp_path):
    source = os.environ.get("ARENA_FUNSEARCH_ORIGINAL_SOURCE")
    if not source:
        pytest.skip("Set ARENA_FUNSEARCH_ORIGINAL_SOURCE for exact source evidence checks")
    source = Path(source)
    assert subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() == RECIPE["repository"]["commit"]
    for filename, digest in RECIPE["evidence"].items():
        assert hashlib.sha256((source / filename).read_bytes()).hexdigest() == digest
    output = tmp_path / "output"
    command = RecipeAdapter(RECIPE).prepare(source, {
        "python": sys.executable,
        "profile": "single-threaded-native",
        "arguments": ["--factory", "inputs/provider.py:build", "--specification", "inputs/task.py", "--max-samples", "5"],
    }, output)
    assert command["argv"][:3] == [sys.executable, "-m", "arena.frameworks.drivers.funsearch_original"]
    assert command["argv"][-2:] == ["--output", str(output / "results")]
    assert command["workspace_copy"] and not output.exists()
    assert "funsearch.implementation.funsearch" not in sys.modules


def test_import_never_imports_native_code(tmp_path):
    script = "import sys; import arena.frameworks.drivers.funsearch_original; assert 'funsearch' not in sys.modules; assert 'numpy' not in sys.modules"
    subprocess.run([sys.executable, "-c", script], cwd=tmp_path,
                   env=os.environ | {"PYTHONPATH": str(ROOT / "src")}, check=True)


def test_namespace_uses_clone_and_restores_prior_modules(tmp_path, monkeypatch):
    implementation = tmp_path / "implementation"
    implementation.mkdir()
    (implementation / "funsearch.py").write_text("from funsearch.implementation import config\nvalue=config.value\n")
    (implementation / "config.py").write_text("value='pinned clone'\n")
    previous = ModuleType("funsearch")
    child = ModuleType("funsearch.preexisting")
    monkeypatch.setitem(sys.modules, "funsearch", previous)
    monkeypatch.setitem(sys.modules, "funsearch.preexisting", child)
    with pytest.raises(RuntimeError):
        with driver.native_namespace(tmp_path) as native:
            assert native.value == "pinned clone"
            assert "funsearch.preexisting" not in sys.modules
            raise RuntimeError("controlled failure")
    assert sys.modules["funsearch"] is previous
    assert sys.modules["funsearch.preexisting"] is child
    assert "funsearch.implementation.funsearch" not in sys.modules


def test_full_native_main_delegation_stops_at_exact_budget_and_evaluates_final_batch(tmp_path):
    native = native_fixture()
    original = native.sampler.LLM, native.evaluator.Sandbox, native.programs_database.ProgramsDatabase
    calls = []
    evaluations = []

    def draw(prompt):
        calls.append(prompt)
        return f"sample-{len(calls)}"

    class Sandbox:
        def run(self, program, function_to_run, value, timeout_seconds):
            evaluations.append((program, function_to_run, value, timeout_seconds))
            # A controlled provider result; no candidate program executes.
            return (0 if program == "seed" else int(program[-1])) + value, value == 1

    factory = {"draw_sample": draw, "sandbox_factory": Sandbox, "inputs": [1, 2]}
    config = SimpleNamespace(samples_per_prompt=3)
    assert driver.run_native(native, "native specification", factory, config, tmp_path, 5, 100000) == 0
    assert native.main_calls == [("native specification", [1, 2], config)]
    assert calls == ["native prompt"] * 5
    assert native.batch_sizes == [3, 2]
    assert len(evaluations) == 12  # Seed plus five samples, each on two inputs.
    assert ("sample-5", "evaluate", 2, 30) in evaluations
    assert (native.sampler.LLM, native.evaluator.Sandbox, native.programs_database.ProgramsDatabase) == original
    result = json.loads((tmp_path / "native-result.json").read_text())
    assert result["native_status"] == "sample_budget_reached"
    assert result["sample_calls"] == result["completed_samples"] == 5
    assert result["canonical_evaluation"] is False
    assert "fitness" not in result and "valid" not in result
    assert result["island_leaders"][0]["native_score"] == 6
    assert result["island_leaders"][0]["scores_per_test"] == [{"input": 1, "score": 6}]
    events = [json.loads(line) for line in (tmp_path / "native-trace.jsonl").read_text().splitlines()]
    assert len([event for event in events if event["event"] == "sample"]) == 5
    assert any(event["event"] == "evaluation" and event["runs_ok"] is False for event in events)
    assert events[-1]["event"] == "database_registration"
    assert events[-1]["program"] == "sample-5"


def test_provider_failure_is_not_success_and_credentials_are_not_serialized(tmp_path):
    native = native_fixture()
    original = native.sampler.LLM

    def draw(prompt):
        raise RuntimeError("provider error key=DO_NOT_RECORD")

    factory = {"draw_sample": draw,
               "sandbox_factory": lambda: SimpleNamespace(run=lambda *args: (1, True)),
               "inputs": [1]}
    with pytest.raises(RuntimeError, match="DO_NOT_RECORD"):
        driver.run_native(native, "specification", factory, SimpleNamespace(samples_per_prompt=2), tmp_path, 5, 100000)
    assert native.sampler.LLM is original
    raw = (tmp_path / "native-result.json").read_text()
    result = json.loads(raw)
    assert result["native_status"] == "error" and result["error_type"] == "RuntimeError"
    assert result["sample_calls"] == 1 and result["completed_samples"] == 0
    assert "DO_NOT_RECORD" not in raw


def test_trace_limit_stops_without_calling_provider_or_hiding_partial_result(tmp_path):
    native = native_fixture()
    calls = []
    factory = {"draw_sample": lambda prompt: calls.append(prompt),
               "sandbox_factory": lambda: SimpleNamespace(run=lambda *args: (1, True)),
               "inputs": [1]}
    assert driver.run_native(native, "specification", factory, SimpleNamespace(samples_per_prompt=2), tmp_path, 5, 1) == 2
    result = json.loads((tmp_path / "native-result.json").read_text())
    assert result["native_status"] == "trace_limit_reached"
    assert result["sample_calls"] == 0 and not calls
    assert (tmp_path / "native-trace.jsonl").stat().st_size <= 1
    assert result["island_leaders"][0]["native_score"] == {"nonfinite": "-inf"}


@pytest.mark.parametrize("inputs", [[1, 1], [], [{"unhashable": 1}]])
def test_invalid_inputs_are_rejected_before_native_loop(tmp_path, inputs):
    native = native_fixture()
    factory = {"draw_sample": lambda prompt: "body", "sandbox_factory": lambda: None, "inputs": inputs}
    with pytest.raises((TypeError, ValueError)):
        driver.run_native(native, "spec", factory, SimpleNamespace(samples_per_prompt=1), tmp_path, 1, 100)
    assert not native.main_calls and not list(tmp_path.iterdir())


def test_invalid_budget_does_not_load_factory_or_source(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(driver, "load_factory", lambda reference: pytest.fail("Factory must not load"))
    with pytest.raises(SystemExit):
        driver.main(["--factory", "provider.py:build", "--specification", "task.py", "--max-samples", "0", "--output", str(tmp_path / "result")])
    assert not (tmp_path / "result").exists()
