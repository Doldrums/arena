"""Inert native report/loop fixtures; no Docker, model or upstream execution."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

import pytest

from arena.frameworks.dgm import COMMIT, DGMAdapter
from arena.frameworks.drivers import dgm_pilot as pilot


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    for name in (*pilot.SOURCE_HASHES, "DGM_outer.py", "polyglot/harness.py", "utils/evo_utils.py"):
        file = source / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("deliberately not importable upstream fixture !")
    dump(source / "initial_polyglot/metadata.json", {"run_id": "initial", "cached_score": 225})
    dump(source / "polyglot/subsets/small.json", ["cached_other_task"])
    directory = tmp_path / "prepared"
    inputs = directory / "native-inputs"
    rows = []
    for task in pilot.TASKS:
        repo = "polyglot/polyglot-benchmark/python/exercises/practice/" + task.split("__")[1]
        (inputs / repo / ".git").mkdir(parents=True)
        (inputs / repo / "exercise.py").write_text("fixture seed")
        rows.append({"instance_id": task, "language": "python", "repo": repo,
                     "base_commit": "a" * 40, "test_commit": "b" * 40,
                     "problem_statement": "fixture", "test_patch": "fixture patch"})
    dump(inputs / "polyglot/polyglot_benchmark_metadata.json", rows)
    overlays = {name: "reviewed overlay fixture " + name for name in pilot.SOURCE_HASHES}
    monkeypatch.setattr(pilot, "provider_overlays", lambda _: overlays)
    for name, text in overlays.items():
        file = directory / "provider-overlays" / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text)
    dump(directory / "native-image-recipes.json", {task: "fixture recipe" for task in pilot.TASKS})
    freeze = tmp_path / "freeze.txt"
    freeze.write_text("fixture==1\n")
    manifest = {"schema": "arena.dgm-native-preparation/1", "source_commit": COMMIT,
                "benchmark": {"commit": pilot.AIDER_COMMIT, "task_ids": list(pilot.TASKS)},
                "swebench_import_dependency": {"commit": pilot.SWE_COMMIT},
                "provider_original_files": pilot.SOURCE_HASHES,
                "native_input_files": pilot.tree(inputs),
                "provider_overlay_files": pilot.tree(directory / "provider-overlays"),
                "native_image_recipes_sha256": pilot.sha(directory / "native-image-recipes.json"),
                "dependency_freeze_sha256": pilot.sha(freeze),
                "integration_sha256": pilot.sha(Path(pilot.__file__).with_name("dgm_gateway.py"))}
    dump(directory / "preparation.json", manifest)
    request = {"python": sys.executable, "benchmark": "polyglot", "profile": pilot.PROFILE,
               "model": pilot.MODELS[0], "preparation_dir": str(directory), "dependency_freeze": str(freeze)}
    return source, directory, request, tmp_path / "output"


def stage(prepared):
    source, _, request, output = prepared
    command = DGMAdapter().prepare(source, request, output)
    workspace = Path(command["cwd"])
    shutil.copytree(source, workspace)
    for entry in command["workspace_inputs"]:
        src, dst = Path(entry["source"]), workspace / entry["destination"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst) if src.is_dir() else shutil.copyfile(src, dst)
    plan = {"schema": "arena.native-plan/1", "framework": "dgm", "source": {"commit": COMMIT},
            "command": command, "inputs": [{"path": str(Path(request["preparation_dir"]) / "preparation.json"),
                                             "sha256": command["preparation_sha256"]}]}
    plan["sha256"] = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    dump(output / ".arena/plan.json", plan)
    return command, workspace


def fake_native(monkeypatch, workspace, model, *, resolved=0, incomplete=False):
    calls = []
    report = {"total_instances": 2, "submitted_instances": 2, "completed_instances": 2,
              "resolved_instances": resolved, "unresolved_instances": 2 - resolved,
              "empty_patch_instances": 0, "error_instances": 0,
              "submitted_ids": list(pilot.TASKS), "completed_ids": list(pilot.TASKS),
              "incomplete_ids": [], "error_ids": [], "unstopped_containers": [],
              "resolved_ids": list(pilot.TASKS[:resolved]), "unresolved_ids": list(pilot.TASKS[resolved:]), "empty_patch_ids": []}
    performance = {"accuracy_score": resolved / 2, "total_resolved_instances": resolved,
                   "total_submitted_instances": 2, "total_resolved_ids": report["resolved_ids"],
                   "total_unresolved_ids": report["unresolved_ids"], "total_emptypatch_ids": [],
                   "files": [model + "_0.0.json"]}
    if incomplete:
        report.update(completed_instances=1, incomplete_ids=[pilot.TASKS[0]])
    def harness(**kwargs):
        calls.append(("harness", kwargs))
        predictions = Path(kwargs["pred_dname"]) / (model + "_0")
        predictions.mkdir()
        for index, task in enumerate(pilot.TASKS):
            dump(predictions / (task + ".json"), {"instance_id": task, "success": True,
                "model_name_or_path": model + "_0",
                "eval_result": "resolved" if index < resolved else "unresolved"})
            (predictions / (task + ".md")).write_text("native fixture conversation")
            (predictions / (task + "_eval.md")).write_text("native fixture test output")
        dump(Path(kwargs["output_dir"]) / (model + "_0.0.json"), report)
    def native_outer(argv, **kwargs):
        calls.append(("outer", argv))
        run = workspace / "output_dgm/20260921120530_123456"
        run.mkdir(parents=True)
        shutil.copytree(workspace / "initial_polyglot", run / "initial")
        dump(run / "dgm_metadata.jsonl", {"generation": 0, "archive": ["initial"], "children": [], "children_compiled": []})
        return SimpleNamespace(returncode=0)
    monkeypatch.setitem(sys.modules, "polyglot.harness", SimpleNamespace(harness=harness))
    monkeypatch.setitem(sys.modules, "utils.evo_utils", SimpleNamespace(get_all_performance=lambda *a, **k: ([], performance)))
    monkeypatch.setattr(pilot.subprocess, "run", native_outer)
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.chdir(workspace)
    monkeypatch.setenv("ARENA_DGM_MODEL", model)
    monkeypatch.setenv("ARENA_DGM_GATEWAY_URL", pilot.GATEWAY)
    monkeypatch.setenv("DOCKER_HOST", pilot.DOCKER_HOST)
    monkeypatch.setenv("ARENA_CONTROL_RUN_ID", "a" * 32)
    return calls


def test_plan_is_pure_and_binds_every_runtime_input(prepared, monkeypatch):
    source, directory, request, output = prepared
    monkeypatch.setattr(pilot.subprocess, "run", lambda *a, **k: pytest.fail("Planning must not execute native code"))
    plan = DGMAdapter().prepare(source, request, output)
    assert not output.exists()
    assert plan["argv"] == [sys.executable, "-m", "arena.frameworks.drivers.dgm_pilot", "--model", request["model"]]
    assert all(entry["source"] in plan["input_paths"] for entry in plan["workspace_inputs"])
    assert str(directory / "provider-overlays") in plan["input_paths"]
    assert str(directory / "preparation.json") in plan["input_paths"]
    assert plan["env"]["DOCKER_HOST"] == pilot.DOCKER_HOST
    assert plan["env"]["ARENA_DGM_MODEL"] == request["model"]
    assert "OPENAI_API_KEY" not in plan["env"]


@pytest.mark.parametrize("change", [{"model": "other"}, {"max_generation": 2}, {"docker_host": "unix:///var/run/docker.sock"}, {"benchmark": "swe-bench"}])
def test_profile_does_not_accept_unbounded_or_unreviewed_controls(prepared, change):
    source, _, request, output = prepared
    with pytest.raises(ValueError):
        DGMAdapter().prepare(source, request | change, output)


@pytest.mark.parametrize("relative", ["provider-overlays/llm.py", "native-inputs/polyglot/polyglot_benchmark_metadata.json", "native-image-recipes.json"])
def test_input_tampering_fails_before_workspace_creation(prepared, relative):
    source, directory, request, output = prepared
    (directory / relative).write_text("changed")
    with pytest.raises(ValueError):
        DGMAdapter().prepare(source, request, output)
    assert not output.exists()


@pytest.mark.parametrize("resolved", [0, 2])
def test_real_report_shape_drives_fresh_initial_then_unchanged_native_loop(prepared, monkeypatch, resolved):
    _, _, request, output = prepared
    command, workspace = stage(prepared)
    calls = fake_native(monkeypatch, workspace, request["model"], resolved=resolved)
    pilot.run(workspace, request["model"])
    assert [kind for kind, _ in calls] == ["harness", "outer"]
    assert calls[0][1]["test_task_list"] == list(pilot.TASKS)
    assert calls[0][1]["max_workers"] == calls[0][1]["num_evals"] == calls[0][1]["num_evals_parallel"] == 1
    assert calls[0][1]["model_name_or_path"] == request["model"]
    assert calls[1][1] == [sys.executable, *pilot.NATIVE_ARGUMENTS]
    result = DGMAdapter().read_results(output)
    member = result["native"]["runs"][0]["members"][0]
    assert result["status"] == "recorded" and result["canonical_evaluation"] is False
    assert member["cached_initial"] is False and member["baseline_provenance"] == "fresh_native_two_task"
    assert member["overall_performance"]["accuracy_score"] == resolved / 2
    assert member["overall_performance"]["total_submitted_instances"] == 2


def test_incomplete_baseline_never_starts_search_or_fabricates_zero(prepared, monkeypatch):
    _, _, request, _ = prepared
    _, workspace = stage(prepared)
    calls = fake_native(monkeypatch, workspace, request["model"], incomplete=True)
    with pytest.raises(ValueError, match="incomplete"):
        pilot.run(workspace, request["model"])
    assert [kind for kind, _ in calls] == ["harness"]
    assert not (workspace / ".arena-pilot/baseline-proof.json").exists()
    assert not (workspace / "initial_polyglot/metadata.json").exists()


def test_reader_refuses_fresh_label_after_report_tampering(prepared, monkeypatch):
    _, _, request, output = prepared
    _, workspace = stage(prepared)
    fake_native(monkeypatch, workspace, request["model"])
    pilot.run(workspace, request["model"])
    report = workspace / "output_dgm/20260921120530_123456/initial" / (request["model"] + "_0.0.json")
    report.write_text("{}")
    result = DGMAdapter().read_results(output)
    member = result["native"]["runs"][0]["members"][0]
    assert result["status"] == "partial" and member["cached_initial"] is None
    assert member["baseline_provenance"] == "unverified"
    assert "fresh_baseline" not in result["native"]


@pytest.mark.parametrize("suffix", [".json", ".md", "_eval.md"])
def test_reader_requires_every_baseline_prediction_artifact_in_proof(prepared, monkeypatch, suffix):
    _, _, request, output = prepared
    _, workspace = stage(prepared)
    fake_native(monkeypatch, workspace, request["model"])
    pilot.run(workspace, request["model"])
    proof_path = workspace / ".arena-pilot/baseline-proof.json"
    proof = json.loads(proof_path.read_text())
    missing = f"predictions/{request['model']}_0/{pilot.TASKS[0]}{suffix}"
    del proof["files"][missing]
    dump(proof_path, proof)
    result = DGMAdapter().read_results(output)
    member = result["native"]["runs"][0]["members"][0]
    assert result["status"] == "partial"
    assert member["cached_initial"] is None and member["baseline_provenance"] == "unverified"
    assert "fresh_baseline" not in result["native"]


@pytest.mark.parametrize("listed", [False, True])
def test_reader_never_reads_predictions_through_external_parent(prepared, monkeypatch, tmp_path, listed):
    _, _, request, output = prepared
    _, workspace = stage(prepared)
    fake_native(monkeypatch, workspace, request["model"])
    pilot.run(workspace, request["model"])
    initial = workspace / "output_dgm/20260921120530_123456/initial"
    outside = tmp_path / "outside-native-output"
    (initial / "predictions").rename(outside)
    (initial / "predictions").symlink_to(outside, target_is_directory=True)
    proof_path = workspace / ".arena-pilot/baseline-proof.json"
    proof = json.loads(proof_path.read_text())
    if not listed:
        proof["files"] = {k: v for k, v in proof["files"].items() if not k.startswith("predictions/")}
    dump(proof_path, proof)
    external_reads = []
    # These benign fixtures reproduce the old direct Path.read_* bypass without
    # accessing any real data outside the test directory.
    for method in ("read_bytes", "read_text"):
        original = getattr(Path, method)
        def checked(path, *args, _original=original, **kwargs):
            if path.resolve().is_relative_to(outside):
                external_reads.append(str(path))
            return _original(path, *args, **kwargs)
        monkeypatch.setattr(Path, method, checked)
    result = DGMAdapter().read_results(output)
    assert external_reads == []
    assert result["status"] == "partial"
    assert "fresh_baseline" not in result["native"]


def test_reader_preserves_native_empty_patch_without_inventing_eval_logs(prepared, monkeypatch):
    _, _, request, output = prepared
    _, workspace = stage(prepared)
    fake_native(monkeypatch, workspace, request["model"])
    pilot.run(workspace, request["model"])
    initial = workspace / "output_dgm/20260921120530_123456/initial"
    report_path = initial / (request["model"] + "_0.0.json")
    report = json.loads(report_path.read_text())
    report.update(unresolved_instances=0, unresolved_ids=[], empty_patch_instances=2,
                  empty_patch_ids=list(pilot.TASKS))
    dump(report_path, report)
    for task in pilot.TASKS:
        path = initial / f"predictions/{request['model']}_0/{task}.json"
        dump(path, json.loads(path.read_text()) | {"eval_result": "empty_patch"})
        path.with_name(task + "_eval.md").unlink()
    metadata = json.loads((initial / "metadata.json").read_text())
    metadata["overall_performance"].update(total_unresolved_ids=[], total_emptypatch_ids=list(pilot.TASKS))
    dump(initial / "metadata.json", metadata)
    proof_path = workspace / ".arena-pilot/baseline-proof.json"
    proof = json.loads(proof_path.read_text())
    proof.update(files=pilot.tree(initial), native_performance=metadata["overall_performance"])
    dump(proof_path, proof)
    # Result reading must not reuse the live-harness helpers that open paths.
    monkeypatch.setattr(pilot, "read_json", lambda *_: pytest.fail("reader bypassed bounded evidence"))
    monkeypatch.setattr(pilot, "sha", lambda *_: pytest.fail("reader bypassed bounded evidence"))
    result = DGMAdapter().read_results(output)
    assert result["status"] == "recorded"
    assert result["native"]["fresh_baseline"]["overall_performance"]["accuracy_score"] == 0
    assert result["native"]["fresh_baseline"]["cached_initial"] is False


def test_reader_bounds_prediction_json_even_with_matching_proof_hash(prepared, monkeypatch):
    from arena.frameworks import dgm
    _, _, request, output = prepared
    _, workspace = stage(prepared)
    fake_native(monkeypatch, workspace, request["model"])
    pilot.run(workspace, request["model"])
    initial = workspace / "output_dgm/20260921120530_123456/initial"
    name = f"predictions/{request['model']}_0/{pilot.TASKS[0]}.json"
    path = initial / name
    path.write_text(path.read_text() + " " * dgm._MAX_JSON)
    proof_path = workspace / ".arena-pilot/baseline-proof.json"
    proof = json.loads(proof_path.read_text())
    proof["files"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    dump(proof_path, proof)
    result = DGMAdapter().read_results(output)
    assert result["status"] == "partial"
    assert "fresh_baseline" not in result["native"]


def test_wrapper_refuses_raw_docker_before_imports_or_mutation(prepared, monkeypatch):
    _, _, request, _ = prepared
    _, workspace = stage(prepared)
    fake_native(monkeypatch, workspace, request["model"])
    monkeypatch.setenv("DOCKER_HOST", "unix:///var/run/docker.sock")
    with pytest.raises(ValueError, match="scoped Docker"):
        pilot.run(workspace, request["model"])
    assert json.loads((workspace / "initial_polyglot/metadata.json").read_text())["cached_score"] == 225


def test_all_model_templates_reserve_native_child_concurrency_and_require_review():
    path = Path(__file__).resolve().parents[2] / "scripts/deployment/prepare_dgm_runtime_pilots.py"
    spec = importlib.util.spec_from_file_location("dgm_runtime_templates", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows = [module.template(Path("/srv/arena"), model) for model in pilot.MODELS]
    assert len({row["id"] for row in rows}) == len(pilot.MODELS) == 7
    for model, row in zip(pilot.MODELS, rows):
        assert row["model"] == row["spec"]["request"]["model"] == model
        assert row["framework"] == row["spec"]["framework"] == "dgm"
        assert row["profile"] == row["spec"]["request"]["profile"] == pilot.PROFILE
        assert row["resources"] == {"cpus": 4, "memory_mb": 16384, "evaluation_slots": 2, "pids": 1024}
        assert row["status"] == "blocked" and row["blocked_reason"]
        assert row["spec"]["timeout_seconds"] == 3600
        assert row["spec"]["environment_names"] == ["OPENAI_API_KEY"]
