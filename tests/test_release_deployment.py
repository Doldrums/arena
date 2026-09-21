import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from arena import release_deployment as deployment
from arena.releases import ReleaseError, public_release, register_release


def test_private_source_pin_and_image_digest_remain_bound(release_fixture):
    fixture = release_fixture
    manifest, digest = deployment.load_manifest(fixture["path"], expected_release=fixture["reference"])
    assert manifest["binding"]["repository"]["commit"] == fixture["binding"]["repository"]["commit"]
    assert manifest["source"]["commit"] == manifest["binding"]["repository"]["commit"]
    assert manifest["image"]["reference"] == fixture["binding"]["image"]
    assert digest == fixture["digest"]
    assert digest == hashlib.sha256(fixture["path"].read_bytes()).hexdigest()
    rendered = json.dumps(manifest)
    assert "must-not-be-projected" not in rendered and "not-for-manifest" not in rendered
    assert manifest["image"]["metadata_is_build_attestation"] is False
    assert fixture["path"].stat().st_mode & 0o077 == 0


@pytest.mark.parametrize("change", [
    lambda inspection: inspection[0].update(RepoDigests=[]),
    lambda inspection: inspection[0].update(Id="moving-image-tag"),
    lambda inspection: inspection[0]["Config"].update(Entrypoint=["/bin/sh"]),
    lambda inspection: inspection[0]["Config"]["Labels"].update({"org.opencontainers.image.revision": "c" * 40}),
    lambda inspection: inspection[0]["Config"]["Labels"].update({"org.opencontainers.image.source": "https://elsewhere.invalid/another"}),
    lambda inspection: inspection[0]["Config"]["Labels"].update({"io.arena.sciel.contract": "unknown"}),
])
def test_image_provenance_and_entrypoint_mismatches_fail_closed(release_fixture, change):
    inspection = copy.deepcopy(release_fixture["inspection"])
    change(inspection)
    with pytest.raises(ReleaseError):
        deployment.inspect_image_evidence(inspection, release_fixture["binding"])


def test_local_image_id_cannot_substitute_for_a_repository_digest(release_fixture):
    inspection = copy.deepcopy(release_fixture["inspection"])
    inspection[0]["RepoDigests"] = ["registry.example.invalid/private/sciel@" + inspection[0]["Id"]]
    with pytest.raises(ReleaseError, match="RepoDigests"):
        deployment.inspect_image_evidence(inspection, release_fixture["binding"])


def test_dirty_source_is_not_reviewed_as_the_private_release(release_fixture):
    fixture = release_fixture
    (fixture["source"] / "research.py").write_text("changed\n")
    with pytest.raises(ReleaseError, match="clean private release"):
        deployment.prepare_deployment(fixture["reference"], fixture["store"], fixture["source"], fixture["inspection"],
                                      broker_socket="/run/arena/sciel-images.sock", operator="fixture", review_reference="review-1")


def test_manifest_immutable_public_identity_and_private_permissions(release_fixture):
    fixture = release_fixture
    with pytest.raises(FileExistsError):
        deployment.write_manifest(fixture["path"], fixture["manifest"])
    different = {**fixture["reference"], "version": "0.0.1-inert-test"}
    with pytest.raises(ReleaseError, match="requested public release"):
        deployment.load_manifest(fixture["path"], expected_release=different)
    fixture["path"].chmod(0o666)
    with pytest.raises(ReleaseError, match="private"):
        deployment.load_manifest(fixture["path"])


def test_manifest_rejects_duplicate_and_unknown_fields(release_fixture):
    with pytest.raises(ReleaseError, match="Invalid deployment JSON"):
        deployment._decode('{"release":1,"release":2}')
    value = copy.deepcopy(release_fixture["manifest"])
    value["image"]["metadata_is_build_attestation"] = True
    with pytest.raises(ReleaseError):
        deployment.validate_manifest(value)
    value = copy.deepcopy(release_fixture["manifest"])
    value["credentials"] = "not allowed"
    with pytest.raises(ReleaseError):
        deployment.validate_manifest(value)


def test_cli_summary_contains_no_private_pointer_and_never_admits_execution(release_fixture, capsys):
    assert deployment.main(["check", str(release_fixture["path"])]) == 0
    text = capsys.readouterr().out
    value = json.loads(text)
    assert value["release"] == release_fixture["reference"]
    assert value["status"] == "prepared_not_admitted"
    for private in (release_fixture["binding"]["repository"]["url"], release_fixture["binding"]["image"], str(release_fixture["source"])):
        assert private not in text


def test_manifest_binding_tampering_fails(release_fixture):
    value = copy.deepcopy(release_fixture["manifest"])
    value["binding"]["repository"]["commit"] = "c" * 40
    with pytest.raises(ReleaseError, match="binding digest"):
        deployment.validate_manifest(value)


def template_args(fixture, tmp_path):
    config = tmp_path / "native-config.json"
    config.write_text('{"fixture": true}')
    tasks = tmp_path / "tasks"
    tasks.mkdir()
    return {"template_id": "private-sciel-fixture", "name": "Inert private SCiEL", "model": "fixture-model",
            "python": sys.executable, "config": config, "tasks_root": tasks,
            "resources": {"cpus": 4, "memory_mb": 8192, "evaluation_slots": 1, "pids": 512},
            "timeout_seconds": 60, "budget": 2}


def test_template_materialization_requires_exact_hash_named_broker_approval(release_fixture, tmp_path):
    fixture = release_fixture
    approved = fixture["path"].parent / (fixture["digest"] + ".json")
    approved.write_bytes(fixture["path"].read_bytes())
    approved.chmod(0o600)
    template = deployment.materialize_template(fixture["path"], approved, **template_args(fixture, tmp_path))
    assert template["framework"] == "sciel-release" and template["status"] == "ready"
    assert template["spec"]["request"]["release"] == fixture["reference"]
    assert template["spec"]["source_dir"] == str(fixture["source"])
    assert template["spec"]["output_dir"] == "{output_dir}"
    assert "image" not in template["spec"]["request"]
    assert template["resources"]["evaluation_slots"] == 1


def test_unapproved_or_changed_release_cannot_materialize_ready_template(release_fixture, tmp_path):
    fixture = release_fixture
    kwargs = template_args(fixture, tmp_path)
    with pytest.raises(FileNotFoundError):
        deployment.materialize_template(fixture["path"], tmp_path / "absent-approval.json", **kwargs)
    value = copy.deepcopy(fixture["manifest"])
    value["review"]["reference"] = "different-reviewed-document"
    approved = fixture["path"].parent / (fixture["digest"] + ".json")
    approved.write_bytes(deployment.canonical_bytes(value))
    approved.chmod(0o600)
    with pytest.raises(ReleaseError, match="exact deployment"):
        deployment.materialize_template(fixture["path"], approved, **kwargs)


def test_template_cannot_override_global_32_evaluation_slot_ceiling(release_fixture, tmp_path):
    fixture = release_fixture
    approved = fixture["path"].parent / (fixture["digest"] + ".json")
    approved.write_bytes(fixture["path"].read_bytes())
    approved.chmod(0o600)
    kwargs = template_args(fixture, tmp_path)
    kwargs["resources"]["evaluation_slots"] = 33
    with pytest.raises(ValueError, match="global capacity"):
        deployment.materialize_template(fixture["path"], approved, **kwargs)
