"""Inert fixtures follow jennyzzt/dgm at a565fd2d; no upstream imports/runs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from arena.frameworks.dgm import COMMIT, DGMAdapter
import arena.frameworks.dgm as dgm


RUN = "20260921120530_123456"
CHILD = "20260921_120600_123456"


@pytest.fixture
def plan_inputs(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    # Deliberately invalid Python: prepare must neither import nor execute it.
    (source / "DGM_outer.py").write_text("not importable native source !")
    swe = tmp_path / "swe"
    evaluator = swe / "swebench/harness/run_evaluation.py"
    evaluator.parent.mkdir(parents=True)
    evaluator.write_text("must not execute")
    python = tmp_path / "venv/bin/python"
    python.parent.mkdir(parents=True)
    python.symlink_to(sys.executable)
    request = {"python": str(python), "benchmark": "swe-bench", "max_generation": 2,
               "swe_bench_dir": str(swe)}
    return source, request, tmp_path / "output"


def pinned_parser():
    """Native declarations from DGM_outer.py:234–257, including its choices typo."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--max_generation", type=int, default=80)
    parser.add_argument("--selfimprove_size", type=int, default=2)
    parser.add_argument("--selfimprove_workers", type=int, default=2)
    parser.add_argument("--choose_selfimproves_method", default="score_child_prop",
                        choices=["random", "score_prop", "score_child_prop" "best"])
    parser.add_argument("--continue_from")
    parser.add_argument("--update_archive", default="keep_all", choices=["keep_better", "keep_all"])
    parser.add_argument("--num_swe_evals", type=int, default=1)
    for name in ("post_improve_diagnose", "shallow_eval", "polyglot", "no_full_eval"):
        parser.add_argument("--" + name, action="store_true")
    parser.add_argument("--eval_noise", type=float, default=0.1)
    parser.add_argument("--run_baseline", choices=["no_selfimprove", "no_darwin"])
    return parser


def test_plan_is_inert_and_uses_output_contained_git_workspace(plan_inputs, monkeypatch):
    source, request, output = plan_inputs
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("No processes during planning"))
    plan = DGMAdapter().prepare(source, request, output)
    assert not output.exists()
    assert plan["argv"][:2] == [request["python"], "DGM_outer.py"]
    assert plan["cwd"] == str(output / "workspace/dgm")
    assert plan["workspace_copy"] is True
    assert plan["workspace_inputs"] == [{"source": request["swe_bench_dir"], "destination": "swe_bench/SWE-bench"}]
    assert plan["input_paths"] == [request["swe_bench_dir"]]
    assert plan["evaluator_profile"] == "dgm-native-swe-bench"
    assert plan["env"]["PATH"].split(os.pathsep)[0] == str(Path(request["python"]).parent)
    assert set(plan["env"]) == {"PATH"}
    assert DGMAdapter.commit == COMMIT == "a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2"
    args = pinned_parser().parse_args(plan["argv"][2:])
    assert (args.max_generation, args.selfimprove_size, args.selfimprove_workers, args.num_swe_evals) == (2, 1, 1, 1)
    assert args.shallow_eval and args.no_full_eval and not args.polyglot
    assert args.choose_selfimproves_method == "score_child_prop"
    assert "--choose_selfimproves_method" not in plan["argv"]


def test_explicit_native_controls_parse_at_pin(plan_inputs):
    source, request, output = plan_inputs
    request.update(max_generation=4, selfimprove_size=3, selfimprove_workers=2, num_swe_evals=2,
                   choose_selfimproves_method="score_prop", update_archive="keep_better",
                   shallow_eval=False, no_full_eval=False, eval_noise=0.2, run_baseline="no_darwin")
    args = pinned_parser().parse_args(DGMAdapter().prepare(source, request, output)["argv"][2:])
    assert (args.max_generation, args.selfimprove_size, args.selfimprove_workers, args.num_swe_evals) == (4, 3, 2, 2)
    assert args.choose_selfimproves_method == "score_prop" and args.update_archive == "keep_better"
    assert not args.shallow_eval and not args.no_full_eval and args.run_baseline == "no_darwin"


