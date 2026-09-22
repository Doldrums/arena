"""Private integration evidence is checked without running models or candidates."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "sciel_catalog_conformance", ROOT / "scripts/deployment/sciel_catalog_conformance.py")
conformance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(conformance)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    sha = "a" * 64
    source = {"kind": "bundled", "id": "arena-tasks", "manifest_sha256": sha}
    release = {"version": "fixture", "id": "sciel"}
    image = "sha256:" + "b" * 64
    deployment = {"image": {"reference": "fixture@" + image, "image_id": image},
                  "source": {"commit": "c" * 40, "tree": "d" * 40}}
    monkeypatch.setattr(conformance, "load_manifest", lambda *a, **kw: (deployment, sha))
    inventory = {"model": "gpt-5.5", "task_source": source, "release": release,
                 "deployment_sha256": sha, "canonical_image": image, "tasks": []}
    proof = {"schema": "arena.sciel-catalog-conformance/1", "status": "verified",
             "conformance": "runtime_integration_observed", "science_success": False,
             "model": "gpt-5.5", "task_source": source, "release": release, "runs": []}
    templates = []

    def artifact(name, value):
        return {"path": name, "sha256": write(root / name, value)}

    for index in range(3):
        task_id, template_id, run_id = f"task-{index}", f"pilot-{index}", f"{index:032x}"
        task_root = root / "native/arena" / task_id
        task_root.mkdir(parents=True)
        seed = task_root / "initial_program.py"
        seed.write_text("raise AssertionError('must never execute')\n")
        candidate = hashlib.sha256(seed.read_bytes()).hexdigest()
        binding = {"task_source": source, "seed_sha256": candidate, "evaluator_sha256": sha,
                   "problem_sha256": sha, "protocol": "fixture", "metric": "cost", "direction": "minimize"}
        write(task_root / "evaluation.json", {"binding": binding})
        templates.append({"id": template_id, "model": "gpt-5.5", "spec": {"request": {
            "release": release, "deployment": str(root / "deployment.json"), "tasks_root": str(root / "native")}}})
        inventory["tasks"].append({"template_id": template_id, "task_id": task_id})
        run = {"run_id": run_id, "task_id": task_id, "template_id": template_id,
               "model": "gpt-5.5", "release": release, "task_source": source,
               "contract": "sciel-cli-v1", "baseline": {"full_plus_confirm_valid": True},
               "snapshot_sha256": sha, "control_revision": sha, "batch_id": "pilot-fixture",
               "deployment_sha256": sha, "image_reference": deployment["image"]["reference"],
               "image_id": image, "source_commit": deployment["source"]["commit"],
               "source_tree": deployment["source"]["tree"], "canonical_image": image,
               "candidate_sha256": candidate, "canonical_receipts": [], "model_calls_observed": 1,
               **{key: binding[key] for key in ("evaluator_sha256", "problem_sha256", "protocol", "metric", "direction")}}
        for trial in range(4):
            receipt = {"schema": "arena.evaluation/1", "evaluation_id": f"evaluation-{index}-{trial}",
                       "status": "completed", "validity": True, "raw_score": 10.0, "fitness": -10.0,
                       "control": {"run_id": run_id}, "execution": {"kind": "docker", "image": image,
                       "python": "python", "require_control_cgroup": True},
                       **{key: run[key] for key in ("task_id", "task_source", "candidate_sha256",
                          "evaluator_sha256", "problem_sha256", "protocol", "metric", "direction")}}
            descriptor = artifact(f"{run_id}/receipt-{trial}.json", receipt)
            descriptor["role"] = "full" if trial == 0 else "confirm"
            run["canonical_receipts"].append(descriptor)
        run["native_confirmation"] = artifact(f"{run_id}/confirmation.json", {
            "schema": "arena.native-confirmation-evidence/1", "ok": True, "confirmed_sampled": True,
            "candidate_sha256": candidate, "source_sha256": sha, "task_hash": sha,
            "canonical_evaluation_ids": [f"evaluation-{index}-{trial}" for trial in (1, 2, 3)],
            "cases": {"n_trials": 3, "validity": 1, "raw_score": 10.0, "canonical_fitness": -10.0}})
        run["model_call_evidence"] = artifact(f"{run_id}/calls.json", {
            "schema": "arena.model-call-evidence/1", "run_id": run_id,
            "calls": [{"model": "gpt-5.5", "resolved_model": "gpt-5.5",
                       "source_sha256": sha, "request_sha256": sha}]})
        proof["runs"].append(run)
    path = root / "manifest.json"
    write(path, proof)
    kwargs = {"pilot_inventory": inventory, "pilot_templates": templates,
              "model": "gpt-5.5", "task_source": source}
    return path, proof, kwargs


def test_accepts_observed_integration_without_scientific_success_claim(evidence):
    path, proof, kwargs = evidence
    result = conformance.validate_conformance(path, **kwargs)
    assert result["run_ids"] == sorted(run["run_id"] for run in proof["runs"])
    assert result["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert proof["science_success"] is False


@pytest.mark.parametrize("mutation", ["digest", "duplicate", "model", "mean", "public", "traversal", "invalid"])
def test_rejects_tampered_evidence(evidence, mutation):
    path, proof, kwargs = evidence
    run = proof["runs"][0]
    if mutation == "public":
        path.chmod(0o644)
    else:
        descriptor = run["canonical_receipts"][1]
        if mutation == "model":
            descriptor = run["model_call_evidence"]
        elif mutation == "mean":
            descriptor = run["native_confirmation"]
        target = path.parent / descriptor["path"]
        data = json.loads(target.read_text())
        if mutation == "duplicate":
            data["evaluation_id"] = "evaluation-0-0"
        elif mutation == "model":
            data["calls"][0]["model"] = "different-model"
        elif mutation == "mean":
            data["cases"]["raw_score"] = 11.0
        elif mutation == "invalid":
            data["validity"] = False
        else:
            data["raw_score"] = 20.0
        digest = write(target, data)
        if mutation != "digest":
            descriptor["sha256"] = digest
        if mutation == "traversal":
            descriptor["path"] = "../receipt.json"
        write(path, proof)
    with pytest.raises(ValueError, match="Pilot conformance"):
        conformance.validate_conformance(path, **kwargs)
