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


@pytest.fixture
def catalog():
    return get_catalog()


def test_pinned_catalog_is_available_without_runtime_or_frameworks(catalog):
    assert catalog["summary"] == {
        "task_count": 1138, "executable_count": 710, "unsupported_count": 428,
        "protocol_counts": {"original": 134, "recreated_verified": 122, "recreated": 454, "unsupported": 428},
        "runtime_readiness": "not_verified"}
    assert catalog["sources"][0]["repository"]["commit"] == "995768fc462b8e327f90e6762846cc6ccb06cc2c"
    assert all(task["runtime_readiness"] == "not_verified" for task in catalog["tasks"])
    assert validate_registry()["valid"] is True


@pytest.mark.parametrize("mutate", [
    lambda c: c["tasks"][0].update(runtime_readiness="ready"),
    lambda c: c["tasks"][0].update(direction=None),
    lambda c: c["tasks"][0].update(source_id="missing-source"),
    lambda c: c["tasks"].append(deepcopy(c["tasks"][0])),
    lambda c: c["summary"].update(executable_count=1138),
    lambda c: c["sources"][0]["repository"].update(commit="main"),
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


def test_alternate_dependency_declarations_are_preserved(catalog):
    affected = [task for task in catalog["tasks"] if task["provenance"]["index_requirements"] is not None]
    assert len(affected) == 6
    for task in affected:
        assert "network:openrouter" in task["requirements"]
        assert "service:llm_api" in task["provenance"]["index_requirements"]
        assert task["provenance"]["metadata_notes"]
        assert task["runtime_readiness"] == "not_verified"


def test_get_catalog_returns_detached_values():
    first = get_catalog()
    first["tasks"].clear()
    assert len(get_catalog()["tasks"]) == 1138


def test_input_output_contracts_are_bound_to_pinned_problem_files(catalog):
    tasks = {task["id"]: task for task in catalog["tasks"]}
    task = tasks["alphaevolve-circle-packing-in-unit-square"]
    assert "construct()" in task["contract"]
    assert "(n, 3)" in task["contract"]
    source = task["contract_source"]
    assert source["path"] == "suite/alphaevolve-circle-packing-in-unit-square/problem.json"
    assert "/blob/995768fc462b8e327f90e6762846cc6ccb06cc2c/" in source["url"]
    assert len(source["sha256"]) == 64
    assert all(t["contract_source"] for t in tasks.values())
    source["url"] = source["url"].replace("995768fc462b8e327f90e6762846cc6ccb06cc2c", "main")
    with pytest.raises(RegistryError, match="pinned repository"):
        validate_catalog(catalog)


def test_participants_are_pinned_but_native_adapters_are_not_claimed():
    view = get_participants()
    assert view["summary"] == {"participant_count": 3, "integrated_count": 0}
    assert {p["id"] for p in view["participants"]} == {"sciel", "shinka", "dgm"}
    for participant in view["participants"]:
        assert participant["adapter_status"] == "not_implemented"
        assert not any(participant["capabilities"].values())
        assert participant["supported_protocols"] == []
        changed = deepcopy(participant)
        changed["capabilities"]["native_run"] = True
        with pytest.raises(RegistryError, match="cannot advertise"):
            validate_participant(changed)


@pytest.mark.parametrize("updates", [
    {"manifest_path": "../secret.json"}, {"admission": "webhook_auto_run"},
    {"refresh": "automated"}, {"kind": "arbitrary_shell"}, {"unexpected": "field"},
])
def test_registration_is_constrained_and_not_a_shell_request(updates):
    value = json.loads((ROOT / "registry/task-sources/autoresearch-tasks.json").read_text())
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
    registration = copied / "task-sources/autoresearch-tasks.json"
    value = json.loads(registration.read_text())
    value["repository"]["commit"] = "a" * 40
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
    index = {"count": 1, "tasks": [{"id": "fixture-task", "protocol": "recreated", "family": "fixture", "requires": ["py:numpy"]}]}
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
    registration = json.loads((ROOT / "registry/task-sources/autoresearch-tasks.json").read_text())
    registration["repository"]["commit"] = commit
    (registry / "task-sources/autoresearch-tasks.json").write_text(json.dumps(registration))
    result = subprocess.run([sys.executable, str(ROOT / "scripts/sync_task_catalog.py"), str(checkout),
                             "--registry-root", str(registry)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    imported = get_catalog(registry)
    assert imported["tasks"][0]["description"] == "Committed description"
    assert imported["tasks"][0]["contract"] is None
    assert imported["tasks"][0]["contract_source"] is None
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
    other = json.loads((copied / "task-sources/autoresearch-tasks.json").read_text())
    other.update(id="other", snapshot_source_id="other")
    (copied / "task-sources/other.json").write_text(json.dumps(other))
    before = (copied / "catalog.json").read_bytes()
    result = subprocess.run([sys.executable, str(ROOT / "scripts/sync_task_catalog.py"), str(tmp_path / "unused"),
                             "--registry-root", str(copied)], capture_output=True, text=True)
    assert result.returncode == 1
    assert "multi-source merging is not implemented" in result.stderr
    assert (copied / "catalog.json").read_bytes() == before
