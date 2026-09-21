#!/usr/bin/env python3
"""Prepare seven DGM native RunSpecs and plans; never run or admit research."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from arena.frameworks.drivers.dgm_pilot import MODELS, PROFILE, TASKS


def template(root, model):
    if model not in MODELS:
        raise ValueError("Select one reviewed exact gateway model")
    return {"id": "dgm-gateway-pilot-" + model.replace(".", "-"), "name": "DGM native Polyglot two-task pilot",
            "framework": "dgm", "profile": PROFILE, "model": model,
            "status": "blocked", "blocked_reason": "Await operator review and actual scoped Docker SDK conformance; no research has run.",
            "resources": {"cpus": 4, "memory_mb": 16384, "evaluation_slots": 2, "pids": 1024},
            "containment": "cgroup-v2", "evaluation_concurrency_verified": True,
            "spec": {"schema": "arena.native-run/1", "framework": "dgm", "source_dir": str(root / "sources/dgm"),
                     "output_dir": "{output_dir}", "timeout_seconds": 3600, "environment_names": ["OPENAI_API_KEY"],
                     "request": {"python": str(root / "envs/dgm/bin/python"), "benchmark": "polyglot",
                                 "profile": PROFILE, "model": model,
                                 "preparation_dir": str(root / "configs/dgm-pilot-20260921"),
                                 "dependency_freeze": str(root / "configs/pilot-dependencies-dgm.txt")}}}


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def prepare(root, destination):
    from arena.control import validate_config
    from arena.frameworks.runtime import prepare_plan
    if not root.is_absolute() or not destination.is_absolute():
        raise ValueError("Preparation paths must be absolute")
    destination.mkdir(parents=True, exist_ok=False, mode=0o700)
    templates, evidence = [], []
    for model in MODELS:
        item = template(root, model)
        plan = prepare_plan({**item["spec"], "output_dir": str(root / "runs" / (item["id"] + "-plan-only"))})
        write(destination / (model + "-plan.json"), plan)
        templates.append(item)
        evidence.append({"model": model, "plan_sha256": plan["sha256"],
                         "preparation_sha256": plan["command"]["preparation_sha256"]})
    validate_config({"schema": "arena.control/1", "state_dir": str(root / "control"),
                     "cgroup_root": "/sys/fs/cgroup/arena-workers",
                     "limits": {"cpus": 96, "memory_mb": 307200, "evaluation_slots": 32, "max_active": 4,
                                "max_queued": 2048, "max_runs_per_key": 2048, "max_reserved_seconds_per_key": 6048000},
                     "templates": templates})
    write(destination / "templates.json", templates)
    write(destination / "preparation.json", {"schema": "arena.dgm-runtime-preparation/1", "profile": PROFILE,
        "models": evidence, "task_ids": list(TASKS), "fresh_baseline_required": True,
        "native_generations": 1, "selfimprove_workers": 1, "baseline_evaluation_concurrency": 1,
        "native_child_evaluation_concurrency": 2, "timeout_seconds": 3600,
        "canonical_evaluation": False, "runtime_readiness": "not_verified", "model_calls": 0,
        "task_evaluations": 0, "optimizer_runs": 0,
        "driver_sha256": hashlib.sha256((REPO / "src/arena/frameworks/drivers/dgm_pilot.py").read_bytes()).hexdigest(),
        "limitations": ["Native retries/tool loops can exceed generation counts; the outer timeout is enforced.",
                        "Preinstalled image dependencies only; runtime Internet and PyPI are disabled.",
                        "A native zero baseline is valid only when both task reports completed without errors.",
                        "Operator must review images and SDK-through-proxy conformance before changing blocked templates to ready."]})
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", type=Path, default=Path("/srv/arena"))
    parser.add_argument("--destination", type=Path, default=Path("/srv/arena/configs/dgm-runtime-pilots-20260921"))
    args = parser.parse_args()
    print(prepare(args.root, args.destination))


if __name__ == "__main__":
    main()
