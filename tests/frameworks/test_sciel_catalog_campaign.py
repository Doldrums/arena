"""Campaign preparation binds inert seed receipts; no Docker or provider calls."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

from arena import task_library
from arena.frameworks import evaluation

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("sciel_catalog_campaign",
    ROOT / "scripts/deployment/prepare_sciel_catalog_campaign.py")
campaign = importlib.util.module_from_spec(spec)
spec.loader.exec_module(campaign)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def prepared_inputs(tmp_path, monkeypatch, release_fixture):
    root = tmp_path.resolve()
    tasks = root / "tasks"
    definition = tasks / "suite/fixture"
    definition.mkdir(parents=True)
    (definition / "initial_program.py").write_text("raise AssertionError('seed execution forbidden')\n")
    (definition / "evaluator.py").write_text("raise AssertionError('host evaluator import forbidden')\n")
    (definition / "task.json").write_text(json.dumps({"execution": {"suite": {
        "initial_program": "initial_program.py", "requires": ["py:numpy"], "env": {}}}}))
    problem = definition / "problem.json"
    problem.write_text(json.dumps({"parameters": {"n": 4}, "contract": "construct() -> list"}))
    registry = root / "registry"
    registry.mkdir()
    manifest_path = registry / "task-library-manifest.json"
    manifest_path.write_text(json.dumps({"schema": "arena.task-library/1", "files": {
        path.relative_to(tasks).as_posix(): digest(path) for path in definition.iterdir()}}))
    source = {"id": "arena-tasks", "kind": "bundled", "root_path": "tasks",
              "manifest_path": "registry/task-library-manifest.json", "manifest_sha256": digest(manifest_path)}
    task = {"id": "fixture", "name": "Finite minimization fixture", "source_id": "arena-tasks",
        "executable": True, "direction": "minimize", "protocol": "original", "metric": "energy",
        "family": "test", "contract": "construct() -> list", "requirements": ["py:numpy"],
        "contract_source": {"path": "suite/fixture/problem.json", "sha256": digest(problem)}}
    pending = {**task, "id": "pending", "executable": False}
    catalog = {"sources": [source], "tasks": [task, pending]}
    monkeypatch.setattr(task_library, "resolve_registry_root", lambda _: registry)
    monkeypatch.setattr(evaluation, "get_catalog", lambda: catalog)
    monkeypatch.setattr(campaign, "get_catalog", lambda: catalog)
    monkeypatch.setattr(campaign, "COMMIT", release_fixture["binding"]["repository"]["commit"])
    monkeypatch.setattr(campaign, "VERSION", release_fixture["reference"]["version"])
    def no_evaluation(*_, **__):
        pytest.fail("Preparation must not execute an evaluator")
    monkeypatch.setattr(evaluation, "evaluate", no_evaluation)
    identity = task_library.verify_task_library(tasks, source)
    preflight = root / "preflight"
    (preflight / "fixture").mkdir(parents=True)
    receipt_path = preflight / "fixture/receipt.json"
    image = "sha256:" + "c" * 64
    receipt = {"schema": "arena.evaluation/1", "task_id": "fixture", "evaluation_id": "seed-fixture",
        "direction": "minimize", "metric": "energy", "protocol": "original", "status": "completed",
        "validity": True, "raw_score": 12.0, "fitness": -12.0, "wall_seconds": 0.25,
        "candidate_sha256": digest(definition / "initial_program.py"),
        "evaluator_sha256": digest(definition / "evaluator.py"), "problem_sha256": digest(problem),
        "task_source": identity, "receipt_path": str(receipt_path),
        "execution": {"kind": "docker", "image": image, "python": "python"}}
    receipt_path.write_text(json.dumps(receipt))
    rows = [{"task_id": t["id"], **{key: t[key] for key in
        ("family", "protocol", "metric", "direction", "requirements")},
        "status": "seed_verified" if t["executable"] else "evaluation_integration_pending",
        "reason": None if t["executable"] else "No executable evaluator definition."}
        for t in catalog["tasks"]]
    rows[0].update(seed_evaluation={key: receipt[key] for key in campaign.SEED_FIELDS},
                   receipt_sha256=digest(receipt_path))
    preflight_path = preflight / "manifest.json"
    preflight_path.write_text(json.dumps({"schema": "arena.sciel-catalog-preflight/1",
        "task_source": identity, "model_calls": 0, "image": image, "timeout_seconds": 30,
        "tasks": rows, "counts": {"seed_verified": 1, "evaluation_integration_pending": 1}}))
    approval = release_fixture["path"].parent / (release_fixture["digest"] + ".json")
    approval.write_bytes(release_fixture["path"].read_bytes())
    approval.chmod(0o600)
    args = {"tasks_root": tasks, "config_destination": root / "configs/campaign",
        "native_tasks": root / "native-tasks/campaign", "preflight_manifest": preflight_path,
        "deployment": release_fixture["path"], "approval": approval,
        "campaign": "catalog-fixture", "python": Path(sys.executable), "model": "gpt-5.5"}
    return args, preflight_path, receipt_path, catalog


def test_only_verified_seeds_get_bounded_templates_and_all_tasks_stay_in_inventory(prepared_inputs):
    args, preflight_path, receipt_path, _ = prepared_inputs
    before = (preflight_path.read_bytes(), receipt_path.read_bytes())
    summary = campaign.prepare(**args)
    assert summary["counts"] == {"prepared": 1, "pending": 1}
    assert summary["model_calls"] == 0 and summary["queue_mutated"] is False
    templates = json.loads((args["config_destination"] / "templates.json").read_text())
    assert len(templates) == 1
    template = templates[0]
    assert template["model"] == "gpt-5.5" and template["resources"] == campaign.RESOURCES
    assert template["spec"]["timeout_seconds"] == 3600 and template["spec"]["environment_names"] == []
    request = template["spec"]["request"]
    assert request["seed"] == 0 and request["budget"] == 16 and request["campaign"] == args["campaign"]
    config = json.loads(Path(request["config"]).read_text())
    assert config["max_iterations"] == 32 and config["confirm_records"] is True
    assert config["embed_grid"] is config["embed_niche"] is False
    assert config["parallel_search"]["workers"] == config["parallel_search"]["host_evaluator_slots"] == 1
    assert config["research"]["max_aux_calls"] == 4 and config["research"]["max_experiments"] == 48
    assert config["llm"]["models"] == ["gpt-5.5"] and config["llm"]["api_base"] == campaign.GATEWAY
    bridge = json.loads((Path(request["tasks_root"]) / "arena/fixture/evaluation.json").read_text())
    assert bridge["fitness"]["scale"] == 12 and digest(receipt_path) in bridge["fitness"]["basis"]
    assert bridge["evaluation"]["tasks_dir"] == str(args["tasks_root"])
    assert bridge["evaluation"]["execution"]["require_control_cgroup"] is True
    assert bridge["confirmation"] == {"stochastic": True, "samples": 3}
    inventory = json.loads((args["config_destination"] / "campaign-inventory.json").read_text())
    assert inventory["preflight_finished"] is False
    assert inventory["tasks"][1]["preflight_status"] == "evaluation_integration_pending"
    assert inventory["tasks"][0]["native_runtime_conformance"] == "pending_first_run"
    assert before == (preflight_path.read_bytes(), receipt_path.read_bytes())
    with pytest.raises(ValueError, match="new and separate"):
        campaign.prepare(**args)


@pytest.mark.parametrize("mutation", ["digest", "image", "direction"])
def test_forged_seed_success_never_creates_a_template(prepared_inputs, mutation):
    args, preflight_path, receipt_path, _ = prepared_inputs
    manifest = json.loads(preflight_path.read_text())
    receipt = json.loads(receipt_path.read_text())
    if mutation == "digest":
        receipt["fitness"] = -10
    elif mutation == "image":
        receipt["execution"]["image"] = "sha256:" + "d" * 64
    else:
        receipt["raw_score"], receipt["fitness"] = 10.0, 10.0
    receipt_path.write_text(json.dumps(receipt))
    if mutation != "digest":
        manifest["tasks"][0]["receipt_sha256"] = digest(receipt_path)
        manifest["tasks"][0]["seed_evaluation"] = {key: receipt[key] for key in campaign.SEED_FIELDS}
        preflight_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="receipt|fitness"):
        campaign.prepare(**args)
    assert not (args["config_destination"] / "templates.json").exists()


def test_incomplete_inventory_cannot_silently_omit_pending_catalog_tasks(prepared_inputs):
    args, preflight_path, _, _ = prepared_inputs
    manifest = json.loads(preflight_path.read_text())
    manifest["tasks"].pop()
    preflight_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="every current catalog task"):
        campaign.prepare(**args)
    assert not args["config_destination"].exists()


def test_verified_seed_can_remain_pending_when_native_contract_needs_more_integration(prepared_inputs):
    args, _, _, catalog = prepared_inputs
    catalog["tasks"][0]["contract"] = "Interface too long. " * 160
    summary = campaign.prepare(**args)
    assert summary["counts"] == {"pending": 2}
    assert json.loads((args["config_destination"] / "templates.json").read_text()) == []
    inventory = json.loads((args["config_destination"] / "campaign-inventory.json").read_text())
    assert "1600" in inventory["tasks"][0]["reason"]


def test_explicit_pilot_exclusion_never_materializes_another_run(prepared_inputs):
    args, _, _, _ = prepared_inputs
    summary = campaign.prepare(**args, exclude_tasks=["fixture"])
    assert summary["counts"] == {"excluded": 1, "pending": 1}
    assert json.loads((args["config_destination"] / "templates.json").read_text()) == []
    assert list(args["native_tasks"].iterdir()) == []
    assert summary["model_calls"] == 0 and summary["queue_mutated"] is False


def test_explicit_new_build_preserves_source_pin_and_exact_approval(prepared_inputs):
    from arena.release_deployment import binding_digest
    args, _, _, _ = prepared_inputs
    version = f"0.2.0+arena.{campaign.COMMIT[:8]}.worker2"
    deployment = json.loads(args["deployment"].read_text())
    deployment["release"]["version"] = deployment["binding"]["version"] = version
    deployment["binding_sha256"] = binding_digest(deployment["binding"])
    args["deployment"].write_text(json.dumps(deployment))
    approval = args["approval"].parent / (digest(args["deployment"]) + ".json")
    approval.write_bytes(args["deployment"].read_bytes())
    approval.chmod(0o600)
    args["approval"] = approval
    with pytest.raises(ValueError, match="exact approved"):
        campaign.prepare(**args)
    result = campaign.prepare(**args, release_version=version)
    assert result["counts"]["prepared"] == 1
    inventory = json.loads((args["config_destination"] / "campaign-inventory.json").read_text())
    assert inventory["release"]["version"] == version


@pytest.mark.parametrize("version", ["0.3.0", "0.2.0+arena.00000000.worker2", "latest", 123])
def test_new_build_option_cannot_relax_the_native_source_contract(prepared_inputs, version):
    args, _, _, _ = prepared_inputs
    with pytest.raises(ValueError, match="pinned SCiEL 0.2.0"):
        campaign.prepare(**args, release_version=version)
    assert not args["config_destination"].exists()


@pytest.mark.parametrize("mutation", [None, "data", "image", "implicit"])
def test_science_preflight_requires_the_explicit_immutable_environment(prepared_inputs, mutation):
    from arena.frameworks.sciel_catalog_profile import SCIENCE_IMAGE_ID, SCIENCE_PROFILE, science_environment
    _, path, _, catalog = prepared_inputs
    manifest = json.loads(path.read_text())
    identity = manifest["task_source"]
    manifest.update(group="science", profile=SCIENCE_PROFILE, image=SCIENCE_IMAGE_ID,
                    prepared_environment=science_environment(SCIENCE_IMAGE_ID))
    if mutation == "data":
        manifest["prepared_environment"]["data_lock_sha256"] = "0" * 64
    elif mutation == "image":
        manifest["image"] = "sha256:" + "0" * 64
    elif mutation == "implicit":
        manifest["group"] = "all"
    if mutation is None:
        tasks, rows = campaign.preflight_records(manifest, catalog, identity)
        assert len(tasks) == len(rows) == 2
    else:
        with pytest.raises(ValueError, match="science|reviewed image"):
            campaign.preflight_records(manifest, catalog, identity)
