"""Canonical SCiEL bridge wiring without native or candidate execution."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

import pytest

from arena.frameworks import sciel_evaluate as bridge


@pytest.fixture
def example(tmp_path, monkeypatch):
    source = tmp_path / "upstream"
    seed_dir = source / "suite/reference-sat"
    seed_dir.mkdir(parents=True)
    seed = b"def solve(instance):\n    return [False] * instance['n']\n"
    (seed_dir / "initial_program.py").write_bytes(seed)
    monkeypatch.setattr(bridge, "_SEED_SHA256", hashlib.sha256(seed).hexdigest())
    config = {"schema": "arena.evaluation-config/1", "tasks_dir": str(source),
              "task_id": "reference-sat", "timeout_seconds": 30,
              "execution": {"kind": "local_trusted", "python": sys.executable},
              "profile": bridge.PROFILE, "receipts_dir": str(tmp_path / "receipts")}
    module = ModuleType("arena.frameworks.evaluation")
    context = {"source": {"kind": "bundled", "manifest_sha256": "a" * 64}, "source_dir": str(source),
               "config": config, "problem_sha256": bridge._PROBLEM_SHA256, "evaluator_sha256": bridge._EVALUATOR_SHA256}
    module.validate_config = lambda _: context
    calls = []
    updates = {}

    def evaluate(actual_config, program, output):
        calls.append((deepcopy(actual_config), program, output))
        assert not output.exists()
        output.mkdir(parents=True)
        receipt = {"schema": "arena.evaluation/1", "evaluation_id": f"eval-{len(calls)}",
                   "task_id": "reference-sat", "raw_score": 0.7, "fitness": 0.7, "direction": "maximize",
                   "validity": True, "status": "completed", "receipt_path": str(output / "receipt.json")}
        receipt.update(updates)
        (output / "receipt.json").write_text(json.dumps(receipt))
        return receipt
    module.evaluate = evaluate
    monkeypatch.setitem(sys.modules, module.__name__, module)
    program = tmp_path / "candidate.py"
    marker = tmp_path / "candidate-was-executed"
    program.write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\ndef solve(instance): return []\n")
    return config, source, context, program, marker, calls, updates


def test_create_task_emits_native_contract_without_an_evaluation(example, tmp_path):
    config, source, _, program, marker, calls, _ = example
    destination = tmp_path / "tasks/arena/reference-sat"
    result = bridge.create_task(config, destination)
    task = json.loads((destination / "task.yaml").read_text())
    assert task["tiers"] == ["smoke", "full"] and task["stochastic"] is False
    assert task["full_timeout"] > config["timeout_seconds"]
    assert result["native_config"]["confirm_records"] is False
    assert result["runtime_conformance"] == "not_verified"
    assert (destination / "initial_program.py").read_bytes() == (source / "suite/reference-sat/initial_program.py").read_bytes()
    assert json.loads((destination / "evaluation.json").read_text()) == config
    assert not calls and not marker.exists()
    # Import only our newly generated inert wrapper, never the copied seed or
    # upstream evaluator. This verifies its actual smoke/full export wiring.
    spec = importlib.util.spec_from_file_location("test_generated_arena_evaluator", destination / "evaluator.py")
    evaluator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluator)
    assert evaluator.smoke(program)["ok"] is True and not calls
    assert evaluator.full(program)["score"] == 0.7 and len(calls) == 1
    assert not marker.exists()


@pytest.mark.parametrize("changes", [
    {"task_id": "science-chemistry-lennard-jones-38"}, {"task_id": "a2dept-capacitated-facility-location"},
    {"profile": "generic"}, {"receipts_dir": "relative"}, {"extra": True},
])
def test_profile_rejects_unreviewed_tasks_and_options_before_execution(example, changes):
    config, _, _, program, _, calls, _ = example
    with pytest.raises(ValueError):
        bridge.full({**config, **changes}, program)
    assert not calls


def test_task_creation_rejects_unreviewed_version_or_modified_seed(example, tmp_path):
    config, source, context, program, _, calls, _ = example
    context["evaluator_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="reviewed task version"):
        bridge.create_task(config, tmp_path / "task")
    with pytest.raises(ValueError, match="reviewed task version"):
        bridge.full(config, program)
    context["evaluator_sha256"] = bridge._EVALUATOR_SHA256
    (source / "suite/reference-sat/initial_program.py").write_text("changed seed")
    with pytest.raises(ValueError, match="seed digest"):
        bridge.create_task(config, tmp_path / "task")
    assert not (tmp_path / "task").exists() and not calls


def test_receipt_directory_cannot_mutate_source_or_generated_inputs(example, tmp_path):
    config, source, _, _, _, calls, _ = example
    with pytest.raises(ValueError, match="outside the task-source"):
        bridge.create_task({**config, "receipts_dir": str(source / "receipts")}, tmp_path / "task")
    with pytest.raises(ValueError, match="outside the generated task"):
        bridge.create_task({**config, "receipts_dir": str(tmp_path / "task/receipts")}, tmp_path / "task")
    assert not calls


def test_smoke_never_executes_a_syntactically_valid_malicious_program(example):
    _, _, _, program, marker, calls, _ = example
    result = bridge.smoke(program)
    assert result == {"ok": True, "score": 0.0, "cases": {},
                      "artifacts": {"preflight": "syntax_only_no_evaluation"}}
    assert not calls and not marker.exists()
    program.write_text("def invalid(:\n")
    assert bridge.smoke(program)["ok"] is False and not calls


def test_each_full_call_measures_once_and_preserves_raw_fitness_and_receipt(example):
    config, _, _, program, marker, calls, _ = example
    first, second = bridge.full(config, program), bridge.full(config, program)
    assert len(calls) == 2 and calls[0][2] != calls[1][2]
    assert first["score"] == first["cases"]["raw_score"] == 0.7
    assert first["cases"]["validity"] == 1.0
    assert first["artifacts"]["arena_evaluation_id"] != second["artifacts"]["arena_evaluation_id"]
    receipt = Path(first["artifacts"]["arena_receipt"])
    assert first["artifacts"]["arena_receipt_sha256"] == hashlib.sha256(receipt.read_bytes()).hexdigest()
    assert not marker.exists()


def test_controlled_bridge_uses_admitted_receipts_root_instead_of_static_task_config(example, tmp_path, monkeypatch):
    config, _, _, program, marker, calls, _ = example
    config["execution"] = {"kind": "docker", "image": "sha256:" + "a" * 64,
                           "python": "python", "require_control_cgroup": True}
    admitted = tmp_path / "admitted/artifacts/canonical-evaluations"
    resolver_calls = []
    def resolve(actual, fallback):
        resolver_calls.append((actual, fallback))
        return admitted
    monkeypatch.setattr(sys.modules["arena.frameworks.evaluation"], "receipt_root", resolve, raising=False)
    result = bridge.full(config, program)
    assert result["ok"] is True and len(calls) == 1
    assert calls[0][2].parent == admitted
    assert resolver_calls == [(config, Path(config["receipts_dir"]))]
    assert not marker.exists()


@pytest.mark.parametrize("updates", [
    {"raw_score": -0.2, "fitness": -0.2}, {"raw_score": 1.2, "fitness": 1.2},
    {"raw_score": 0.7, "fitness": 0.8}, {"raw_score": float("nan")}, {"raw_score": True},
    {"direction": "minimize"}, {"task_id": "another-task"}, {"evaluation_id": None},
])
def test_receipts_outside_the_profile_are_not_admitted_to_sciel(example, updates):
    config, _, _, program, _, calls, overrides = example
    overrides.update(updates)
    with pytest.raises(ValueError):
        bridge.full(config, program)
    assert len(calls) == 1  # invalid metadata never triggers a silent re-evaluation


@pytest.mark.parametrize("updates", [
    {"validity": None}, {"validity": False, "status": "invalid", "raw_score": None, "fitness": None},
    {"status": "timeout", "validity": None}, {"status": "error", "validity": None},
])
def test_unknown_or_failed_evaluations_preserve_receipt_and_fail_native_admission(example, updates):
    config, _, _, program, _, calls, overrides = example
    overrides.update(updates)
    result = bridge.full(config, program)
    assert result["ok"] is False and result["cases"] == {}
    assert "arena_receipt" in result["artifacts"] and "error" in result["artifacts"]
    assert len(calls) == 1
