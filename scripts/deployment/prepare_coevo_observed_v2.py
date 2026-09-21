#!/usr/bin/env python3
"""Prepare distinct CoEvo v2 templates and pure plans; never admit or run."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
IDENTITY = "coevo-observed-v2"


def base_generator():
    path = Path(__file__).with_name("prepare_additional_program_pilots.py")
    spec = importlib.util.spec_from_file_location("arena_coevo_v1_preparation", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def templates(root, directory, recipe):
    generator = base_generator()
    result = []
    for model in generator.MODELS:
        item = generator.template(root, "coevo", model, directory, recipe)
        item["id"] = "program-pilot-coevo-observed-v2-" + model.replace(".", "-")
        item["name"] = recipe["name"]
        item["framework"] = item["spec"]["framework"] = IDENTITY
        # Source, interpreter, task, model, budget and native arguments remain
        # those of CoEvo. Only recipe/driver/artifact identity is versioned.
        result.append(item)
    return result


def prepare(root):
    from arena.control import validate_config
    from arena.frameworks.recipes import load_recipes
    from arena.frameworks.runtime import prepare_plan, verify_source
    from arena.frameworks.drivers.cpu_program_gateway import verify_embedding_cache
    from arena.frameworks.drivers.coevo_history import verify_sources
    recipe = load_recipes()[IDENTITY]
    source = root / "sources/coevo"
    provenance = verify_source(source, recipe["repository"]["commit"])
    verify_embedding_cache(root / "caches/coevo-hf", root / "caches/coevo-hf/manifest.json")
    dependency = root / "envs/coevo/lib/python3.11/site-packages/evotoolkit"
    evidence = verify_sources(source, dependency)
    freeze = root / "configs/pilot-dependencies-coevo.txt"
    if not freeze.is_file(): raise ValueError("Prepared CoEvo dependency freeze is required")
    directory = root / "configs/program-pilots-20260921-coevo-observed-v2"
    directory.mkdir(exist_ok=False)
    items = templates(root, directory, recipe)
    plans = []
    for item in items:
        plan = prepare_plan({**item["spec"], "output_dir": str(root / "runs" / (item["id"] + "-plan-only"))})
        with (directory / (item["model"] + "-plan.json")).open("x") as stream:
            json.dump(plan, stream, indent=2, allow_nan=False); stream.write("\n")
        plans.append({"model": item["model"], "plan_sha256": plan["sha256"]})
    validate_config({"schema": "arena.control/1", "state_dir": str(root / "control"),
                     "cgroup_root": "/sys/fs/cgroup/arena-workers",
                     "limits": {"cpus": 96, "memory_mb": 307200, "evaluation_slots": 32, "max_active": 8,
                                "max_queued": 2048, "max_runs_per_key": 2048, "max_reserved_seconds_per_key": 6048000},
                     "templates": items})
    for name, value in (("templates.json", items), ("preparation.json", {
            "schema": "arena.native-pilot-preparation/1", "engine": IDENTITY,
            "participant": "coevo", "source": provenance, "observation_source": evidence,
            "dependency_freeze_sha256": hashlib.sha256(freeze.read_bytes()).hexdigest(),
            "configurations": plans, "model_runs_performed": False, "runtime_readiness": "not_verified",
            "canonical_evaluation": False, "native_state_modified": False,
            "accounting": "Save sequence and distinct registered records are not physical evaluations or model calls."})):
        with (directory / name).open("x") as stream:
            json.dump(value, stream, indent=2, allow_nan=False); stream.write("\n")
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", type=Path, default=Path("/srv/arena"))
    args = parser.parse_args()
    if not args.root.is_absolute(): parser.error("root must be absolute")
    print(prepare(args.root))


if __name__ == "__main__": main()