@pytest.mark.parametrize("change", [
    {"max_generation": 0}, {"max_generation": 81}, {"max_generation": True},
    {"selfimprove_size": 9}, {"selfimprove_workers": 2}, {"num_swe_evals": 0},
    {"choose_selfimproves_method": "best"}, {"choose_selfimproves_method": "score_child_propbest"},
    {"eval_noise": float("nan")}, {"eval_noise": True}, {"shallow_eval": "false"},
    {"benchmark": "arena-task"}, {"continue_from": "/old/run"}, {"api_key": "secret"},
    {"model": "arbitrary"}, {"python": "python"}, {"run_baseline": "invented"},
    {"polyglot_metadata": "/irrelevant"},
])
def test_bad_or_unsupported_requests_are_rejected(plan_inputs, change):
    source, request, output = plan_inputs
    with pytest.raises(ValueError):
        DGMAdapter().prepare(source, request | change, output)
    assert not output.exists()


def test_max_generation_required_and_workspace_never_reused(plan_inputs):
    source, request, output = plan_inputs
    del request["max_generation"]
    with pytest.raises(ValueError, match="max_generation"):
        DGMAdapter().prepare(source, request, output)
    request["max_generation"] = 1
    (output / "workspace/dgm").mkdir(parents=True)
    with pytest.raises(ValueError, match="new isolated workspace"):
        DGMAdapter().prepare(source, request, output)
    with pytest.raises(ValueError, match="whitespace"):
        DGMAdapter().prepare(source, request, output.parent / "has space")


def test_polyglot_stages_prepared_inputs_without_regenerating_them(plan_inputs, tmp_path):
    source, request, output = plan_inputs
    benchmark = tmp_path / "prepared"
    (benchmark / "python/exercises/practice/hello-world/.git").mkdir(parents=True)
    metadata = tmp_path / "polyglot.json"
    entry = {"instance_id": "python__hello-world", "language": "python", "problem_statement": "Return a greeting.",
             "base_commit": "a" * 40, "test_commit": "b" * 40, "test_patch": "diff --git a/test.py b/test.py",
             "repo": "polyglot/polyglot-benchmark/python/exercises/practice/hello-world"}
    metadata.write_text(json.dumps([entry]))
    request.pop("swe_bench_dir")
    request.update(benchmark="polyglot", polyglot_metadata=str(metadata), polyglot_benchmark_dir=str(benchmark))
    plan = DGMAdapter().prepare(source, request, output)
    assert plan["evaluator_profile"] == "dgm-native-polyglot"
    assert pinned_parser().parse_args(plan["argv"][2:]).polyglot
    assert plan["workspace_inputs"] == [
        {"source": str(metadata), "destination": "polyglot/polyglot_benchmark_metadata.json"},
        {"source": str(benchmark), "destination": "polyglot/polyglot-benchmark"}]
    assert not output.exists()
    for bad_path in ("/outside/exercise", "polyglot/polyglot-benchmark/../../../escape", "polyglot\\bad"):
        metadata.write_text(json.dumps([entry | {"repo": bad_path}]))
        with pytest.raises(ValueError, match="repo paths"):
            DGMAdapter().prepare(source, request, output)


@pytest.fixture
def native_output(tmp_path):
    run = tmp_path / "workspace/dgm/output_dgm" / RUN
    run.mkdir(parents=True)
    generations = [
        {"generation": 0, "selfimprove_entries": [["initial", "django__django-10999"]],
         "children": [CHILD], "children_compiled": [CHILD], "archive": ["initial", CHILD]},
        {"generation": 1, "selfimprove_entries": [], "children": [], "children_compiled": [],
         "archive": ["initial", CHILD]},
    ]
    # This is the exact upstream serialization: concatenated multiline objects.
    (run / "dgm_metadata.jsonl").write_text("".join(json.dumps(row, indent=2) + "\n" for row in generations))
    for member, score, submitted in [("initial", 0.142, 225), (CHILD, 0.3, 10)]:
        (run / member).mkdir()
        metadata = {"run_id": member, "parent_commit": "initial", "overall_performance": {
            "accuracy_score": score, "total_resolved_instances": 32 if member == "initial" else 3,
            "total_submitted_instances": submitted, "total_resolved_ids": [], "total_unresolved_ids": [],
            "total_emptypatch_ids": []}}
        (run / member / "metadata.json").write_text(json.dumps(metadata, indent=4))
    return tmp_path, run


