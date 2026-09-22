"""Fresh Torch evidence must bind library, evaluator, immutable image and resources."""
import json
from pathlib import Path

import pytest

from arena import task_library
from arena.evaluation_resources import worker_resources
from arena.frameworks import sciel_catalog_torch as torch
from test_sciel_catalog_campaign import prepared_inputs, campaign, digest


@pytest.fixture
def torch_inputs(prepared_inputs, request):
    args, path, old_receipt_path, catalog = prepared_inputs
    group = getattr(request, "param", "torch-cpu-2g")
    name = next(name for name, reqs in torch.TORCH_TASK_REQUIREMENTS.items()
                if torch.torch_task_group(name, list(reqs)) == group)
    requirements = list(torch.TORCH_TASK_REQUIREMENTS[name])
    tasks_root = args["tasks_root"]
    definition = tasks_root / "suite" / name
    (tasks_root / "suite/fixture").rename(definition)
    task_json = definition / "task.json"
    data = json.loads(task_json.read_text())
    data["execution"]["suite"]["requires"] = requirements
    task_json.write_text(json.dumps(data))
    source = catalog["sources"][0]
    library_manifest = tasks_root.parent / "registry/task-library-manifest.json"
    library_manifest.write_text(json.dumps({"schema": "arena.task-library/1", "files": {
        p.relative_to(tasks_root).as_posix(): digest(p) for p in definition.iterdir()}}))
    source["manifest_sha256"] = digest(library_manifest)
    task = catalog["tasks"][0]
    task.update(id=name, protocol="recreated", requirements=requirements)
    task["contract_source"]["path"] = f"suite/{name}/problem.json"
    identity = task_library.verify_task_library(tasks_root, source)
    environment = torch.torch_environment(torch.TORCH_IMAGE, group)
    receipt = json.loads(old_receipt_path.read_text())
    old_receipt_path.parent.rename(path.parent / name)
    receipt_path = path.parent / name / "receipt.json"
    receipt.update(task_id=name, protocol="recreated", task_source=identity, receipt_path=str(receipt_path))
    receipt["execution"].update(image=torch.TORCH_IMAGE, resource_profile=environment["resource_profile"])
    native = receipt_path.parent / "native-output/native.json"
    native.parent.mkdir()
    native.write_text(json.dumps({**{key: receipt[key] for key in
        ("task_id", "candidate_sha256", "evaluator_sha256", "protocol", "direction")},
        "mode": "suite", "status": "completed", "valid": True, "score": receipt["raw_score"],
        "upstream_result": {"thread_policy": torch.TORCH_THREAD_POLICY, "threads": 1, "interop_threads": 1}}))
    receipt.update(native_result_path=str(native), native_result_sha256=digest(native))
    receipt_path.write_text(json.dumps(receipt))
    manifest = json.loads(path.read_text())
    manifest.update(group=group, profile=torch.TORCH_PROFILE, image=torch.TORCH_IMAGE,
                    prepared_environment=environment, resource_profile=environment["resource_profile"],
                    task_source=identity)
    row = manifest["tasks"][0]
    row.update(task_id=name, protocol="recreated", requirements=requirements,
               seed_evaluation={key: receipt[key] for key in campaign.SEED_FIELDS},
               receipt_sha256=digest(receipt_path))
    path.write_text(json.dumps(manifest))
    return args, path, receipt_path, catalog


def rewrite_receipt(path, receipt_path, receipt):
    receipt_path.write_text(json.dumps(receipt))
    manifest = json.loads(path.read_text())
    manifest["tasks"][0].update(receipt_sha256=digest(receipt_path),
        seed_evaluation={key: receipt[key] for key in campaign.SEED_FIELDS})
    path.write_text(json.dumps(manifest))


@pytest.mark.parametrize("torch_inputs", torch.TORCH_GROUPS, indirect=True)
def test_fresh_exact_receipt_prepares_inert_resource_bound_template(torch_inputs):
    args, path, receipt_path, catalog = torch_inputs
    evidence = path.read_bytes(), receipt_path.read_bytes()
    manifest = json.loads(path.read_text())
    result = campaign.prepare(**args)
    assert result["counts"] == {"prepared": 1, "pending": 1}
    assert result["model_calls"] == 0 and result["queue_mutated"] is False
    templates = json.loads((args["config_destination"] / "templates.json").read_text())
    assert len(templates) == 1
    template = templates[0]
    assert template["resources"] == worker_resources(manifest["resource_profile"])
    assert template["resources"]["memory_mb"] == (12288 if manifest["group"] == "torch-cpu-8g" else 8192)
    name = catalog["tasks"][0]["id"]
    generated = Path(template["spec"]["request"]["tasks_root"]) / "arena" / name
    bridge = json.loads((generated / "evaluation.json").read_text())
    assert bridge["evaluation"]["profile"] == torch.TORCH_PROFILE
    assert bridge["evaluation"]["execution"] == {
        "kind": "docker", "image": manifest["image"], "python": "python",
        "resource_profile": manifest["resource_profile"], "require_control_cgroup": True}
    assert bridge["binding"]["prepared_environment"] == manifest["prepared_environment"]
    assert bridge["binding"]["task_source"] == manifest["task_source"]
    inventory = json.loads((args["config_destination"] / "campaign-inventory.json").read_text())
    assert inventory["resource_profile"] == manifest["resource_profile"]
    assert inventory["prepared_environment"] == manifest["prepared_environment"]
    assert inventory["resources_per_run"] == worker_resources(manifest["resource_profile"])
    assert inventory["canonical_evaluator_calls"] == 0 and not inventory["research_executed"]
    assert evidence == (path.read_bytes(), receipt_path.read_bytes())


