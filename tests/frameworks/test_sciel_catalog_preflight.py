"""Catalog preflight classification and receipts, without executing candidates."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import subprocess

import pytest

from arena.frameworks import evaluation
from arena.frameworks.sciel_catalog_profile import supports_requirements
from arena.registry import get_catalog
from arena import task_library


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "sciel_catalog_preflight", ROOT / "scripts/deployment/sciel_catalog_preflight.py")
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)
IMAGE = "sha256:" + "a" * 64


@pytest.fixture(autouse=True)
def forbid_runtime_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Preflight tests must not execute processes or contact providers")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


def task(ident="fixture", **changes):
    return {"id": ident, "executable": True, "requirements": ["py:numpy"],
            "family": "fixture", "protocol": "recreated", "metric": "score",
            "direction": "maximize", **changes}


def seed(root, ident):
    path = root / "suite" / ident / "initial_program.py"
    path.parent.mkdir(parents=True)
    path.write_text("raise AssertionError('A preflight inventory must never import its seed')\n")
    return path


def receipt(tmp_path, **changes):
    path = tmp_path / "receipt.json"
    path.write_text('{"inert_test_receipt": true}\n')
    return {"status": "completed", "raw_score": 0.0, "fitness": 0.0,
            "validity": True, "wall_seconds": 0.1, "candidate_sha256": "b" * 64,
            "evaluator_sha256": "c" * 64, "problem_sha256": "d" * 64,
            "task_source": {"kind": "bundled", "id": "arena-tasks"},
            "receipt_path": str(path), **changes}


def arguments(root, output, *extra):
    return ["--tasks-root", str(root), "--output", str(output), "--image", IMAGE, *extra]


def test_every_catalog_record_remains_visible_and_cpu_candidates_are_manifest_bound():
    catalog = get_catalog()
    source = next(s for s in catalog["sources"] if s["id"] == "arena-tasks")
    root = ROOT / "tasks"
    task_library.verify_task_library(root, source)
    files = task_library.load_task_manifest(source)["files"]
    rows = preflight.inventory(catalog["tasks"], root)
    assert len(rows) == len(catalog["tasks"]) == 959
    assert [row["task_id"] for row in rows] == [t["id"] for t in catalog["tasks"]]
    assert Counter(row["status"] for row in rows) == {
        "seed_check_pending": 349, "environment_preparation_pending": 332,
        "evaluation_integration_pending": 257, "runtime_integration_pending": 21}
    assert all(row["status"] != "seed_verified" for row in rows)
    for row in rows:
        if row["status"] == "seed_check_pending":
            assert supports_requirements(row["requirements"])
            for filename in ("initial_program.py", "evaluator.py", "task.json"):
                relative = f"suite/{row['task_id']}/{filename}"
                assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == files[relative]
    for group, eligible, deferred in (("base", 278, 71), ("extended", 71, 278)):
        selected = preflight.inventory(catalog["tasks"], root, group)
        assert len(selected) == 959
        assert Counter(row["status"] for row in selected) == {
            "seed_check_pending": eligible, "seed_check_deferred": deferred,
            "environment_preparation_pending": 332, "evaluation_integration_pending": 257,
            "runtime_integration_pending": 21}


def test_pending_reasons_distinguish_missing_evaluator_seed_and_environment(tmp_path):
    tasks = [task("no-evaluator", executable=False), task("no-python-seed"),
             task("gpu", requirements=["py:numpy", "py:torch", "gpu:cuda"]),
             task("linked"), task("cpu", requirements=["py:scipy", "py:numpy"])]
    for ident in ("no-evaluator", "gpu", "cpu"):
        seed(tmp_path, ident)
    linked = tmp_path / "suite/linked/initial_program.py"
    linked.parent.mkdir(parents=True)
    linked.symlink_to(tmp_path / "suite/cpu/initial_program.py")
    rows = preflight.inventory(tasks, tmp_path)
    assert [row["status"] for row in rows] == [
        "evaluation_integration_pending", "runtime_integration_pending",
        "environment_preparation_pending", "runtime_integration_pending", "seed_check_pending"]
    assert all(row["reason"] for row in rows[:-1])
    assert rows[-1]["reason"] is None


def test_default_inventory_never_evaluates_and_binds_the_verified_library(tmp_path, monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("--execute-seeds is required before evaluation")
    monkeypatch.setattr(evaluation, "evaluate", unexpected)
    output = tmp_path.resolve() / "inventory"
    assert preflight.main(arguments(ROOT / "tasks", output)) == 0
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["model_calls"] == 0
    assert manifest["image"] == IMAGE
    assert manifest["task_source"]["kind"] == "bundled"
    assert manifest["finished_at"] >= manifest["created_at"]
    assert sum(manifest["counts"].values()) == 959
    assert manifest["group"] == "all"
    assert manifest["counts"]["seed_check_pending"] == 349
    assert not list(output.glob("*/receipt.json"))
    assert (output / "manifest.json").stat().st_mode & 0o077 == 0


@pytest.mark.parametrize("status,validity,fitness,expected", [
    ("completed", True, 0.0, "seed_verified"),
    ("completed", None, 1.0, "seed_check_failed"),
    ("completed", False, 1.0, "seed_check_failed"),
    ("completed", True, None, "seed_check_failed"),
    ("timeout", True, 1.0, "seed_check_failed"),
    ("error", False, None, "seed_check_failed"),
])
def test_seed_check_uses_docker_and_requires_explicit_valid_fitness(
        tmp_path, monkeypatch, status, validity, fitness, expected):
    root, output = tmp_path / "library", tmp_path / "results"
    native = receipt(tmp_path, status=status, validity=validity, fitness=fitness)
    calls = []
    def evaluate(config, candidate, directory):
        calls.append((config, candidate, directory))
        return native
    monkeypatch.setattr(evaluation, "evaluate", evaluate)
    row = preflight.inventory([task()], root)[0]
    checked = preflight.check_seed(row, root=root, output=output, image=IMAGE, timeout=15)
    assert checked["status"] == expected
    assert checked["receipt_sha256"] == hashlib.sha256(Path(native["receipt_path"]).read_bytes()).hexdigest()
    assert len(calls) == 1
    config, candidate, directory = calls[0]
    assert config["execution"] == {"kind": "docker", "image": IMAGE, "python": "python"}
    assert config["timeout_seconds"] == 15
    assert candidate == root / "suite/fixture/initial_program.py"
    assert directory == output / "fixture"


def test_evaluation_exception_is_recorded_without_disclosing_exception_contents(tmp_path, monkeypatch):
    def unavailable(*args, **kwargs):
        raise RuntimeError("private provider information must not be projected")
    monkeypatch.setattr(evaluation, "evaluate", unavailable)
    row = preflight.inventory([task()], tmp_path)[0]
    checked = preflight.check_seed(row, root=tmp_path, output=tmp_path / "results", image=IMAGE, timeout=15)
    assert checked["status"] == "seed_check_failed"
    assert checked["reason"] == "RuntimeError"
    assert "private provider" not in json.dumps(checked)


def test_unreadable_receipt_is_one_task_failure_not_a_campaign_abort(tmp_path, monkeypatch):
    native = receipt(tmp_path, receipt_path=str(tmp_path / "missing-receipt.json"))
    monkeypatch.setattr(evaluation, "evaluate", lambda *args: native)
    row = preflight.inventory([task()], tmp_path)[0]
    checked = preflight.check_seed(row, root=tmp_path, output=tmp_path / "results", image=IMAGE, timeout=15)
    assert checked["status"] == "seed_check_failed"
    assert checked["reason"] == "FileNotFoundError"


def test_output_cannot_contaminate_the_immutable_task_library(tmp_path, monkeypatch):
    root = tmp_path.resolve() / "library"
    seed(root, "fixture")
    monkeypatch.setattr("arena.registry.get_catalog", lambda: {
        "sources": [{"id": "arena-tasks"}], "tasks": [task()]})
    monkeypatch.setattr(task_library, "verify_task_library", lambda *args: {"id": "arena-tasks"})
    monkeypatch.setattr(evaluation, "validate_config", lambda *args: {})
    output = root / "preflight-output"
    with pytest.raises(SystemExit) as error:
        preflight.main(arguments(root, output))
    assert error.value.code == 2
    assert not output.exists()
