"""Translate canonical Arena receipts into Shinka's native evaluator files.

Only the explicit evaluator entrypoint runs candidate evaluation. Importing
this module or creating a task never imports Shinka or candidate programs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import uuid


_WRAPPER = '''"""Canonical Arena evaluator for this generated Shinka task."""
from arena.frameworks.shinka_evaluate import main

# Shinka copies only this Python source into its run directory. Keep the
# validated, nonsecret configuration in that same provenance-hashed artifact.
ARENA_EVALUATION_CONFIG_JSON = {config_json}
ARENA_EVALUATION_CONFIG_SHA256 = {config_sha256}

if __name__ == "__main__":
    raise SystemExit(main(config_json=ARENA_EVALUATION_CONFIG_JSON,
                          config_sha256=ARENA_EVALUATION_CONFIG_SHA256))
'''


def _canonical_api():
    from arena.frameworks import evaluation
    return evaluation


def _absolute(value, label):
    if not isinstance(value, (str, Path)) or not Path(value).is_absolute():
        raise ValueError(f"{label} must be an absolute path")
    return Path(value).resolve()


def _write_json(path, value):
    payload = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=".arena-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def create_task(config: dict, destination: Path) -> dict:
    """Explicitly create a native task from the pin-verified canonical seed."""
    if Path(destination).is_symlink():
        raise ValueError("Task destination must not be a symlink")
    destination = _absolute(destination, "destination")
    if destination.exists():
        raise ValueError("Task destination already exists; refusing to replace it")
    api = _canonical_api()
    verified = api.validate_config(config)
    checked = verified["config"]
    payload = json.dumps(checked, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    if len(payload.encode("utf-8")) > 64 * 1024:
        raise ValueError("Evaluation configuration is too large")
    config_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    source = Path(verified["source_dir"])
    if destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError("Generated task must be outside the task-source tree")
    if checked.get("receipts_dir"):
        receipts = _absolute(checked["receipts_dir"], "receipts_dir")
        if receipts.is_relative_to(destination) or destination.is_relative_to(receipts):
            raise ValueError("Receipts must be outside the generated task input tree")
    seed = source / "suite" / checked["task_id"] / "initial_program.py"
    plan = api.prepare_evaluation(checked, seed, destination / "arena-evaluation")
    seed_bytes = seed.read_bytes()
    seed_hash = hashlib.sha256(seed_bytes).hexdigest()
    if seed_hash != plan["candidate_sha256"]:
        raise ValueError("Pinned task seed changed during preparation")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".arena-shinka-task-", dir=destination.parent) as staging:
        stage = Path(staging) / "task"
        stage.mkdir()
        (stage / "initial.py").write_bytes(seed_bytes)
        (stage / "evaluate.py").write_text(_WRAPPER.format(config_json=repr(payload),
                                                         config_sha256=repr(config_sha256)), encoding="utf-8")
        _write_json(stage / "evaluation.json", checked)
        if destination.exists():
            raise ValueError("Task destination appeared during preparation")
        stage.rename(destination)
    return {"task_dir": str(destination), "task_id": checked["task_id"],
            "seed_source": str(seed), "seed_sha256": seed_hash,
            "evaluation_config_sha256": config_sha256,
            "files": [str(destination / name) for name in ("initial.py", "evaluate.py", "evaluation.json")],
            "canonical_evaluation_configured": True, "evaluation_performed": False}


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _receipt_evidence(receipt, verified, output):
    if (type(receipt) is not dict or receipt.get("schema") != "arena.evaluation/1"
            or receipt.get("task_id") != verified["config"]["task_id"]
            or receipt.get("direction") != verified["task"]["direction"]
            or not isinstance(receipt.get("evaluation_id"), str) or not receipt["evaluation_id"]):
        raise ValueError("Canonical receipt does not match the requested task")
    path = _absolute(receipt.get("receipt_path"), "receipt_path")
    if (Path(receipt["receipt_path"]).is_symlink() or not path.is_file()
            or not path.is_relative_to(output) or path.stat().st_size > 4 * 1024 * 1024):
        raise ValueError("Canonical receipt is not bound to this evaluation output")
    data = path.read_bytes()
    if json.loads(data) != receipt:
        raise ValueError("Canonical receipt differs from the recorded artifact")
    return hashlib.sha256(data).hexdigest()


def evaluate_candidate(config: dict, program_path: Path, results_dir: Path) -> dict:
    """Run the explicit canonical evaluator and publish native result files."""
    program = _absolute(program_path, "program_path")
    results = _absolute(results_dir, "results_dir")
    results.mkdir(parents=True, exist_ok=True)
    # Fail closed if a timeout interrupts publication or this directory is reused.
    _write_json(results / "correct.json", {"correct": False, "error": "Canonical evaluation has not completed"})
    _write_json(results / "metrics.json", {"combined_score": None, "public": {}, "private": {},
                                          "text_feedback": "Canonical evaluation has not completed"})
    receipt = None
    failure = None
    receipt_hash = None
    try:
        api = _canonical_api()
        verified = api.validate_config(config)
        checked = verified["config"]
        receipt_root = _absolute(checked["receipts_dir"], "receipts_dir") if checked.get("receipts_dir") else results / "arena-evaluation"
        if checked.get("execution", {}).get("require_control_cgroup") is True:
            receipt_root = api.receipt_root(checked, receipt_root)
        receipt_output = receipt_root / uuid.uuid4().hex
        receipt = api.evaluate(checked, program, receipt_output)
        receipt_hash = _receipt_evidence(receipt, verified, receipt_output)
        raw, fitness = receipt.get("raw_score"), receipt.get("fitness")
        valid = (receipt.get("validity") is True and receipt.get("status") == "completed"
                 and _finite(raw) and _finite(fitness)
                 and fitness == (raw if receipt["direction"] == "maximize" else -raw))
        if not valid:
            failure = "Canonical evaluator did not establish a completed, explicitly valid, finite fitness"
    except Exception as exc:
        # A configuration or execution exception must not reuse an earlier score.
        # Avoid copying arbitrary exception text that might include credentials.
        valid = False
        failure = f"Canonical evaluation failed ({type(exc).__name__})"
    evidence = {}
    if receipt_hash is not None:
        for key in ("evaluation_id", "task_id", "status", "direction", "receipt_path"):
            value = receipt.get(key)
            evidence[key] = value if isinstance(value, str) else None
        evidence["validity"] = receipt.get("validity") if type(receipt.get("validity")) is bool else None
        for key in ("raw_score", "fitness"):
            evidence[key] = receipt.get(key) if _finite(receipt.get(key)) else None
        evidence["receipt_sha256"] = receipt_hash
    metrics = {"combined_score": receipt["fitness"] if valid else None,
               "public": {}, "private": {"arena_evaluation": evidence},
               "text_feedback": "Canonical Arena evaluation completed; see the recorded receipt" if valid else failure}
    if evidence.get("raw_score") is not None:
        metrics["public"]["arena_raw_score"] = evidence["raw_score"]
    _write_json(results / "metrics.json", metrics)
    _write_json(results / "correct.json", {"correct": valid, "error": failure})
    return {"correct": valid, "metrics": metrics, "receipt": receipt, "error": failure}


def main(argv=None, *, config_path: Path | None = None, config_json: str | None = None,
         config_sha256: str | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program_path", required=True, type=Path)
    parser.add_argument("--results_dir", required=True, type=Path)
    parser.add_argument("--config", type=Path, required=config_path is None and config_json is None)
    args = parser.parse_args(argv)
    path = config_path or args.config
    try:
        if config_json is not None:
            if config_path is not None or args.config is not None or type(config_json) is not str:
                raise ValueError("Generated evaluation configuration cannot be overridden")
            payload = config_json.encode("utf-8")
            if hashlib.sha256(payload).hexdigest() != config_sha256:
                raise ValueError("Generated evaluation configuration digest mismatch")
        else:
            if path.stat().st_size > 64 * 1024:
                raise ValueError("Evaluation configuration is too large")
            payload = path.read_bytes()
        if len(payload) > 64 * 1024:
            raise ValueError("Evaluation configuration is too large")
        config = json.loads(payload)
    except (OSError, ValueError):
        # Publish a rejected result through the same fail-closed path.
        config = None
    evaluate_candidate(config, args.program_path, args.results_dir)
    # Invalid candidates are normal evaluator outcomes; correctness is in the
    # contract files. Nonzero exits would hide the canonical failure explanation.
    return 0 if (Path(args.results_dir) / "correct.json").is_file() else 1


if __name__ == "__main__":
    raise SystemExit(main())
