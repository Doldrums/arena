#!/usr/bin/env python3
"""Prepare reviewed private SCiEL catalog templates without submitting any run.

Only seed measurements bound to the current library and selected Docker image
qualify. Every other catalog task remains explicitly pending in the inventory.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from arena.engine_policy import checked_native_config
from arena.evaluation_resources import worker_resources
from arena.frameworks.sciel_catalog_jax import JAX_GROUPS, JAX_PROFILE, jax_environment, jax_task_group
from arena.frameworks.sciel_catalog_torch import (
    TORCH_GROUPS, TORCH_PROFILE, torch_environment, torch_task_group, validate_torch_seed_receipt,
)
from arena.control_config import validate_config as validate_control
from arena.frameworks.sciel_catalog_evaluate import create_task, validate_config as validate_bridge
from arena.frameworks.sciel_catalog_profile import SCIENCE_PROFILE, science_environment
from arena.frameworks.runtime import verify_source
from arena.registry import get_catalog
from arena.release_deployment import load_manifest, materialize_template
from arena.task_library import verify_task_library

COMMIT = "a6c0d215b61ee52dae608a6390c9f2c6d2f2554d"
VERSION = "0.2.0+arena.a6c0d215.worker1"
RESOURCES = {"cpus": 4, "memory_mb": 8192, "evaluation_slots": 1, "pids": 512}
GATEWAY = "http://127.0.0.1:8789/v1"
SEED_FIELDS = ("status", "raw_score", "fitness", "validity", "wall_seconds", "candidate_sha256",
               "evaluator_sha256", "problem_sha256", "task_source", "receipt_path")


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def exact_path(path):
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts or path.resolve() != path:
        raise ValueError("Operator paths must be absolute and must not traverse symlinks")
    return path


def read_json(path, maximum=32 * 1024 * 1024):
    path = exact_path(path)
    if not path.is_file() or path.stat().st_size > maximum:
        raise ValueError("Expected a bounded regular JSON file")
    raw = path.read_bytes()
    if len(raw) > maximum:
        raise ValueError("JSON input exceeds the size limit")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON input field")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique)
    if type(value) is not dict:
        raise ValueError("Expected a JSON object")
    return value, sha(raw)


def write(path, value):
    path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(encoded(value))
    path.chmod(0o640)


def preflight_records(manifest, catalog, identity):
    if (manifest.get("schema") != "arena.sciel-catalog-preflight/1"
            or manifest.get("task_source") != identity or manifest.get("model_calls") != 0
            or type(manifest.get("timeout_seconds")) is not int
            or not 1 <= manifest["timeout_seconds"] <= 600):
        raise ValueError("Preflight must describe this exact task library and CPU seed profile")
    if manifest.get("group") == "science":
        if (manifest.get("profile") != SCIENCE_PROFILE
                or manifest.get("prepared_environment") != science_environment(manifest.get("image"))):
            raise ValueError("Preflight differs from the pinned prepared science environment")
    elif manifest.get("group") in JAX_GROUPS:
        environment = jax_environment(manifest.get("image"), manifest["group"])
        if (manifest.get("profile") != JAX_PROFILE
                or manifest.get("prepared_environment") != environment
                or manifest.get("resource_profile") != environment["resource_profile"]):
            raise ValueError("Preflight differs from the pinned prepared JAX environment and resources")
    elif manifest.get("group") in TORCH_GROUPS:
        environment = torch_environment(manifest.get("image"), manifest["group"])
        if (manifest.get("profile") != TORCH_PROFILE
                or manifest.get("prepared_environment") != environment
                or manifest.get("resource_profile") != environment["resource_profile"]):
            raise ValueError("Preflight differs from the pinned prepared Torch environment and resources")
    elif any(key in manifest for key in ("profile", "prepared_environment", "resource_profile")):
        raise ValueError("Prepared environment binding requires the explicit science, JAX or Torch group")
    if manifest.get("group") not in (*JAX_GROUPS, *TORCH_GROUPS) and "resource_profile" in manifest:
        raise ValueError("Resource profile requires the exact prepared JAX or Torch group")
    rows = manifest.get("tasks")
    if type(rows) is not list or any(type(row) is not dict for row in rows):
        raise ValueError("Preflight task inventory is missing")
    tasks = {task["id"]: task for task in catalog["tasks"]}
    ids = [row.get("task_id") for row in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(tasks):
        raise ValueError("Preflight must contain every current catalog task exactly once")
    for row in rows:
        task = tasks[row["task_id"]]
        if any(row.get(key) != task[key] for key in ("family", "protocol", "metric", "direction", "requirements")):
            raise ValueError("Preflight task metadata differs from the current catalog")
        if (manifest.get("group") in JAX_GROUPS and row.get("status") == "seed_verified"
                and jax_task_group(task["id"], task["requirements"]) != manifest["group"]):
            raise ValueError("Verified seed is outside the exact prepared JAX cohort")
        if (manifest.get("group") in TORCH_GROUPS and row.get("status") == "seed_verified"
                and torch_task_group(task["id"], task["requirements"]) != manifest["group"]):
            raise ValueError("Verified seed is outside the exact prepared Torch cohort")
    return tasks, rows


def verified_seed(row, manifest, manifest_path, verified):
    """A manifest status alone cannot establish runtime evidence."""
    summary = row.get("seed_evaluation")
    if type(summary) is not dict or set(summary) != set(SEED_FIELDS):
        raise ValueError("Verified seed is missing its canonical receipt fields")
    path = exact_path(summary["receipt_path"])
    if path != manifest_path.parent / row["task_id"] / "receipt.json":
        raise ValueError("Seed receipt must belong to this preflight task output")
    receipt, digest = read_json(path)
    if digest != row.get("receipt_sha256") or any(summary[key] != receipt.get(key) for key in SEED_FIELDS):
        raise ValueError("Seed receipt bytes differ from the preflight evidence")
    task = verified["task"]
    expected = {"schema": "arena.evaluation/1", "task_id": task["id"],
                "direction": task["direction"], "metric": task["metric"], "protocol": task["protocol"],
                "status": "completed", "validity": True,
                "execution": {"kind": "docker", "image": manifest["image"], "python": "python"},
                "candidate_sha256": sha(verified["seed"]), "task_source": verified["source"],
                "problem_sha256": verified["problem_sha256"], "evaluator_sha256": verified["evaluator_sha256"]}
    if manifest.get("group") in JAX_GROUPS:
        expected["execution"]["resource_profile"] = jax_environment(
            manifest["image"], manifest["group"])["resource_profile"]
    if manifest.get("group") in TORCH_GROUPS:
        expected["execution"]["resource_profile"] = torch_environment(
            manifest["image"], manifest["group"])["resource_profile"]
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise ValueError("Seed receipt does not match the exact candidate, evaluator and Docker image")
    if manifest.get("group") in TORCH_GROUPS:
        validate_torch_seed_receipt(receipt, path.parent)
    raw, fitness = receipt.get("raw_score"), receipt.get("fitness")
    if (any(type(value) not in (int, float) or not math.isfinite(value) for value in (raw, fitness))
            or fitness != (raw if task["direction"] == "maximize" else -raw)):
        raise ValueError("Seed receipt has inconsistent raw and maximizing fitness values")
    return fitness, digest


def native_configuration(task, model, campaign, slug):
    return {
        "task": "arena/" + task["id"], "budget": 16, "max_iterations": 32, "random_seed": 0,
        "num_islands": 3, "pop_cap": 12, "archive_size": 12, "grid_bins": 10,
        "inflight_cap": 1, "dup_cap": 4, "backstop_k": 4,
        "schedule_policy": "sh", "milestone_fracs": [0.5, 0.75],
        "op_temperature": 0.5, "op_floor": 0.05, "op_window": 50,
        "selection_floor": 0.001, "tau_floor": 0.001, "reward_w_pop": 1.0, "reward_w_isl": 1.0,
        "base_temp": 0.7, "bet_enabled": False, "confirm_records": True, "checkpoint_on_milestone": True,
        "embed_grid": False, "embed_niche": False,
        "parallel_search": {"enabled": True, "workers": 1, "host_llm_slots": 2, "provider_slots": 2,
            "host_evaluator_slots": 1, "capacity_dir": f"/srv/arena/runs/{campaign}/{slug}/capacity",
            "max_inflight_per_island": 1, "max_inflight_per_parent": 1, "portfolio_schedule": "blocking"},
        "candidate_novelty": {"enabled": True, "max_resamples": 1, "neighbors": 3, "output_repeats": False},
        "research": {"enabled": True, "reflection_interval": 3, "max_aux_calls": 4, "max_experiments": 48},
        "wandb": {"enabled": False},
        "llm": {"models": [model], "weights": [1.0], "api_base": GATEWAY,
            "api_key_env": "OPENAI_API_KEY", "max_retries": 1, "timeout": 300, "max_tokens": 8192,
            "model_capabilities": {model: {"temperature": False}}},
    }


def prepare(*, tasks_root, config_destination, native_tasks, preflight_manifest,
            deployment, approval, campaign, python, model="gpt-5.5", exclude_tasks=(), release_version=None):
    paths = [exact_path(path) for path in (tasks_root, config_destination, native_tasks,
                                         preflight_manifest, deployment, approval)]
    tasks_root, config_destination, native_tasks, preflight_manifest, deployment, approval = paths
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", campaign):
        raise ValueError("Campaign must be a short identifier")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", model) or "astra" in model.lower():
        raise ValueError("Choose an explicit non-Astra model ID verified on the gateway")
    python = Path(python)
    if not python.is_absolute() or not python.is_file() or not os.access(python, os.X_OK):
        raise ValueError("Python must be the executable Arena worker interpreter")
    for destination in (config_destination, native_tasks):
        if destination.exists() or any(destination.is_relative_to(root) or root.is_relative_to(destination)
            for root in (tasks_root, preflight_manifest.parent)):
            raise ValueError("Campaign destinations must be new and separate from source/evidence trees")
    if config_destination.is_relative_to(native_tasks) or native_tasks.is_relative_to(config_destination):
        raise ValueError("Configuration and native tasks must use separate directories")
    manifest, deployment_sha = load_manifest(deployment)
    approved, approved_sha = load_manifest(approval)
    if release_version is not None and (type(release_version) is not str
            or not re.fullmatch(r"0\.2\.0\+arena\." + re.escape(COMMIT[:8]) + r"\.[A-Za-z0-9.-]+", release_version)):
        raise ValueError("Explicit release version must identify a build of the pinned SCiEL 0.2.0 source")
    expected_version = VERSION if release_version is None else release_version
    if (approved != manifest or approved_sha != deployment_sha or approval.name != deployment_sha + ".json"
            or manifest["release"] != {"schema": "arena.release/1", "system": "sciel", "version": expected_version}
            or manifest["binding"]["repository"]["commit"] != COMMIT):
        raise ValueError("Use the exact approved SCiEL 0.2.0 private deployment")
    verify_source(Path(manifest["source"]["path"]), COMMIT)
    catalog = get_catalog()
    source = next(item for item in catalog["sources"] if item["id"] == "arena-tasks")
    identity = verify_task_library(tasks_root, source)
    preflight, preflight_sha = read_json(preflight_manifest)
    tasks, rows = preflight_records(preflight, catalog, identity)
    resources = worker_resources(preflight.get("resource_profile"))
    if type(exclude_tasks) not in (list, tuple, set) or any(type(task) is not str for task in exclude_tasks):
        raise ValueError("Excluded task IDs must be an explicit collection of strings")
    excluded = set(exclude_tasks)
    if not excluded <= set(tasks):
        raise ValueError("An excluded task is absent from the current catalog")
    config_destination.mkdir(mode=0o750, parents=True)
    native_tasks.mkdir(mode=0o750, parents=True)
    templates, inventory = [], []
    for row in rows:
        record = {**row, "preflight_status": row["status"]}
        if row["task_id"] in excluded:
            record.update(status="excluded", reason="Excluded by the explicit operator task list.")
            inventory.append(record)
            continue
        if row["status"] != "seed_verified":
            record.update(status="pending", reason=row.get("reason") or row["status"])
            inventory.append(record)
            continue
        task = tasks[row["task_id"]]
        slug = sha(encoded({"campaign": campaign, "task": task["id"], "model": model,
                           "release": manifest["release"]}))[:20]
        task_root = native_tasks / slug
        config_path = config_destination / slug / "sciel.json"
        bridge = {"schema": "arena.sciel-catalog-config/1",
            "evaluation": {"schema": "arena.evaluation-config/1", "task_id": task["id"],
                "tasks_dir": str(tasks_root), "timeout_seconds": preflight["timeout_seconds"],
                "receipts_dir": f"/srv/arena/runs/{campaign}/{slug}/canonical-evaluations",
                "execution": {"kind": "docker", "image": preflight["image"], "python": "python",
                              "require_control_cgroup": True}},
            "fitness": {"kind": "atan", "scale": 1, "basis": "Pending exact verified seed binding"},
            "confirmation": {"stochastic": True, "samples": 3}}
        if preflight.get("group") == "science":
            bridge["evaluation"]["profile"] = SCIENCE_PROFILE
        if preflight.get("group") in JAX_GROUPS:
            bridge["evaluation"]["profile"] = JAX_PROFILE
            bridge["evaluation"]["execution"]["resource_profile"] = preflight["resource_profile"]
        if preflight.get("group") in TORCH_GROUPS:
            bridge["evaluation"]["profile"] = TORCH_PROFILE
            bridge["evaluation"]["execution"]["resource_profile"] = preflight["resource_profile"]
        try:
            verified = validate_bridge(bridge)
        except ValueError as exc:
            record.update(status="pending", reason="Native task integration: " + str(exc)[:400])
            inventory.append(record)
            continue
        fitness, receipt_sha = verified_seed(row, preflight, preflight_manifest, verified)
        bridge["fitness"] = {"kind": "atan", "scale": max(1, abs(fitness)),
            "basis": "max(1, abs(canonical seed fitness)); seed receipt sha256=" + receipt_sha}
        try:
            generated = create_task(bridge, task_root / "arena" / task["id"])
        except ValueError as exc:
            record.update(status="pending", reason="Native task integration: " + str(exc)[:400])
            inventory.append(record)
            continue
        for path in (task_root, *task_root.rglob("*")):
            path.chmod(0o750 if path.is_dir() else 0o640)
        config = native_configuration(task, model, campaign, slug)
        write(config_path, config)
        checked_native_config(config_path.read_bytes(), model,
                              Path("/srv/arena/control/runs") / ("0" * 32) / "artifacts", GATEWAY)
        template = materialize_template(deployment, approval, template_id="sciel-cat-" + slug,
            name="SCiEL · " + task["name"][:180], model=model, python=python, config=config_path,
            tasks_root=task_root, resources=resources, timeout_seconds=3600,
            seed=0, budget=16, environment_names=())
        template["spec"]["request"].update(campaign=campaign, arm=slug)
        write(config_path.parent / "template.json", template)
        templates.append(template)
        record.update(status="prepared", reason=None, template_id=template["id"],
            model=model, batch_id=campaign, configuration_sha256=sha(config_path.read_bytes()),
            task_configuration_sha256=generated["configuration_sha256"], fitness=bridge["fitness"],
            native_runtime_conformance="pending_first_run", research_executed=False)
        inventory.append(record)
    if verify_task_library(tasks_root, source) != identity:
        raise ValueError("Canonical task library changed during campaign preparation")
    validate_control({"schema": "arena.control/1", "state_dir": "/private-campaign-validation",
        "cgroup_root": "/sys/fs/cgroup/private-campaign-validation",
        "limits": {**{key: resources[key] for key in ("cpus", "memory_mb", "evaluation_slots")}, "max_active": 1,
            "max_queued": 1, "max_runs_per_key": 1, "max_reserved_seconds_per_key": 3600},
        "templates": templates})
    result = {"schema": "arena.sciel-catalog-campaign/1", "campaign": campaign, "model": model,
        "release": manifest["release"], "deployment_sha256": deployment_sha,
        "task_source": identity, "canonical_image": preflight["image"],
        "preflight_manifest_sha256": preflight_sha, "preflight_finished": "finished_at" in preflight,
        "counts": dict(Counter(row["status"] for row in inventory)), "tasks": inventory,
        "budgets": {"full_evaluations": 16, "max_iterations": 32, "wall_seconds": 3600,
                    "confirmation_samples": 3, "max_aux_calls": 4, "max_experiments": 48},
        "resources_per_run": resources, "model_calls": 0, "canonical_evaluator_calls": 0,
        "research_executed": False, "queue_mutated": False,
        "scope": "Seed-verified task integration; benchmark reproduction and research outcomes require run evidence.",
        "score_semantics": "Raw metrics and canonical signed fitness stay in receipts; atan scales search only.",
        "storage_profile": "Explicit code-length grid; learned descriptors and learned niches disabled."}
    if preflight.get("group") == "science":
        result.update(preflight_group="science", prepared_environment=preflight["prepared_environment"])
    if preflight.get("group") in JAX_GROUPS:
        result.update(preflight_group=preflight["group"], profile=JAX_PROFILE,
                      resource_profile=preflight["resource_profile"],
                      prepared_environment=preflight["prepared_environment"])
    if preflight.get("group") in TORCH_GROUPS:
        result.update(preflight_group=preflight["group"], profile=TORCH_PROFILE,
                      resource_profile=preflight["resource_profile"],
                      prepared_environment=preflight["prepared_environment"])
    write(config_destination / "templates.json", templates)
    write(config_destination / "campaign-inventory.json", result)
    return {"destination": str(config_destination), "campaign": campaign, "counts": result["counts"],
            "model_calls": 0, "queue_mutated": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ("tasks-root", "config-destination", "native-tasks", "preflight-manifest",
                 "deployment", "approval", "python"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--release-version", help="Explicit approved build of the same pinned SCiEL 0.2.0 source")
    parser.add_argument("--exclude-task", dest="exclude_tasks", action="append", default=[])
    args = parser.parse_args(argv)
    print(json.dumps(prepare(**vars(args))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
