"""Catalog-to-SCiEL contracts; all measurements use inert receipt fixtures."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import pytest

from arena import task_library
from arena.frameworks import evaluation, sciel_evaluate
from arena.frameworks import sciel_catalog_evaluate as bridge


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def setup(tmp_path, monkeypatch):
    root = tmp_path / "tasks"
    directory = root / "suite/fixture"
    directory.mkdir(parents=True)
    (directory / "evaluator.py").write_text("raise AssertionError('Never import task evaluator on host')\n")
    (directory / "initial_program.py").write_text("raise AssertionError('Never import seed on host')\n")
    (directory / "task.json").write_text(json.dumps({"execution": {"suite": {
        "initial_program": "initial_program.py", "env": {}, "requires": ["py:numpy", "py:scipy"]}}}))
    problem = directory / "problem.json"
    problem.write_text(json.dumps({"parameters": {"n": 21}, "contract": "construct() -> array"}))
    registry = tmp_path / "registry"
    registry.mkdir()
    manifest = registry / "task-library-manifest.json"
    manifest.write_text(json.dumps({"schema": "arena.task-library/1", "files": {
        p.relative_to(root).as_posix(): digest(p) for p in directory.iterdir()}}))
    source = {"id": "fixture", "kind": "bundled", "root_path": "tasks",
              "manifest_path": "registry/task-library-manifest.json", "manifest_sha256": digest(manifest)}
    task = {"id": "fixture", "name": "Fixture packing", "source_id": "fixture", "executable": True,
            "direction": "minimize", "protocol": "original", "metric": "energy", "contract": "construct() -> array",
            "requirements": ["py:numpy", "py:scipy"], "contract_source": {
                "path": "suite/fixture/problem.json", "sha256": digest(problem)}}
    monkeypatch.setattr(task_library, "resolve_registry_root", lambda _: registry)
    monkeypatch.setattr(evaluation, "get_catalog", lambda: {"tasks": [task], "sources": [source]})
    config = {"schema": bridge.SCHEMA, "evaluation": {"schema": "arena.evaluation-config/1",
        "task_id": "fixture", "timeout_seconds": 30, "receipts_dir": str(tmp_path / "receipts"),
        "execution": {"kind": "docker", "image": "sha256:" + "a" * 64, "python": "python"}},
        "fitness": {"kind": "atan", "scale": 1, "basis": "Explicit campaign scale"},
        "confirmation": {"stochastic": True, "samples": 3}}
    candidate = tmp_path / "candidate.py"
    marker = tmp_path / "candidate-executed"
    candidate.write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\n")
    calls, updates = [], {}

    def evaluate(actual, program, output):
        verified = evaluation.validate_config(actual)
        calls.append((deepcopy(actual), program, output))
        raw = float(len(calls) + 1)
        receipt = {"schema": "arena.evaluation/1", "evaluation_id": f"evaluation-{len(calls)}",
            "task_id": task["id"], "direction": task["direction"], "metric": task["metric"],
            "protocol": task["protocol"], "candidate_sha256": digest(program),
            "problem_sha256": verified["problem_sha256"], "evaluator_sha256": verified["evaluator_sha256"],
            "task_source": verified["source"], "execution": actual["execution"],
            "receipt_path": str(output / "receipt.json"), "status": "completed", "validity": True,
            "raw_score": raw, "fitness": raw if task["direction"] == "maximize" else -raw}
        receipt.update(updates)
        output.mkdir(parents=True)
        (output / "receipt.json").write_text(json.dumps(receipt))
        return receipt

    monkeypatch.setattr(evaluation, "evaluate", evaluate)
    return config, candidate, marker, calls, updates, root, task


def test_create_task_pins_config_and_public_interface_without_running_code(setup, tmp_path):
    config, candidate, marker, calls, _, root, _ = setup
    target = tmp_path / "native/arena/fixture"
    created = sciel_evaluate.create_task(config, target)
    assert created["profile"] == bridge.PROFILE and created["runtime_conformance"] == "not_verified"
    assert created["readiness_requirements"] == ["py:numpy", "py:scipy"]
    assert created["native_config"]["confirm_records"] is True
    native = json.loads((target / "task.yaml").read_text())
    assert native["primary_metric"] == "arena_search_score" and native["confirm_n"] == 3
    assert native["stochastic"] is True and "research_metric" not in native
    assert '"n":21' in native["task_prompt"] and "minimize" in native["task_prompt"]
    assert len(native["task_prompt"]) <= 1600
    embedded = json.loads((target / "evaluation.json").read_text())
    assert "tasks_dir" not in embedded["evaluation"]
    assert embedded["binding"]["task_source"]["manifest_sha256"]
    assert (target / "initial_program.py").read_bytes() == (root / "suite/fixture/initial_program.py").read_bytes()
    assert not marker.exists() and not calls
    # evaluation.json is for inspection; its mutation cannot redirect the hashed wrapper.
    (target / "evaluation.json").write_text("{}")
    spec = importlib.util.spec_from_file_location("arena_generated_fixture", target / "evaluator.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.smoke(candidate)["ok"] and not calls
    assert module.full(candidate)["ok"] and len(calls) == 1 and not marker.exists()


@pytest.mark.parametrize("direction", ["maximize", "minimize"])
@pytest.mark.parametrize("kind", ["identity", "atan"])
def test_full_preserves_raw_metric_and_objective_while_declaring_search_transform(setup, direction, kind):
    config, candidate, marker, calls, _, _, task = setup
    task["direction"] = direction
    if kind == "identity":
        config["fitness"] = {"kind": "identity", "basis": "No scaling"}
    result = bridge.full(config, candidate)
    signed = 2.0 if direction == "maximize" else -2.0
    assert result["cases"] == {"raw_score": 2.0, "canonical_fitness": signed, "validity": 1.0}
    expected = signed if kind == "identity" else 0.5 + math.atan(signed) / math.pi
    assert result["score"] == pytest.approx(expected)
    receipt = Path(result["artifacts"]["arena_receipt"])
    assert result["artifacts"]["arena_receipt_sha256"] == digest(receipt)
    assert json.loads(receipt.read_text())["raw_score"] == 2.0
    assert result["artifacts"]["arena_raw_direction"] == direction
    assert len(calls) == 1 and not marker.exists()


def test_confirm_measures_fresh_trials_and_transforms_mean_not_mean_of_transforms(setup):
    config, candidate, marker, calls, _, _, _ = setup
    result = bridge.confirm(config, candidate, 3)
    assert result["ok"] and result["cases"]["n_trials"] == 3.0
    assert result["cases"]["raw_score"] == 3.0 and result["cases"]["canonical_fitness"] == -3.0
    assert result["score"] == pytest.approx(0.5 + math.atan(-3.0) / math.pi)
    assert len(calls) == len({str(call[2]) for call in calls}) == 3
    artifacts = json.loads(result["artifacts"]["arena_trial_receipts"])
    assert len(artifacts) == 3 and all(Path(item["arena_receipt"]).is_file() for item in artifacts)
    assert not marker.exists()


def test_failed_trial_is_not_summarized_as_confirmed_success(setup):
    config, candidate, _, calls, updates, _, _ = setup
    updates.update(validity=False, status="invalid", fitness=None)
    result = bridge.confirm(config, candidate, 3)
    assert result["ok"] is False and result["score"] == 0.0 and result["cases"] == {}
    assert len(calls) == 1 and "n_trials" not in result["cases"]


@pytest.mark.parametrize("update", [
    {"fitness": {}}, {"fitness": {"kind": "atan", "scale": 0, "basis": "bad"}},
    {"fitness": {"kind": "atan", "scale": float("inf"), "basis": "bad"}},
    {"fitness": {"kind": "identity"}}, {"confirmation": {"stochastic": False, "samples": 3}},
    {"confirmation": {"stochastic": True, "samples": 1}}, {"confirmation": {"stochastic": True, "samples": 11}},
])
def test_invalid_semantics_fail_before_execution(setup, update):
    config, candidate, _, calls, _, _, _ = setup
    with pytest.raises(ValueError):
        bridge.full({**config, **update}, candidate)
    assert not calls


@pytest.mark.parametrize("requirement", ["network", "env:KEY", "file:data", "py:torch", "bin:g++"])
def test_outside_cpu_dependency_profile_fails_before_execution(setup, requirement):
    config, candidate, _, calls, _, _, task = setup
    task["requirements"].append(requirement)
    with pytest.raises(ValueError, match="approved CPU"):
        bridge.full(config, candidate)
    assert not calls


def test_local_execution_missing_transform_and_tampered_bundle_are_rejected(setup):
    config, candidate, _, calls, _, root, _ = setup
    local = deepcopy(config)
    local["evaluation"]["execution"]["kind"] = "local_trusted"
    with pytest.raises(ValueError, match="Docker"):
        bridge.full(local, candidate)
    missing = deepcopy(config)
    del missing["fitness"]
    with pytest.raises(ValueError):
        bridge.full(missing, candidate)
    (root / "suite/fixture/evaluator.py").write_text("modified")
    with pytest.raises(ValueError, match="digest"):
        bridge.full(config, candidate)
    assert not calls


@pytest.mark.parametrize("update", [
    {"raw_score": float("nan")}, {"fitness": 2}, {"direction": "maximize"},
    {"candidate_sha256": "wrong"}, {"evaluator_sha256": "wrong"}, {"task_source": {}},
    {"task_id": "other"}, {"metric": "other"}, {"receipt_path": "/tmp/not-this-call.json"},
])
def test_invalid_or_unbound_receipts_are_rejected(setup, update):
    config, candidate, _, _, updates, _, _ = setup
    updates.update(update)
    with pytest.raises(ValueError):
        bridge.full(config, candidate)


def test_binding_stays_fixed_across_native_package_reuse(setup, tmp_path):
    config, candidate, _, calls, _, _, task = setup
    target = tmp_path / "native"
    bridge.create_task(config, target)
    bound = json.loads((target / "evaluation.json").read_text())
    task["metric"] = "different"
    with pytest.raises(ValueError, match="binding"):
        bridge.full(bound, candidate)
    assert not calls


def test_confirm_rejects_unrequested_repeat_count(setup):
    config, candidate, _, calls, _, _, _ = setup
    with pytest.raises(ValueError, match="count"):
        bridge.confirm(config, candidate, 2)
    assert not calls


@pytest.mark.parametrize("requirements", [
    ["py:sklearn", "py:numpy"], ["py:cvxpy", "py:scipy"], ["py:gymnasium"],
    ["py:sympy", "py:shapely"], ["py:bs4", "py:lxml"],
    ["py:matplotlib", "py:pykalman", "py:pywt", "py:networkx", "py:pandas"],
])
def test_approved_extended_cpu_requirements_pass_bridge_without_importing_packages(setup, requirements):
    config, candidate, marker, calls, _, root, task = setup
    task["requirements"] = requirements
    metadata = root / "suite/fixture/task.json"
    value = json.loads(metadata.read_text())
    value["execution"]["suite"]["requires"] = requirements
    metadata.write_text(json.dumps(value))
    manifest_path = root.parent / "registry/task-library-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["suite/fixture/task.json"] = digest(metadata)
    manifest_path.write_text(json.dumps(manifest))
    evaluation.get_catalog()["sources"][0]["manifest_sha256"] = digest(manifest_path)
    assert bridge.full(config, candidate)["ok"]
    assert len(calls) == 1 and not marker.exists()
