#!/usr/bin/env python3
"""Prepare seven ADAS MGSM templates and plans; never execute or admit a run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from arena.frameworks.drivers.adas_mgsm_gateway import (
    DATASET_SHA256, EVALUATIONS, IDENTITY, MODELS, REQUESTS, SDK_TIMEOUT,
    WALL_SECONDS, digest, load_dataset, write_json,
)


def templates(root, dataset):
    return [{"id": IDENTITY + "-" + model.replace(".", "-"),
             "name": "ADAS MGSM native pilot · " + model, "framework": IDENTITY,
             "profile": "mgsm-cpu-pilot", "model": model, "status": "ready", "blocked_reason": None,
             "resources": {"cpus": 4, "memory_mb": 8192, "evaluation_slots": 1, "pids": 512},
             "containment": "cgroup-v2", "evaluation_concurrency_verified": True,
             "spec": {"schema": "arena.native-run/1", "framework": IDENTITY,
                      "source_dir": str(root / "sources/adas"), "output_dir": "{output_dir}",
                      "timeout_seconds": WALL_SECONDS, "environment_names": ["OPENAI_API_KEY"],
                      "request": {"python": str(root / "envs/adas-gateway/bin/python"),
                                  "profile": "mgsm-cpu-pilot", "arguments": ["--model", model],
                                  "inputs": {"arena-inputs/mgsm-adas-pilot-v1.json": str(dataset)}}}}
            for model in MODELS]


def prepare(root, destination, dataset_source):
    from arena.control import validate_config
    from arena.frameworks.runtime import prepare_plan
    if not root.is_absolute() or not destination.is_absolute() or destination.exists():
        raise ValueError("Use an absolute root and a new absolute destination")
    data = load_dataset(dataset_source)
    destination.mkdir(parents=True, mode=0o750)
    dataset = destination / "mgsm-adas-pilot-v1.json"
    shutil.copyfile(dataset_source, dataset)
    items = templates(root, dataset)
    validate_config({"schema": "arena.control/1", "state_dir": str(root / "control"),
                     "cgroup_root": "/sys/fs/cgroup/arena-workers",
                     "limits": {"cpus": 96, "memory_mb": 307200, "evaluation_slots": 32,
                                "max_active": 4, "max_queued": 2048, "max_runs_per_key": 2048,
                                "max_reserved_seconds_per_key": 6048000}, "templates": items})
    records = []
    for item in items:
        plan = prepare_plan({**item["spec"], "output_dir": str(root / "runs" / (item["id"] + "-plan-only"))})
        write_json(destination / (item["model"] + ".plan.json"), plan)
        records.append({"model": item["model"], "plan_sha256": plan["sha256"], "source": plan["source"]})
    write_json(destination / "templates.json", items)
    proof = {"schema": "arena.adas-mgsm-preparation/1", "framework": IDENTITY, "plans": records,
             "dataset_sha256": DATASET_SHA256, "selection": data["selection"], "metric": data["metric"],
             "budgets": {"request_attempts": REQUESTS, "evaluator_invocations": EVALUATIONS,
                         "sdk_timeout_seconds": SDK_TIMEOUT, "sdk_max_retries": 0,
                         "meta_generations": 1, "initial_strategies": 7, "debug_max": 1,
                         "outer_wall_seconds": WALL_SECONDS, "native_workers": 1},
             "helper_sha256": digest((ROOT / "src/arena/frameworks/drivers/adas_mgsm_gateway.py").read_bytes()),
             "model_calls": 0, "admitted": False, "research_executed": False,
             "canonical_evaluation": False, "generated_code_is_sandboxed": False}
    write_json(destination / "preparation.json", proof)
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", type=Path, default=Path("/srv/arena"))
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=ROOT / "registry/datasets/mgsm-adas-pilot-v1.json")
    args = parser.parse_args()
    proof = prepare(args.root, args.destination, args.dataset)
    print(json.dumps({"templates": len(proof["plans"]), "model_calls": 0, "admitted": False}))


if __name__ == "__main__":
    main()
