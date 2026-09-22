"""Read-only validation of private, observed SCiEL pilot integration evidence.

This gate establishes model/evaluator wiring, not completion or scientific
success. The launcher independently checks live queue identities and capacity.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import statistics

from arena.release_deployment import load_manifest


def _require(value, message):
    if not value:
        raise ValueError("Pilot conformance: " + message)


def _hash(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _read(path, *, private=True):
    path = Path(path)
    _require(path.is_absolute() and path.resolve() == path and path.is_file(), "evidence path is linked or missing")
    info = path.stat()
    if private:
        _require(info.st_uid == os.getuid() and not stat.S_IMODE(info.st_mode) & 0o077,
                 "evidence must be owned and private")
    _require(info.st_size <= 4 * 1024 * 1024, "evidence exceeds size limit")
    raw = path.read_bytes()
    _require(len(raw) <= 4 * 1024 * 1024, "evidence grew beyond size limit")
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, "duplicate evidence field")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite evidence")))
    _require(type(value) is dict, "evidence must be an object")
    return value, hashlib.sha256(raw).hexdigest()


def _artifact(root, descriptor):
    _require(type(descriptor) is dict and _hash(descriptor.get("sha256")), "artifact digest missing")
    relative = descriptor.get("path")
    _require(type(relative) is str and relative and not PurePosixPath(relative).is_absolute()
             and "\\" not in relative and all(p not in {"", ".", ".."} for p in relative.split("/")),
             "artifact must be a contained relative path")
    value, digest = _read(root / relative)
    _require(digest == descriptor["sha256"], "artifact digest mismatch")
    return value


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _receipts(root, run):
    refs = run.get("canonical_receipts")
    _require(type(refs) is list and len(refs) == 4, "one full and three confirmation receipts required")
    _require([ref.get("role") for ref in refs].count("full") == 1
             and [ref.get("role") for ref in refs].count("confirm") == 3, "incorrect evaluation roles")
    rows, trials = [], []
    expected = {"schema": "arena.evaluation/1", "task_id": run["task_id"], "status": "completed",
                "validity": True, "task_source": run["task_source"], "candidate_sha256": run["candidate_sha256"],
                "evaluator_sha256": run["evaluator_sha256"], "problem_sha256": run["problem_sha256"],
                "protocol": run["protocol"], "metric": run["metric"], "direction": run["direction"]}
    for ref in refs:
        receipt = _artifact(root, ref)
        _require(all(receipt.get(k) == v for k, v in expected.items()), "canonical task or validity differs")
        _require(receipt.get("control", {}).get("run_id") == run["run_id"], "canonical run identity differs")
        _require(receipt.get("execution") == {"kind": "docker", "image": run["canonical_image"],
                 "python": "python", "require_control_cgroup": True}, "canonical execution profile differs")
        raw, fitness = receipt.get("raw_score"), receipt.get("fitness")
        _require(_finite(raw) and _finite(fitness) and run["direction"] in {"maximize", "minimize"}
                 and fitness == (raw if run["direction"] == "maximize" else -raw), "raw objective differs")
        _require(type(receipt.get("evaluation_id")) is str and receipt["evaluation_id"], "evaluation ID missing")
        rows.append(receipt)
        if ref["role"] == "confirm":
            trials.append(receipt)
    _require(len({row["evaluation_id"] for row in rows}) == 4, "evaluations must be independent")
    proof = _artifact(root, run["native_confirmation"])
    cases = proof.get("cases", {})
    _require(proof.get("schema") == "arena.native-confirmation-evidence/1"
             and proof.get("ok") is True and proof.get("confirmed_sampled") is True
             and proof.get("candidate_sha256") == run["candidate_sha256"]
             and _hash(proof.get("source_sha256")) and _hash(proof.get("task_hash"))
             and cases.get("n_trials") == 3 and cases.get("validity") == 1
             and set(proof.get("canonical_evaluation_ids", [])) == {r["evaluation_id"] for r in trials}
             and cases.get("raw_score") == statistics.mean(r["raw_score"] for r in trials)
             and cases.get("canonical_fitness") == statistics.mean(r["fitness"] for r in trials),
             "native confirmed result differs from its three canonical trials")


def validate_conformance(path, *, pilot_inventory, pilot_templates, model, task_source):
    path = Path(path)
    proof, digest = _read(path)
    _require(proof.get("schema") == "arena.sciel-catalog-conformance/1" and proof.get("status") == "verified"
             and proof.get("conformance") == "runtime_integration_observed" and proof.get("science_success") is False,
             "expected observed integration evidence without a science-success claim")
    _require(proof.get("model") == model == pilot_inventory.get("model")
             and proof.get("task_source") == task_source == pilot_inventory.get("task_source")
             and proof.get("release") == pilot_inventory.get("release"), "campaign identity differs")
    templates = (pilot_templates if type(pilot_templates) is dict else {t["id"]: t for t in pilot_templates})
    inventory = {row["template_id"]: row for row in pilot_inventory["tasks"] if row.get("template_id") in templates}
    runs = proof.get("runs")
    _require(type(runs) is list and len(runs) == len(templates) >= 3
             and {r.get("template_id") for r in runs} == set(templates) == set(inventory)
             and len({r.get("run_id") for r in runs}) == len(runs), "every pilot requires distinct run evidence")
    for run in runs:
        template = templates[run["template_id"]]
        request = template["spec"]["request"]
        _require(re.fullmatch(r"[0-9a-f]{32}", run.get("run_id", "")) is not None
                 and run.get("task_id") == inventory[run["template_id"]]["task_id"]
                 and run.get("model") == model == template["model"]
                 and run.get("release") == proof["release"] == request["release"]
                 and run.get("task_source") == task_source and run.get("contract") == "sciel-cli-v1"
                 and run.get("baseline", {}).get("full_plus_confirm_valid") is True
                 and _hash(run.get("snapshot_sha256")) and _hash(run.get("control_revision"))
                 and type(run.get("batch_id")) is str and run["batch_id"], "pilot binding differs")
        deployment, deployment_sha = load_manifest(request["deployment"], expected_release=proof["release"])
        _require(run.get("deployment_sha256") == deployment_sha == pilot_inventory["deployment_sha256"]
                 and run.get("image_reference") == deployment["image"]["reference"]
                 and run.get("image_id") == deployment["image"]["image_id"]
                 and run.get("source_commit") == deployment["source"]["commit"]
                 and run.get("source_tree") == deployment["source"]["tree"]
                 and run.get("canonical_image") == pilot_inventory["canonical_image"], "engine deployment differs")
        task_root = Path(request["tasks_root"]) / "arena" / run["task_id"]
        bridge, _ = _read(task_root / "evaluation.json", private=False)
        binding = bridge.get("binding", {})
        seed = task_root / "initial_program.py"
        _require(seed.is_file() and seed.resolve() == seed and seed.stat().st_size <= 16 * 1024 * 1024,
                 "seed source is missing or linked")
        _require(hashlib.sha256(seed.read_bytes()).hexdigest() == run.get("candidate_sha256") == binding.get("seed_sha256")
                 and all(run.get(k) == binding.get(k) for k in
                         ("task_source", "evaluator_sha256", "problem_sha256", "protocol", "metric", "direction")),
                 "native task binding differs")
        _receipts(path.parent, run)
        calls = _artifact(path.parent, run["model_call_evidence"])
        _require(calls.get("schema") == "arena.model-call-evidence/1" and calls.get("run_id") == run["run_id"]
                 and type(calls.get("calls")) is list and len(calls["calls"]) == run.get("model_calls_observed", 0)
                 and len(calls["calls"]) >= 1, "no recorded model calls")
        _require(all(call.get("model") == model and call.get("resolved_model") in {None, model}
                     and _hash(call.get("source_sha256")) and _hash(call.get("request_sha256"))
                     for call in calls["calls"]), "model call evidence differs")
    return {"run_ids": sorted(row["run_id"] for row in runs), "task_ids": sorted(row["task_id"] for row in runs),
            "sha256": digest, "runs": runs}
