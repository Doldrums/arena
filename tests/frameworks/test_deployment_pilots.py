"""Pilot generation and native planning only; no model or evaluator execution."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("pilot_templates", ROOT / "scripts/deployment/prepare_sciel_shinka.py")
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)
IMAGE = "sha256:" + "a" * 64


def test_generation_is_deterministic_nonsecret_and_bound_to_real_catalog_tasks():
    from arena.registry import get_catalog
    from arena.frameworks.sciel import COMMIT as sciel_pin
    from arena.frameworks.shinka import COMMIT as shinka_pin
    first = pilot.build_bundle(Path("/srv/arena"), "pilot-01", IMAGE)
    assert first == pilot.build_bundle(Path("/srv/arena"), "pilot-01", IMAGE)
    assert pilot.PINS["sciel"] == sciel_pin and pilot.PINS["shinka"] == shinka_pin
    catalog = get_catalog()
    tasks = {task["id"]: task for task in catalog["tasks"]}
    assert catalog["sources"][0]["repository"]["commit"] == pilot.PINS["autoresearch-tasks"]
    for framework in ("sciel", "shinka"):
        evaluation = first[framework + ".evaluation.json"]
        assert tasks[evaluation["task_id"]]["executable"] is True
        assert evaluation["execution"] == {"kind": "docker", "image": IMAGE, "python": "python", "require_control_cgroup": True}
        request = first[framework + ".run.json"]
        assert request["framework"] == framework
        assert request["environment_names"][0] == "OPENAI_API_KEY"
        assert Path(evaluation["receipts_dir"]).is_relative_to("/srv/arena/runs/pilot-01")
        assert not Path(evaluation["receipts_dir"]).is_relative_to("/srv/arena/tasks")
    manifest = first["manifest.json"]
    assert manifest["research_executed"] is False
    assert manifest["models_generation_verified"] is False
    assert manifest["provider"]["required_compatibility_policy"] == "codex-native"
    assert "max_tokens" in manifest["provider"]["unenforced_controls"]
    assert "mock" not in json.dumps(first).lower()


def test_generated_shinka_request_passes_real_adapter_and_forces_one_numeric_thread(tmp_path):
    from arena.frameworks.shinka import ShinkaAdapter
    bundle = pilot.build_bundle(tmp_path / "runtime", "pilot", IMAGE)
    request = bundle["shinka.run.json"]["request"]
    request["python"] = sys.executable
    source = tmp_path / "runtime/sources/shinka"
    entry = source / "shinka/cli/run.py"
    entry.parent.mkdir(parents=True)
    entry.write_text("raise AssertionError('do not import source')\n")
    task = Path(request["task_dir"])
    task.mkdir(parents=True)
    for name in ("initial.py", "evaluate.py"):
        (task / name).write_text("raise AssertionError('do not run task')\n")
    command = ShinkaAdapter().prepare(source, request, tmp_path / "output")
    assert "job.numeric_threads_per_job=1" in command["argv"]
    assert any("?api_key_env=OPENAI_API_KEY" in arg for arg in command["argv"])
    assert not (tmp_path / "output").exists()


def test_offline_write_never_launches_or_inspects_remote_runtime(tmp_path, monkeypatch):
    def no_process(*args, **kwargs):
        raise AssertionError("offline template generation cannot spawn subprocesses")
    monkeypatch.setattr(subprocess, "Popen", no_process)
    bundle = pilot.build_bundle(Path("/srv/arena"), "pilot", IMAGE)
    directory = tmp_path / "bundle"
    manifest = pilot.write_bundle(directory, bundle, root=Path("/srv/arena"), campaign="pilot")
    assert manifest["task_materialization"] == "pending"
    assert manifest["research_executed"] is False
    for name, digest in manifest["file_sha256"].items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest
        assert (directory / name).stat().st_mode & 0o077 == 0
    with pytest.raises(ValueError, match="new absolute directory"):
        pilot.write_bundle(directory, bundle, root=Path("/srv/arena"), campaign="pilot")


@pytest.mark.parametrize("change", [
    {"root": Path("relative")}, {"campaign": "../outside"}, {"image": "python:latest"},
    {"model": "mock-model"}, {"gateway": "https://public.example/v1"},
    {"gateway": "http://user:secret@127.0.0.1:8789/v1"},
    {"gateway": "http://127.0.0.1:8789/v1?api_key=secret"},
])
def test_invalid_or_credential_bearing_templates_are_rejected(change):
    kwargs = {"root": Path("/srv/arena"), "campaign": "pilot", "image": IMAGE, **change}
    with pytest.raises(ValueError):
        pilot.build_bundle(**kwargs)


def test_inventory_covers_all_source_verified_profiles_without_claiming_readiness():
    from arena.frameworks.recipes import load_recipes
    recipes = load_recipes()
    expected = {(ident, profile["id"]) for ident, recipe in recipes.items()
                if recipe["status"] == "source_verified" for profile in recipe["profiles"]}
    inventory = pilot.cpu_inventory()
    assert {(row["engine"], row["profile"]) for row in inventory["profiles"]} == expected
    assert sum(inventory["counts"].values()) == len(expected)
    assert all(row["runtime_readiness"] == "not_verified" and not row["canonical_evaluation"]
               for row in inventory["profiles"])
    evolcaf = next(row for row in inventory["profiles"] if row["engine"] == "evolcaf")
    assert any("20 joblib workers" in text for text in evolcaf["limitations"])


def test_provider_binding_preserves_exact_model_and_cannot_mark_offline_templates_ready(tmp_path):
    record = {"model": "gpt-5.6-sol", "response_model": "gpt-5.6-sol", "status": "generation_verified",
              "seconds": 1.2, "usage": {"prompt_tokens": 13, "completion_tokens": 5, "total_tokens": 18}}
    proof = tmp_path / "probe.json"
    proof.write_text(json.dumps([record]))
    bundle = pilot.build_bundle(Path("/srv/arena"), "pilot", IMAGE)
    destination = tmp_path / "prepared"
    manifest = pilot.write_bundle(destination, bundle, root=Path("/srv/arena"), campaign="pilot", probe_evidence=proof)
    assert manifest["models_generation_verified"] is True
    assert manifest["research_executed"] is False
    binding = json.loads((destination / "provider-probe.json").read_text())
    assert binding["source_sha256"] == hashlib.sha256(proof.read_bytes()).hexdigest()
    assert binding["record"] == record
    templates = json.loads((destination / "control-templates.json").read_text())
    assert len(templates) == 2 and all(row["status"] == "blocked" for row in templates)
    bundle["manifest.json"].update(source_verification="verified_clean_pins", models_generation_verified=True)
    ready = pilot.control_templates(bundle)
    from arena.control import validate_config
    example = json.loads((ROOT / "docs/control.example.json").read_text())
    example["templates"] = ready
    validate_config(example)
    assert all(row["status"] == "ready" and row["spec"]["output_dir"] == "{output_dir}" for row in ready)


@pytest.mark.parametrize("change", [
    {"response_model": "other-model"}, {"status": "discovery_only"}, {"seconds": float("nan")},
    {"api_key": "not-a-real-key"}, {"usage": {"prompt_tokens": 13, "completion_tokens": 0, "total_tokens": 13}},
])
def test_bad_provider_evidence_is_rejected_before_bundle_creation(tmp_path, change):
    record = {"model": "gpt-5.6-sol", "response_model": "gpt-5.6-sol", "status": "generation_verified",
              "seconds": 1.2, "usage": {"prompt_tokens": 13, "completion_tokens": 5, "total_tokens": 18}, **change}
    proof = tmp_path / "probe.json"
    proof.write_text(json.dumps([record]))
    bundle = pilot.build_bundle(Path("/srv/arena"), "pilot", IMAGE)
    with pytest.raises(ValueError):
        pilot.write_bundle(tmp_path / "absent", bundle, root=Path("/srv/arena"), campaign="pilot", probe_evidence=proof)
    assert not (tmp_path / "absent").exists()