@pytest.mark.parametrize("mutation", ["resource", "absent_resource", "image", "validity", "evaluator", "source"])
def test_historical_or_wrong_resource_receipt_cannot_qualify_even_if_rehashed(torch_inputs, mutation):
    args, path, receipt_path, _ = torch_inputs
    receipt = json.loads(receipt_path.read_text())
    if mutation == "resource":
        receipt["execution"]["resource_profile"] = "cpu-4g-p256-v1"
    elif mutation == "absent_resource":
        del receipt["execution"]["resource_profile"]
    elif mutation == "image":
        receipt["execution"]["image"] = "sha256:" + "0" * 64
    elif mutation == "validity":
        receipt["validity"] = None
    elif mutation == "evaluator":
        receipt["evaluator_sha256"] = "0" * 64
    else:
        receipt["task_source"]["manifest_sha256"] = "0" * 64
    rewrite_receipt(path, receipt_path, receipt)
    with pytest.raises(ValueError, match="receipt does not match"):
        campaign.prepare(**args)
    assert not (args["config_destination"] / "templates.json").exists()
    assert not list(args["native_tasks"].rglob("task.yaml"))


@pytest.mark.parametrize("mutation", ["profile", "resource", "image", "lock", "data", "thread_policy", "implicit", "foreign", "library"])
def test_manifests_cannot_silently_widen_exact_prepared_group(torch_inputs, mutation):
    args, path, _, catalog = torch_inputs
    manifest = json.loads(path.read_text())
    if mutation == "profile":
        manifest["profile"] = "sciel-catalog-cpu/1"
    elif mutation == "resource":
        manifest["resource_profile"] = "cpu-4g-p256-v1"
    elif mutation == "image":
        manifest["image"] = "sha256:" + "0" * 64
    elif mutation == "lock":
        manifest["prepared_environment"]["dependency_lock_sha256"] = "0" * 64
    elif mutation == "data":
        manifest["prepared_environment"]["data_assets"] = ["unreviewed-data"]
    elif mutation == "thread_policy":
        manifest["prepared_environment"]["runtime_policy"] = {"name": torch.TORCH_THREAD_POLICY, "threads": 2, "interop_threads": 1}
    elif mutation == "implicit":
        manifest["group"] = "all"
    elif mutation == "foreign":
        manifest["tasks"][1]["status"] = "seed_verified"
    else:
        manifest["task_source"]["manifest_sha256"] = "0" * 64
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Torch|image|library"):
        campaign.prepare(**args)
    assert not args["config_destination"].exists()


def test_manifest_must_bind_resource_profile_even_when_legacy_default_has_same_limits(torch_inputs):
    args, path, _, _ = torch_inputs
    manifest = json.loads(path.read_text())
    del manifest["resource_profile"]
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Torch environment and resources"):
        campaign.prepare(**args)


@pytest.mark.parametrize("mutation", ["missing", "bytes", "hash", "path", "threads", "boolean", "interop", "policy", "candidate", "validity", "score"])
def test_native_thread_evidence_must_be_exact_even_when_receipt_is_rehashed(torch_inputs, mutation):
    args, path, receipt_path, _ = torch_inputs
    receipt = json.loads(receipt_path.read_text())
    native_path = Path(receipt["native_result_path"])
    native = json.loads(native_path.read_text())
    if mutation == "missing":
        del receipt["native_result_path"]
    elif mutation == "bytes":
        native_path.write_text(native_path.read_text() + " ")
    elif mutation == "hash":
        receipt["native_result_sha256"] = "0" * 64
    elif mutation == "path":
        receipt["native_result_path"] = str(native_path.parent / "other.json")
    else:
        if mutation == "candidate":
            native["candidate_sha256"] = "0" * 64
        elif mutation == "validity":
            native["valid"] = None
        elif mutation == "score":
            native["score"] = receipt["raw_score"] + 1
        elif mutation == "threads":
            native["upstream_result"]["threads"] = 2
        elif mutation == "boolean":
            native["upstream_result"]["threads"] = True
        elif mutation == "interop":
            native["upstream_result"]["interop_threads"] = 2
        else:
            native["upstream_result"]["thread_policy"] = "host-wide-default"
        native_path.write_text(json.dumps(native))
        receipt["native_result_sha256"] = digest(native_path)
    rewrite_receipt(path, receipt_path, receipt)
    with pytest.raises(ValueError, match="Torch seed"):
        campaign.prepare(**args)
    assert not (args["config_destination"] / "templates.json").exists()
    assert not list(args["native_tasks"].rglob("task.yaml"))
