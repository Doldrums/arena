"""Exact LMX preparation/measurement boundary; no GPU or model is executed."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from arena.frameworks import sciel_catalog_lmx as lmx
from arena.frameworks.sciel_catalog_profile import validate_task_profile
from test_sciel_catalog_evaluate import setup, bridge, evaluation, digest

REPO = Path(__file__).resolve().parents[2]


def rehash(root):
    manifest = root.parent / "registry/task-library-manifest.json"
    manifest.write_text(json.dumps({"schema": "arena.task-library/1", "files": {
        p.relative_to(root).as_posix(): digest(p) for p in root.rglob("*") if p.is_file()}}))
    evaluation.get_catalog()["sources"][0]["manifest_sha256"] = digest(manifest)


@pytest.fixture
def lmx_inputs(setup, monkeypatch):
    config, candidate, marker, calls, updates, root, task = setup
    name = lmx.TASK_IDS[0]
    task.update(id=name, name="Stable Diffusion excess blue", requirements=list(lmx.REQUIREMENTS),
                direction="maximize", protocol="recreated", metric="excess blue (full-image RGB channel sums)")
    directory = root / "suite" / name
    (root / "suite/fixture").rename(directory)
    original = REPO / "tasks/suite" / name
    for filename in ("task.json", "problem.json", "initial_program.py"):
        (directory / filename).write_bytes((original / filename).read_bytes())
    task["contract"] = json.loads((directory / "problem.json").read_bytes())["contract"]
    task["contract_source"] = {"path": f"suite/{name}/problem.json",
                               "sha256": digest(directory / "problem.json")}
    assets = root / lmx.ASSET_PATH
    assets.parent.mkdir()
    assets.write_bytes((REPO / "tasks" / lmx.ASSET_PATH).read_bytes())
    rehash(root)
    config["evaluation"].update(task_id=name, profile=lmx.LMX_PROFILE, timeout_seconds=600)
    config["evaluation"]["execution"].update(image=lmx.IMAGE, resource_profile=lmx.RESOURCE_PROFILE,
                                             require_control_cgroup=True)
    monkeypatch.setattr(evaluation, "receipt_root", lambda config, fallback: fallback)
    old_evaluate = evaluation.evaluate
    native_updates = {}

    def evaluate(actual, program, output):
        receipt = old_evaluate(actual, program, output)
        if receipt["status"] == "capacity_unavailable":
            (output / "receipt.json").write_text(json.dumps(receipt))
            return receipt
        raw = receipt["raw_score"]
        result = {"protocol": lmx.PROTOCOL, "channel": name.rsplit("-", 1)[1][0],
            "score": raw, "combined_score": raw, "direction": "maximize", "valid": True,
            "generation": deepcopy(lmx.GENERATION), "runtime_packages": deepcopy(lmx.RUNTIME),
            "safety_checker_enabled": True, "nsfw_content_detected": False, "paper_reproduction": False,
            "model_usage": {"diffusion_images": 1, "llm_calls": 0, "external_api_calls": 0},
            "normalized_excess": raw / lmx.MAXIMUM_SCORE, "normalization_role": "display_only",
            "image_sha256": "f" * 64, "assets": {"model_id": "CompVis/stable-diffusion-v1-4",
                "revision": lmx.REVISION, "manifest_sha256": lmx.MODEL_SHA, "verified_files": 17},
            "device": {"uuid": lmx.DEVICE_UUID.removeprefix("GPU-"),
                "reported_memory_bytes": 24 * 1024 ** 3, "torch_allocator_limit_bytes": lmx.ALLOCATOR_LIMIT,
                "peak_allocated_bytes": 3 * 1024 ** 3, "peak_reserved_bytes": 4 * 1024 ** 3}}
        for key, value in native_updates.items():
            result[key] = value
        native = {key: receipt[key] for key in
                  ("task_id", "candidate_sha256", "evaluator_sha256", "protocol", "direction")}
        native.update(mode="suite", status="completed", valid=True, score=raw, upstream_result=result)
        path = output / "native-output/native.json"
        path.parent.mkdir()
        path.write_text(json.dumps(native))
        receipt.update(native_result_path=str(path), native_result_sha256=digest(path),
                       evaluation_attempts=1, retries=0)
        (output / "receipt.json").write_text(json.dumps(receipt))
        return receipt
    monkeypatch.setattr(evaluation, "evaluate", evaluate)
    return setup, native_updates


def test_exact_three_real_metadata_records_and_asset_lock_match_profile():
    assert len(lmx.TASK_IDS) == 3
    for name in lmx.TASK_IDS:
        metadata = json.loads((REPO / "tasks/suite" / name / "task.json").read_bytes())
        problem = json.loads((REPO / "tasks/suite" / name / "problem.json").read_bytes())
        assert lmx.supports_lmx_task(name, metadata["execution"]["suite"]["requires"])
        lmx.validate_lmx_metadata({"id": name}, metadata, problem, REPO / "tasks",
                                 {lmx.ASSET_PATH: lmx.MODEL_SHA})


def test_native_package_describes_gpu_and_pins_environment_without_evaluating(lmx_inputs, tmp_path):
    (config, _, marker, calls, _, _, _), _ = lmx_inputs
    target = tmp_path / "native"
    result = bridge.create_task(config, target)
    native = json.loads((target / "task.yaml").read_bytes())
    bound = json.loads((target / "evaluation.json").read_bytes())
    assert native["resources"] == "gpu" and native["origin"] == "heavy"
    assert "isolated GPU container" in native["task_prompt"] and "CPU container" not in native["task_prompt"]
    assert len(native["task_prompt"]) <= 1600 and native["full_timeout"] == 720
    assert native["confirm_timeout"] == 2160 and native["confirm_n"] == 3
    assert bound["binding"]["prepared_environment"] == lmx.lmx_environment(lmx.IMAGE)
    assert lmx.MODEL_SHA in (target / "evaluator.py").read_text()
    assert result["runtime_conformance"] == "not_verified" and not calls and not marker.exists()


@pytest.mark.parametrize("change", ["task", "order", "additional", "model", "image", "tag", "profile",
                                    "cgroup", "timeout", "protocol", "direction", "python"])
def test_lmx_profile_has_no_generic_gpu_or_dependency_admission(lmx_inputs, change):
    (config, _, _, calls, _, _, task), _ = lmx_inputs
    if change == "task": task["id"] = "some-other-gpu-task"
    elif change == "order": task["requirements"].reverse()
    elif change == "additional": task["requirements"].append("py:pandas")
    elif change == "model": task["requirements"][-2] = "model:other"
    elif change == "image": config["evaluation"]["execution"]["image"] = lmx.IMAGE_ID
    elif change == "tag": config["evaluation"]["execution"]["image"] = "some-image:latest"
    elif change == "profile": config["evaluation"]["execution"]["resource_profile"] = "cpu-2g-p256"
    elif change == "cgroup": config["evaluation"]["execution"]["require_control_cgroup"] = False
    elif change == "timeout": config["evaluation"]["timeout_seconds"] = 599
    elif change == "protocol": task["protocol"] = "original"
    elif change == "direction": task["direction"] = "minimize"
    else: config["evaluation"]["execution"]["python"] = "/unreviewed/python"
    with pytest.raises(ValueError):
        validate_task_profile(task, config["evaluation"])
    assert not calls


@pytest.mark.parametrize("change", ["env", "requires", "dimensions", "model", "steps", "seed", "assets", "boolean"])
def test_rehashed_task_cannot_override_lmx_environment_or_protocol(lmx_inputs, change):
    (config, candidate, _, calls, _, root, task), _ = lmx_inputs
    directory = root / "suite" / task["id"]
    metadata_path, problem_path = directory / "task.json", directory / "problem.json"
    metadata, problem = json.loads(metadata_path.read_bytes()), json.loads(problem_path.read_bytes())
    if change == "env": metadata["execution"]["suite"]["env"] = {"LMX_SD_ASSETS_DIR": "/candidate/model"}
    elif change == "requires": metadata["execution"]["suite"]["requires"].reverse()
    elif change == "dimensions": problem["parameters"]["height"] = 256
    elif change == "model": problem["parameters"]["model_revision"] = "wrong"
    elif change == "steps": problem["parameters"]["num_inference_steps"] = 1
    elif change == "seed": problem["parameters"]["seed"] = 0
    elif change == "boolean": problem["parameters"]["num_images_per_prompt"] = True
    else: (root / lmx.ASSET_PATH).write_text("{}")
    metadata_path.write_text(json.dumps(metadata))
    problem_path.write_text(json.dumps(problem))
    task["contract_source"]["sha256"] = digest(problem_path)
    rehash(root)
    with pytest.raises(ValueError): bridge.full(config, candidate)
    assert not calls


def test_lmx_result_keeps_raw_metric_and_observed_protocol_evidence(lmx_inputs):
    (config, candidate, marker, calls, _, _, _), _ = lmx_inputs
    result = bridge.full(config, candidate)
    assert result["ok"] and result["cases"] == {"raw_score": 2.0, "canonical_fitness": 2.0, "validity": 1.0}
    assert result["score"] != result["cases"]["raw_score"]
    proof = json.loads(result["artifacts"]["arena_lmx_protocol_evidence"])
    assert proof["protocol"] == lmx.PROTOCOL and proof["device_uuid"] == lmx.DEVICE_UUID
    assert proof["paper_reproduction"] is False and len(calls) == 1 and not marker.exists()


@pytest.mark.parametrize("change", ["safety", "generation", "packages", "assets", "device", "score", "paper"])
def test_missing_or_changed_native_protocol_evidence_never_becomes_a_measurement(lmx_inputs, change):
    (config, candidate, _, _, _, _, _), updates = lmx_inputs
    if change == "safety": updates["safety_checker_enabled"] = False
    elif change == "generation": updates["generation"] = {**lmx.GENERATION, "height": 256}
    elif change == "packages": updates["runtime_packages"] = {**lmx.RUNTIME, "diffusers": "other"}
    elif change == "assets": updates["assets"] = {}
    elif change == "device": updates["device"] = {"uuid": "unapproved"}
    elif change == "score": updates["score"] = 100
    else: updates["paper_reproduction"] = True
    with pytest.raises(ValueError): bridge.full(config, candidate)


@pytest.mark.parametrize("field", ["raw_score", "fitness", "native_score", "upstream_score", "combined_score",
    "normalized_excess", "diffusion_images", "llm_calls", "external_api_calls", "fractional_count",
    "fractional_verified_files", "control_flag"])
def test_standalone_receipt_validator_rejects_boolean_numeric_aliases_at_zero(lmx_inputs, tmp_path, field):
    (config, candidate, _, _, updates, _, _), _ = lmx_inputs
    updates.update(raw_score=0.0, fitness=0.0)
    output = tmp_path / "zero-score-proof"
    receipt = evaluation.evaluate(config["evaluation"], candidate, output)
    assert lmx.validate_lmx_seed_receipt(receipt, output)["protocol"] == lmx.PROTOCOL
    path = output / "native-output/native.json"
    native = json.loads(path.read_bytes())
    if field in {"raw_score", "fitness"}: receipt[field] = False
    elif field == "native_score": native["score"] = False
    elif field == "upstream_score": native["upstream_result"]["score"] = False
    elif field in {"combined_score", "normalized_excess"}: native["upstream_result"][field] = False
    elif field in {"diffusion_images", "llm_calls", "external_api_calls"}:
        native["upstream_result"]["model_usage"][field] = field == "diffusion_images"
    elif field == "fractional_count": native["upstream_result"]["model_usage"]["diffusion_images"] = 1.0
    elif field == "fractional_verified_files": native["upstream_result"]["assets"]["verified_files"] = 17.0
    else: receipt["execution"]["require_control_cgroup"] = 1
    path.write_text(json.dumps(native))
    receipt["native_result_sha256"] = digest(path)
    (output / "receipt.json").write_text(json.dumps(receipt))
    with pytest.raises(ValueError): lmx.validate_lmx_seed_receipt(receipt, output)


def capacity(updates):
    updates.update(status="capacity_unavailable", raw_score=None, fitness=None, validity=None,
        evaluation_attempts=0, retries=0,
        capacity_wait={"create_requests": 600, "busy_responses": 600, "wait_seconds": 600.0})


@pytest.mark.parametrize("stage", ["full", "confirm"])
def test_capacity_is_infrastructure_without_raw_score_or_candidate_verdict(lmx_inputs, stage):
    (config, candidate, _, calls, updates, _, _), _ = lmx_inputs
    capacity(updates)
    result = bridge.full(config, candidate) if stage == "full" else bridge.confirm(config, candidate, 3)
    assert result["ok"] is False and result["cases"] == {} and len(calls) == 1
    assert result["artifacts"]["error_type"] == "ArenaGpuCapacityUnavailable"
    assert result["artifacts"]["arena_failure_class"] == "infrastructure"
    assert result["artifacts"]["arena_candidate_evaluated"] == "false"
    receipt = json.loads((calls[0][2] / "receipt.json").read_bytes())
    assert all(receipt[key] is None for key in ("raw_score", "fitness", "validity"))
    assert receipt["evaluation_attempts"] == 0 and receipt["retries"] == 0


@pytest.mark.parametrize("changed", [{"raw_score": 0}, {"fitness": 0}, {"validity": False},
    {"evaluation_attempts": 1}, {"evaluation_attempts": False}, {"retries": 1}, {"container_id": "a" * 64},
    {"native_result_sha256": "a" * 64}, {"capacity_wait": {}},
    {"capacity_wait": {"create_requests": 2, "busy_responses": 1, "wait_seconds": 1.0}}])
def test_capacity_cannot_relabel_an_executed_or_invalid_candidate(lmx_inputs, changed):
    (config, candidate, _, _, updates, _, _), _ = lmx_inputs
    capacity(updates)
    updates.update(changed)
    with pytest.raises(ValueError, match="capacity receipt"): bridge.full(config, candidate)


def test_later_capacity_trial_does_not_erase_prior_confirmation_execution(lmx_inputs, monkeypatch):
    (config, candidate, _, calls, updates, _, _), _ = lmx_inputs
    original = evaluation.evaluate
    def evaluate(config, program, output):
        if calls:
            capacity(updates)
        return original(config, program, output)
    monkeypatch.setattr(evaluation, "evaluate", evaluate)
    result = bridge.confirm(config, candidate, 3)
    assert not result["ok"] and result["cases"] == {} and len(calls) == 2
    assert result["artifacts"]["arena_candidate_evaluated"] == "true"
    assert result["artifacts"]["arena_confirmation_completed_trials"] == "1"
    assert result["artifacts"]["arena_failed_trial_candidate_evaluated"] == "false"
    trials = json.loads(result["artifacts"]["arena_trial_receipts"])
    assert "arena_lmx_protocol_evidence" in trials[0]
    assert trials[1]["error_type"] == "ArenaGpuCapacityUnavailable"


def test_cpu_cannot_claim_gpu_capacity_or_prepared_lmx_profile(setup):
    config, candidate, _, _, updates, _, task = setup
    capacity(updates)
    with pytest.raises(ValueError, match="capacity receipt"): bridge.full(config, candidate)
    config["evaluation"]["profile"] = lmx.LMX_PROFILE
    with pytest.raises(ValueError, match="controlled"): validate_task_profile(task, config["evaluation"])


def test_cpu_prompt_and_native_metadata_bytes_keep_the_existing_contract(setup, tmp_path):
    config, _, _, _, _, _, task = setup
    expected = ('Task: Fixture packing.\nInterface: construct() -> array\nParameters: {"n":21}\n'
        "Objective: minimize the evaluator's raw energy metric. canonical_fitness = raw_score for maximization, "
        "-raw_score for minimization. search_score = 0.5 + atan(canonical_fitness / 1) / pi. "
        "This is search scaling only; raw scores remain in canonical receipts. Smoke checks syntax only. "
        "Full evaluates once in an isolated CPU container. Confirmation, when requested, averages fresh "
        "canonical trials before scaling.")
    assert bridge._prompt(task, config, {"n": 21}).encode() == expected.encode()
    target = tmp_path / "cpu-native"
    bridge.create_task(config, target)
    assert digest(target / "task.yaml") == "635bebae409dcebb2447d484d34ca5bf0e02abfa24a5ca62788637d0fad0fc7b"
