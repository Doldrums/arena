#!/usr/bin/env python3
"""Materialize reviewed CodeEvolve/LoongFlow/CoEvo configurations, without runs."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
MODELS = ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-6-astra", "gpt-5.5", "gpt-reserve", "codex-auto-review")
CONFIG_PATHS = {
    "codeevolve": "configs/templates/config_qwen.yaml",
    "loongflow": "agents/math_agent/examples/packing_circle_in_unit_square/task_config.yaml",
}


def configuration(engine, model, source):
    import yaml
    if model not in MODELS or engine not in CONFIG_PATHS:
        raise ValueError("Unsupported native pilot configuration")
    config = yaml.safe_load((source / CONFIG_PATHS[engine]).read_text())
    if engine == "codeevolve":
        config["EVOLVE_CONFIG"].update(num_epochs=4, ckpt=1, init_pop=2, num_islands=1)
        config["BUDGET_CONFIG"].update(eval_timeout=60, max_mem_bytes=2_000_000_000)
        for item in [*config["EXPLORATION_ENSEMBLE"], *config["EXPLOITATION_ENSEMBLE"], config["SAMPLER_AUX_LM"]]:
            item.update(model_name=model, verify_ssl=True, retries=1, max_tok=8192)
    else:
        config["workspace_path"] = "results"
        config["llm_config"].pop("api_key", None)  # Native LiteLLM reads OPENAI_API_KEY.
        # The native schema defaults these optional fields to None. The pinned
        # gateway cannot enforce them, and LiteLLM rejects them for GPT-5 aliases.
        config["llm_config"].pop("temperature", None)
        config["llm_config"].pop("top_p", None)
        config["llm_config"].update(url="http://127.0.0.1:8789/v1", model=model,
                                  model_provider="openai", max_tokens=8192, timeout=180)
        config["planners"]["evolve_planner"]["react_max_steps"] = 3
        config["executors"]["evolve_executor_fuse"].update(max_rounds=1, react_max_steps=3)
        config["summarizers"]["evolve_summary"]["react_max_steps"] = 2
        config["evolve"].update(max_iterations=4, concurrency=1)
        config["evolve"]["evaluator"]["timeout"] = 60
        config["evolve"]["task"] = config["evolve"]["task"].replace("1000 seconds of runtime", "60 seconds of runtime")
    return config


def template(root, engine, model, directory, recipe):
    if engine not in ("codeevolve", "loongflow", "coevo") or model not in MODELS:
        raise ValueError("Unsupported native pilot engine or model")
    request = {"python": str(root / "envs" / engine / "bin/python"), "profile": "gateway-cpu-pilot", "arguments": [],
               "inputs": {"arena-inputs/dependencies.txt": str(root / "configs" / ("pilot-dependencies-" + engine + ".txt"))}}
    if engine in CONFIG_PATHS:
        request["config_overlays"] = {CONFIG_PATHS[engine]: str(directory / (model + ".yaml"))}
    else:
        # In this exact implementation initialization leaves generation at zero;
        # max_gen=1 therefore performs initialization AND one offspring round.
        request["arguments"] = ["--model", model, "--max_gen", "1", "--pop_size", "2",
                                "--tls-ca", "arena-inputs/worker-ca.pem", "--hf-cache", str(root / "caches/coevo-hf"),
                                "--hf-manifest", "arena-inputs/embedding-manifest.json"]
        request["inputs"].update({"arena-inputs/worker-ca.pem": "/etc/ssl/certs/arena-worker-bundle.pem",
                                  "arena-inputs/embedding-manifest.json": str(root / "caches/coevo-hf/manifest.json")})
    return {"id": "program-pilot-" + engine + "-" + model.replace(".", "-"),
            "name": recipe["name"], "framework": engine, "profile": "gateway-cpu-pilot", "model": model,
            "status": "ready", "blocked_reason": None,
            "resources": {"cpus": 4, "memory_mb": 8192, "evaluation_slots": 1, "pids": 512},
            "containment": "cgroup-v2", "evaluation_concurrency_verified": True,
            "spec": {"schema": "arena.native-run/1", "framework": engine, "source_dir": str(root / "sources" / engine),
                     "output_dir": "{output_dir}", "timeout_seconds": 2400,
                     "environment_names": ["OPENAI_API_KEY"], "request": request}}


def write(path, data):
    with path.open("x") as stream:
        stream.write(json.dumps(data, indent=2, allow_nan=False) + "\n")


def prepare(root, engine):
    import yaml
    from arena.control import validate_config
    from arena.frameworks.recipes import load_recipes
    from arena.frameworks.runtime import prepare_plan, verify_source
    from arena.frameworks.drivers.cpu_program_gateway import verify_embedding_cache
    recipe = load_recipes()[engine]
    source = root / "sources" / engine
    provenance = verify_source(source, recipe["repository"]["commit"])
    freeze = root / "configs" / ("pilot-dependencies-" + engine + ".txt")
    if not freeze.is_file():
        raise ValueError("Record the installed dependency freeze before preparation")
    if engine == "coevo":
        verify_embedding_cache(root / "caches/coevo-hf", root / "caches/coevo-hf/manifest.json")
    directory = root / "configs" / ("program-pilots-20260921-" + engine)
    directory.mkdir(exist_ok=False)
    templates, evidence = [], []
    for model in MODELS:
        if engine in CONFIG_PATHS:
            (directory / (model + ".yaml")).write_text(yaml.safe_dump(configuration(engine, model, source), sort_keys=False))
        item = template(root, engine, model, directory, recipe)
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
    write(directory / "preparation.json", {
        "schema": "arena.native-pilot-preparation/1", "engine": engine, "source": provenance,
        "configurations": evidence, "dependency_freeze_sha256": hashlib.sha256(freeze.read_bytes()).hexdigest(),
        "budget": {"codeevolve": {"epochs": 4, "islands": 1, "initial_population_target": 2},
                   "loongflow": {"pes_iterations": 4, "executor_rounds": 1, "react_steps": [3, 3, 2]},
                   "coevo": {"native_max_gen": 1, "initialization_plus_evolution_rounds": 2, "population": 2,
                             "initial_chains": 4, "offspring_and_new_chains": 10,
                             "maximum_solutions_generated_per_chain_before_retries": 2}}[engine],
        "concurrency": {"native_evaluations": 1, "numeric_threads": 1}, "wall_timeout_seconds": 2400,
        "native_evaluation": True, "canonical_evaluation": False, "model_runs_performed": False,
        "runtime_readiness": "not_verified", "gateway_inference_conformance": "not_verified",
        "provider_compatibility": {"discarded_metadata": ["user"] if engine == "codeevolve" else [],
                                   "omitted_native_optional_controls": ["temperature", "top_p"] if engine == "loongflow" else []},
        "limitations": ["Native retries and tool calls can exceed generation counts; the outer wall timeout is enforced.",
                        "Gateway codex-native policy records temperature/top_p/token-limit controls as unenforced.",
                        "Native task metrics are not a common benchmark across frameworks."]})
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", type=Path, default=Path("/srv/arena"))
    parser.add_argument("--engine", choices=("codeevolve", "loongflow", "coevo"), required=True)
    args = parser.parse_args()
    if not args.root.is_absolute():
        parser.error("root must be absolute")
    print(prepare(args.root, args.engine))


if __name__ == "__main__":
    main()
