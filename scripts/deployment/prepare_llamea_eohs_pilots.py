#!/usr/bin/env python3
"""Prepare three pinned native CPU profiles across seven exact gateway models.

This command only validates sources and writes plans; it never queries a model
or calls an evaluator, and never changes a live control configuration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from arena.frameworks.drivers.base_gateway import MODELS

PROFILES = (("llamea-hpo", "gateway-bbob-pilot", "LLaMEA BBOB"),
            ("llamea-hpo", "gateway-bbob-hpo-pilot", "LLaMEA-HPO BBOB"),
            ("eoh-s", "gateway-obp-set-pilot", "EoH-S online bin packing set"))


def template(root, engine, profile, label, model, ca_bundle):
    if model not in MODELS or (engine, profile, label) not in PROFILES:
        raise ValueError("Unknown native pilot profile/model")
    arguments = ["--model", model]
    request = {"python": str(root / "envs" / engine / "bin/python"),
               "profile": profile, "arguments": arguments}
    if engine == "eoh-s":
        arguments += ["--samples", "8", "--tls-ca", "arena-inputs/worker-ca.pem"]
        request["inputs"] = {"arena-inputs/worker-ca.pem": str(ca_bundle)}
    else:
        arguments += ["--budget", "4"]
    return {"id": "cpu-" + engine + "-" + profile + "-" + model.replace(".", "-"),
            "name": label + " native pilot · " + model, "framework": engine,
            "profile": profile, "model": model, "status": "ready", "blocked_reason": None,
            "resources": {"cpus": 4, "memory_mb": 8192, "evaluation_slots": 1, "pids": 512},
            "containment": "cgroup-v2", "evaluation_concurrency_verified": True,
            "spec": {"schema": "arena.native-run/1", "framework": engine,
                     "source_dir": str(root / "sources" / engine), "output_dir": "{output_dir}",
                     "timeout_seconds": 2400, "environment_names": ["OPENAI_API_KEY"],
                     "request": request}}


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", type=Path, default=Path("/srv/arena"))
    parser.add_argument("--ca-bundle", type=Path, default=Path("/etc/ssl/certs/arena-worker-bundle.pem"))
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    if not all(p.is_absolute() for p in (args.root, args.ca_bundle, args.destination)) or args.destination.exists():
        raise ValueError("Use absolute paths and a new destination")
    from arena.frameworks.drivers._tls import configure_ca
    from arena.frameworks.runtime import prepare_plan
    configure_ca(args.ca_bundle)
    args.destination.mkdir(mode=0o750, parents=True)
    templates, records = [], []
    for engine, profile, label in PROFILES:
        folder = args.destination / profile
        folder.mkdir(mode=0o750)
        selected = []
        for model in MODELS:
            item = template(args.root, engine, profile, label, model, args.ca_bundle)
            plan = prepare_plan({**item["spec"], "output_dir": str(args.root / "runs" / (item["id"] + "-plan-only"))})
            (folder / (model + ".plan.json")).write_text(json.dumps(plan, indent=2) + "\n")
            selected.append(item)
            templates.append(item)
            records.append({"framework": engine, "profile": profile, "model": model,
                            "source": plan["source"], "plan_sha256": plan["sha256"]})
        (folder / "templates.json").write_text(json.dumps(selected, indent=2) + "\n")
    (args.destination / "templates.json").write_text(json.dumps(templates, indent=2) + "\n")
    (args.destination / "preparation.json").write_text(json.dumps({
        "schema": "arena.llamea-eohs-pilot-preparation/1", "records": records,
        "model_calls": 0, "research_executed": False, "canonical_evaluation": False,
        "ca_bundle_sha256": hashlib.sha256(args.ca_bundle.read_bytes()).hexdigest(),
        "native_sources": "Two implementations, three profiles; ordinary LLaMEA and HPO share the pinned XAI-liacs source, not LLaMEA-BO.",
        "concurrency_basis": "LLaMEA max_workers=1 with SMAC default n_workers=1; EoHS one sampler/evaluation worker; numeric threads=1. Outer admission controls all descendants.",
        "provider": "Exact aliases and scoped environment credential only; codex-native temperature/token controls are recorded but unenforced.",
        "limits": "Native retries/parse failures can exceed nominal samples. These are small native-protocol pilots, not paper-scale reproduction or cross-framework score comparison.",
    }, indent=2) + "\n")
    print(json.dumps({"templates": len(templates), "destination": str(args.destination), "model_calls": 0}))


if __name__ == "__main__":
    main()
