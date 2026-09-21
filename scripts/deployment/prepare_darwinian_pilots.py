#!/usr/bin/env python3
"""Prepare inert Darwinian Evolver gateway templates; never submit or run them."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from arena.frameworks.drivers.darwinian_gateway import MODELS


def template(root, model):
    if model not in MODELS:
        raise ValueError("Use an exact reviewed model")
    return {"id": "darwinian-gateway-" + model.replace(".", "-"),
            "name": "Darwinian Evolver circle packing · " + model,
            "framework": "darwinian-evolver-gateway", "profile": "circle-packing-pilot",
            "model": model, "status": "ready", "blocked_reason": None,
            "resources": {"cpus": 4, "memory_mb": 8192, "evaluation_slots": 1, "pids": 512},
            "containment": "cgroup-v2", "evaluation_concurrency_verified": True,
            "spec": {"schema": "arena.native-run/1", "framework": "darwinian-evolver-gateway",
                     "source_dir": str(root / "sources/darwinian-evolver"), "output_dir": "{output_dir}",
                     "timeout_seconds": 2400, "environment_names": ["OPENAI_API_KEY"],
                     "request": {"python": str(root / "envs/darwinian-evolver/bin/python"),
                                 "profile": "circle-packing-pilot",
                                 "arguments": ["--model", model, "--iterations", "4"]}}}


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", type=Path, default=Path("/srv/arena"))
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    if not args.root.is_absolute() or not args.destination.is_absolute() or args.destination.exists():
        raise ValueError("Use absolute paths and a new destination")
    from arena.frameworks.runtime import prepare_plan
    args.destination.mkdir(parents=True, mode=0o750)
    templates, records = [], []
    for model in MODELS:
        item = template(args.root, model)
        plan = prepare_plan({**item["spec"], "output_dir": str(args.root / "runs" / (item["id"] + "-plan-only"))})
        (args.destination / (model + ".plan.json")).write_text(json.dumps(plan, indent=2) + "\n")
        templates.append(item)
        records.append({"model": model, "plan_sha256": plan["sha256"], "source": plan["source"]})
    (args.destination / "templates.json").write_text(json.dumps(templates, indent=2) + "\n")
    (args.destination / "preparation.json").write_text(json.dumps({
        "schema": "arena.darwinian-gateway-preparation/1", "records": records,
        "model_calls": 0, "research_executed": False, "canonical_evaluation": False,
        "native_evaluator": "Unchanged n=26 circle-packing evaluator and packaged seed",
        "native_search": "WeightedSamplingPopulation, ancestor learning log; one parent, one mutator and evaluator worker; four iterations",
        "limits": "4 CPU, 8 GiB, 512 PIDs, one evaluation slot, 2400-second outer deadline. Native function timeout is not a hostile-code sandbox.",
    }, indent=2) + "\n")
    print(json.dumps({"templates": len(templates), "destination": str(args.destination), "model_calls": 0}))


if __name__ == "__main__":
    main()
