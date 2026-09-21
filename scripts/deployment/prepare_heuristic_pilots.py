#!/usr/bin/env python3
"""Write EoH/MEoH pilot templates and pure plans; never invoke native research.

Requires preinstalled, import-checked native environments and the verified
public relay CA bundle. Queue admission is a separate explicit operator step.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import ssl
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
MODELS = ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-6-astra", "gpt-5.5", "gpt-reserve", "codex-auto-review")


def write(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
    path.chmod(0o644)


def template(root, engine, model, ca_bundle, recipe):
    if engine not in ("eoh", "meoh") or model not in MODELS:
        raise ValueError("Unsupported pilot engine or model")
    profile = "online-bin-packing" if engine == "eoh" else "online-bin-packing-two-objectives"
    # EoH counts 2*population initialization samples separately from its
    # max_sample_nums evolution budget; MEoH includes initialization.
    population, samples = (2, 4) if engine == "eoh" else (4, 8)
    destination = ("examples/bp_online/" if engine == "eoh" else "") + "arena-inputs/worker-ca.pem"
    arguments = ["--endpoint" if engine == "eoh" else "--host", "127.0.0.1:8790", "--model", model,
                 "--population", str(population), "--generations", "2", "--samples", str(samples),
                 "--samplers", "1", "--evaluators", "1", "--eval-timeout", "60",
                 "--numeric-threads", "1", "--tls-ca", "arena-inputs/worker-ca.pem"]
    spec = {"schema": "arena.native-run/1", "framework": engine,
            "source_dir": str(root / "sources" / engine), "output_dir": "{output_dir}",
            "timeout_seconds": 2400, "environment_names": ["OPENAI_API_KEY"],
            "request": {"python": str(root / "envs" / engine / "bin/python"), "profile": profile,
                        "arguments": arguments, "inputs": {destination: str(ca_bundle)}}}
    return {"id": "heuristic-pilot-" + engine + "-" + model.replace(".", "-"),
            "name": recipe["name"], "framework": engine, "profile": profile, "model": model,
            "status": "ready", "blocked_reason": None,
            "resources": {"cpus": 4, "memory_mb": 8192, "evaluation_slots": 1, "pids": 512},
            "containment": "cgroup-v2", "evaluation_concurrency_verified": True, "spec": spec}


def prepare(root: Path, engine: str, ca_bundle: Path):
    from arena.control import validate_config
    from arena.frameworks.recipes import load_recipes
    from arena.frameworks.runtime import prepare_plan, verify_source
    from arena.frameworks.drivers._tls import configure_ca

    configure_ca(ca_bundle)
    recipe = load_recipes()[engine]
    provenance = verify_source(root / "sources" / engine, recipe["repository"]["commit"])
    freeze = root / "configs" / ("pilot-dependencies-" + engine + ".txt")
    if not freeze.is_file():
        raise ValueError("Prepare and record the native dependency environment before generating templates")
    directory = root / "configs" / ("heuristic-pilots-20260921-" + engine)
    directory.mkdir(mode=0o755, exist_ok=False)
    templates, evidence = [], []
    for model in MODELS:
        item = template(root, engine, model, ca_bundle, recipe)
        plan = prepare_plan({**item["spec"], "output_dir": str(root / "runs" / (item["id"] + "-plan-only"))})
        write(directory / (model + "-plan.json"), plan)
        templates.append(item)
        evidence.append({"model": model, "plan_sha256": plan["sha256"]})
    validate_config({"schema": "arena.control/1", "state_dir": str(root / "control"),
                     "cgroup_root": "/sys/fs/cgroup/arena-workers",
                     "limits": {"cpus": 96, "memory_mb": 307200, "evaluation_slots": 32, "max_active": 8,
                                "max_queued": 2048, "max_runs_per_key": 2048, "max_reserved_seconds_per_key": 6048000},
                     "templates": templates})
    write(directory / "templates.json", templates)
    write(directory / "preparation.json", {"schema": "arena.native-pilot-preparation/1", "engine": engine,
          "source": provenance, "task": "native packaged online bin packing", "generations": 2,
          "population": 2 if engine == "eoh" else 4,
          "sample_budget": {"initialization": 4, "evolution": 4} if engine == "eoh" else {"total_registered": 8},
          "concurrency": {"samplers": 1, "evaluators": 1, "numeric_threads": 1},
          "ca_bundle_sha256": hashlib.sha256(ca_bundle.read_bytes()).hexdigest(),
          "dependency_freeze_sha256": hashlib.sha256(freeze.read_bytes()).hexdigest(), "configurations": evidence,
          "native_evaluation": True, "canonical_evaluation": False, "model_runs_performed": False,
          "runtime_readiness": "not_verified", "gateway_inference_conformance": "not_verified",
          "limitations": ["Native retries and parse failures may generate more API requests than sample records; wall limit is 2400 seconds.",
                          "EoH performs one native startup connectivity probe in addition to candidate requests.",
                          "Native score definitions, tasks and protocols differ; this is not a cross-framework comparison."]})
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/srv/arena"))
    parser.add_argument("--engine", choices=("eoh", "meoh"), required=True)
    parser.add_argument("--ca-bundle", type=Path, default=Path("/etc/ssl/certs/arena-worker-bundle.pem"))
    args = parser.parse_args()
    if not args.root.is_absolute() or not args.ca_bundle.is_absolute():
        parser.error("root and CA bundle must be absolute")
    print(prepare(args.root, args.engine, args.ca_bundle))


if __name__ == "__main__":
    main()
