#!/usr/bin/env python3
"""Create seven offline AFlow pilot plans; never submit or execute them."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from arena.frameworks.drivers.aflow_gateway_pilot import COMMIT, MAX_CALLS, MAX_EVALUATIONS, MODELS, SDK_TIMEOUT_SECONDS
from arena.frameworks.drivers._gsm8k_pilot import DATASET_SHA256, load_dataset, write_json


def template(root, model, dataset):
    if model not in MODELS:
        raise ValueError("Choose an exact gateway model")
    identifier = "aflow-gateway-gsm8k-v1-" + model.replace(".", "-")
    return {"id": identifier, "name": "AFlow GSM8K graph pilot · " + model,
        "framework": "aflow-gateway-gsm8k-v1", "profile": "gsm8k-graph-pilot-v1", "model": model,
        "status": "ready", "blocked_reason": None,
        "resources": {"cpus": 4, "memory_mb": 8192, "evaluation_slots": 1, "pids": 512},
        "containment": "cgroup-v2", "evaluation_concurrency_verified": True,
        "spec": {"schema": "arena.native-run/1", "framework": "aflow-gateway-gsm8k-v1",
            "source_dir": str(root / "sources/aflow"), "output_dir": "{output_dir}", "timeout_seconds": 2400,
            "environment_names": ["OPENAI_API_KEY"],
            "request": {"python": str(root / "envs/aflow-gateway/bin/python"),
                "profile": "gsm8k-graph-pilot-v1", "arguments": ["--model", model],
                "inputs": {"arena-inputs/gsm8k-prompt-pilot-v1.json": str(dataset)}}}}


def prepare(root, destination, dataset_source):
    from arena.frameworks.runtime import prepare_plan
    if not root.is_absolute() or not destination.is_absolute() or destination.exists():
        raise ValueError("Root and fresh destination must be absolute")
    dataset = load_dataset(dataset_source)
    destination.mkdir(parents=True, mode=0o750)
    data_path = destination / "gsm8k-prompt-pilot-v1.json"
    shutil.copyfile(dataset_source, data_path)
    templates, records = [], []
    for model in MODELS:
        item = template(root, model, data_path)
        plan = prepare_plan({**item["spec"], "output_dir": str(root / "runs" / (item["id"] + "-preparation-only"))})
        write_json(destination / (item["id"] + ".plan.json"), plan)
        templates.append(item)
        records.append({"template_id": item["id"], "model": model, "plan_sha256": plan["sha256"], "source": plan["source"]})
    proof = {"schema": "arena.aflow-gateway-preparation/1", "source_commit": COMMIT,
        "dataset_sha256": DATASET_SHA256, "dataset_source_commit": dataset["commit"],
        "optimization_validation": 8, "heldout": 8, "unused_train": 8,
        "native_rounds": 2, "validation_repeats": 1, "request_limit": MAX_CALLS,
        "sdk_timeout_seconds": SDK_TIMEOUT_SECONDS,
        "problem_evaluation_limit": MAX_EVALUATIONS, "evaluation_concurrency": 1,
        "concurrency_basis": "Native BaseBenchmark.evaluate_all_problems receives max_concurrent_tasks=1; SDK admissions serialized per native event loop.",
        "records": records, "model_calls": 0, "runs_admitted": 0, "research_executed": False,
        "canonical_evaluation": False, "paper_replication": False}
    write_json(destination / "templates.json", templates)
    write_json(destination / "preparation.json", proof)
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", type=Path, default=Path("/srv/arena"))
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=ROOT / "registry/datasets/gsm8k-prompt-pilot-v1.json")
    args = parser.parse_args()
    proof = prepare(args.root, args.destination, args.dataset)
    print(json.dumps({"templates": len(proof["records"]), "model_calls": 0, "destination": str(args.destination)}))


if __name__ == "__main__":
    main()
