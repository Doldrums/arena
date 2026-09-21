#!/usr/bin/env python3
"""Write bounded real-native pilot templates; never launch a model or evaluator.

Default mode is offline template generation. --materialize additionally verifies
the three installed source pins and creates the two canonical native task trees.
Dependencies, gateway authentication and actual runs are separate operator steps.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

PINS = {
    "sciel": "0d67f813dd4ac21dee304f2b0de0b0ce59bf4157",
    "shinka": "9912af12d423504b8d580f4179fd15f5f88b8c50",
    "autoresearch-tasks": "5729caa7a3bd4e66c39a447c0d4ee56dc8fa0935",
}
MODELS = ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-6-astra", "gpt-5.5", "gpt-reserve", "codex-auto-review")
THREAD_ENV = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
CPU_PACKAGED = {
    "adaevolve", "evox", "base", "codeevolve", "coevo", "eoh", "eurekagent", "evolcaf",
    "hsevo", "loongflow", "mcts-ahd", "meoh", "reevo", "darwinian-evolver",
}
CPU_INPUTS = {
    "openevolve", "avo-community", "funsearch-original", "funsearch-re-implementation", "llm-lex",
    "eob", "evoor-agent", "lasr", "adas", "ael-harness", "aflow", "g-del-agent", "gepa", "mipro",
    "evoprompt", "promptagent", "protegi", "llamea-hpo", "eoh-s", "cocoevo", "rankevolve",
}
SPECIALIZED = {"dreureka", "limen", "omni-epic", "the-station", "accelopt", "revolve", "text2reward",
               "eureka", "l-autoda", "llm-evolved-rl-algorithms", "lmx", "coral"}


def _json(value):
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def cpu_inventory(registry_root=None):
    """Editorial deployment triage of reviewed profiles, never a readiness claim."""
    from arena.frameworks.recipes import load_recipes
    rows = []
    for ident, recipe in sorted(load_recipes(registry_root).items()):
        if recipe["status"] != "source_verified":
            continue
        group = ("cpu_packaged_task" if ident in CPU_PACKAGED else "cpu_requires_inputs" if ident in CPU_INPUTS
                 else "specialized_environment" if ident in SPECIALIZED else "needs_profile_review")
        for profile in recipe["profiles"]:
            rows.append({"engine": ident, "profile": profile["id"], "deployment_group": group,
                         "repository": recipe["repository"], "setup": recipe["setup"],
                         "limitations": profile["limitations"], "native_evaluation": profile["evaluation"],
                         "source_evidence": recipe["evidence"], "runtime_readiness": "not_verified",
                         "gateway_conformance": "not_verified", "canonical_evaluation": False})
    return {"schema": "arena.cpu-profile-inventory/1", "profiles": rows,
            "basis": "Source-reviewed deployment triage, not measured runtime readiness. CPU groups still require native dependencies and provider setup.",
            "counts": {group: sum(row["deployment_group"] == group for row in rows)
                       for group in ("cpu_packaged_task", "cpu_requires_inputs", "specialized_environment", "needs_profile_review")}}


def build_bundle(root, campaign, image, model="gpt-5.6-sol", gateway="http://127.0.0.1:8789/v1"):
    root = Path(root)
    if not root.is_absolute() or ".." in root.parts or "\x00" in str(root):
        raise ValueError("Runtime root must be an absolute contained path")
    if not isinstance(campaign, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", campaign):
        raise ValueError("Campaign must be a short lowercase identifier")
    if model not in MODELS:
        raise ValueError("Choose one explicitly supported deployment model alias")
    if not isinstance(image, str) or not re.fullmatch(r"(?:[A-Za-z0-9][A-Za-z0-9._/:\-]*@)?sha256:[0-9a-f]{64}", image):
        raise ValueError("Evaluator image must be immutable and preinstalled")
    parsed = urlsplit(gateway)
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment
            or parsed.path.rstrip("/") != "/v1"):
        raise ValueError("Pilot gateway must be credential-free loopback HTTP /v1")
    parsed.port
    gateway = gateway.rstrip("/")
    config_dir, task_dir, run_dir = (root / name / campaign for name in ("configs", "tasks", "runs"))
    source_root = root / "sources"
    arena_python = str(root / "envs/arena/bin/python")
    execution = {"kind": "docker", "image": image, "python": "python", "require_control_cgroup": True}
    evaluation = {"schema": "arena.evaluation-config/1", "tasks_dir": str(source_root / "autoresearch-tasks"),
                  "timeout_seconds": 120, "execution": execution}
    sciel_eval = {**evaluation, "task_id": "reference-sat", "profile": "sciel-unit-interval/1",
                  "receipts_dir": str(run_dir / "canonical-sciel")}
    shinka_eval = {**evaluation, "task_id": "alphaevolve-circle-packing-in-unit-square",
                   "receipts_dir": str(run_dir / "canonical-shinka")}
    # Explicit standalone configuration: no extends file or mutable external
    # model reference. Native defaults retain crossover, portfolio and ideas.
    sciel = {
        "task": "arena/reference-sat", "budget": 12, "max_iterations": 24, "random_seed": 0,
        "num_islands": 3, "pop_cap": 12, "archive_size": 12, "grid_bins": 10,
        "inflight_cap": 1, "dup_cap": 4, "backstop_k": 4,
        "schedule_policy": "sh", "milestone_fracs": [0.5, 0.75],
        "op_temperature": 0.5, "op_floor": 0.05, "op_window": 50,
        "selection_floor": 0.001, "tau_floor": 0.001, "reward_w_pop": 1.0, "reward_w_isl": 1.0,
        "base_temp": 0.7, "bet_enabled": False, "confirm_records": False, "checkpoint_on_milestone": True,
        "embed_grid": True, "embed_grid_path": str(source_root / "sciel/models/code_embed_v3.pt"),
        "embed_axis_path": str(source_root / "sciel/models/behavior_axis/{task}_v3.npz"),
        "parallel_search": {"enabled": True, "workers": 1, "host_llm_slots": 2, "provider_slots": 2,
                            "host_evaluator_slots": 1, "capacity_dir": str(root / "state/sciel-capacity"),
                            "max_inflight_per_island": 1, "max_inflight_per_parent": 1, "portfolio_schedule": "blocking"},
        "candidate_novelty": {"enabled": True, "max_resamples": 1, "neighbors": 3, "output_repeats": False},
        "research": {"enabled": True, "reflection_interval": 3, "max_aux_calls": 4, "max_experiments": 48},
        "wandb": {"enabled": False},
        "llm": {"models": [model], "weights": [1.0], "api_base": gateway,
                "api_key_env": "OPENAI_API_KEY", "max_retries": 1, "timeout": 300,
                "max_tokens": 8192, "model_capabilities": {model: {"temperature": False}},
                "system_message": "Implement solve(instance) -> a list of booleans of length instance['n']. instance['clauses'] contains signed 1-based literals. Maximize the fraction of ten fixed generated satisfiable 3-CNF instances solved (50 variables, evaluator seed 0). Preserve the solve entrypoint. The seed already scores 1.0: this pilot validates the native research loop, not a claim of benchmark improvement."},
    }
    def run_spec(framework, request):
        return {"schema": "arena.native-run/1", "framework": framework,
                "source_dir": str(source_root / framework), "output_dir": str(run_dir / framework),
                "timeout_seconds": 3600, "environment_names": ["OPENAI_API_KEY", "DOCKER_HOST",
                    "ARENA_EVALUATION_CGROUP_PARENT", "ARENA_EVALUATION_RECEIPTS_DIR", *THREAD_ENV], "request": request}
    sciel_run = run_spec("sciel", {"python": str(root / "envs/sciel/bin/python"),
                                   "config": str(config_dir / "sciel.yaml"),
                                   "tasks_root": str(task_dir / "sciel"), "seed": 0,
                                   "budget": 12, "campaign": campaign, "arm": "native-pilot"})
    shinka_run = run_spec("shinka", {"python": str(root / "envs/shinka/bin/python"),
                                     "task_dir": str(task_dir / "shinka-circle"), "num_generations": 6,
                                     "native_config": {"llm_models": [f"local/{model}@{gateway}?api_key_env=OPENAI_API_KEY"],
                                                       "embedding_model": None, "max_api_costs": 1.0,
                                                       "evaluation_timeout": "00:04:00", "max_evaluation_jobs": 1,
                                                       "max_proposal_jobs": 1, "max_db_workers": 1,
                                                       "numeric_threads_per_job": 1, "num_islands": 2, "archive_size": 10,
                                                       "llm_kwargs": {"temperatures": [1.0], "max_tokens": 8192}}})
    manifest = {
        "schema": "arena.native-pilot-bundle/1", "campaign": campaign, "source_pins": PINS,
        "source_verification": "pending_worker_materialization", "task_materialization": "pending",
        "models_generation_verified": False, "research_executed": False,
        "provider": {"gateway": gateway, "model": model, "credential_environment_name": "OPENAI_API_KEY",
                     "required_compatibility_policy": "codex-native", "unenforced_controls": ["max_tokens", "temperature"],
                     "cost_accounting": "Use gateway/provider receipts; native Shinka local pricing is zero for uncataloged models and SCiEL can use token estimates."},
        "environment": {name: "1" for name in THREAD_ENV},
        "resources_per_run": {"cpus": 4, "memory_mb": 8192, "evaluation_slots": 1, "pids": 512},
        "resource_basis": "Initial CPU admission envelope, not measured peak or throughput. Canonical Docker evaluator has separate 1 CPU / 2 GiB limits.",
        "acceptance": ["A real gateway model response must precede native launch.",
                       "Native run must record at least one model-generated candidate and its canonical receipt; seed-only output is not a research run.",
                       "Preserve requested model, native lineage, gateway usage and candidate/receipt hashes.",
                       "SCiEL SAT seed is already 1.0; pilot is integration conformance, not scientific improvement.",
                       "SCiEL SAT and Shinka packing have different objectives and must not be ranked against each other."],
        "commands": {framework: {action: [arena_python, "-m", "arena.frameworks", action, str(config_dir / (framework + ".run.json"))]
                                 for action in ("plan", "run")} for framework in ("sciel", "shinka")},
    }
    return {"sciel.yaml": sciel, "sciel.run.json": sciel_run, "shinka.run.json": shinka_run,
            "sciel.evaluation.json": sciel_eval, "shinka.evaluation.json": shinka_eval, "manifest.json": manifest}


def provider_probe(path, model):
    """Bind an operator-captured successful probe, without accepting credentials."""
    path = Path(path)
    if not path.is_absolute() or not path.is_file() or path.stat().st_size > 65536:
        raise ValueError("Provider probe evidence must be a bounded absolute JSON file")
    raw = path.read_bytes()
    records = json.loads(raw)
    if not isinstance(records, list):
        raise ValueError("Provider probe evidence must contain a list")
    matches = [row for row in records if isinstance(row, dict) and row.get("model") == model]
    if len(matches) != 1:
        raise ValueError("Provider evidence must identify the exact model once")
    row = matches[0]
    if (set(row) != {"model", "status", "usage", "seconds", "response_model"}
            or row["status"] != "generation_verified" or row["response_model"] != model):
        raise ValueError("Provider probe must verify generation with the exact requested model")
    usage = row["usage"]
    if (not isinstance(usage, dict) or set(usage) != {"prompt_tokens", "completion_tokens", "total_tokens"}
            or any(type(value) is not int or value < 0 for value in usage.values())
            or usage["completion_tokens"] < 1 or usage["total_tokens"] != usage["prompt_tokens"] + usage["completion_tokens"]
            or type(row["seconds"]) not in (int, float) or not math.isfinite(row["seconds"]) or row["seconds"] < 0):
        raise ValueError("Provider probe usage and duration must be explicit and consistent")
    return {"schema": "arena.provider-probe-binding/1", "source_sha256": hashlib.sha256(raw).hexdigest(),
            "record": row, "basis": "Operator-captured gateway generation probe; not a native research run."}


def control_templates(bundle):
    manifest = bundle["manifest.json"]
    ready = manifest["source_verification"] == "verified_clean_pins" and manifest["models_generation_verified"]
    rows = []
    for framework in ("sciel", "shinka"):
        native = {**bundle[framework + ".run.json"], "output_dir": "{output_dir}"}
        # The control worker injects these names and their trusted values after
        # admission; operators cannot choose their values in a template.
        native["environment_names"] = [name for name in native["environment_names"]
                                       if not name.startswith("ARENA_EVALUATION_")]
        rows.append({"id": manifest["campaign"] + "-" + framework,
                     "name": framework.upper() if framework == "sciel" else "Shinka",
                     "framework": framework, "profile": "canonical-native-pilot",
                     "model": manifest["provider"]["model"], "status": "ready" if ready else "blocked",
                     "blocked_reason": None if ready else "Materialize clean source/task pins and bind a successful exact-model gateway probe before admission.",
                     "resources": manifest["resources_per_run"], "containment": "cgroup-v2",
                     "evaluation_concurrency_verified": True, "spec": native})
    return rows


def write_bundle(destination, bundle, *, root, campaign, materialize=False, probe_evidence=None):
    destination, root = Path(destination), Path(root)
    if not destination.is_absolute() or destination.exists() or destination.is_symlink():
        raise ValueError("Bundle destination must be a new absolute directory")
    if probe_evidence is not None:
        proof = provider_probe(probe_evidence, bundle["manifest.json"]["provider"]["model"])
        bundle = {**bundle, "provider-probe.json": proof}
        bundle["manifest.json"].update(models_generation_verified=True, provider_probe="provider-probe.json")
    if materialize:
        if destination != root / "configs" / campaign:
            raise ValueError("Materialized config destination must match its runtime paths")
        from arena.frameworks.runtime import verify_source
        from arena.frameworks.sciel_evaluate import create_task as sciel_task
        from arena.frameworks.shinka_evaluate import create_task as shinka_task
        from arena.frameworks.evaluation import validate_config
        verified = {name: verify_source(root / "sources" / name, pin) for name, pin in PINS.items()}
        for name in ("sciel", "shinka"):
            validate_config(bundle[name + ".evaluation.json"])
            executable = Path(bundle[name + ".run.json"]["request"]["python"])
            if not executable.is_file():
                raise ValueError("Native environment Python is missing")
        task_root = root / "tasks" / campaign
        if task_root.exists():
            raise ValueError("Generated task root already exists")
        sciel_task(bundle["sciel.evaluation.json"], task_root / "sciel/arena/reference-sat")
        shinka_task(bundle["shinka.evaluation.json"], task_root / "shinka-circle")
        bundle["manifest.json"].update(source_verification="verified_clean_pins", source_identities=verified,
                                      task_materialization="created_without_execution")
    inventory = cpu_inventory()
    bundle = {**bundle, "cpu-profiles.json": inventory, "control-templates.json": control_templates(bundle)}
    bundle["manifest.json"]["file_sha256"] = {name: hashlib.sha256(_json(value).encode()).hexdigest()
                                             for name, value in bundle.items() if name != "manifest.json"}
    destination.mkdir(parents=True, mode=0o700)
    for name, value in bundle.items():
        path = destination / name
        path.write_text(_json(value))
        path.chmod(0o600)
    return bundle["manifest.json"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/srv/arena"))
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--image", required=True, help="Existing immutable Linux worker evaluator image")
    parser.add_argument("--model", choices=MODELS, default=MODELS[0])
    parser.add_argument("--gateway", default="http://127.0.0.1:8789/v1")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--materialize", action="store_true", help="Verify installed pins and create tasks; never evaluates or runs a model")
    parser.add_argument("--probe-evidence", type=Path, help="Operator-captured gateway probe JSON; bind the selected exact model and its usage")
    args = parser.parse_args(argv)
    try:
        bundle = build_bundle(args.root, args.campaign, args.image, args.model, args.gateway)
        destination = args.output or args.root / "configs" / args.campaign
        manifest = write_bundle(destination, bundle, root=args.root, campaign=args.campaign, materialize=args.materialize,
                                probe_evidence=args.probe_evidence)
        print(_json({"directory": str(destination), "research_executed": False,
                     "source_verification": manifest["source_verification"], "commands": manifest["commands"]}), end="")
        return 0
    except (OSError, ValueError) as error:
        parser.exit(2, f"Pilot preparation failed: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
