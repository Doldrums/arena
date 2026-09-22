"""Exact source-derived LMX prompt cohort; this profile does not grant a GPU.

Preparation pins the declared environment. Fresh controlled canonical receipts
and separately approved server capability are still required for admission.
Neither private seed scores nor this bridge establish paper reproduction.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import re

from arena.evaluator_gpu import (DEVICE_UUID, DRIVER_SHA, DRIVER_VERSION, GPU_BUDGET,
                                 IMAGE, IMAGE_ID, IMAGE_LABELS, MODEL_SHA,
                                 PROFILE as RESOURCE_PROFILE, TASK_IDS)
from arena.task_library import read_task_file

LMX_PROFILE = "sciel-catalog-prepared-lmx/1"
PROTOCOL = "arena.lmx-sd14-excess-rgb/1"
REVISION = "2880f2ca379f41b0226444936bb7a6766a227587"
ASSET_PATH = "adapters/lmx_sd_assets.json"
MAXIMUM_SCORE = 512 * 512 * 255
ALLOCATOR_LIMIT = 8 * 1024 ** 3
REQUIREMENTS = ("hardware:gpu", "py:numpy", "py:torch", "py:torchvision",
                "py:transformers", "py:diffusers", "py:PIL", "py:ftfy",
                "model:stable-diffusion-v1-4@" + REVISION, "env:LMX_SD_ASSETS_DIR")
RUNTIME = {"torch": "2.9.1+cu128", "torchvision": "0.24.1+cu128", "diffusers": "0.35.2",
           "transformers": "4.57.3", "Pillow": "11.3.0", "safetensors": "0.7.0",
           "ftfy": "6.3.1", "numpy": "2.2.6", "scipy": "1.15.3"}
GENERATION = {"height": 512, "width": 512, "num_inference_steps": 10, "guidance_scale": 7.5,
              "negative_prompt": None, "num_images_per_prompt": 1, "eta": 0.0,
              "output_type": "pil", "seed": 99, "dtype": "float16",
              "attention_processor": "AttnProcessor", "tf32": False}


def _number_equal(value, expected):
    # Python equality alone aliases JSON false/true with numeric zero/one.
    return type(value) in (int, float) and value == expected


def _counts_equal(value, expected):
    return (type(value) is dict and set(value) == set(expected)
            and all(type(value[key]) is int and value[key] == count for key, count in expected.items()))


def supports_lmx_task(task_id, requirements):
    return (type(task_id) is str and task_id in TASK_IDS and type(requirements) is list
            and tuple(requirements) == REQUIREMENTS)


def lmx_environment(image):
    if image != IMAGE:
        raise ValueError("Prepared LMX requires its exact reviewed GPU image digest")
    return {"profile": LMX_PROFILE, "image_reference": IMAGE, "image_id": IMAGE_ID,
            "dependency_lock_sha256": IMAGE_LABELS["io.arena.requirements.sha256"],
            "model_id": "CompVis/stable-diffusion-v1-4", "model_revision": REVISION,
            "model_asset_manifest_sha256": MODEL_SHA, "driver_manifest_sha256": DRIVER_SHA,
            "driver_version": DRIVER_VERSION, "device_uuid": DEVICE_UUID,
            "resource_profile": RESOURCE_PROFILE, "resources": dict(GPU_BUDGET),
            "timeout_seconds": 600, "protocol": PROTOCOL, "runtime_packages": dict(RUNTIME),
            "torch_allocator_limit_bytes": ALLOCATOR_LIMIT, "gpu_hard_memory_limit": None,
            "comparability": "source-derived Arena protocol; published paper scores are not comparable"}


def validate_lmx_task(task, evaluation):
    execution = evaluation["execution"]
    if (not supports_lmx_task(task["id"], task.get("requirements"))
            or task.get("protocol") != "recreated" or task.get("direction") != "maximize"
            or execution.get("kind") != "docker" or execution.get("resource_profile") != RESOURCE_PROFILE
            or execution.get("require_control_cgroup") is not True
            or execution.get("python") not in {"python", "python3"}
            or type(evaluation.get("timeout_seconds")) is not int or evaluation["timeout_seconds"] != 600):
        raise ValueError("Prepared LMX requires the exact controlled 600-second GPU task profile")
    return lmx_environment(execution["image"])


def validate_lmx_metadata(task, metadata, problem, root, files):
    """Read pinned metadata/model lock only; never import a GPU or task package."""
    suite = metadata.get("execution", {}).get("suite", {})
    expected = {"protocol": "recreated", "family": "lmx_sd_prompt", "evaluator": "evaluator.py",
                "initial_program": "initial_program.py", "callable": "evaluate", "env": {},
                "score_key": "score", "error_key": "error", "validity_key": "valid",
                "requires": list(REQUIREMENTS), "timeout": 600}
    parameters = {key: value for key, value in GENERATION.items() if key not in {"eta", "output_type"}}
    parameters.update(channel=task["id"].rsplit("-", 1)[1][0], scheduler="PNDMScheduler",
                      safety_checker=True, model_revision=REVISION, asset_manifest_sha256=MODEL_SHA)
    if (json.dumps(suite, sort_keys=True) != json.dumps(expected, sort_keys=True)
            or json.dumps(problem.get("parameters"), sort_keys=True) != json.dumps(parameters, sort_keys=True)
            or problem.get("requires") != list(REQUIREMENTS) or problem.get("timeout") != 600
            or files.get(ASSET_PATH) != MODEL_SHA):
        raise ValueError("Prepared LMX metadata differs from the exact source-derived protocol")
    # The source manifest alone must not substitute a different model lock.
    lock = json.loads(read_task_file(root, ASSET_PATH, MODEL_SHA))
    if (lock.get("schema") != "arena.lmx-sd-assets/1" or lock.get("revision") != REVISION
            or lock.get("model_id") != "CompVis/stable-diffusion-v1-4" or len(lock.get("files", {})) != 17):
        raise ValueError("Prepared LMX model asset identity changed")


def validate_lmx_seed_receipt(receipt, output):
    """Bind a full canonical result to observed SD protocol, not seed score parity.

