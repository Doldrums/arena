"""Exact prepared CPU kernel cohort; resource membership is not seed readiness.

Only fresh canonical receipts for this library/image/resource/thread policy can
qualify. CPU timings cannot establish GPU benchmark or published SOTA claims.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from arena.evaluation_resources import budget
from arena.registry import resolve_registry_root
from arena.task_library import read_task_file

TORCH_PROFILE = "sciel-catalog-prepared-torch/1"
TORCH_IMAGE = ("127.0.0.1:5000/empira/canonical-torch-cpu@sha256:"
               "23917809181d13d863764e28646ba79349cca91f11ea7f424b9863ca8ca23069")
TORCH_ENVIRONMENT_SHA256 = "35a26c9ded6211544d0b0d441ebc20725e1a5e172c38281dbf2860e04a7f7d29"
TORCH_THREAD_POLICY = "arena.kernel-cpu.single-thread/1"
TORCH_TASK_GROUPS = {
    "torch-cpu-2g": (
        "accelopt-adamw-m10944-n2048-0",
        "accelopt-add-rmsnorm-matmul-m4096-n2048-k1024-0",
        "accelopt-gqa-full-b1-n4096-qh16-kh8-d128-0",
        "accelopt-lora-m4096-n12288-k5120-r128-0",
        "accelopt-mamba-m7168-c256-s16-0",
        "accelopt-matmul-add-rmsnorm-m4096-n2048-k2048-0",
        "accelopt-matmul-m4096-n12288-k5120-0",
        "accelopt-rmsnorm-matmul-m4096-n2048-k1024-0",
        "accelopt-rope-single-freq-apply-b1-h64-n4096-d128-0",
        "accelopt-silu-m4096-n7168-0",
        "accelopt-swiglu-m4096-n3072-k1024-0",
        "accelopt-transpose-matmul-m4096-k2048-n10944-0",
        "eurekagent-gpumode-trimul-a100",
        "kernelpro-kernelbench-level-1-single-operators",
        "kernelpro-kernelbench-level-2-fused-operators",
        "kernelpro-kernelbench-level-3-architectures",
        "kernelpro-swish-energy-aware-kernel-optimization",
        "kernelpro-triton-inference-fused-moe",
        "kernelpro-triton-inference-gemm-split-k",
        "kernelpro-triton-inference-kernel-paged-attention",
        "kernelpro-triton-inference-layer-norm",
        "kernelpro-triton-inference-persistent-vec-matmul",
        "kernelpro-triton-inference-vec-matmul",
        "kernelpro-veomni-dw1-grouped-gemm-weight-gradient",
    ),
    "torch-cpu-4g": (
        "agentic-optimization-decode-attention-kernel-optimization",
        "avo-mha-16-heads-causal-sequence-4096",
        "avo-mha-16-heads-non-causal-sequence-4096",
    ),
    "torch-cpu-8g": (
        "accelopt-bmm-b16-m4096-k64-n4096-0",
        "accelopt-bmm-softmax-b16-k64-m4096-n4096-0",
        "avo-gqa-32-query-heads-4-kv-heads-causal-sequence-16384",
        "avo-gqa-32-query-heads-4-kv-heads-causal-sequence-32768",
        "avo-gqa-32-query-heads-4-kv-heads-causal-sequence-4096",
        "avo-gqa-32-query-heads-4-kv-heads-causal-sequence-8192",
        "avo-gqa-32-query-heads-4-kv-heads-non-causal-sequence-16384",
        "avo-gqa-32-query-heads-4-kv-heads-non-causal-sequence-32768",
        "avo-gqa-32-query-heads-4-kv-heads-non-causal-sequence-4096",
        "avo-gqa-32-query-heads-4-kv-heads-non-causal-sequence-8192",
        "avo-gqa-32-query-heads-8-kv-heads-causal-sequence-16384",
        "avo-gqa-32-query-heads-8-kv-heads-causal-sequence-32768",
        "avo-gqa-32-query-heads-8-kv-heads-causal-sequence-4096",
        "avo-gqa-32-query-heads-8-kv-heads-causal-sequence-8192",
        "avo-gqa-32-query-heads-8-kv-heads-non-causal-sequence-16384",
        "avo-gqa-32-query-heads-8-kv-heads-non-causal-sequence-32768",
        "avo-gqa-32-query-heads-8-kv-heads-non-causal-sequence-4096",
        "avo-gqa-32-query-heads-8-kv-heads-non-causal-sequence-8192",
        "avo-mha-16-heads-causal-sequence-16384",
        "avo-mha-16-heads-causal-sequence-32768",
        "avo-mha-16-heads-causal-sequence-8192",
        "avo-mha-16-heads-non-causal-sequence-16384",
        "avo-mha-16-heads-non-causal-sequence-32768",
        "avo-mha-16-heads-non-causal-sequence-8192",
    ),
}
TORCH_GROUPS = tuple(TORCH_TASK_GROUPS)
TORCH_TASK_REQUIREMENTS = {name: ("py:numpy", "py:torch")
                           for names in TORCH_TASK_GROUPS.values() for name in names}


def torch_task_group(task_id, requirements):
    """Exact IDs and ordered requirements; never grant package-wide Torch access."""
    if (type(task_id) is not str or task_id not in TORCH_TASK_REQUIREMENTS
            or type(requirements) is not list
            or tuple(requirements) != TORCH_TASK_REQUIREMENTS[task_id]):
        return None
    return next(group for group, names in TORCH_TASK_GROUPS.items() if task_id in names)


def torch_environment(image, group):
    if image != TORCH_IMAGE or group not in TORCH_GROUPS:
        raise ValueError("Prepared Torch requires the exact reviewed image and resource group")
    record = json.loads(read_task_file(resolve_registry_root(),
        "evaluation-environments/sciel-torch-cpu.json", TORCH_ENVIRONMENT_SHA256))
    resource = record["resources"][group]
    limits = budget(resource["profile"])
    if (record["image_reference"] != image or record["entrypoint"] is not None
            or hashlib.sha256(record["requirements_lock"].encode()).hexdigest() != record["requirements_sha256"]
            or {key: resource[key] for key in limits} != limits
            or record["thread_policy"] != {"name": TORCH_THREAD_POLICY, "threads": 1, "interop_threads": 1}):
        raise ValueError("Prepared Torch dependency, resource or thread policy changed")
    return {"profile": TORCH_PROFILE, "group": group, "image_reference": image,
            "image_id": record["image_id"], "environment_sha256": TORCH_ENVIRONMENT_SHA256,
            "dependency_lock_sha256": record["requirements_sha256"],
            "base_image_reference": record["base_image_reference"],
            "data_lock_sha256": record["data_lock_sha256"], "data_assets": record["data_assets"],
            "resource_profile": resource["profile"], "resources": limits,
            "runtime_policy": record["thread_policy"], "comparability": record["comparability"]}


def validate_torch_task(task, evaluation):
    group = torch_task_group(task["id"], task.get("requirements"))
    environment = torch_environment(evaluation["execution"]["image"], group)
    if evaluation["execution"].get("resource_profile") != environment["resource_profile"]:
        raise ValueError("Prepared Torch requires the exact explicit resource profile")
    return environment


def validate_torch_seed_receipt(receipt, output):
    """Bind the observed 1/1 timing policy to this exact canonical native result."""
    from .evaluation import _read_native_result

    path = Path(output) / "native-output/native.json"
    if (receipt.get("native_result_path") != str(path) or path.resolve() != path
            or path.is_symlink()):
        raise ValueError("Torch seed requires its canonical native result path")
    native, digest = _read_native_result(path)
    if (digest != receipt.get("native_result_sha256") or type(native) is not dict
            or any(native.get(key) != receipt.get(key) for key in
                   ("task_id", "candidate_sha256", "evaluator_sha256", "protocol", "direction"))
            or native.get("mode") != "suite" or native.get("status") != "completed"
            or native.get("valid") is not True or native.get("score") != receipt.get("raw_score")):
        raise ValueError("Torch seed native result differs from its receipt binding")
    result = native.get("upstream_result")
    if (type(result) is not dict or result.get("thread_policy") != TORCH_THREAD_POLICY
            or type(result.get("threads")) is not int or result["threads"] != 1
            or type(result.get("interop_threads")) is not int or result["interop_threads"] != 1):
        raise ValueError("Torch seed requires observed single-thread CPU timing evidence")
