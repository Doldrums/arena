"""Bundle integrity without Git or evaluator imports."""
import hashlib
import json

import pytest

from arena import task_library as library


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    tasks = tmp_path / "tasks"
    registry = tmp_path / "registry"
    registry.mkdir()
    payloads = {"run.py": b"raise AssertionError('must not import')\n",
                "suite/task/evaluator.py": b"raise AssertionError('must not import')\n",
                "suite/task/initial_program.py": b"raise AssertionError('must not import')\n",
                "adapters/helper.py": b"raise AssertionError('must not import')\n"}
    for relative, raw in payloads.items():
        path = tasks / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    manifest = {"schema": "arena.task-library/1", "files": {key: sha(raw) for key, raw in payloads.items()}}
    path = registry / "task-library-manifest.json"
    path.write_text(json.dumps(manifest))
    source = {"id": "arena-tasks", "kind": "bundled", "root_path": "tasks",
              "manifest_path": "registry/task-library-manifest.json", "manifest_sha256": sha(path.read_bytes())}
    monkeypatch.setattr(library, "resolve_registry_root", lambda _: registry)
    return tasks, source, path, manifest


def rewrite(source, path, manifest):
    path.write_text(json.dumps(manifest))
    source["manifest_sha256"] = sha(path.read_bytes())


def test_default_bundle_is_verified_without_git_or_imports(bundle):
    tasks, source, _, _ = bundle
    assert library.resolve_task_root(source=source) == tasks
    assert library.verify_task_library(tasks, source) == {
        "id": "arena-tasks", "kind": "bundled", "manifest_sha256": source["manifest_sha256"], "file_count": 4}
    assert not (tasks / ".git").exists()


@pytest.mark.parametrize("relative", ["run.py", "adapters/helper.py", "suite/task/evaluator.py", "suite/task/initial_program.py"])
def test_any_changed_code_or_seed_is_rejected(bundle, relative):
    tasks, source, _, _ = bundle
    (tasks / relative).write_text("changed")
    with pytest.raises(ValueError, match="digest mismatch"):
        library.verify_task_library(tasks, source)


def test_missing_and_unregistered_files_are_rejected(bundle):
    tasks, source, _, _ = bundle
    extra = tasks / "unexpected.py"
    extra.write_text("extra")
    with pytest.raises(ValueError, match="Unregistered"):
        library.verify_task_library(tasks, source)
    extra.unlink()
    (tasks / "run.py").unlink()
    with pytest.raises(ValueError, match="missing registered"):
        library.verify_task_library(tasks, source)


def test_modified_manifest_cannot_redefine_the_trust_root(bundle):
    tasks, source, path, manifest = bundle
    manifest["files"]["run.py"] = "0" * 64
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="digest mismatch"):
        library.verify_task_library(tasks, source)


@pytest.mark.parametrize("relative", ["../outside.py", "/absolute.py", "suite/../outside.py", "suite//task", "./run.py", "suite\\task"])
def test_bound_manifest_still_rejects_path_traversal(bundle, relative):
    tasks, source, path, manifest = bundle
    manifest["files"][relative] = "a" * 64
    rewrite(source, path, manifest)
    with pytest.raises(ValueError, match="contained canonical"):
        library.verify_task_library(tasks, source)


@pytest.mark.parametrize("location", ["run.py", "adapters"])
def test_links_are_rejected_even_when_target_content_matches(bundle, tmp_path, location):
    tasks, source, _, _ = bundle
    original = tasks / location
    moved = tmp_path / (location + "-target")
    original.rename(moved)
    original.symlink_to(moved, target_is_directory=moved.is_dir())
    with pytest.raises(ValueError, match="links"):
        library.verify_task_library(tasks, source)
    with pytest.raises(ValueError, match="linked"):
        library.read_task_file(tasks, location if moved.is_file() else "adapters/helper.py")


def test_linked_root_and_manifest_are_rejected(bundle, tmp_path):
    tasks, source, path, _ = bundle
    link = tmp_path / "linked-tasks"
    link.symlink_to(tasks, target_is_directory=True)
    with pytest.raises(ValueError, match="without links"):
        library.resolve_task_root(link)
    target = tmp_path / "manifest.json"
    path.rename(target)
    path.symlink_to(target)
    with pytest.raises(ValueError, match="linked"):
        library.verify_task_library(tasks, source)


def test_installed_assets_layout_needs_no_checkout(bundle, tmp_path, monkeypatch):
    tasks, source, path, _ = bundle
    assets = tmp_path / "site-packages/arena/_assets"
    assets.mkdir(parents=True)
    tasks.rename(assets / "tasks")
    path.parent.rename(assets / "registry")
    monkeypatch.setattr(library, "resolve_registry_root", lambda _: assets / "registry")
    root = library.resolve_task_root(source=source)
    assert root == assets / "tasks"
    assert library.verify_task_library(root, source)["file_count"] == 4