def test_reader_preserves_native_denominators_and_cached_baseline(native_output):
    output, run = native_output
    result = DGMAdapter().read_results(output)
    assert result["schema"] == "arena.native-result/1" and result["status"] == "recorded"
    assert result["canonical_evaluation"] is False
    data = result["native"]["runs"][0]
    assert [row["generation"] for row in data["generations"]] == [0, 1]
    members = {row["run_id"]: row for row in data["members"]}
    assert members["initial"]["cached_initial"] is True
    assert members["initial"]["overall_performance"]["accuracy_score"] == 0.142
    assert members["initial"]["overall_performance"]["total_submitted_instances"] == 225
    assert members[CHILD]["overall_performance"]["total_submitted_instances"] == 10
    assert members[CHILD]["validity"] == "unknown"
    assert "best_score" not in result and "score" not in result
    assert len(result["artifacts"]) == 3
    for artifact in result["artifacts"]:
        assert artifact["sha256"] == hashlib.sha256((output / artifact["path"]).read_bytes()).hexdigest()


def test_truncated_journal_preserves_complete_records_and_marks_partial(native_output):
    output, run = native_output
    with (run / "dgm_metadata.jsonl").open("a") as stream:
        stream.write('{"generation": 2, "archive": [')
    result = DGMAdapter().read_results(output)
    assert result["status"] == "partial"
    assert len(result["native"]["runs"][0]["generations"]) == 2
    assert any("unfinished" in warning for warning in result["warnings"])


def test_missing_metadata_is_partial_and_missing_run_is_not_zero(native_output, tmp_path):
    output, run = native_output
    (run / CHILD / "metadata.json").unlink()
    assert DGMAdapter().read_results(output)["status"] == "partial"
    empty = tmp_path / "empty"
    empty.mkdir()
    result = DGMAdapter().read_results(empty)
    assert result["status"] == "missing" and result["native"]["runs"] == []
    assert not result["artifacts"]


def test_reader_does_not_trust_path_ids_or_load_pickle(native_output):
    output, run = native_output
    (run / "state.pkl").write_bytes(b"not JSON and never read")
    row = {"generation": 0, "children": ["../../outside"], "children_compiled": [], "archive": ["initial"]}
    (run / "dgm_metadata.jsonl").write_text(json.dumps(row, indent=2))
    result = DGMAdapter().read_results(output)
    assert result["status"] == "partial" and not result["native"]["runs"][0]["members"]
    assert len(result["artifacts"]) == 1


def test_symlinked_metadata_is_rejected(native_output):
    output, run = native_output
    path = run / CHILD / "metadata.json"
    path.unlink()
    path.symlink_to(run / "initial/metadata.json")
    with pytest.raises(ValueError, match="symlinks"):
        DGMAdapter().read_results(output)


def test_reader_limits_json_size_and_rejects_nonfinite_json(native_output, monkeypatch):
    output, run = native_output
    monkeypatch.setattr(dgm, "_MAX_JSON", 16)
    with pytest.raises(ValueError, match="bounded regular"):
        DGMAdapter().read_results(output)
    monkeypatch.setattr(dgm, "_MAX_JSON", 4 * 1024 * 1024)
    (run / CHILD / "metadata.json").write_text('{"run_id":"' + CHILD + '","overall_performance":{"accuracy_score":NaN}}')
    with pytest.raises(ValueError, match="Non-finite"):
        DGMAdapter().read_results(output)


def test_metadata_identity_mismatch_never_borrows_a_score(native_output):
    output, run = native_output
    path = run / CHILD / "metadata.json"
    data = json.loads(path.read_text())
    data["run_id"] = "initial"
    path.write_text(json.dumps(data))
    result = DGMAdapter().read_results(output)
    assert result["status"] == "partial"
    assert [row["run_id"] for row in result["native"]["runs"][0]["members"]] == ["initial"]
