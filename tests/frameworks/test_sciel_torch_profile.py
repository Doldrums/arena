"""Prepared Torch admission is exact and inert until canonical seed execution."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import subprocess

import pytest

from arena.frameworks import evaluation, sciel_catalog_torch as torch
from arena.frameworks.sciel_catalog_profile import supports_requirements, validate_task_profile
from arena.registry import get_catalog

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "torch_preflight", ROOT / "scripts/deployment/sciel_catalog_preflight.py")
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


@pytest.fixture(autouse=True)
def no_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Preparation must not execute a candidate, process or network call")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(evaluation, "evaluate", forbidden)


def test_all_fifty_one_require_explicit_image_resources_and_cannot_widen_general_cpu():
    tasks = {t["id"]: t for t in get_catalog()["tasks"]}
    assert len(torch.TORCH_TASK_REQUIREMENTS) == 51
    assert [len(torch.TORCH_TASK_GROUPS[g]) for g in torch.TORCH_GROUPS] == [24, 3, 24]
    assert sum(len(names) for names in torch.TORCH_TASK_GROUPS.values()) == 51
    for name, requirements in torch.TORCH_TASK_REQUIREMENTS.items():
        task = tasks[name]
        assert task["requirements"] == list(requirements)
        assert task["protocol"] == "recreated"
        group = torch.torch_task_group(name, task["requirements"])
        environment = torch.torch_environment(torch.TORCH_IMAGE, group)
        config = {"profile": torch.TORCH_PROFILE, "execution": {
            "image": torch.TORCH_IMAGE, "resource_profile": environment["resource_profile"]}}
        assert validate_task_profile(task, config) == environment
        assert environment["runtime_policy"] == {
            "name": torch.TORCH_THREAD_POLICY, "threads": 1, "interop_threads": 1}
        assert environment["resources"]["cpus"] == 1 and environment["resources"]["pids"] == 256
        assert environment["data_assets"] == []
        assert environment["data_lock_sha256"] == hashlib.sha256(b"[]").hexdigest()
        assert "not CUDA/GPU latency" in environment["comparability"]
        assert not supports_requirements(task["requirements"])
        with pytest.raises(ValueError, match="approved CPU"):
            validate_task_profile(task, {})


@pytest.mark.parametrize("mutation", ["foreign", "extra", "file", "reorder", "duplicate", "type", "image", "resource", "absent"])
def test_nearby_task_or_environment_cannot_inherit_access(mutation):
    name, requirements = next(iter(torch.TORCH_TASK_REQUIREMENTS.items()))
    task = {"id": name, "requirements": list(requirements)}
    config = {"profile": torch.TORCH_PROFILE, "execution": {
        "image": torch.TORCH_IMAGE, "resource_profile": "cpu-2g-p256-v1"}}
    if mutation == "foreign": task["id"] = "a-new-torch-task"
    elif mutation == "extra": task["requirements"].append("py:triton")
    elif mutation == "file": task["requirements"][0] = "file:/data/private"
    elif mutation == "reorder": task["requirements"].reverse()
    elif mutation == "duplicate": task["requirements"].append("py:torch")
    elif mutation == "type": task["requirements"] = requirements
    elif mutation == "image": config["execution"]["image"] = "sha256:" + "0" * 64
    elif mutation == "resource": config["execution"]["resource_profile"] = "cpu-4g-p256-v1"
    else: del config["execution"]["resource_profile"]
    with pytest.raises(ValueError, match="exact reviewed|exact explicit"):
        validate_task_profile(task, config)


def test_environment_lock_and_fixed_base_are_bound_without_runtime_success_claim(tmp_path, monkeypatch):
    source = ROOT / "registry/evaluation-environments/sciel-torch-cpu.json"
    record = json.loads(source.read_bytes())
    assert record["entrypoint"] is None and record["cuda"] is None
    assert record["base_image_reference"].endswith(
        "@sha256:5483308aca52e347ea81e4739d9789e76765d63a91ce2b62f41cb314af4446cc")
    assert record["evidence"]["initial_results"] == {"resource_seed_passed": 29, "oom": 22}
    assert not record["evidence"]["canonical_admission"]
    assert record["evidence"]["fresh_canonical_receipts_required"]
    destination = tmp_path / "evaluation-environments/sciel-torch-cpu.json"
    destination.parent.mkdir()
    destination.write_bytes(source.read_bytes())
    monkeypatch.setattr(torch, "resolve_registry_root", lambda: tmp_path)
    assert torch.torch_environment(torch.TORCH_IMAGE, "torch-cpu-2g")
    destination.write_bytes(destination.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="digest"):
        torch.torch_environment(torch.TORCH_IMAGE, "torch-cpu-2g")


@pytest.mark.parametrize("group,count", [("torch-cpu-2g", 24), ("torch-cpu-4g", 3), ("torch-cpu-8g", 24)])
def test_inventory_keeps_959_and_never_relabels_resource_probes_as_verified(tmp_path, group, count):
    tasks = get_catalog()["tasks"]
    default = preflight.inventory(tasks, ROOT / "tasks")
    assert sum(r["status"] == "seed_check_pending" for r in default) == 349
    assert all(r["status"] == "environment_preparation_pending" for r in default
               if r["task_id"] in torch.TORCH_TASK_REQUIREMENTS)
    output = tmp_path.resolve() / group
    assert preflight.main(["--tasks-root", str(ROOT / "tasks"), "--output", str(output),
                           "--image", torch.TORCH_IMAGE, "--group", group]) == 0
    manifest = json.loads((output / "manifest.json").read_text())
    assert len(manifest["tasks"]) == 959 and manifest["model_calls"] == 0
    assert manifest["counts"]["seed_check_pending"] == count
    assert "seed_verified" not in manifest["counts"]
    assert manifest["profile"] == torch.TORCH_PROFILE
    assert manifest["prepared_environment"] == torch.torch_environment(torch.TORCH_IMAGE, group)
    assert manifest["resource_profile"] == manifest["prepared_environment"]["resource_profile"]
    assert {r["task_id"] for r in manifest["tasks"] if r["status"] == "seed_check_pending"} == set(torch.TORCH_TASK_GROUPS[group])
    assert not list(output.glob("*/receipt.json"))
    with pytest.raises(ValueError, match="exact reviewed image"):
        preflight.inventory(tasks, ROOT / "tasks", group, "sha256:" + "0" * 64)


@pytest.mark.parametrize("group", torch.TORCH_GROUPS)
def test_canonical_seed_dispatch_requires_correct_group_and_observed_thread_policy(tmp_path, monkeypatch, group):
    name = torch.TORCH_TASK_GROUPS[group][0]
    row = {"task_id": name, "requirements": list(torch.TORCH_TASK_REQUIREMENTS[name])}
    output = tmp_path / name
    output.mkdir()
    native = output / "native-output/native.json"
    native.parent.mkdir()
    payload = {"task_id": name, "candidate_sha256": "a" * 64, "evaluator_sha256": "b" * 64,
               "protocol": "recreated", "direction": "maximize", "mode": "suite",
               "status": "completed", "valid": True, "score": 0.5, "upstream_result": {
                   "thread_policy": torch.TORCH_THREAD_POLICY, "threads": 1, "interop_threads": 1}}
    native.write_text(json.dumps(payload))
    receipt = {key: value for key, value in payload.items() if key != "upstream_result"}
    receipt.update(status="completed", validity=True, fitness=0.5, raw_score=0.5, wall_seconds=1,
        problem_sha256="c" * 64, task_source={}, receipt_path=str(output / "receipt.json"),
        native_result_path=str(native), native_result_sha256=hashlib.sha256(native.read_bytes()).hexdigest())
    Path(receipt["receipt_path"]).write_text(json.dumps(receipt))
    calls = []
    monkeypatch.setattr(evaluation, "evaluate", lambda config, *_: calls.append(deepcopy(config)) or receipt)
    args = {"root": ROOT / "tasks", "output": tmp_path, "image": torch.TORCH_IMAGE, "timeout": 180, "group": group}
    assert preflight.check_seed(row, **args)["status"] == "seed_verified"
    assert calls[0]["profile"] == torch.TORCH_PROFILE
    assert calls[0]["execution"]["resource_profile"] == torch.torch_environment(torch.TORCH_IMAGE, group)["resource_profile"]
    with pytest.raises(ValueError, match="exact prepared Torch cohort"):
        preflight.check_seed({**row, "task_id": "foreign"}, **args)
    assert len(calls) == 1
    payload["upstream_result"]["threads"] = 2
    native.write_text(json.dumps(payload))
    receipt["native_result_sha256"] = hashlib.sha256(native.read_bytes()).hexdigest()
    assert preflight.check_seed(row, **args)["status"] == "seed_check_failed"
