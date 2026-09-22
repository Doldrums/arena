"""Exact eight-task JAX CPU environment, independent of general CPU admission.

The reviewed image IDs include dependency bytes and the affinity policy. This
does not establish task readiness: fresh valid seed receipts are still required.
"""
from __future__ import annotations

import json

from arena.evaluation_resources import budget
from arena.registry import resolve_registry_root
from arena.task_library import read_task_file

JAX_PROFILE = "sciel-catalog-prepared-jax/1"
JAX_GROUPS = ("jax-affinity", "jax-original-4g")
JAX_ENVIRONMENT_SHA256 = "72488a9dc358af223eb4159c19ea1db8353971b1c062c53183d8e20dffbdb23f"
JAX_AFFINITY_IMAGE = "sha256:a6477246f35216c2c74d8fe3f74b0ea23df97f54bb1aed82cb1df7ab7d9ee351"
JAX_ORIGINAL_IMAGE = "sha256:0f9c4ffe3d53ac8770104f23b0b5fc9d93beb2ecb87cb8676153c69769ba531e"
JAX_IMAGES = dict(zip(JAX_GROUPS, (JAX_AFFINITY_IMAGE, JAX_ORIGINAL_IMAGE)))
JAX_TASK_REQUIREMENTS = {
    "sciel-math-erdos-min-overlap": ("py:jax", "py:numpy", "py:optax", "py:tqdm"),
    "sciel-math-first-autocorr-ineq": ("py:jax", "py:numpy", "py:optax"),
    "sciel-math-heilbronn-convex-14": ("py:jax", "py:numpy", "py:optax", "py:scipy"),
    "sciel-math-matmul": ("py:jax", "py:numpy", "py:optax", "py:tqdm"),
    "sciel-math-second-autocorr-ineq": ("py:jax", "py:numpy", "py:optax"),
    "sciel-math-sums-diffs-finite-sets": ("py:jax", "py:numpy", "py:tqdm"),
    "sciel-math-third-autocorr-ineq": ("py:jax", "py:numpy", "py:optax"),
    "sciel-math-uncertainty-ineq": ("py:jax", "py:numpy", "py:optax", "py:scipy", "py:sympy", "py:tqdm"),
}


def jax_task_group(task_id, requirements):
    """Exact task and ordered requirement list; no package-wide permission."""
    if (type(task_id) is not str or task_id not in JAX_TASK_REQUIREMENTS
            or type(requirements) is not list
            or tuple(requirements) != JAX_TASK_REQUIREMENTS[task_id]):
        return None
    return "jax-original-4g" if task_id == "sciel-math-sums-diffs-finite-sets" else "jax-affinity"


def jax_environment(image, group=None):
    """Verify bundled lock bytes as well as the selected immutable image ID."""
    selected = next((name for name, value in JAX_IMAGES.items() if image == value), None)
    if selected is None or group is not None and group != selected:
        raise ValueError("Prepared JAX requires its exact reviewed image and group")
    root = resolve_registry_root()
    prefix = "evaluation-environments/"
    raw = read_task_file(root, prefix + "sciel-jax-cpu.json", JAX_ENVIRONMENT_SHA256)
    record = json.loads(raw)
    for key in ("dependencies", "installed_packages"):
        lock = record[key]
        read_task_file(root, prefix + lock["path"], lock["sha256"])
    variant = record["variants"][selected]
    if variant["image_id"] != image or variant["resources"] != budget(variant["resource_profile"]):
        raise ValueError("Prepared JAX environment resource contract changed")
    return {"profile": JAX_PROFILE, "group": selected, "image_id": image,
            "environment_sha256": JAX_ENVIRONMENT_SHA256,
            "dependency_lock_sha256": record["dependencies"]["sha256"],
            "installed_packages_sha256": record["installed_packages"]["sha256"],
            "data_lock_sha256": record["data"]["sha256"], "data_assets": record["data"]["assets"],
            "base_image_id": record["base"]["image_id"],
            **{key: variant[key] for key in ("resource_profile", "resources", "runtime_policy",
                                            "sitecustomize_sha256", "precision_override")}}


def validate_jax_task(task, evaluation):
    environment = jax_environment(evaluation["execution"]["image"])
    if jax_task_group(task["id"], task.get("requirements")) != environment["group"]:
        raise ValueError("Task and requirements are outside the exact prepared JAX cohort")
    if evaluation["execution"].get("resource_profile") != environment["resource_profile"]:
        raise ValueError("Prepared JAX requires the exact explicit resource profile")
    return environment
