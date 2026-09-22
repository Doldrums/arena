#!/usr/bin/env python3
"""Inventory every catalog task and optionally check CPU seeds in Docker.

This does not call a model or admit a research run. A successful seed check is
runtime evidence for this image and library, not benchmark reproduction evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from arena.frameworks.sciel_catalog_jax import JAX_GROUPS, JAX_PROFILE, jax_environment, jax_task_group
from arena.frameworks.sciel_catalog_profile import (
    SCIENCE_PROFILE, requirement_group, science_environment, supports_science_task,
)


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def write(path, value):
    temporary = path.with_suffix(path.suffix + ".pending")
    temporary.write_bytes(encode(value))
    temporary.chmod(0o600)
    temporary.replace(path)


def inventory(tasks, root, group="all", image=None):
    if group not in {"base", "extended", "all", "science", *JAX_GROUPS}:
        raise ValueError("Choose an explicit supported CPU seed group")
    if group in JAX_GROUPS:
        jax_environment(image, group)
    if group == "science":
        science_environment(image)
    rows = []
    for task in tasks:
        seed = root / "suite" / task["id"] / "initial_program.py"
        required_group = requirement_group(task["requirements"])
        if group == "science" and supports_science_task(task["id"], task["requirements"]):
            required_group = "science"
        if group in JAX_GROUPS:
            required_group = jax_task_group(task["id"], task["requirements"]) or required_group
        if not task["executable"]:
            status, reason = "evaluation_integration_pending", "No executable evaluator definition."
        elif not seed.is_file() or seed.is_symlink():
            status, reason = "runtime_integration_pending", "Requires a non-Python candidate profile or seed."
        elif required_group is None:
            status, reason = "environment_preparation_pending", "Requires a separately prepared evaluation environment."
        elif group != "all" and group != required_group:
            status = "seed_check_deferred"
            reason = f"Seed check deferred to the {required_group} CPU profile."
        else:
            status, reason = "seed_check_pending", None
        rows.append({"task_id": task["id"], "family": task["family"],
                     "protocol": task["protocol"], "metric": task["metric"],
                     "direction": task["direction"], "requirements": task["requirements"],
                     "status": status, "reason": reason})
    return rows


def check_seed(row, *, root, output, image, timeout, group="all"):
    from arena.frameworks.evaluation import evaluate

    task_id = row["task_id"]
    config = {"schema": "arena.evaluation-config/1", "task_id": task_id,
              "tasks_dir": str(root), "timeout_seconds": timeout,
              "execution": {"kind": "docker", "image": image, "python": "python"}}
    if group == "science":
        science_environment(image)
        if not supports_science_task(task_id, row["requirements"]):
            raise ValueError("Task is outside the exact prepared science cohort")
        config["profile"] = SCIENCE_PROFILE
    if group in JAX_GROUPS:
        environment = jax_environment(image, group)
        if jax_task_group(task_id, row["requirements"]) != group:
            raise ValueError("Task is outside the exact prepared JAX cohort")
        config["profile"] = JAX_PROFILE
        config["execution"]["resource_profile"] = environment["resource_profile"]
    try:
        receipt = evaluate(config, root / "suite" / task_id / "initial_program.py", output / task_id)
        good = (receipt["status"] == "completed" and receipt["validity"] is True
                and receipt["fitness"] is not None)
        receipt_path = Path(receipt["receipt_path"])
        return {**row, "status": "seed_verified" if good else "seed_check_failed",
                "reason": None if good else "Seed evaluation: " + receipt["status"],
                "seed_evaluation": {key: receipt[key] for key in
                    ("status", "raw_score", "fitness", "validity", "wall_seconds", "candidate_sha256",
                     "evaluator_sha256", "problem_sha256", "task_source", "receipt_path")},
                "receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest()}
    except Exception as error:
        return {**row, "status": "seed_check_failed", "reason": type(error).__name__}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--execute-seeds", action="store_true")
    parser.add_argument("--group", choices=("base", "extended", "all", "science", *JAX_GROUPS), default="all",
                        help="Check one CPU dependency group; retain all other tasks in the inventory")
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= 16 or not 1 <= args.timeout <= 600:
        parser.error("Choose 1–16 seed workers and 1–600 seconds per evaluation")
    if (not args.output.is_absolute() or args.output.exists()
            or args.output.resolve() != args.output or args.tasks_root.resolve() != args.tasks_root):
        parser.error("Use a new absolute output directory and an exact task-library path")
    if args.output.is_relative_to(args.tasks_root):
        parser.error("Preflight output must be outside the immutable task library")
    from arena.registry import get_catalog
    from arena.task_library import verify_task_library
    from arena.frameworks.evaluation import validate_config

    catalog = get_catalog()
    source = next(s for s in catalog["sources"] if s["id"] == "arena-tasks")
    identity = verify_task_library(args.tasks_root, source)
    rows = inventory(catalog["tasks"], args.tasks_root, args.group, args.image)
    eligible = [row for row in rows if row["status"] == "seed_check_pending"]
    if not eligible:
        parser.error("No tasks match the prepared CPU profile")
    config = {"schema": "arena.evaluation-config/1", "task_id": eligible[0]["task_id"],
              "tasks_dir": str(args.tasks_root), "timeout_seconds": args.timeout,
              "execution": {"kind": "docker", "image": args.image, "python": "python"}}
    environment = jax_environment(args.image, args.group) if args.group in JAX_GROUPS else None
    if environment is not None:
        config["profile"] = JAX_PROFILE
        config["execution"]["resource_profile"] = environment["resource_profile"]
    validate_config(config)
    args.output.mkdir(mode=0o700, parents=True)
    manifest = {"schema": "arena.sciel-catalog-preflight/1", "created_at": time.time(),
                "task_source": identity, "image": args.image, "timeout_seconds": args.timeout,
                "seed_workers": args.workers, "group": args.group, "model_calls": 0, "tasks": rows}
    if args.group == "science":
        manifest.update(profile=SCIENCE_PROFILE, prepared_environment=science_environment(args.image))
    if environment is not None:
        manifest.update(profile=JAX_PROFILE, prepared_environment=environment,
                        resource_profile=environment["resource_profile"])
    path = args.output / "manifest.json"

    def save():
        manifest["counts"] = dict(Counter(row["status"] for row in rows))
        write(path, manifest)

    save()
    print(json.dumps({"output": str(path), "counts": manifest["counts"]}), flush=True)
    if args.execute_seeds:
        positions = {row["task_id"]: i for i, row in enumerate(rows)}
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            pending = [executor.submit(check_seed, row, root=args.tasks_root,
                       output=args.output, image=args.image, timeout=args.timeout, group=args.group) for row in eligible]
            for future in as_completed(pending):
                row = future.result()
                rows[positions[row["task_id"]]] = row
                save()
                print(json.dumps({"task_id": row["task_id"], "status": row["status"]}), flush=True)
    manifest["finished_at"] = time.time()
    if verify_task_library(args.tasks_root, source) != identity:
        raise ValueError("Task library changed during preflight")
    save()
    print(json.dumps({"output": str(path), "counts": manifest["counts"]}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
