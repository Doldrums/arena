"""Real catalog/metadata contract for the separately reviewed science5 image."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from arena.frameworks import evaluation, sciel_catalog_evaluate as bridge
from arena.frameworks import sciel_catalog_science5 as science5
from arena.frameworks.sciel_catalog_profile import (
    SCIENCE_TASK_REQUIREMENTS, supports_science_task, validate_task_profile,
)
from arena.registry import get_catalog
from arena.task_library import load_task_manifest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_IMAGE = "registry.example.invalid/science5@sha256:" + "a" * 64
FIXTURE_ID = "sha256:" + "b" * 64


def actual_tasks():
    return [task for task in get_catalog()["tasks"] if task["id"] in science5.TASKS]


def test_real_catalog_and_raw_metadata_match_exact_five_different_orderings():
    tasks = actual_tasks()
    assert len(tasks) == 5
    assert not set(science5.TASKS) & set(SCIENCE_TASK_REQUIREMENTS)
    assert len(get_catalog()["tasks"]) == 959
    source = next(s for s in get_catalog()["sources"] if s["id"] == "arena-tasks")
    files = load_task_manifest(source)["files"]
    for task in tasks:
        directory = ROOT / "tasks/suite" / task["id"]
        metadata = json.loads((directory / "task.json").read_bytes())
        problem = json.loads((directory / "problem.json").read_bytes())
        raw = metadata["execution"]["suite"]["requires"]
        assert raw != task["requirements"]  # the original LMX integration pitfall
        assert sorted(raw) == task["requirements"]
        assert science5.supports_science5_task(task["id"], raw)
        assert science5.supports_science5_task(task["id"], task["requirements"])
        science5.validate_science5_metadata(task, metadata, problem, ROOT / "tasks", files)
        assert not supports_science_task(task["id"], task["requirements"])
        with pytest.raises(ValueError, match="approved CPU"):
            validate_task_profile(task, {})


@pytest.mark.parametrize("name", sorted([
    "science-cosmology-pantheon-plus-expansion-fit", "science-biology-proteingym-fitness",
    "science-biology-eterna-rna-design", "science-earth-oceanbench-satellite-ssh",
    "science-materials-geom-conformer-search",
]))
def test_actual_catalog_prepares_pinned_native_contract_without_execution(name, tmp_path, monkeypatch):
    # No real image is admitted by this fixture. It tests the shared bridge's
    # real catalog/metadata/seed/prompt path without executing an image.
    monkeypatch.setattr(science5, "IMAGE", FIXTURE_IMAGE)
    monkeypatch.setattr(science5, "IMAGE_ID", FIXTURE_ID)
    monkeypatch.setattr(evaluation, "evaluate", lambda *a, **k: pytest.fail("No seed evaluation"))
    task = next(t for t in actual_tasks() if t["id"] == name)
    config = {"schema": bridge.SCHEMA, "evaluation": {
        "schema": "arena.evaluation-config/1", "task_id": name,
        "tasks_dir": str(ROOT / "tasks"), "receipts_dir": str(tmp_path / "receipts"),
        "profile": science5.PROFILE, "timeout_seconds": science5.TASKS[name]["timeout"],
        "execution": {"kind": "docker", "image": FIXTURE_IMAGE, "python": "python",
            "require_control_cgroup": True, "resource_profile": science5.RESOURCE_PROFILE}},
        "fitness": {"kind": "atan", "scale": 1, "basis": "Fixture-only preparation regression"},
        "confirmation": {"stochastic": True, "samples": 3}}
    checked = bridge.validate_config(config)
    target = tmp_path / "native"
    result = bridge.create_task(config, target)
    native = json.loads((target / "task.yaml").read_bytes())
    assert native["resources"] == "cpu" and native["confirm_n"] == 3
    assert len(native["task_prompt"]) <= 1600
    assert native["full_timeout"] == science5.TASKS[name]["timeout"] + 120
    assert (target / "initial_program.py").read_bytes() == checked["seed"]
    assert result["readiness_requirements"] == task["requirements"]
    assert result["runtime_conformance"] == "not_verified"
    assert checked["bridge_config"]["binding"]["prepared_environment"]["data_lock_sha256"] == science5.DATA_LOCK_SHA256
    assert not (tmp_path / "receipts").exists()


def test_unbuilt_image_is_fail_closed_even_for_correct_task(monkeypatch):
    monkeypatch.setattr(science5, "IMAGE", None)
    monkeypatch.setattr(science5, "IMAGE_ID", None)
    for image in (None, "science5:latest", FIXTURE_IMAGE, FIXTURE_ID):
        with pytest.raises(ValueError, match="pending"):
            science5.science5_environment(image)


def test_reviewed_image_binds_data_and_dependency_proof_without_seed_claim():
    for image in (science5.IMAGE, science5.IMAGE_ID):
        environment = science5.science5_environment(image)
        assert environment["build_receipt_sha256"] == science5.BUILD_RECEIPT_SHA256
        assert environment["dependency_lock_sha256"] == science5.DEPENDENCY_LOCK_SHA256
        assert environment["data_lock_sha256"] == science5.DATA_LOCK_SHA256
        assert "seed_verified" not in environment
    for image in ("science5:latest", FIXTURE_IMAGE, FIXTURE_ID):
        with pytest.raises(ValueError, match="exact reviewed"):
            science5.science5_environment(image)


@pytest.mark.parametrize("change", ["task", "duplicate", "extra", "file", "type"])
def test_no_general_package_or_file_admission(change):
    task = deepcopy(actual_tasks()[0])
    if change == "task": task["id"] = "unreviewed-task"
    elif change == "duplicate": task["requirements"].append(task["requirements"][0])
    elif change == "extra": task["requirements"].append("py:torch")
    elif change == "file": task["requirements"][0] = "file:/host/private"
    else: task["requirements"] = tuple(task["requirements"])
    assert not science5.supports_science5_task(task["id"], task["requirements"])


@pytest.mark.parametrize("change", ["protocol", "metric", "direction", "family", "problem",
                                  "timeout", "bool_timeout", "resource", "cgroup", "python", "image"])
def test_scientific_and_resource_contract_cannot_drift(change, monkeypatch):
    monkeypatch.setattr(science5, "IMAGE", FIXTURE_IMAGE)
    monkeypatch.setattr(science5, "IMAGE_ID", FIXTURE_ID)
    task = deepcopy(actual_tasks()[0])
    config = {"timeout_seconds": science5.TASKS[task["id"]]["timeout"], "execution": {
        "kind": "docker", "image": FIXTURE_IMAGE, "python": "python",
        "require_control_cgroup": True, "resource_profile": science5.RESOURCE_PROFILE}}
    assert science5.validate_science5_task(task, config)["profile"] == science5.PROFILE
    if change in ("protocol", "metric", "direction", "family"): task[change] = "different"
    elif change == "problem": task["contract_source"]["sha256"] = "0" * 64
    elif change == "timeout": config["timeout_seconds"] -= 1
    elif change == "bool_timeout": config["timeout_seconds"] = True
    elif change == "resource": config["execution"]["resource_profile"] = "cpu-8g-p256-v1"
    elif change == "cgroup": config["execution"]["require_control_cgroup"] = 1
    elif change == "python": config["execution"]["python"] = "another-python"
    else: config["execution"]["image"] = "science5:latest"
    with pytest.raises(ValueError):
        science5.validate_science5_task(task, config)


@pytest.mark.parametrize("filename", ["task.json", "problem.json", "initial_program.py", "evaluator.py"])
def test_changed_task_bytes_cannot_inherit_existing_scientific_profile(filename):
    task = actual_tasks()[0]
    directory = ROOT / "tasks/suite" / task["id"]
    metadata = json.loads((directory / "task.json").read_bytes())
    problem = json.loads((directory / "problem.json").read_bytes())
    source = next(s for s in get_catalog()["sources"] if s["id"] == "arena-tasks")
    files = dict(load_task_manifest(source)["files"])
    files[f"suite/{task['id']}/{filename}"] = "0" * 64
    with pytest.raises(ValueError, match="bytes changed"):
        science5.validate_science5_metadata(task, metadata, problem, ROOT / "tasks", files)


@pytest.mark.parametrize("changed", ["metadata", "problem"])
def test_supplied_metadata_must_match_actual_frozen_file(changed):
    task = actual_tasks()[0]
    directory = ROOT / "tasks/suite" / task["id"]
    metadata = json.loads((directory / "task.json").read_bytes())
    problem = json.loads((directory / "problem.json").read_bytes())
    source = next(s for s in get_catalog()["sources"] if s["id"] == "arena-tasks")
    files = load_task_manifest(source)["files"]
    if changed == "metadata": metadata["execution"]["suite"]["requires"].reverse()
    else: problem["parameters"]["new_smaller_cut"] = 1
    with pytest.raises(ValueError, match="differs from pinned bytes"):
        science5.validate_science5_metadata(task, metadata, problem, ROOT / "tasks", files)
