"""SCiEL bridge for the bundled CPU/Python catalog, with declared score semantics.

Preparation reads pinned bytes only. Candidate execution belongs exclusively to
the canonical Docker evaluator; search transforms never replace its raw metric.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import statistics
import tempfile
import uuid

from .sciel_evaluate import smoke
from .sciel_catalog_profile import CPU_PROFILE, validate_task_profile

SCHEMA = "arena.sciel-catalog-config/1"
PROFILE = CPU_PROFILE


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def search_score(fitness, transform):
    """Map maximizing canonical fitness only under an explicit operator contract."""
    if not _finite(fitness):
        raise ValueError("Canonical fitness must be finite")
    if transform["kind"] == "identity":
        return fitness
    return 0.5 + math.atan2(fitness, transform["scale"]) / math.pi


def validate_config(config):
    """Validate pinned task metadata without importing any task or candidate code."""
    from arena.task_library import load_task_manifest, read_task_file
    from .evaluation import validate_config as validate_evaluation
    required = {"schema", "evaluation", "fitness", "confirmation"}
    if (type(config) is not dict or not required <= config.keys()
            or config.keys() - required - {"binding"} or config["schema"] != SCHEMA):
        raise ValueError("Expected exact arena.sciel-catalog-config/1 fields")
    transform = config["fitness"]
    if type(transform) is not dict or transform.get("kind") not in {"identity", "atan"}:
        raise ValueError("An explicit identity or atan fitness contract is required")
    fields = {"kind", "basis"} | ({"scale"} if transform["kind"] == "atan" else set())
    if (set(transform) != fields or type(transform["basis"]) is not str
            or not transform["basis"].strip() or len(transform["basis"]) > 400):
        raise ValueError("Fitness requires a bounded explanation of its declared basis")
    if transform["kind"] == "atan" and (not _finite(transform["scale"]) or transform["scale"] <= 0):
        raise ValueError("Atan fitness scale must be positive and finite")
    confirmation = config["confirmation"]
    if (type(confirmation) is not dict or set(confirmation) != {"stochastic", "samples"}
            or type(confirmation["stochastic"]) is not bool
            or type(confirmation["samples"]) is not int
            or not 1 <= confirmation["samples"] <= 10
            or confirmation["stochastic"] != (confirmation["samples"] >= 2)):
        raise ValueError("Declare stochastic confirmation with 2–10 samples, or deterministic with 1")
    evaluation = config["evaluation"]
    if (type(evaluation) is not dict or type(evaluation.get("execution")) is not dict
            or evaluation["execution"].get("kind") != "docker"):
        raise ValueError("Catalog candidate execution requires the canonical Docker evaluator")
    verified = validate_evaluation(evaluation)
    task, root = verified["task"], Path(verified["source_dir"])
    if task["direction"] not in {"maximize", "minimize"} or not task.get("contract"):
        raise ValueError("A declared task interface and objective direction are required")
    requirements = task.get("requirements")
    prepared_environment = validate_task_profile(task, evaluation)
    files = load_task_manifest(verified["source_registration"])["files"]
    metadata_path = f"suite/{task['id']}/task.json"
    metadata = json.loads(read_task_file(root, metadata_path, files[metadata_path]))
    suite = metadata.get("execution", {}).get("suite", {})
    if suite.get("env", {}) or set(suite.get("requires", [])) != set(requirements):
        raise ValueError("Task execution requires undeclared dependencies or environment")
    seed_name = suite.get("initial_program")
    if type(seed_name) is not str or not re.fullmatch(r"[A-Za-z0-9_.-]+\.py", seed_name):
        raise ValueError("Catalog CPU profile requires a declared Python seed")
    seed_path = f"suite/{task['id']}/{seed_name}"
    seed = read_task_file(root, seed_path, files[seed_path])
    receipts = evaluation.get("receipts_dir")
    if type(receipts) is not str or "\x00" in receipts or not Path(receipts).is_absolute():
        raise ValueError("receipts_dir must be an absolute path")
    receipts = Path(receipts).resolve()
    if receipts.is_relative_to(root) or root.is_relative_to(receipts):
        raise ValueError("Receipts must be outside the task-source tree")
    binding = {"task_source": verified["source"], "problem_sha256": verified["problem_sha256"],
               "evaluator_sha256": verified["evaluator_sha256"], "seed_sha256": files[seed_path],
               "protocol": task["protocol"], "direction": task["direction"], "metric": task["metric"]}
    if prepared_environment is not None:
        binding["prepared_environment"] = prepared_environment
    if "binding" in config and config["binding"] != binding:
        raise ValueError("Catalog configuration binding differs from the pinned task")
    problem = json.loads(read_task_file(root, task["contract_source"]["path"], verified["problem_sha256"]))
    return {**verified, "bridge_config": {**config, "binding": binding}, "seed": seed,
            "receipts": receipts, "parameters": problem.get("parameters", {})}


def _prompt(task, config, parameters):
    transform = config["fitness"]
    rule = ("search_score = canonical_fitness" if transform["kind"] == "identity" else
            f"search_score = 0.5 + atan(canonical_fitness / {transform['scale']}) / pi")
    semantics = (f"Objective: {task['direction']} the evaluator's raw {task['metric']} metric. "
                 "canonical_fitness = raw_score for maximization, -raw_score for minimization. "
                 f"{rule}. This is search scaling only; raw scores remain in canonical receipts. "
                 "Smoke checks syntax only. Full evaluates once in an isolated CPU container. "
                 "Confirmation, when requested, averages fresh canonical trials before scaling.")
    prompt = (f"Task: {task['name']}.\nInterface: {task['contract']}\n"
              f"Parameters: {_json(parameters)}\n{semantics}")
    if len(prompt) > 1600:
        raise ValueError("Task interface exceeds SCiEL's 1600-character public contract limit")
    return prompt


def create_task(config, destination):
    verified = validate_config(config)
    config = verified["bridge_config"]
    task, source, receipts = verified["task"], Path(verified["source_dir"]), verified["receipts"]
    destination = Path(destination)
    if not destination.is_absolute() or destination.exists() or destination.is_symlink():
        raise ValueError("destination must be a new absolute task directory")
    destination = destination.resolve()
    for other in (source, receipts):
        if destination.is_relative_to(other) or other.is_relative_to(destination):
            raise ValueError("Generated task, source and receipts must be separate trees")
    timeout, confirmation = config["evaluation"]["timeout_seconds"], config["confirmation"]
    prompt = _prompt(task, config, verified["parameters"])
    native = {"suite": "arena", "name": task["id"], "origin": "math", "resources": "cpu",
              "primary_metric": "arena_search_score", "case_metrics": ["raw_score", "canonical_fitness", "validity"],
              "tiers": ["smoke", "full"] + (["confirm"] if confirmation["stochastic"] else []),
              "stochastic": confirmation["stochastic"], "confirm_n": confirmation["samples"],
              "smoke_timeout": 10, "full_timeout": timeout + 120,
              "confirm_timeout": (timeout + 120) * confirmation["samples"], "task_prompt": prompt}
    payload = _json(config)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    evaluator = f'''"""Canonical Arena CPU evaluator; configuration participates in SCiEL task_hash."""
import hashlib
import json
from arena.frameworks.sciel_catalog_evaluate import smoke, full as _full, confirm as _confirm

_CONFIG_JSON = {payload!r}
_CONFIG_SHA256 = {digest!r}

def _config():
    if hashlib.sha256(_CONFIG_JSON.encode()).hexdigest() != _CONFIG_SHA256:
        raise ValueError("Arena evaluator configuration digest mismatch")
    return json.loads(_CONFIG_JSON)

def full(program_path):
    return _full(_config(), program_path)

def confirm(program_path, n):
    return _confirm(_config(), program_path, n)
'''
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".arena-task-", dir=destination.parent))
    try:
        (temporary / "task.yaml").write_text(json.dumps(native, indent=2) + "\n")
        (temporary / "evaluation.json").write_text(json.dumps(config, indent=2) + "\n")
        (temporary / "evaluator.py").write_text(evaluator)
        (temporary / "initial_program.py").write_bytes(verified["seed"])
        (temporary / "README.md").write_text(prompt + "\n")
        temporary.rename(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return {"profile": config["evaluation"].get("profile", PROFILE),
            "directory": str(destination), "qualified_task": f"arena/{task['id']}",
            "task_source": verified["source"], "canonical_evaluation": True,
            "configuration_sha256": digest, "fitness": config["fitness"],
            "readiness_requirements": sorted(task["requirements"]),
            "native_config": {"task": f"arena/{task['id']}", "confirm_records": confirmation["stochastic"]},
            "runtime_conformance": "not_verified"}


def _measurement(verified, program_path):
    from .evaluation import evaluate, receipt_root, _read_native_result
    config = verified["bridge_config"]
    evaluation, task = config["evaluation"], verified["task"]
    call_dir = receipt_root(evaluation, verified["receipts"]) / uuid.uuid4().hex
    program = Path(program_path)
    if (not program.is_absolute() or program.is_symlink() or not program.is_file()
            or program.suffix != ".py" or program.stat().st_size > 16 * 1024 * 1024):
        raise ValueError("Candidate must be an absolute regular Python file")
    candidate_sha = hashlib.sha256(program.read_bytes()).hexdigest()
    receipt = evaluate(evaluation, program, call_dir)
    expected = {"schema": "arena.evaluation/1", "task_id": task["id"],
                "direction": task["direction"], "metric": task["metric"], "protocol": task["protocol"],
                "candidate_sha256": candidate_sha, "problem_sha256": verified["problem_sha256"],
                "evaluator_sha256": verified["evaluator_sha256"], "task_source": verified["source"],
                "execution": evaluation["execution"]}
    if (any(receipt.get(key) != value for key, value in expected.items())
            or type(receipt.get("evaluation_id")) is not str or not receipt["evaluation_id"]):
        raise ValueError("Canonical receipt does not match the task, candidate or execution request")
    path = call_dir / "receipt.json"
    if receipt.get("receipt_path") != str(path) or path.is_symlink():
        raise ValueError("Canonical receipt path differs from its evaluation output")
    persisted, digest = _read_native_result(path)
    if persisted != receipt:
        raise ValueError("Persisted canonical receipt differs from the returned measurement")
    artifacts = {"arena_evaluation_id": receipt["evaluation_id"], "arena_receipt": str(path),
                 "arena_receipt_sha256": digest, "arena_raw_direction": task["direction"],
                 "arena_raw_metric": task["metric"], "arena_candidate_sha256": candidate_sha,
                 "arena_fitness_transform": _json(config["fitness"])}
    if "prepared_environment" in config["binding"]:
        artifacts["arena_prepared_environment"] = _json(config["binding"]["prepared_environment"])
    if receipt.get("status") != "completed" or receipt.get("validity") is not True:
        artifacts.update(error_type="ArenaEvaluationUnavailable", error="No explicitly valid completed canonical result")
        return {"ok": False, "score": 0.0, "cases": {}, "artifacts": artifacts}
    raw, fitness = receipt.get("raw_score"), receipt.get("fitness")
    if (not _finite(raw) or not _finite(fitness)
            or fitness != (raw if task["direction"] == "maximize" else -raw)):
        raise ValueError("Canonical raw score and objective direction disagree with fitness")
    return {"ok": True, "score": search_score(fitness, config["fitness"]),
            "cases": {"raw_score": raw, "canonical_fitness": fitness, "validity": 1.0}, "artifacts": artifacts}


def full(config, program_path):
    """Exactly one canonical evaluation, with both raw and search metrics retained."""
    return _measurement(validate_config(config), program_path)


def confirm(config, program_path, n):
    """Perform independent trials; never relabel a cached/full result as confirmation."""
    verified = validate_config(config)
    declared = config["confirmation"]
    if not declared["stochastic"] or type(n) is not int or n != declared["samples"]:
        raise ValueError("Confirmation count must equal the explicitly declared stochastic contract")
    trials = []
    for _ in range(n):
        result = _measurement(verified, program_path)
        trials.append(result)
        if not result["ok"]:
            break
    artifacts = {"arena_trial_receipts": _json([item["artifacts"] for item in trials]),
                 "arena_fitness_transform": _json(config["fitness"]),
                 "arena_confirmation": "arithmetic mean of independent canonical scores, then declared transform"}
    if len(trials) != n or any(not item["ok"] for item in trials):
        artifacts.update(error_type="ArenaConfirmationUnavailable", error="At least one confirmation trial failed")
        return {"ok": False, "score": 0.0, "cases": {}, "artifacts": artifacts}
    if len({item["artifacts"]["arena_candidate_sha256"] for item in trials}) != 1:
        raise ValueError("Candidate changed between confirmation trials")
    cases = {key: statistics.mean(item["cases"][key] for item in trials)
             for key in ("raw_score", "canonical_fitness", "validity")}
    cases["n_trials"] = float(n)
    return {"ok": True, "score": search_score(cases["canonical_fitness"], config["fitness"]),
            "cases": cases, "artifacts": artifacts}
