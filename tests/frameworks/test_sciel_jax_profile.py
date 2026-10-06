"""Exact JAX cohorts remain inert until resource-bound seed checks are requested."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import socket
import subprocess

import pytest

from arena.frameworks import evaluation, sciel_catalog_jax as jax
from arena.frameworks.sciel_catalog_profile import supports_requirements, validate_task_profile
from arena.registry import get_catalog

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "jax_preflight", ROOT / "scripts/deployment/sciel_catalog_preflight.py")
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


@pytest.fixture(autouse=True)
def no_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("JAX preparation must not execute a process, candidate, or network call")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(evaluation, "evaluate", forbidden)


def test_exact_eight_tasks_require_both_prepared_image_and_explicit_resource_profile():
    tasks = [t for t in get_catalog()["tasks"] if t["id"] in jax.JAX_TASK_REQUIREMENTS]
    assert len(tasks) == 8
    groups = []
    for task in tasks:
        group = jax.jax_task_group(task["id"], task["requirements"])
        groups.append(group)
        environment = jax.jax_environment(jax.JAX_IMAGES[group], group)
        config = {"profile": jax.JAX_PROFILE, "execution": {
            "image": jax.JAX_IMAGES[group], "resource_profile": environment["resource_profile"]}}
        assert validate_task_profile(task, config) == environment
        assert environment["data_assets"] == []
        assert environment["data_lock_sha256"] == hashlib.sha256(b"[]").hexdigest()
        assert not supports_requirements(task["requirements"])
        with pytest.raises(ValueError, match="approved CPU"):
            validate_task_profile(task, {})
    assert groups.count("jax-affinity") == 7 and groups.count("jax-original-4g") == 1


@pytest.mark.parametrize("mutation", ["id", "extra", "file", "reorder", "duplicate", "type", "image", "resource", "absent"])
def test_nearby_task_requirements_or_resources_cannot_inherit_jax_access(mutation):
    name, requirements = next(iter(jax.JAX_TASK_REQUIREMENTS.items()))
    task = {"id": name, "requirements": list(requirements)}
    config = {"profile": jax.JAX_PROFILE, "execution": {
        "image": jax.JAX_AFFINITY_IMAGE, "resource_profile": "cpu-2g-p128-v1"}}
    if mutation == "id":
        task["id"] = "another-jax-task"
    elif mutation == "extra":
        task["requirements"].append("py:torch")
    elif mutation == "file":
        task["requirements"][0] = "file:/private/dataset"
    elif mutation == "reorder":
        task["requirements"].reverse()
    elif mutation == "duplicate":
        task["requirements"].append("py:jax")
    elif mutation == "type":
        task["requirements"] = requirements
    elif mutation == "image":
        config["execution"]["image"] = jax.JAX_ORIGINAL_IMAGE
    elif mutation == "resource":
        config["execution"]["resource_profile"] = "cpu-4g-p128-v1"
    else:
        del config["execution"]["resource_profile"]
    with pytest.raises(ValueError, match="cohort|resource profile"):
        validate_task_profile(task, config)


@pytest.mark.parametrize("filename", ["sciel-jax-cpu.json", "jax-requirements.lock", "jax-installed-packages.lock"])
def test_environment_or_dependency_lock_byte_changes_are_rejected(tmp_path, monkeypatch, filename):
    shutil.copytree(ROOT / "registry/evaluation-environments", tmp_path / "evaluation-environments")
    monkeypatch.setattr(jax, "resolve_registry_root", lambda: tmp_path)
    assert jax.jax_environment(jax.JAX_AFFINITY_IMAGE)
    path = tmp_path / "evaluation-environments" / filename
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="digest"):
        jax.jax_environment(jax.JAX_AFFINITY_IMAGE)


def test_identity_pins_the_fixed_no_entrypoint_base_and_preserves_original_precision():
    record = json.loads((ROOT / "registry/evaluation-environments/sciel-jax-cpu.json").read_text())
    assert record["base"]["image_reference"].endswith(
        "@sha256:5483308aca52e347ea81e4739d9789e76765d63a91ce2b62f41cb314af4446cc")
    assert record["base"]["entrypoint"] is None
    assert all(v["entrypoint"] is None and not v["precision_override"] for v in record["variants"].values())
    assert record["variants"]["jax-affinity"]["sitecustomize_sha256"]
    assert record["variants"]["jax-original-4g"]["sitecustomize_sha256"] is None


@pytest.mark.parametrize("group,count", [("jax-affinity", 7), ("jax-original-4g", 1)])
def test_inventory_preserves_all_tasks_and_records_exact_resources_without_execution(tmp_path, group, count):
    tasks = get_catalog()["tasks"]
    default = preflight.inventory(tasks, ROOT / "tasks")
    assert sum(r["status"] == "seed_check_pending" for r in default) == 552
    assert all(r["status"] == "environment_preparation_pending" for r in default
               if r["task_id"] in jax.JAX_TASK_REQUIREMENTS)
    output = tmp_path.resolve() / group
    assert preflight.main(["--tasks-root", str(ROOT / "tasks"), "--output", str(output),
                           "--image", jax.JAX_IMAGES[group], "--group", group]) == 0
    manifest = json.loads((output / "manifest.json").read_text())
    assert len(manifest["tasks"]) == 1163 and manifest["model_calls"] == 0
    assert manifest["counts"]["seed_check_pending"] == count
    assert manifest["profile"] == jax.JAX_PROFILE
    assert manifest["prepared_environment"] == jax.jax_environment(jax.JAX_IMAGES[group], group)
    assert manifest["resource_profile"] == manifest["prepared_environment"]["resource_profile"]
    assert {r["task_id"] for r in manifest["tasks"] if r["status"] == "seed_check_pending"} == {
        task["id"] for task in tasks if jax.jax_task_group(task["id"], task["requirements"]) == group}
    assert not list(output.glob("*/receipt.json"))
    with pytest.raises(ValueError, match="exact reviewed image"):
        preflight.inventory(tasks, ROOT / "tasks", group, "sha256:" + "0" * 64)


@pytest.mark.parametrize("group", jax.JAX_GROUPS)
def test_seed_dispatch_binds_exact_resource_profile_and_rejects_foreign_task(tmp_path, monkeypatch, group):
    calls = []
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text("{}")
    receipt = {key: None for key in ("raw_score", "candidate_sha256", "evaluator_sha256",
               "problem_sha256", "task_source", "wall_seconds")}
    receipt.update(status="completed", validity=True, fitness=0, receipt_path=str(receipt_path))
    monkeypatch.setattr(evaluation, "evaluate", lambda config, *_: calls.append(deepcopy(config)) or receipt)
    name = next(name for name, reqs in jax.JAX_TASK_REQUIREMENTS.items()
                if jax.jax_task_group(name, list(reqs)) == group)
    row = {"task_id": name, "requirements": list(jax.JAX_TASK_REQUIREMENTS[name])}
    args = {"root": ROOT / "tasks", "output": tmp_path, "image": jax.JAX_IMAGES[group],
            "timeout": 180, "group": group}
    assert preflight.check_seed(row, **args)["status"] == "seed_verified"
    assert calls[0]["profile"] == jax.JAX_PROFILE
    assert calls[0]["execution"]["resource_profile"] == jax.jax_environment(args["image"])["resource_profile"]
    with pytest.raises(ValueError, match="exact prepared JAX cohort"):
        preflight.check_seed({**row, "task_id": "foreign"}, **args)
    assert len(calls) == 1
