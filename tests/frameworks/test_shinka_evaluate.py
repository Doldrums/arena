"""Canonical bridge fixtures execute no framework or candidate code."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace

import pytest

from arena.frameworks import shinka_evaluate as bridge


@pytest.fixture
def canonical(tmp_path, monkeypatch):
    tasks = tmp_path / "tasks"
    seed = tasks / "suite" / "fixture-task" / "initial_program.py"
    seed.parent.mkdir(parents=True)
    seed.write_text("# EVOLVE-BLOCK-START\nraise AssertionError('Never execute this seed')\n# EVOLVE-BLOCK-END\n")
    config = {"schema": "arena.evaluation-config/1", "tasks_dir": str(tasks),
              "task_id": "fixture-task", "timeout_seconds": 10,
              "execution": {"kind": "local_trusted", "python": "/reviewed/python"}}
    calls = []
    outcome = {"schema": "arena.evaluation/1", "evaluation_id": "fixture-evaluation",
               "task_id": "fixture-task", "raw_score": 0.0, "fitness": 0.0,
               "direction": "maximize", "validity": True, "status": "completed"}

    def validate(value):
        if type(value) is not dict or value.get("schema") != "arena.evaluation-config/1":
            raise ValueError("Invalid fixture config")
        return {"config": value, "source_dir": str(tasks), "task": {"direction": outcome["direction"]}}

    def prepare(value, program, output):
        calls.append(("prepare", program, output))
        return {**validate(value), "candidate_sha256": hashlib.sha256(program.read_bytes()).hexdigest()}

    def evaluate(value, program, output):
        calls.append(("evaluate", program, output))
        output.mkdir(parents=True)
        receipt = {**deepcopy(outcome), "receipt_path": str(output / "receipt.json")}
        (output / "receipt.json").write_text(json.dumps(receipt))
        return receipt

    api = SimpleNamespace(validate_config=validate, prepare_evaluation=prepare, evaluate=evaluate)
    monkeypatch.setattr(bridge, "_canonical_api", lambda: api)
    return SimpleNamespace(config=config, seed=seed, api=api, calls=calls, outcome=outcome)


def test_create_task_copies_verified_seed_and_does_not_evaluate(canonical, tmp_path):
    destination = tmp_path / "new task"
    original = deepcopy(canonical.config)
    result = bridge.create_task(canonical.config, destination)
    assert (destination / "initial.py").read_bytes() == canonical.seed.read_bytes()
    assert json.loads((destination / "evaluation.json").read_text()) == original
    wrapper = (destination / "evaluate.py").read_text()
    compile(wrapper, "evaluate.py", "exec")
    assert 'from arena.frameworks.shinka_evaluate import main' in wrapper
    assert 'ARENA_EVALUATION_CONFIG_SHA256' in wrapper
    assert 'with_name("evaluation.json")' not in wrapper
    assert canonical.config == original
    assert [call[0] for call in canonical.calls] == ["prepare"]
    assert result["evaluation_performed"] is False
    assert result["canonical_evaluation_configured"] is True
    assert result["seed_sha256"] == hashlib.sha256(canonical.seed.read_bytes()).hexdigest()
    assert sorted(p.name for p in destination.iterdir()) == ["evaluate.py", "evaluation.json", "initial.py"]
    with pytest.raises(ValueError, match="already exists"):
        bridge.create_task(canonical.config, destination)


def test_native_evaluate_str_relocation_keeps_verified_configuration(canonical, tmp_path, monkeypatch):
    task = tmp_path / "task"
    generated = bridge.create_task(canonical.config, task)
    # Pinned CLI reads evaluate.py as evaluate_str; AsyncRunner writes only that
    # string under results_dir. Deliberately provide no sidecar in that directory.
    evaluate_str = (task / "evaluate.py").read_text()
    relocated = tmp_path / "native-run" / "evaluate.py"
    relocated.parent.mkdir()
    relocated.write_text(evaluate_str)
    (task / "evaluation.json").unlink()
    results = relocated.parent / "gen_0"
    monkeypatch.setattr(sys, "argv", [str(relocated), "--program_path", str(canonical.seed),
                                    "--results_dir", str(results)])
    with pytest.raises(SystemExit) as status:
        runpy.run_path(str(relocated), run_name="__main__")
    assert status.value.code == 0
    assert json.loads((results / "correct.json").read_text())["correct"] is True
    assert [call[0] for call in canonical.calls] == ["prepare", "evaluate"]
    assert len(list(results.glob("arena-evaluation/*/receipt.json"))) == 1
    namespace = runpy.run_path(str(relocated))
    payload = namespace["ARENA_EVALUATION_CONFIG_JSON"]
    assert json.loads(payload) == canonical.config
    assert hashlib.sha256(payload.encode()).hexdigest() == generated["evaluation_config_sha256"]


@pytest.mark.parametrize("failure", ["digest", "override"])
def test_generated_configuration_cannot_drift_or_be_overridden(canonical, tmp_path, failure):
    payload = json.dumps(canonical.config)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    arguments = ["--program_path", str(canonical.seed), "--results_dir", str(tmp_path / "results")]
    if failure == "digest":
        payload = payload.replace("fixture-task", "another-task")
    else:
        config = tmp_path / "override.json"
        config.write_text(json.dumps(canonical.config))
        arguments += ["--config", str(config)]
    assert bridge.main(arguments, config_json=payload, config_sha256=digest) == 0
    assert canonical.calls == []
    assert json.loads((tmp_path / "results/correct.json").read_text())["correct"] is False


def test_create_task_refuses_changed_seed_before_writing(canonical, tmp_path):
    canonical.api.prepare_evaluation = lambda *args: {"candidate_sha256": "0" * 64}
    destination = tmp_path / "new-task"
    with pytest.raises(ValueError, match="seed changed"):
        bridge.create_task(canonical.config, destination)
    assert not destination.exists()


def test_create_task_keeps_generated_inputs_outside_sources_and_receipts(canonical, tmp_path):
    with pytest.raises(ValueError, match="task-source tree"):
        bridge.create_task(canonical.config, canonical.seed.parent / "generated")
    destination = tmp_path / "task"
    canonical.config["receipts_dir"] = str(destination / "receipts")
    with pytest.raises(ValueError, match="task input tree"):
        bridge.create_task(canonical.config, destination)
    destination.symlink_to(tmp_path / "absent", target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        bridge.create_task(canonical.config, destination)


@pytest.mark.parametrize(("direction", "raw", "fitness"), [("maximize", 0.0, 0.0), ("maximize", -2.0, -2.0), ("minimize", 8.5, -8.5)])
def test_valid_receipt_preserves_score_and_direction_once(canonical, tmp_path, direction, raw, fitness):
    canonical.outcome.update(direction=direction, raw_score=raw, fitness=fitness)
    results = tmp_path / "results"
    value = bridge.evaluate_candidate(canonical.config, canonical.seed, results)
    assert value["correct"] is True
    metrics = json.loads((results / "metrics.json").read_text())
    assert metrics["combined_score"] == fitness
    assert metrics["public"]["arena_raw_score"] == raw
    evidence = metrics["private"]["arena_evaluation"]
    receipt_file = Path(evidence["receipt_path"])
    assert evidence["direction"] == direction and evidence["validity"] is True
    assert evidence["receipt_sha256"] == hashlib.sha256(receipt_file.read_bytes()).hexdigest()
    assert json.loads((results / "correct.json").read_text()) == {"correct": True, "error": None}
    assert [call[0] for call in canonical.calls] == ["evaluate"]


@pytest.mark.parametrize("update", [
    {"validity": None}, {"validity": False}, {"validity": 1}, {"status": "timeout"},
    {"status": "error"}, {"status": "invalid"}, {"status": "interrupted"},
    {"fitness": None}, {"fitness": float("inf")}, {"fitness": float("nan")},
    {"fitness": True}, {"raw_score": None}, {"raw_score": 8.5, "fitness": -8.5},
    {"raw_score": 10 ** 400, "fitness": 10 ** 400},
])
def test_unknown_invalid_nonfinite_or_mismapped_results_have_no_native_score(canonical, tmp_path, update):
    canonical.outcome.update(update)
    result = bridge.evaluate_candidate(canonical.config, canonical.seed, tmp_path / "results")
    assert result["correct"] is False
    assert result["metrics"]["combined_score"] is None
    assert json.loads((tmp_path / "results" / "correct.json").read_text())["correct"] is False
    json.dumps(result["metrics"], allow_nan=False)


@pytest.mark.parametrize("problem", ["task", "schema", "artifact", "outside", "symlink"])
def test_receipt_must_match_task_and_its_saved_artifact(canonical, tmp_path, problem):
    original = canonical.api.evaluate

    def bad_receipt(config, candidate, output):
        receipt = original(config, candidate, output)
        if problem == "task":
            receipt["task_id"] = "another-task"
        elif problem == "schema":
            receipt["schema"] = "unknown"
        elif problem == "artifact":
            (output / "receipt.json").write_text("{}")
        elif problem == "outside":
            receipt["receipt_path"] = str(tmp_path / "outside.json")
        else:
            path = output / "receipt.json"
            data = path.read_bytes()
            path.unlink()
            external = tmp_path / "outside.json"
            external.write_bytes(data)
            path.symlink_to(external)
        return receipt

    canonical.api.evaluate = bad_receipt
    result = bridge.evaluate_candidate(canonical.config, canonical.seed, tmp_path / "results")
    assert result["correct"] is False and result["metrics"]["combined_score"] is None
    assert result["metrics"]["private"]["arena_evaluation"] == {}


def test_exception_and_interruption_cannot_reuse_a_previous_score(canonical, tmp_path):
    results = tmp_path / "results"
    bridge.evaluate_candidate(canonical.config, canonical.seed, results)

    def fail(*args):
        raise RuntimeError("secret credential must not be published")

    canonical.api.evaluate = fail
    result = bridge.evaluate_candidate(canonical.config, canonical.seed, results)
    assert result["correct"] is False and result["metrics"]["combined_score"] is None
    assert "secret credential" not in json.dumps(result)

    def interrupt(*args):
        raise KeyboardInterrupt

    canonical.api.evaluate = interrupt
    with pytest.raises(KeyboardInterrupt):
        bridge.evaluate_candidate(canonical.config, canonical.seed, results)
    assert json.loads((results / "correct.json").read_text())["correct"] is False
    assert json.loads((results / "metrics.json").read_text())["combined_score"] is None


def test_each_call_gets_a_unique_external_receipt_directory(canonical, tmp_path):
    receipts = tmp_path / "receipts"
    canonical.config["receipts_dir"] = str(receipts)
    for _ in range(2):
        assert bridge.evaluate_candidate(canonical.config, canonical.seed, tmp_path / "results")["correct"]
    outputs = [call[2] for call in canonical.calls]
    assert len(set(outputs)) == 2 and all(path.parent == receipts for path in outputs)


def test_controlled_shinka_bridge_uses_queue_receipt_root(canonical, tmp_path):
    canonical.config["execution"] = {"kind": "docker", "image": "sha256:" + "a" * 64,
                                     "python": "python", "require_control_cgroup": True}
    canonical.config["receipts_dir"] = str(tmp_path / "static-task-receipts")
    admitted = tmp_path / "admitted/artifacts/canonical-evaluations"
    canonical.api.receipt_root = lambda config, fallback: admitted
    result = bridge.evaluate_candidate(canonical.config, canonical.seed, tmp_path / "results")
    assert result["correct"] is True
    assert len(canonical.calls) == 1 and canonical.calls[0][2].parent == admitted
    assert not Path(canonical.config["receipts_dir"]).exists()


def test_cli_publishes_rejection_for_unreadable_config(canonical, tmp_path):
    results = tmp_path / "results"
    status = bridge.main(["--program_path", str(canonical.seed), "--results_dir", str(results)],
                         config_path=tmp_path / "absent.json")
    assert status == 0
    assert canonical.calls == []
    assert json.loads((results / "correct.json").read_text())["correct"] is False
    assert json.loads((results / "metrics.json").read_text())["combined_score"] is None
