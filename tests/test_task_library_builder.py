"""Explicit manifest refresh and source-only execution of an installed task CLI."""
import hashlib
import importlib.util
import json
import marshal
from pathlib import Path
import py_compile
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("task_library_builder", ROOT / "scripts/build_task_library.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


@pytest.fixture
def repo(tmp_path):
    tasks = tmp_path / "tasks"
    (tasks / "catalog").mkdir(parents=True)
    (tasks / "catalog/tasks.json").write_text('[{"id":"fixture"}]')
    (tasks / "run.py").write_text("raise AssertionError('must never import')\n")
    registry = tmp_path / "registry/task-sources"
    registry.mkdir(parents=True)
    (registry / "arena-tasks.json").write_text(json.dumps({"storage": "bundled",
        "manifest_path": "registry/task-library-manifest.json", "manifest_sha256": "0" * 64}))
    return tmp_path


def test_refresh_is_explicit_deterministic_and_detects_source_tamper(repo):
    with pytest.raises(ValueError, match="stale"):
        builder.update(repo)
    assert not (repo / "registry/task-library-manifest.json").exists()
    first, digest = builder.update(repo, write=True)
    recorded = (repo / "registry/task-library-manifest.json").read_bytes()
    assert first["task_count"] == 1 and hashlib.sha256(recorded).hexdigest() == digest
    assert builder.update(repo) == (first, digest)
    assert (repo / "registry/task-library-manifest.json").read_bytes() == recorded
    (repo / "tasks/run.py").write_text("changed")
    with pytest.raises(ValueError, match="stale"):
        builder.update(repo)
    assert (repo / "registry/task-library-manifest.json").read_bytes() == recorded


def test_links_and_unrecognized_cache_artifacts_are_not_packaged(repo):
    link = repo / "tasks/linked.py"
    link.symlink_to(repo / "tasks/run.py")
    with pytest.raises(ValueError, match="links"):
        builder.build_manifest(repo)
    link.unlink()
    cache = repo / "tasks/__pycache__"
    cache.mkdir()
    (cache / "unknown.cpython-311.pyc").write_bytes(b"cache")
    with pytest.raises(ValueError, match="Unrecognized"):
        builder.build_manifest(repo)


def test_optional_source_assets_remain_bound_when_not_installed(repo):
    asset = {"path": "vendor/native.cpp", "sha256": hashlib.sha256(b"reviewed").hexdigest()}
    (repo / "tasks/catalog/source-assets.json").write_text(json.dumps({"schema": "arena.source-assets/1", "files": [asset]}))
    manifest, _ = builder.update(repo, write=True)
    assert manifest["external_files"] == {asset["path"]: asset["sha256"]}
    assert asset["path"] not in manifest["files"]
    path = repo / "tasks" / asset["path"]
    path.parent.mkdir()
    path.write_bytes(b"reviewed")
    assert builder.update(repo)[0] == manifest
    path.write_bytes(b"different")
    with pytest.raises(ValueError, match="digest mismatch"):
        builder.update(repo, write=True)


def test_direct_task_cli_imports_source_even_when_pip_cache_is_poisoned(tmp_path):
    runner = tmp_path / "run.py"
    runner.write_bytes((ROOT / "tasks/run.py").read_bytes())
    package = tmp_path / "src/autoresearch_tasks"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    cli = package / "cli.py"
    cli.write_text("def main():\n    print('reviewed source')\n    return 0\n")
    py_compile.compile(str(cli), doraise=True)
    cache = Path(importlib.util.cache_from_source(str(cli)))
    malicious = "def main():\n    print('poisoned cache')\n    return 0\n"
    cache.write_bytes(cache.read_bytes()[:16] + marshal.dumps(compile(malicious, str(cli), "exec")))
    result = subprocess.run([sys.executable, str(runner)], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "reviewed source"
