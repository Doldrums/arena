"""A narrowly reviewed SCiEL task bridge: syntax preflight, one real evaluation.

Creating a task and running smoke never execute upstream code. Calling full is
an explicit evaluation operation and delegates execution to Arena's evaluator.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import Path
import shutil
import tempfile
import uuid


PROFILE = "sciel-unit-interval/1"
TASK_ID = "reference-sat"
TASK_COMMIT = "5729caa7a3bd4e66c39a447c0d4ee56dc8fa0935"
_MAX_CANDIDATE = 10 * 1024 * 1024
_PROBLEM_SHA256 = "040f339b9871d23def130b429233b9d56b8a4fcaa0cdb86a1e6837771ada8ed9"
_SEED_SHA256 = "f0cc231aebfbb48c490cb28beee229ac5b133403d6c615e19789a4800e70d23d"
_ALLOWED_CONFIG = {"schema", "tasks_dir", "task_id", "timeout_seconds", "execution", "profile", "receipts_dir"}


def _profile(config):
    if type(config) is not dict or set(config) != _ALLOWED_CONFIG:
        raise ValueError("SCiEL bridge requires the exact evaluation-config fields plus profile and receipts_dir")
    if config.get("schema") != "arena.evaluation-config/1" or config.get("profile") != PROFILE:
        raise ValueError("Unknown SCiEL evaluation profile")
    if config.get("task_id") != TASK_ID:
        raise ValueError("This SCiEL profile supports only the reviewed reference-sat task")
    for key in ("tasks_dir", "receipts_dir"):
        if type(config[key]) is not str or "\x00" in config[key] or not Path(config[key]).is_absolute():
            raise ValueError(f"{key}: an absolute path is required")
    tasks, receipts = Path(config["tasks_dir"]).resolve(), Path(config["receipts_dir"]).resolve()
    if receipts == tasks or receipts.is_relative_to(tasks) or tasks.is_relative_to(receipts):
        raise ValueError("Receipts must be outside the task-source tree")
    return receipts


def _verified_source(config):
    from .evaluation import validate_config
    verified = validate_config(config)
    if verified["source"]["commit"] != TASK_COMMIT or verified["problem_sha256"] != _PROBLEM_SHA256:
        raise ValueError("The SCiEL unit-interval profile is bound to the reviewed task version")
    return verified


def create_task(config: dict, destination: Path) -> dict:
    """Write one native task package, after read-only source/config verification."""
    receipts = _profile(config)
    verified = _verified_source(config)
    destination = Path(destination)
    if not destination.is_absolute() or destination.exists() or destination.is_symlink():
        raise ValueError("destination must be a new absolute task directory")
    destination = destination.resolve()
    source = Path(verified["source_dir"]).resolve()
    if destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError("Generated task must be outside the upstream source tree")
    if destination.is_relative_to(receipts) or receipts.is_relative_to(destination):
        raise ValueError("Receipts must be outside the generated task input tree")
    seed = (source / "suite" / TASK_ID / "initial_program.py").read_bytes()
    if hashlib.sha256(seed).hexdigest() != _SEED_SHA256:
        raise ValueError("Reviewed SAT seed digest mismatch")
    timeout = config["timeout_seconds"]
    # JSON is valid YAML and avoids introducing a YAML parser into the adapter.
    task = {"suite": "arena", "name": TASK_ID, "origin": "math", "primary_metric": "arena_fitness",
            "case_metrics": ["raw_score", "validity"], "tiers": ["smoke", "full"],
            "stochastic": False, "smoke_timeout": 10, "full_timeout": timeout + 120,
            "confirm_timeout": timeout + 120,
            "resources": "cpu"}
    evaluator = '''"""Arena unit-interval bridge: preflight never evaluates the candidate."""
import json
from pathlib import Path
from arena.frameworks.sciel_evaluate import smoke as _smoke, full as _full


def smoke(program_path):
    return _smoke(program_path)


def full(program_path):
    config = json.loads(Path(__file__).with_name("evaluation.json").read_text())
    return _full(config, program_path)
'''
    prompt = ("Implement solve(instance) -> a list of booleans of length instance['n']. "
              "instance['clauses'] contains signed 1-based literals; a positive literal k reads assignment[k-1] "
              "and a negative literal reads its negation. Maximize the fraction of 10 generated satisfiable "
              "3-CNF instances solved (50 variables, fixed evaluator seed 0). Score is in [0, 1]. "
              "These are development-visible generated instances, not an independent audit or the paper dataset.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".arena-task-", dir=destination.parent))
    try:
        (temporary / "task.yaml").write_text(json.dumps(task, indent=2) + "\n")
        (temporary / "evaluation.json").write_text(json.dumps(config, indent=2) + "\n")
        (temporary / "evaluator.py").write_text(evaluator)
        (temporary / "initial_program.py").write_bytes(seed)
        (temporary / "README.md").write_text(prompt + "\n")
        temporary.rename(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return {"profile": PROFILE, "directory": str(destination), "qualified_task": "arena/reference-sat",
            "task_source_commit": TASK_COMMIT, "canonical_evaluation": True,
            "native_config": {"task": "arena/reference-sat", "confirm_records": False,
                              "llm": {"system_message": prompt}},
            "runtime_conformance": "not_verified"}


def smoke(program_path) -> dict:
    """Syntax-only check: never imports the candidate or calls an evaluator."""
    try:
        path = Path(program_path)
        if path.stat().st_size > _MAX_CANDIDATE:
            raise ValueError("Candidate exceeds the syntax preflight size limit")
        ast.parse(path.read_text(), filename="candidate.py")
    except (OSError, ValueError, SyntaxError, UnicodeError, RecursionError) as exc:
        return {"ok": False, "score": 0.0, "cases": {},
                "artifacts": {"error_type": "SyntaxPreflight", "error": str(exc)[:2000]}}
    return {"ok": True, "score": 0.0, "cases": {},
            "artifacts": {"preflight": "syntax_only_no_evaluation"}}


def full(config: dict, program_path) -> dict:
    """One canonical evaluation per call; fresh calls are never cached repeats."""
    receipts = _profile(config)
    # A source/config check is cheap metadata work, not another measurement.
    # Refuse future catalog revisions before dispatching an expensive evaluator.
    _verified_source(config)
    from .evaluation import evaluate
    if config.get("execution", {}).get("require_control_cgroup") is True:
        from .evaluation import receipt_root
        receipts = receipt_root(config, receipts)
    call_dir = receipts / uuid.uuid4().hex
    receipt = evaluate(config, Path(program_path), call_dir)
    if (receipt.get("schema") != "arena.evaluation/1" or receipt.get("task_id") != TASK_ID
            or receipt.get("direction") != "maximize" or not isinstance(receipt.get("evaluation_id"), str)
            or not receipt["evaluation_id"]):
        raise ValueError("Canonical receipt does not match the reviewed SCiEL profile")
    raw_path = receipt.get("receipt_path")
    if not isinstance(raw_path, str) or not Path(raw_path).is_absolute():
        raise ValueError("Canonical receipt path is missing")
    receipt_path = Path(raw_path)
    if receipt_path.is_symlink() or not receipt_path.is_file() or not receipt_path.resolve().is_relative_to(call_dir.resolve()):
        raise ValueError("Canonical receipt is not bound to this evaluation output")
    artifacts = {"arena_evaluation_id": receipt["evaluation_id"], "arena_receipt": str(receipt_path),
                 "arena_receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest()}
    raw, fitness = receipt.get("raw_score"), receipt.get("fitness")
    good_number = lambda value: type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1
    if receipt.get("status") == "completed" and receipt.get("validity") is True:
        if not good_number(raw) or not good_number(fitness) or raw != fitness:
            raise ValueError("SCiEL profile requires identical finite raw/fitness scores in [0, 1]")
        return {"ok": True, "score": fitness, "cases": {"raw_score": raw, "validity": 1.0}, "artifacts": artifacts}
    artifacts.update(error_type="ArenaEvaluationUnavailable", error="Canonical evaluation did not return an explicitly valid completed result")
    # 0 is only the native failure sentinel with ok=False, never a canonical score.
    return {"ok": False, "score": 0.0, "cases": {}, "artifacts": artifacts}