Also suitable for later candidates: no expected prompt, score or image digest is
fixed. Server-side device/mount identity remains a separate admission proof.
"""
    from .evaluation import _read_native_result

    path = Path(output) / "native-output/native.json"
    if (type(receipt) is not dict or receipt.get("native_result_path") != str(path)
            or path.resolve() != path or path.is_symlink()):
        raise ValueError("LMX requires its canonical native result path")
    native, digest = _read_native_result(path)
    raw = receipt.get("raw_score")
    execution = receipt.get("execution")
    if (type(raw) not in (int, float) or not math.isfinite(raw) or abs(raw) > MAXIMUM_SCORE
            or receipt.get("status") != "completed" or receipt.get("validity") is not True
            or not _number_equal(receipt.get("fitness"), raw) or receipt.get("direction") != "maximize"
            or receipt.get("protocol") != "recreated" or receipt.get("task_id") not in TASK_IDS
            or type(execution) is not dict or execution.get("require_control_cgroup") is not True
            or execution != {"kind": "docker", "image": IMAGE,
                "python": execution.get("python"), "require_control_cgroup": True,
                "resource_profile": RESOURCE_PROFILE}
            or execution["python"] not in {"python", "python3"}
            or type(receipt.get("evaluation_attempts")) is not int or receipt["evaluation_attempts"] != 1
            or type(receipt.get("retries")) is not int or receipt["retries"] != 0
            or digest != receipt.get("native_result_sha256") or type(native) is not dict
            or any(native.get(key) != receipt.get(key) for key in
                   ("task_id", "candidate_sha256", "evaluator_sha256", "protocol", "direction"))
            or native.get("mode") != "suite" or native.get("status") != "completed"
            or native.get("valid") is not True or not _number_equal(native.get("score"), raw)):
        raise ValueError("LMX canonical native result differs from its receipt binding")
    result = native.get("upstream_result")
    if (type(result) is not dict or result.get("protocol") != PROTOCOL
            or result.get("channel") != receipt["task_id"].rsplit("-", 1)[1][0]
            or not _number_equal(result.get("score"), raw) or not _number_equal(result.get("combined_score"), raw)
            or result.get("valid") is not True or result.get("direction") != "maximize"
            or json.dumps(result.get("generation"), sort_keys=True) != json.dumps(GENERATION, sort_keys=True)
            or result.get("runtime_packages") != RUNTIME
            or result.get("safety_checker_enabled") is not True
            or type(result.get("nsfw_content_detected")) is not bool
            or result.get("paper_reproduction") is not False
            or not _counts_equal(result.get("model_usage"), {"diffusion_images": 1, "llm_calls": 0, "external_api_calls": 0})
            or not _number_equal(result.get("normalized_excess"), raw / MAXIMUM_SCORE)
            or result.get("normalization_role") != "display_only"
            or type(result.get("image_sha256")) is not str
            or re.fullmatch(r"[0-9a-f]{64}", result["image_sha256"]) is None
            or json.dumps(result.get("assets"), sort_keys=True) != json.dumps({
                "model_id": "CompVis/stable-diffusion-v1-4", "revision": REVISION,
                "manifest_sha256": MODEL_SHA, "verified_files": 17}, sort_keys=True)):
        raise ValueError("LMX native result lacks the exact full-image SD protocol evidence")
    device = result.get("device", {})
    if (type(device) is not dict or device.get("uuid") != DEVICE_UUID.removeprefix("GPU-")
            or type(device.get("torch_allocator_limit_bytes")) is not int
            or device["torch_allocator_limit_bytes"] != ALLOCATOR_LIMIT
            or any(type(device.get(key)) is not int or device[key] <= 0 for key in
                   ("reported_memory_bytes", "peak_allocated_bytes", "peak_reserved_bytes"))
            or not 0 < device["peak_allocated_bytes"] <= device["peak_reserved_bytes"] <= ALLOCATOR_LIMIT
            or device["reported_memory_bytes"] < ALLOCATOR_LIMIT):
        raise ValueError("LMX native result lacks the assigned GPU/allocator evidence")
    return {"native_result_sha256": digest, "protocol": PROTOCOL,
            "image_sha256": result["image_sha256"], "device_uuid": DEVICE_UUID,
            "model_asset_manifest_sha256": MODEL_SHA, "paper_reproduction": False}
