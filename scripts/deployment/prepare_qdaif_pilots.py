#!/usr/bin/env python3
"""Create seven pure QDAIF poetry plans; never submit or call models."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from arena.frameworks.drivers.qdaif_poetry_gateway import ENGINE, PROFILE, MODELS, preparation
from arena.frameworks.drivers.qdaif_gateway_transport import write_json


def template(root, model, destination):
    if model not in MODELS:
        raise ValueError("Unknown model")
    return {"id": ENGINE + "-" + model.replace(".", "-"), "name": "QDAIF native poetry · " + model,
        "framework": ENGINE, "profile": PROFILE, "model": model, "status": "blocked",
        "blocked_reason": "Awaiting operator review/deployment; only offline native protocol conformance verified.",
        "resources": {"cpus": 2, "memory_mb": 4096, "evaluation_slots": 1, "pids": 256},
        "containment": "cgroup-v2", "evaluation_concurrency_verified": True,
        "spec": {"schema": "arena.native-run/1", "framework": ENGINE,
            "source_dir": str(root / "sources/qdaif"), "output_dir": "{output_dir}", "timeout_seconds": 2400,
            "environment_names": ["OPENAI_API_KEY"],
            "request": {"python": str(root / "envs" / ENGINE / "bin/python"), "profile": PROFILE,
                "arguments": ["--model", model],
                "inputs": {"arena-inputs/qdaif-preparation.json": str(destination / "preparation.json"),
                    "arena-inputs/qdaif-dependencies.txt": str(destination / "dependencies.txt"),
                    "arena-inputs/qdaif-constraints.txt": str(destination / "constraints.txt")}}}}


def prepare(root, destination, freeze, constraints):
    from arena.frameworks.runtime import prepare_plan
    if not root.is_absolute() or not destination.is_absolute() or destination.exists():
        raise ValueError("Absolute root and new absolute destination required")
    proof = preparation(root / "sources/qdaif", freeze, constraints)
    destination.mkdir(parents=True)
    write_json(destination / "preparation.json", proof)
    shutil.copyfile(freeze, destination / "dependencies.txt")
    shutil.copyfile(constraints, destination / "constraints.txt")
    rows, checks = [], []
    for model in MODELS:
        row = template(root, model, destination)
        plan = prepare_plan({**row["spec"], "output_dir": str(root / "runs" / (row["id"] + "-plan-only"))})
        write_json(destination / (row["id"] + ".plan.json"), plan)
        rows.append(row)
        checks.append({"model": model, "plan_sha256": plan["sha256"], "source": plan["source"]})
    write_json(destination / "templates.json", rows)
    write_json(destination / "plan-checks.json", {"checks": checks, "model_calls": 0, "runs_admitted": 0})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", type=Path, default=Path("/srv/arena"))
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--dependencies", type=Path, required=True)
    parser.add_argument("--constraints", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps({"templates": len(prepare(args.root, args.destination, args.dependencies, args.constraints)), "model_calls": 0}))


if __name__ == "__main__":
    main()
