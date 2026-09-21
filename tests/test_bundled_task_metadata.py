"""Local task provenance is verifiable without another checkout or network."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

import pytest

from arena.registry import RegistryError, build_catalog, validate_registration, validate_source
from arena.task_source_reader import TaskSourceReader
from arena.task_sources import registration_source, source_url

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def library(tmp_path):
    registry, tasks = tmp_path / "registry", tmp_path / "tasks"
    registry.mkdir()
    task = {"id": "example", "name": "Example", "description": "A deterministic fixture",
            "status": "ready", "kind": "native", "paper_ids": ["paper"], "limitations": [],
            "sources": [{"url": "https://example.com/paper", "type": "paper", "locator": "Table 1"}],
            "evaluation": {"metric": "score", "direction": "maximize"},
            "validation": {"level": "definition", "upstream_reproduction": False},
            "execution": {"suite": {"protocol": "recreated", "family": "example", "requires": []}}}
    files = {"catalog/tasks.json": [task], "suite/index.json": {"count": 1, "tasks": [
        {"id": "example", "protocol": "recreated", "family": "example", "requires": []}]},
        "suite/example/problem.json": {"id": "example", "protocol": "recreated", "contract": "solve() -> float"}}
    hashes = {}
    for name, data in files.items():
        path = tasks / name
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(data).encode()
        path.write_bytes(raw)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    manifest = json.dumps({"schema": "arena.task-library/1", "files": hashes}).encode()
    (registry / "task-library-manifest.json").write_bytes(manifest)
    registration = json.loads((ROOT / "registry/task-sources/arena-tasks.json").read_text())
    registration["manifest_sha256"] = hashlib.sha256(manifest).hexdigest()
    source = registration_source(registration)
    source.update(catalog_sha256=hashes["catalog/tasks.json"], index_sha256=hashes["suite/index.json"])
    return registry, tasks, registration, source


def test_bundled_metadata_needs_no_git_checkout_or_subprocess(library, monkeypatch):
    registry, tasks, registration, source = library
    def forbidden(*args, **kwargs):
        raise AssertionError("Bundled metadata must not invoke Git, a task or the network")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    validate_registration(registration)
    validate_source(source)
    reader = TaskSourceReader(tasks, source, registry_root=registry)
    catalog = build_catalog(json.loads(reader.read("catalog/tasks.json")),
                            json.loads(reader.read("suite/index.json")), source,
                            {"example": reader.read("suite/example/problem.json")})
    assert catalog["tasks"][0]["source_id"] == "arena-tasks"
    assert catalog["tasks"][0]["contract_source"]["url"] == source_url(source, "suite/example/problem.json")
    assert "Doldrums/arena/blob/main/tasks/" in reader.evidence("catalog/tasks.json")["url"]


@pytest.mark.parametrize("field,value", [
    ("manifest_sha256", "main"), ("root_path", "../other"),
    ("manifest_path", "tasks/untrusted.json"), ("storage", "remote"),
    ("repository_url", "https://github.com/example/tasks"), ("revision", "other"),
])
def test_registration_rejects_unreviewed_bundle_locations(library, field, value):
    registration = deepcopy(library[2])
    registration[field] = value
    with pytest.raises(RegistryError):
        validate_registration(registration)


def test_reader_refuses_changed_or_unregistered_files(library):
    registry, tasks, _, source = library
    (tasks / "catalog/tasks.json").write_text("[]")
    with pytest.raises(ValueError, match="digest mismatch"):
        TaskSourceReader(tasks, source, registry_root=registry)


def test_catalog_sync_builds_a_registry_from_bundled_files(library, monkeypatch):
    registry, tasks, registration, _ = library
    (registry / "task-sources").mkdir()
    (registry / "task-sources/arena-tasks.json").write_text(json.dumps(registration))
    synchronize = runpy.run_path(str(ROOT / "scripts/sync_task_catalog.py"))["synchronize"]
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: pytest.fail("No Git or task execution"))
    result = synchronize(tasks, registration, registry)
    assert result["valid"] is True and result["catalog"]["task_count"] == 1
    assert json.loads((registry / "catalog.json").read_text())["tasks"][0]["contract"] == "solve() -> float"


@pytest.mark.parametrize("change_paper", [False, True])
def test_participant_refresh_rebinds_revision_but_not_new_research_claims(tmp_path, change_paper):
    registry = tmp_path / "registry"
    shutil.copytree(ROOT / "registry", registry)
    capture = registry / "participant-corpus.json"
    before = capture.read_bytes()
    bibliography_path = registry / "search-family-sources.json"
    bibliography = json.loads(bibliography_path.read_text())
    bibliography["catalog_binding"]["manifest_sha256"] = "a" * 64
    if change_paper:
        next(p for p in bibliography["papers"] if p["source_kind"] == "corpus_paper")["title"] = "Unreviewed replacement"
    bibliography_path.write_text(json.dumps(bibliography))
    command = [sys.executable, str(ROOT / "scripts/build_participants.py"), "--registry-root", str(registry)]
    result = subprocess.run(command, capture_output=True, text=True)
    if change_paper:
        assert result.returncode == 1 and capture.read_bytes() == before
    else:
        assert result.returncode == 0, result.stderr
        updated, original = json.loads(capture.read_bytes()), json.loads(before)
        assert updated["works"] == original["works"] and updated["source"] == original["source"]
        assert updated["bibliography_digest"] != original["bibliography_digest"]
