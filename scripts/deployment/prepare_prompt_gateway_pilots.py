#!/usr/bin/env python3
"""Prepare exact-model GEPA/MIPROv2 templates with immutable public-data inputs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from arena.frameworks.drivers._gsm8k_pilot import MODELS, DATASET_SHA256, load_dataset, write_json

ENGINES = {"gepa-gateway-gsm8k": "gepa", "miprov2-gateway-gsm8k": "mipro"}


def template(root, framework, model, dataset):
    if framework not in ENGINES or model not in MODELS:
        raise ValueError("Choose a reviewed framework and exact gateway model")
    native = ENGINES[framework]
    return {"id": framework + "-" + model.replace(".", "-"), "name": native + " GSM8K native pilot · " + model,
            "framework": framework, "profile": "gsm8k-prompt-pilot", "model": model,
            "status": "ready", "blocked_reason": None,
            "resources": {"cpus": 4, "memory_mb": 8192, "evaluation_slots": 1, "pids": 512},
            "containment": "cgroup-v2", "evaluation_concurrency_verified": True,
            "spec": {"schema": "arena.native-run/1", "framework": framework,
                     "source_dir": str(root / "sources" / native), "output_dir": "{output_dir}",
                     "timeout_seconds": 2400, "environment_names": ["OPENAI_API_KEY"],
                     "request": {"python": str(root / "envs" / (native + "-gateway") / "bin/python"),
                                 "profile": "gsm8k-prompt-pilot", "arguments": ["--model", model],
                                 "inputs": {"arena-inputs/gsm8k-prompt-pilot-v1.json": str(dataset)}}}}


def prepare(root, destination, dataset_source):
    from arena.frameworks.runtime import prepare_plan
    if not root.is_absolute() or not destination.is_absolute() or destination.exists():
        raise ValueError("Root must be absolute and destination must be new and absolute")
    dataset = load_dataset(dataset_source)
    destination.mkdir(parents=True, mode=0o750)
    dataset_path = destination / "gsm8k-prompt-pilot-v1.json"
    shutil.copyfile(dataset_source, dataset_path)
    templates, records = [], []
    for framework in ENGINES:
        for model in MODELS:
            item = template(root, framework, model, dataset_path)
            spec = {**item["spec"], "output_dir": str(root / "runs" / (item["id"] + "-preparation-only"))}
            plan = prepare_plan(spec)
            write_json(destination / (item["id"] + ".plan.json"), plan)
            templates.append(item)
            records.append({"template_id": item["id"], "model": model, "source": plan["source"], "plan_sha256": plan["sha256"]})
    write_json(destination / "templates.json", templates)
    proof = {"schema": "arena.prompt-gateway-preparation/1", "records": records,
             "dataset_sha256": DATASET_SHA256, "dataset_commit": dataset["commit"],
             "splits": dataset["selection"], "metric": dataset["metric"],
             "concurrency_basis": "GEPA callable adapter evaluates serially; DSPy num_threads1; the shared transport lock serializes all actual SDK requests, including n>1 draws.",
             "budgets": {"gepa": "Native max_metric_calls24, reflection batch3; complete iterations can overshoot.",
                         "miprov2": "Native candidates3, Optuna trials3, bootstrap1/labeled1 demos, no minibatching. Three demo sets retain the native zero-shot, labeled and bootstrapped branches; these and proposal/default evaluation are additional calls.",
                         "common": "Gateway admission128 requests; SDK retries0; outertimeout2400s. Heldout seed/selected evaluations happen only after optimization."},
             "model_calls": 0, "research_executed": False, "runs_admitted": 0, "canonical_evaluation": False,
             "provider_controls_unenforced": ["temperature", "max_tokens", "top_p"]}
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
