#!/usr/bin/env python3
"""Prepare seven versioned EoH-S guarded pilots; no research or admission."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from arena.frameworks.drivers.eohs_gateway_v2 import MODELS


def template(root, model, ca):
    if model not in MODELS:
        raise ValueError("An exact reviewed gateway model is required")
    return {"id": "eoh-s-gateway-v2-" + model.replace(".", "-"),
            "name": "EoH-S guarded native OBP set pilot · " + model,
            "framework": "eoh-s-gateway-v2", "profile": "gateway-obp-set-pilot-v2", "model": model,
            "status": "ready", "blocked_reason": None,
            "resources": {"cpus": 4, "memory_mb": 8192, "evaluation_slots": 1, "pids": 512},
            "containment": "cgroup-v2", "evaluation_concurrency_verified": True,
            "spec": {"schema": "arena.native-run/1", "framework": "eoh-s-gateway-v2",
                     "source_dir": str(root / "sources/eoh-s"), "output_dir": "{output_dir}",
                     "timeout_seconds": 2400, "environment_names": ["OPENAI_API_KEY"],
                     "request": {"python": str(root / "envs/eoh-s/bin/python"),
                                 "profile": "gateway-obp-set-pilot-v2",
                                 "arguments": ["--model", model, "--samples", "8", "--tls-ca", "arena-inputs/worker-ca.pem"],
                                 "inputs": {"arena-inputs/worker-ca.pem": str(ca)}}}}


def prepare(root, destination, ca):
    from arena.frameworks.runtime import prepare_plan
    from arena.control import validate_config
    if not all(p.is_absolute() for p in (root, destination, ca)):
        raise ValueError("Use absolute preparation paths")
    destination.mkdir(parents=True, exist_ok=False, mode=0o750)
    records, templates = [], []
    for model in MODELS:
        item = template(root, model, ca)
        plan = prepare_plan({**item["spec"], "output_dir": str(root / "runs" / (item["id"] + "-preparation-only"))})
        (destination / (item["id"] + ".plan.json")).write_text(json.dumps(plan, indent=2) + "\n")
        records.append({"id": item["id"], "plan_sha256": plan["sha256"], "source": plan["source"]})
        templates.append(item)
    validate_config({"schema": "arena.control/1", "state_dir": str(root / "control"),
                     "cgroup_root": "/sys/fs/cgroup/arena-workers",
                     "limits": {"cpus": 96, "memory_mb": 307200, "evaluation_slots": 32, "max_active": 4,
                                "max_queued": 2048, "max_runs_per_key": 2048, "max_reserved_seconds_per_key": 6048000},
                     "templates": templates})
    (destination / "templates.json").write_text(json.dumps(templates, indent=2) + "\n")
    proof = {"schema": "arena.eohs-guard-preparation/2", "records": records,
             "ca_sha256": hashlib.sha256(ca.read_bytes()).hexdigest(),
             "registered_sample_budget": 8, "generation_budget": 4, "population": 2,
             "canonical_evaluation": False, "model_calls": 0, "research_executed": False, "runs_admitted": 0,
             "limitation": "The guard records insufficient native population as partial exit75; it does not manufacture a complementary pair or ensure a successful search."}
    (destination / "preparation.json").write_text(json.dumps(proof, indent=2) + "\n")
    return proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", type=Path, default=Path("/srv/arena"))
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--ca-bundle", type=Path, default=Path("/etc/ssl/certs/arena-worker-bundle.pem"))
    args = parser.parse_args()
    print(json.dumps(prepare(args.root, args.destination, args.ca_bundle)))
