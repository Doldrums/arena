"""Prepared science admission never grants general data-path/package access."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

from arena.frameworks.sciel_catalog_profile import (
    CPU_PROFILE, SCIENCE_DATA_LOCK_SHA256, SCIENCE_IMAGE_ID, SCIENCE_IMAGE_REFERENCE,
    SCIENCE_PROFILE, SCIENCE_TASK_REQUIREMENTS, science_environment,
    supports_requirements, supports_science_task, validate_task_profile,
)
from arena.registry import get_catalog

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "science_preflight", ROOT / "scripts/deployment/sciel_catalog_preflight.py")
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


@pytest.mark.parametrize("image", [SCIENCE_IMAGE_ID, SCIENCE_IMAGE_REFERENCE])
def test_exact_catalog_cohort_and_both_immutable_image_identities(image):
    tasks = [t for t in get_catalog()["tasks"] if t["id"] in SCIENCE_TASK_REQUIREMENTS]
    assert len(tasks) == 8
    for task in tasks:
        assert supports_science_task(task["id"], task["requirements"])
        assert not supports_requirements(task["requirements"])
        assert validate_task_profile(task, {"profile": SCIENCE_PROFILE, "execution": {"image": image}}) == {
            "profile": SCIENCE_PROFILE, "image_id": SCIENCE_IMAGE_ID,
            "image_reference": SCIENCE_IMAGE_REFERENCE, "data_lock_sha256": SCIENCE_DATA_LOCK_SHA256}
        with pytest.raises(ValueError, match="approved CPU"):
            validate_task_profile(task, {"profile": CPU_PROFILE})


@pytest.mark.parametrize("mutation", ["id", "file", "package", "duplicate", "reorder", "type"])
def test_task_or_requirement_changes_do_not_inherit_prepared_access(mutation):
    name, requirements = next(iter(SCIENCE_TASK_REQUIREMENTS.items()))
    task = {"id": name, "requirements": list(requirements)}
    if mutation == "id":
        task["id"] = "other-task"
    elif mutation == "file":
        task["requirements"][0] = "file:/private/dataset"
    elif mutation == "package":
        task["requirements"].append("py:torch")
    elif mutation == "duplicate":
        task["requirements"].append(task["requirements"][0])
    elif mutation == "reorder":
        task["requirements"].reverse()
    else:
        task["requirements"] = requirements
    assert not supports_science_task(task["id"], task["requirements"])
    with pytest.raises(ValueError, match="exact prepared science cohort"):
        validate_task_profile(task, {"profile": SCIENCE_PROFILE, "execution": {"image": SCIENCE_IMAGE_ID}})


@pytest.mark.parametrize("image", ["science:latest", "sha256:" + "0" * 64, None])
def test_unreviewed_image_cannot_use_prepared_data_identity(image):
    with pytest.raises(ValueError, match="exact reviewed image"):
        science_environment(image)


def test_science_inventory_is_explicit_and_preserves_default_cpu_selection():
    tasks = get_catalog()["tasks"]
    ordinary = preflight.inventory(tasks, ROOT / "tasks")
    science = preflight.inventory(tasks, ROOT / "tasks", "science", SCIENCE_IMAGE_ID)
    assert len(science) == len(ordinary) == 959
    assert {r["task_id"] for r in science if r["status"] == "seed_check_pending"} == set(SCIENCE_TASK_REQUIREMENTS)
    assert sum(r["status"] == "seed_check_deferred" for r in science) == 350
    assert all(r["status"] == "environment_preparation_pending" for r in ordinary
               if r["task_id"] in SCIENCE_TASK_REQUIREMENTS)
    with pytest.raises(ValueError, match="exact reviewed image"):
        preflight.inventory(tasks, ROOT / "tasks", "science", "sha256:" + "0" * 64)


def test_science_preflight_records_image_and_data_pin_without_evaluating(tmp_path, monkeypatch):
    from arena.frameworks import evaluation
    def forbidden(*args, **kwargs):
        pytest.fail("Inventory must not evaluate seeds")
    monkeypatch.setattr(evaluation, "evaluate", forbidden)
    output = tmp_path.resolve() / "science"
    assert preflight.main(["--tasks-root", str(ROOT / "tasks"), "--output", str(output),
                           "--image", SCIENCE_IMAGE_REFERENCE, "--group", "science"]) == 0
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["group"] == "science" and manifest["profile"] == SCIENCE_PROFILE
    assert manifest["prepared_environment"] == science_environment(SCIENCE_IMAGE_REFERENCE)
    assert manifest["counts"]["seed_check_pending"] == 8 and manifest["model_calls"] == 0


def test_science_seed_measurement_sets_profile_but_rejects_other_task_before_execution(tmp_path, monkeypatch):
    from arena.frameworks import evaluation
    calls = []
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text("{}")
    receipt = {name: None for name in ("raw_score", "fitness", "candidate_sha256", "evaluator_sha256",
               "problem_sha256", "task_source", "wall_seconds")}
    receipt.update(status="completed", validity=True, fitness=0, receipt_path=str(receipt_path))
    monkeypatch.setattr(evaluation, "evaluate", lambda config, *_: calls.append(config) or receipt)
    name = "science-materials-cantera-mechanism-reduction"
    row = {"task_id": name, "requirements": list(SCIENCE_TASK_REQUIREMENTS[name])}
    kwargs = {"root": ROOT / "tasks", "output": tmp_path, "image": SCIENCE_IMAGE_ID,
              "timeout": 30, "group": "science"}
    assert preflight.check_seed(row, **kwargs)["status"] == "seed_verified"
    assert calls[0]["profile"] == SCIENCE_PROFILE
    with pytest.raises(ValueError, match="exact prepared science cohort"):
        preflight.check_seed({**row, "task_id": "other"}, **kwargs)
    assert len(calls) == 1