def test_optional_primary_source_files_are_allowed_only_at_bound_hashes(bundle):
    tasks, source, path, manifest = bundle
    manifest["external_files"] = {"vendor/header.hpp": sha(b"reviewed header")}
    rewrite(source, path, manifest)
    assert library.verify_task_library(tasks, source)["file_count"] == 4
    extra = tasks / "vendor/header.hpp"
    extra.parent.mkdir()
    extra.write_bytes(b"reviewed header")
    assert library.verify_task_library(tasks, source)["file_count"] == 5
    extra.write_text("changed")
    with pytest.raises(ValueError, match="digest mismatch"):
        library.verify_task_library(tasks, source)


def test_external_file_cannot_replace_required_file(bundle):
    tasks, source, path, manifest = bundle
    manifest["external_files"] = {"run.py": manifest["files"]["run.py"]}
    rewrite(source, path, manifest)
    with pytest.raises(ValueError, match="distinct"):
        library.verify_task_library(tasks, source)


@pytest.mark.parametrize("cache_tag", ["cpython-311", "cpython-311-pytest-9.1.1"])
def test_installer_caches_are_ignored_but_unknown_cache_modules_are_rejected(bundle, cache_tag):
    tasks, source, _, _ = bundle
    cache = tasks / f"adapters/__pycache__/helper.{cache_tag}.pyc"
    cache.parent.mkdir()
    cache.write_bytes(b"unused installed cache")
    assert library.verify_task_library(tasks, source)["file_count"] == 4
    unknown = cache.with_name(f"unregistered.{cache_tag}.pyc")
    cache.rename(unknown)
    with pytest.raises(ValueError, match="Unregistered"):
        library.verify_task_library(tasks, source)


def test_canonical_execution_never_consumes_poisoned_installer_cache(bundle, tmp_path, monkeypatch):
    import importlib.util
    import marshal
    import py_compile
    import sys
    from arena.frameworks import evaluation
    tasks, source, path, manifest = bundle
    helper = tasks / "adapters/helper.py"
    helper.write_text("score = 4.25\n")
    py_compile.compile(str(helper), doraise=True)
    cache = helper.parent / "__pycache__" / importlib.util.cache_from_source(str(helper)).rsplit("/", 1)[1]
    cache.write_bytes(cache.read_bytes()[:16] + marshal.dumps(compile("score = 999\n", str(helper), "exec")))
    runner = tasks / "run.py"
    runner.write_text('''import hashlib, json, sys
from pathlib import Path
root=Path(__file__).parent
sys.path.insert(0,str(root/'adapters'))
import helper
args=sys.argv
candidate=Path(args[args.index('--candidate')+1])
result={'task_id':'task','candidate_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),
'evaluator_sha256':hashlib.sha256((root/'suite/task/evaluator.py').read_bytes()).hexdigest(),
'protocol':'original','direction':'maximize','mode':'suite','valid':True,'score':helper.score,'status':'completed'}
Path(args[args.index('--output')+1]).write_text(json.dumps(result))
''')
    for relative in ("adapters/helper.py", "run.py"):
        manifest["files"][relative] = sha((tasks / relative).read_bytes())
    problem = tasks / "suite/task/problem.json"
    problem.write_text("{}")
    manifest["files"]["suite/task/problem.json"] = sha(problem.read_bytes())
    rewrite(source, path, manifest)
    task = {"id": "task", "source_id": source["id"], "executable": True, "direction": "maximize",
            "protocol": "original", "metric": "score", "contract_source": {
                "path": "suite/task/problem.json", "sha256": sha(problem.read_bytes())}}
    monkeypatch.setattr(evaluation, "get_catalog", lambda: {"tasks": [task], "sources": [source]})
    config = {"schema": "arena.evaluation-config/1", "task_id": "task", "timeout_seconds": 10,
              "execution": {"kind": "local_trusted", "python": sys.executable}}
    candidate = tmp_path / "candidate.py"
    candidate.write_text("raise AssertionError('candidate is inert')")
    result = evaluation.evaluate(config, candidate, tmp_path / "output")
    assert result["status"] == "completed" and result["raw_score"] == 4.25


@pytest.mark.parametrize("suffix", ["cpython-311-pytest-anything.pyc", "cpython-311-pytest-9.1.1.py",
                                     "cpython-311-pytest-9.1.1-extra.pyc"])
def test_arbitrary_pytest_named_files_are_not_cache_exceptions(bundle, suffix):
    tasks, source, _, _ = bundle
    cache = tasks / f"adapters/__pycache__/helper.{suffix}"
    cache.parent.mkdir()
    cache.write_bytes(b"not a recognized cache")
    with pytest.raises(ValueError, match="Unregistered"):
        library.verify_task_library(tasks, source)
