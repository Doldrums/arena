#!/usr/bin/env python3
"""Prepare the reviewed AdaEvolve, EvoX and OpenEvolve pilots without executing them.

The checked-in configurations preserve the actual first campaign, including its
native task prompt and different seed policies. They are integration settings,
not a shared benchmark protocol. Additional engines have a separate generator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
MODELS = ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-6-astra",
          "gpt-5.5", "gpt-reserve", "codex-auto-review")
ENGINES = ("adaevolve", "evox", "openevolve")
GATEWAY = "http://127.0.0.1:8789/v1"
THREAD_ENV = ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"]


def configuration(engine, model):
    if engine not in ENGINES or model not in MODELS:
        raise ValueError("Choose a reviewed engine and an exact gateway model")
    path = Path(__file__).with_name("program-pilot-configs") / (engine + ".json")
    config = json.loads(path.read_text())
    config["llm"]["models"] = [{"name": ("openai/" if engine == "evox" else "") + model, "weight": 1.0}]
    return config


def template(root, engine, model, directory, recipe):
    profile = "native-evolution" if engine == "openevolve" else "circle-packing"
    source = root / "sources" / engine
    environment = "openevolve" if engine == "openevolve" else "skydiscover"
    request = {"python": str(root / "envs" / environment / "bin/python"), "profile": profile}
    config = str(directory / (model + ".json"))
    if engine == "openevolve":
        request.update(arguments=["arena-inputs/initial.py", "arena-inputs/evaluate.py", "--config",
                                  "arena-inputs/config.json", "--iterations", "4"],
                       inputs={"arena-inputs/initial.py": str(source / "examples/circle_packing/initial_program.py"),
                               "arena-inputs/evaluate.py": str(source / "examples/circle_packing/evaluator.py"),
                               "arena-inputs/config.json": config})
    else:
        native_config = "benchmarks/math/circle_packing/config.yaml"
        request.update(arguments=["--config", native_config, "--iterations", "4", "--api-base",
                                  GATEWAY, "--model", "openai/" + model],
                       config_overlays={native_config: config})
    return {"id": "program-pilot-" + engine + "-" + model.replace(".", "-"),
            "name": recipe["name"], "framework": engine, "profile": profile, "model": model,
            "status": "ready", "blocked_reason": None,
            "resources": {"cpus": 4, "memory_mb": 8192, "evaluation_slots": 1, "pids": 512},
            "containment": "cgroup-v2", "evaluation_concurrency_verified": True,
            "spec": {"schema": "arena.native-run/1", "framework": engine, "source_dir": str(source),
                     "output_dir": "{output_dir}", "timeout_seconds": 2400,
                     "environment_names": ["OPENAI_API_KEY", *THREAD_ENV], "request": request}}


def write_json(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def prepare(root, engine, destination=None):
    from arena.control import validate_config
    from arena.frameworks.recipes import load_recipes
    from arena.frameworks.runtime import prepare_plan, verify_source

    if engine not in ENGINES or not root.is_absolute():
        raise ValueError("Use an absolute worker root and a reviewed engine")
    directory = destination or root / "configs" / ("program-pilots-20260921-" + engine)
    if not directory.is_absolute() or directory.exists():
        raise ValueError("The destination must be absolute and new; prepared inputs are immutable")
    recipe = load_recipes()[engine]
    provenance = verify_source(root / "sources" / engine, recipe["repository"]["commit"])
    directory.mkdir(parents=True, mode=0o750)
    templates, evidence = [], []
    for model in MODELS:
        config_path = directory / (model + ".json")
        write_json(config_path, configuration(engine, model))
        row = template(root, engine, model, directory, recipe)
        plan = prepare_plan({**row["spec"], "output_dir": str(root / "runs" / (row["id"] + "-plan-only"))})
        write_json(directory / (model + "-plan.json"), plan)
        evidence.append({"model": model, "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
                         "plan_sha256": plan["sha256"]})
        templates.append(row)
    validate_config({"schema": "arena.control/1", "state_dir": str(root / "control"),
                     "cgroup_root": "/sys/fs/cgroup/arena-workers",
                     "limits": {"cpus": 96, "memory_mb": 307200, "evaluation_slots": 32,
                                "max_active": 8, "max_queued": 2048, "max_runs_per_key": 2048,
                                "max_reserved_seconds_per_key": 6048000}, "templates": templates})
    write_json(directory / "templates.json", templates)
    write_json(directory / "preparation.json", {
        "schema": "arena.native-pilot-preparation/1", "engine": engine, "source": provenance,
        "task": "native circle packing, n=26", "iterations": 4, "concurrency": 1,
        "numeric_threads": 1, "configurations": evidence, "model_runs_performed": False,
        "native_evaluation": True, "canonical_evaluation": False,
        "runtime_readiness": "not_verified_by_preparation",
        "scope": "Small integration pilot; native metric and protocol, not paper reproduction or a cross-framework comparison.",
        "limitations": ["Retries and native EvoX meta-search calls can exceed the iteration count.",
                        "Gateway generation controls are recorded as unenforced; nominal max_tokens is not a spending cap.",
                        "Numeric thread limits must also be present in the worker environment."]})
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/srv/arena"))
    parser.add_argument("--engine", choices=ENGINES, required=True)
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    print(prepare(args.root, args.engine, args.destination))


if __name__ == "__main__":
    main()
