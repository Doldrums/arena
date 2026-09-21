#!/usr/bin/env python3
"""Prepare four native CPU pilot campaigns; never call a model or evaluator."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
MODELS = ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-6-astra", "gpt-5.5", "gpt-reserve", "codex-auto-review")
ENGINES = ("base", "reevo", "hsevo", "mcts-ahd")


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n")


def configured(source, engine, model):
    """Change native budgets/provider fields only; preserve task/evaluator YAML."""
    if engine not in ENGINES or model not in MODELS:
        raise ValueError("Choose an inspected engine and exact gateway model")
    if engine == "base":
        return {}
    config = (source / "cfg/config.yaml").read_text()
    updates = dict(max_fe=4 if engine == "mcts-ahd" else 6, pop_size=2, init_pop_size=2, timeout=60)
    if engine == "hsevo":
        updates.update(model="openai/"+model, max_tokens=8192, enable_thinking=False,
                       n_parallel=1, hm_size=2, max_iter=1, mutation_rate=.5)
    elif engine == "reevo":
        updates["mutation_rate"] = .5
    # Only reviewed scalar root fields change. Preserve every unrelated native
    # line/default; fail on missing/duplicate fields rather than guessing YAML.
    for key, value in updates.items():
        config, count = re.subn(r"(?m)^"+re.escape(key)+r":[^\n]*$", key+": "+json.dumps(value), config)
        if count != 1:
            raise ValueError("Native configuration root field is missing or ambiguous: "+key)
    if engine == "hsevo":
        return {"cfg/config.yaml": config}
    client = {"_target_": "arena.frameworks.drivers.reevo_gateway.GatewayClient" if engine == "reevo" else "utils.llm_client.openai.OpenAIClient",
              "model": model, "temperature": 1.0, "base_url": "http://127.0.0.1:8789/v1",
              "api_key": "${oc.env:OPENAI_API_KEY}"}
    # JSON is a YAML subset supported by the native OmegaConf loader.
    return {"cfg/config.yaml": config, "cfg/llm_client/openai.yaml": json.dumps(client, indent=2)+"\n"}


def prepare(root, destination):
    from arena.frameworks.recipes import load_recipes
    from arena.frameworks.runtime import prepare_plan, verify_source
    if not root.is_absolute() or not destination.is_absolute() or destination.exists():
        raise ValueError("Root must be absolute and destination must be new")
    recipes = load_recipes()
    destination.mkdir(parents=True, mode=0o750)
    templates, proofs = [], []
    for engine in ENGINES:
        source = root / "sources" / engine
        revision = verify_source(source, recipes[engine]["repository"]["commit"])
        directory = destination / engine
        directory.mkdir(mode=0o750)
        engine_templates = []
        for model in MODELS:
            slug = model.replace(".", "-")
            files = directory / slug
            files.mkdir(mode=0o750)
            overlays = {}
            for relative, value in configured(source, engine, model).items():
                path = files / relative.replace("/", "--")
                path.write_text(value)
                overlays[relative] = str(path)
            request = {"python": str(root / "envs" / engine / "bin/python"),
                       "profile": "gateway-cpu-pilot", "arguments": [], "config_overlays": overlays}
            if engine == "base":
                request["arguments"] = ["--model", model, "--rounds", "4"]
            if engine == "hsevo":
                request["inputs"] = {"arena-inputs/tiktoken": str(root / "assets/tiktoken")}
            spec = {"schema": "arena.native-run/1", "framework": engine, "source_dir": str(source),
                    "output_dir": str(root / "runs" / destination.name / engine / slug),
                    "timeout_seconds": 2400, "request": request, "environment_names": ["OPENAI_API_KEY"]}
            plan = prepare_plan(spec)
            write_json(files / "plan.json", plan)
            write_json(files / "native-run.json", spec)
            controlled = {**spec, "output_dir": "{output_dir}"}
            template = {"id": "cpu-"+engine+"-"+slug, "name": engine+" native CPU pilot · "+model,
                        "framework": engine, "profile": "gateway-cpu-pilot", "model": model,
                        "status": "ready", "blocked_reason": None,
                        "resources": {"cpus": 4, "memory_mb": 8192, "evaluation_slots": 2 if engine in ("reevo", "hsevo") else 1, "pids": 512},
                        "containment": "cgroup-v2", "evaluation_concurrency_verified": True, "spec": controlled}
            engine_templates.append(template);templates.append(template)
            proofs.append({"framework": engine, "model": model, "source": revision,
                           "plan_sha256": plan["sha256"], "plan_path": str(files / "plan.json"),
                           "canonical_evaluation": False, "research_executed": False})
        write_json(directory / "templates.json", engine_templates)
    write_json(destination / "templates.json", templates)
    evidence = {"schema": "arena.native-cpu-preparation/1", "models": list(MODELS), "records": proofs,
                "provider": {"endpoint": "http://127.0.0.1:8789/v1", "compatibility_policy": "codex-native",
                             "unenforced_controls": ["temperature", "max_tokens", "top_p"],
                             "credentials": "OPENAI_API_KEY environment reference only"},
                "budget": "BaSE: four nominal proposals. ReEvo/HSEvo: max_fe=6, initial/population=2, mutation=.5. HSEvo retains a harmony-search phase hm_size=2/max_iter=1. MCTS-AHD: max_fe=4, init/population=2. Native retries and whole iterations can overshoot; all runs have 2400-second outer timeout.",
                "concurrency_basis": {"base": "Native selected arm only; N=1 and parallel_llm=1; arm seeds evaluated sequentially.",
                                      "reevo": "Population and initialization sizes=2; mutation size=1; native evaluator launches no more than population size concurrently.",
                                      "hsevo": "Initialization, crossover and harmony memory each size=2; mutation and new harmony each size=1.",
                                      "mcts-ahd": "Problem.batch_evaluate waits for each subprocess inside its loop; InterfaceEC requests a single candidate per attempt."},
                "limits": ["Source verification and pure native configuration/import checks are preparation evidence, not research success.",
                           "Native generated Python executes as the admitted worker in its cgroup; these profiles do not use the canonical Docker evaluator or promise hostile-code isolation.",
                           "Generated code can fork or create threads; cgroup CPU/memory/pids limits constrain the run. Evaluator slots describe native orchestrator concurrency.",
                           "Native validation after search is part of the original entrypoint; no cross-framework score equivalence is claimed."]}
    write_json(destination / "preparation.json", evidence)
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/srv/arena"))
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    value = prepare(args.root, args.destination)
    print(json.dumps({"records": len(value["records"]), "destination": str(args.destination), "research_executed": False}))


if __name__ == "__main__":
    main()
