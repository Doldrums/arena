"""Catalog invariants: no readiness inflation, fabricated integration or drift."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from arena.registry import (RegistryError, get_catalog,
    get_participants, validate_catalog, validate_participant, validate_registration, validate_registry)

ROOT = Path(__file__).resolve().parents[1]


def legacy_registration():
    return {"schema": "arena.registration/1", "id": "fixture-source", "kind": "task_collection",
            "repository": {"url": "https://github.com/example/tasks", "commit": "a" * 40},
            "manifest_path": "catalog/tasks.json", "tracked_ref": "main", "access": "github_app_private",
            "admission": "team_registry_pr", "refresh": "manual_pinned_snapshot", "snapshot_source_id": "fixture-source"}



@pytest.fixture
def catalog():
    return get_catalog()


def test_pinned_catalog_is_available_without_runtime_or_frameworks(catalog):
    assert catalog["summary"] == {
        "task_count": 959, "executable_count": 702, "unsupported_count": 257,
        "protocol_counts": {"original": 109, "recreated_verified": 81, "recreated": 512, "unsupported": 257},
        "runtime_readiness": "not_verified"}
    assert catalog["sources"][0]["kind"] == "bundled"
    assert catalog["sources"][0]["id"] == "arena-tasks"
    assert all(task["runtime_readiness"] == "not_verified" for task in catalog["tasks"])
    assert validate_registry()["valid"] is True


@pytest.mark.parametrize("mutate", [
    lambda c: c["tasks"][0].update(runtime_readiness="ready"),
    lambda c: c["tasks"][0].update(direction=None),
    lambda c: c["tasks"][0].update(source_id="missing-source"),
    lambda c: c["tasks"].append(deepcopy(c["tasks"][0])),
    lambda c: c["summary"].update(executable_count=959),
    lambda c: c["sources"][0].update(manifest_sha256="main"),
])
def test_invalid_catalog_rejected(catalog, mutate):
    mutate(catalog)
    with pytest.raises(RegistryError):
        validate_catalog(catalog)


def test_unsupported_evaluator_stub_does_not_become_executable(catalog):
    task = next(task for task in catalog["tasks"] if task["protocol"] == "unsupported")
    task["executable"] = True
    with pytest.raises(RegistryError, match="contradicts"):
        validate_catalog(catalog)
    task["executable"] = False
    task["unsupported_reason"] = None
    with pytest.raises(RegistryError, match="needs a reason"):
        validate_catalog(catalog)


def test_current_source_dependency_declarations_agree(catalog):
    affected = [task for task in catalog["tasks"] if task["provenance"]["index_requirements"] is not None]
    assert affected == []


def test_evaluator_definition_can_require_setup_without_claiming_runtime_readiness(catalog):
    pending = [task for task in catalog["tasks"] if task["executable"] and task["declared_status"] == "requires_setup"]
    assert len(pending) == 28
    assert all(task["runtime_readiness"] == "not_verified" for task in pending)
    assert validate_catalog(catalog) is catalog
    pending[0]["declared_status"] = "blocked"
    with pytest.raises(RegistryError, match="declared status contradicts"):
        validate_catalog(catalog)


def test_missing_evaluator_cannot_claim_ready(catalog):
    task = next(task for task in catalog["tasks"] if not task["executable"])
    task["declared_status"] = "requires_setup"
    validate_catalog(catalog)
    task["declared_status"] = "ready"
    with pytest.raises(RegistryError, match="declared status contradicts"):
        validate_catalog(catalog)


def test_get_catalog_returns_detached_values():
    first = get_catalog()
    first["tasks"].clear()
    assert len(get_catalog()["tasks"]) == 959


def test_input_output_contracts_are_bound_to_pinned_problem_files(catalog):
    tasks = {task["id"]: task for task in catalog["tasks"]}
    task = tasks["alphaevolve-circle-packing-in-unit-square"]
    assert "construct()" in task["contract"]
    assert "(n, 3)" in task["contract"]
    source = task["contract_source"]
    assert source["path"] == "suite/alphaevolve-circle-packing-in-unit-square/problem.json"
    assert "/Doldrums/arena/blob/main/tasks/" in source["url"]
    assert len(source["sha256"]) == 64
    assert all(t["contract_source"] for t in tasks.values())
    source["url"] = source["url"].replace("/main/", "/other/")
    with pytest.raises(RegistryError, match="pinned repository"):
        validate_catalog(catalog)


def test_local_native_drivers_do_not_claim_end_to_end_conformance():
    view = get_participants()
    assert view["summary"] == {"participant_count": 99, "integrated_count": 0, "research_work_count": 98,
                               "pinned_registration_count": 3, "literature_only_count": 96}
    pinned = [p for p in view["participants"] if p["record_kind"] == "system_registration"]
    assert {p["id"] for p in pinned} == {"sciel", "shinka", "dgm"}
    for participant in view["participants"]:
        native = participant["record_kind"] == "system_registration"
        assert participant["adapter_status"] == ("native_cli" if native else "not_implemented")
        assert participant["capabilities"]["native_run"] is native
        assert all(not value for key, value in participant["capabilities"].items() if key != "native_run")
        if native:
            assert participant["runtime_readiness"] == "not_verified"
            assert participant["adapter_validation"] == "source_and_fixture_tests"
        assert participant["supported_protocols"] == []
        changed = deepcopy(participant)
        changed["capabilities"]["canonical_evaluation" if native else "native_run"] = True
        with pytest.raises(RegistryError, match="cannot advertise"):
            validate_participant(changed)


def test_native_capabilities_reject_json_numbers_as_booleans():
    participant = json.loads((ROOT / "registry/participants/sciel.json").read_text())
    participant["capabilities"]["native_run"] = 1
    with pytest.raises(RegistryError, match="booleans"):
        validate_participant(participant)


def test_registry_reports_the_actual_native_driver_stage():
    assert validate_registry()["native_runners"] == dict.fromkeys(("sciel", "shinka", "dgm"), "native_cli")


@pytest.fixture
def attribution():
    return {
        "kind": "organizations", "display": "Sakana AI",
        "organizations": ["Sakana AI"], "authors": [],
        "source_url": "https://arxiv.org/pdf/2505.22954v3",
        "source_locator": "p. 1 author affiliations",
        "evidence_note": "Sakana AI is explicitly named in the author affiliations.",
        "checked_at": "2026-09-20",
    }


@pytest.mark.parametrize("kind,names", [
    ("organizations", ["Sakana AI", "University of British Columbia"]),
    ("authors", ["Junye Pan"]),
    ("team", ["SCiEL research team"]),
])
def test_optional_attribution_preserves_explicit_credit_without_granting_readiness(attribution, kind, names):
    participant = json.loads((ROOT / "registry/participants/dgm.json").read_text())
    validate_participant(participant)  # Existing registrations need no invented affiliation.
    original = deepcopy(participant)
    attribution.update(kind=kind, display=" · ".join(names),
                       organizations=[] if kind == "authors" else names,
                       authors=names if kind == "authors" else [])
    participant["attribution"] = attribution
    before = deepcopy(participant)
    validate_participant(participant)
    assert participant == before
    assert {key: participant[key] for key in original} == original


@pytest.mark.parametrize("mutate", [
    lambda a: a.update(kind="github_owner"),
    lambda a: a.update(organizations=[]),
    lambda a: a.update(kind="authors", authors=[]),
    lambda a: a.update(kind="team", organizations=[]),
    lambda a: a.update(organizations=["Sakana AI", "Sakana AI"]),
    lambda a: a.update(authors=["Junye Pan", "Junye Pan"]),
    lambda a: a.update(organizations="Sakana AI"),
    lambda a: a.update(display=" "),
    lambda a: a.update(source_url="javascript:alert(1)"),
    lambda a: a.update(source_url="https://example.org/paper?access_token=private"),
    lambda a: a.update(source_locator="/Users/reviewer/private/paper.pdf"),
    lambda a: a.update(checked_at="September 2026"),
    lambda a: a.update(unreviewed_owner="github-owner"),
])
def test_attribution_rejects_unsubstantiated_shapes_and_unsafe_provenance(attribution, mutate):
    participant = json.loads((ROOT / "registry/participants/dgm.json").read_text())
    mutate(attribution)
    participant["attribution"] = attribution
    with pytest.raises(RegistryError):
        validate_participant(participant)


@pytest.mark.parametrize("missing", ["source_url", "source_locator", "evidence_note", "checked_at"])
def test_attribution_requires_a_reviewable_source(attribution, missing):
    participant = json.loads((ROOT / "registry/participants/dgm.json").read_text())
    attribution.pop(missing)
    participant["attribution"] = attribution
    with pytest.raises(RegistryError, match="missing fields"):
        validate_participant(participant)


def test_explicit_null_attribution_is_not_an_optional_omission():
    participant = json.loads((ROOT / "registry/participants/dgm.json").read_text())
    participant["attribution"] = None
    with pytest.raises(RegistryError, match="expected object"):
        validate_participant(participant)


@pytest.mark.parametrize("updates", [
    {"manifest_path": "../secret.json"}, {"admission": "webhook_auto_run"},
    {"refresh": "automated"}, {"kind": "arbitrary_shell"}, {"unexpected": "field"},
])
def test_registration_is_constrained_and_not_a_shell_request(updates):
    value = legacy_registration()
    assert value["access"] == "github_app_private"
    validate_registration(value)
    value.update(updates)
    with pytest.raises(RegistryError):
        validate_registration(value)


def test_sensitive_urls_and_machine_paths_are_not_catalog_metadata(catalog):
    catalog["tasks"][0]["provenance"]["sources"][0]["url"] = "https://example.com/paper?access_token=hidden"
    with pytest.raises(RegistryError, match="credential"):
        validate_catalog(catalog)
    catalog["tasks"][0]["provenance"]["sources"][0]["url"] = "https://example.com/paper"
    catalog["tasks"][0]["description"] = "Source at /Users/someone/private/code"
    with pytest.raises(RegistryError, match="local path"):
        validate_catalog(catalog)


def test_registration_and_snapshot_revision_must_agree(tmp_path):
    copied = tmp_path / "registry"
    shutil.copytree(ROOT / "registry", copied)
    registration = copied / "task-sources/arena-tasks.json"
    value = json.loads(registration.read_text())
    value["manifest_sha256"] = "a" * 64
    registration.write_text(json.dumps(value))
    with pytest.raises(RegistryError, match="revision/path differs"):
        validate_registry(copied)


def test_reading_rejects_duplicate_json_keys(tmp_path):
    (tmp_path / "catalog.json").write_text('{"schema":"arena.catalog/1","schema":"other"}')
    with pytest.raises(RegistryError, match="duplicate JSON key"):
        get_catalog(tmp_path)


def test_snapshot_tool_reads_committed_objects_not_dirty_checkout(tmp_path):
    """A working-tree edit cannot acquire the provenance of the pinned commit."""
    checkout = tmp_path / "source"
    checkout.mkdir()
    task = {
        "id": "fixture-task", "name": "Fixture", "description": "Committed description",
        "status": "ready", "kind": "specification", "paper_ids": ["paper"], "limitations": [],
        "sources": [{"url": "https://example.com/paper", "type": "paper", "locator": "Table 1"}],
        "evaluation": {"metric": "loss", "direction": "minimize"},
        "validation": {"level": "paper_inventory", "upstream_reproduction": False},
        "execution": {"suite": {"protocol": "recreated", "family": "fixture", "requires": ["py:numpy"]}}}
    index = {"count": 1, "tasks": [{"id": "fixture-task", "protocol": "recreated", "family": "fixture", "requires": ["py:scipy"]}]}
    for name, value in (("catalog/tasks.json", [task]), ("suite/index.json", index)):
        path = checkout / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
    def git(*args):
        return subprocess.check_output(["git", "-C", str(checkout), *args], stderr=subprocess.PIPE).decode().strip()
    git("init", "-q")
    git("add", ".")
    git("-c", "user.name=Registry Test", "-c", "user.email=registry@example.invalid", "commit", "-qm", "fixture")
    commit = git("rev-parse", "HEAD")
    task["description"] = "Uncommitted description"
    (checkout / "catalog/tasks.json").write_text(json.dumps([task]))
    registry = tmp_path / "registry"
    (registry / "task-sources").mkdir(parents=True)
    (registry / "participants").mkdir()
    registration = legacy_registration()
    registration["repository"]["commit"] = commit
    (registry / "task-sources/autoresearch-tasks.json").write_text(json.dumps(registration))
    result = subprocess.run([sys.executable, str(ROOT / "scripts/sync_task_catalog.py"), str(checkout),
                             "--registry-root", str(registry), "--registration", "task-sources/autoresearch-tasks.json"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    imported = get_catalog(registry)
    assert imported["tasks"][0]["description"] == "Committed description"
    assert imported["tasks"][0]["contract"] is None
    assert imported["tasks"][0]["contract_source"] is None
    assert imported["tasks"][0]["requirements"] == ["py:numpy"]
    assert imported["tasks"][0]["provenance"]["index_requirements"] == ["py:scipy"]
    assert imported["tasks"][0]["provenance"]["metadata_notes"]
    committed_bytes = subprocess.check_output(["git", "-C", str(checkout), "show", f"{commit}:catalog/tasks.json"])
    assert imported["sources"][0]["catalog_sha256"] == hashlib.sha256(committed_bytes).hexdigest()


def test_json_schemas_are_valid_json():
    for path in (ROOT / "schemas").glob("*.json"):
        schema = json.loads(path.read_text())
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"].endswith(path.name)


def test_initial_importer_cannot_overwrite_an_additional_collection(tmp_path):
    copied = tmp_path / "registry"
    shutil.copytree(ROOT / "registry", copied)
    other = json.loads((copied / "task-sources/arena-tasks.json").read_text())
    other.update(id="other", snapshot_source_id="other")
    (copied / "task-sources/other.json").write_text(json.dumps(other))
    before = (copied / "catalog.json").read_bytes()
    result = subprocess.run([sys.executable, str(ROOT / "scripts/sync_task_catalog.py"), str(tmp_path / "unused"),
                             "--registry-root", str(copied)], capture_output=True, text=True)
    assert result.returncode == 1
    assert "multi-source merging is not implemented" in result.stderr
    assert (copied / "catalog.json").read_bytes() == before
