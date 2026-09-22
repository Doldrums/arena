"""Fresh JAX evidence must bind library, evaluator, immutable image and resources."""
import json
from pathlib import Path

import pytest

from arena import task_library
from arena.evaluation_resources import worker_resources
from arena.frameworks import sciel_catalog_jax as jax
from test_sciel_catalog_campaign import prepared_inputs, campaign, digest


@pytest.fixture
def jax_inputs(prepared_inputs, request):
    args, path, old_receipt_path, catalog = prepared_inputs
    group = getattr(request, "param", "jax-affinity")
    name = next(name for name, reqs in jax.JAX_TASK_REQUIREMENTS.items()
                if jax.jax_task_group(name, list(reqs)) == group)
    requirements = list(jax.JAX_TASK_REQUIREMENTS[name])
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
    environment = jax.jax_environment(jax.JAX_IMAGES[group], group)
    receipt = json.loads(old_receipt_path.read_text())
    old_receipt_path.parent.rename(path.parent / name)
    receipt_path = path.parent / name / "receipt.json"
    receipt.update(task_id=name, protocol="recreated", task_source=identity, receipt_path=str(receipt_path))
    receipt["execution"].update(image=jax.JAX_IMAGES[group], resource_profile=environment["resource_profile"])
    receipt_path.write_text(json.dumps(receipt))
    manifest = json.loads(path.read_text())
    manifest.update(group=group, profile=jax.JAX_PROFILE, image=jax.JAX_IMAGES[group],
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


@pytest.mark.parametrize("jax_inputs", jax.JAX_GROUPS, indirect=True)
def test_fresh_exact_receipt_prepares_inert_resource_bound_template(jax_inputs):
    args, path, receipt_path, catalog = jax_inputs
    evidence = path.read_bytes(), receipt_path.read_bytes()
    manifest = json.loads(path.read_text())
    result = campaign.prepare(**args)
    assert result["counts"] == {"prepared": 1, "pending": 1}
    assert result["model_calls"] == 0 and result["queue_mutated"] is False
    templates = json.loads((args["config_destination"] / "templates.json").read_text())
    assert len(templates) == 1
    template = templates[0]
    assert template["resources"] == worker_resources(manifest["resource_profile"])
    name = catalog["tasks"][0]["id"]
    generated = Path(template["spec"]["request"]["tasks_root"]) / "arena" / name
    bridge = json.loads((generated / "evaluation.json").read_text())
    assert bridge["evaluation"]["profile"] == jax.JAX_PROFILE
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
def test_historical_or_wrong_resource_receipt_cannot_qualify_even_if_rehashed(jax_inputs, mutation):
    args, path, receipt_path, _ = jax_inputs
    receipt = json.loads(receipt_path.read_text())
    if mutation == "resource":
        receipt["execution"]["resource_profile"] = "cpu-4g-p128-v1"
    elif mutation == "absent_resource":
        del receipt["execution"]["resource_profile"]
    elif mutation == "image":
        receipt["execution"]["image"] = jax.JAX_ORIGINAL_IMAGE
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


@pytest.mark.parametrize("mutation", ["profile", "resource", "image", "lock", "data", "affinity", "implicit", "foreign", "library"])
def test_manifests_cannot_silently_widen_exact_prepared_group(jax_inputs, mutation):
    args, path, _, catalog = jax_inputs
    manifest = json.loads(path.read_text())
    if mutation == "profile":
        manifest["profile"] = "sciel-catalog-cpu/1"
    elif mutation == "resource":
        manifest["resource_profile"] = "cpu-4g-p128-v1"
    elif mutation == "image":
        manifest["image"] = jax.JAX_ORIGINAL_IMAGE
    elif mutation == "lock":
        manifest["prepared_environment"]["dependency_lock_sha256"] = "0" * 64
    elif mutation == "data":
        manifest["prepared_environment"]["data_assets"] = ["unreviewed-data"]
    elif mutation == "affinity":
        manifest["prepared_environment"]["runtime_policy"] = "no-affinity"
    elif mutation == "implicit":
        manifest["group"] = "all"
    elif mutation == "foreign":
        manifest["tasks"][1]["status"] = "seed_verified"
    else:
        manifest["task_source"]["manifest_sha256"] = "0" * 64
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="JAX|image|library"):
        campaign.prepare(**args)
    assert not args["config_destination"].exists()


def test_manifest_must_bind_resource_profile_even_when_legacy_default_has_same_limits(jax_inputs):
    args, path, _, _ = jax_inputs
    manifest = json.loads(path.read_text())
    del manifest["resource_profile"]
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="JAX environment and resources"):
        campaign.prepare(**args)
