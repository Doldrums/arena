"""Native adapter contracts, with inert synthetic SCiEL artifacts only."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys

import pytest

from arena.frameworks.sciel import COMMIT, SCiELAdapter


@pytest.fixture
def prepared(tmp_path):
    source = tmp_path / "source checkout"
    (source / "src/sciel/cli").mkdir(parents=True)
    (source / "src/sciel/cli/main.py").write_text("raise AssertionError('do not import native framework')\n")
    (source / "tasks").mkdir()
    config = tmp_path / "native config.yaml"
    config.write_text("task: test/task\nllm:\n  api_key: secret-not-for-result\n")
    request = {"python": sys.executable, "config": str(config), "seed": 0, "budget": 2}
    return SCiELAdapter(), source, request, tmp_path / "output"


def test_prepare_uses_pinned_native_cli_and_keeps_configuration_inert(prepared):
    adapter, source, request, output = prepared
    plan = adapter.prepare(source, request, output)
    assert adapter.id == "sciel" and adapter.commit == COMMIT
    assert plan["argv"][:6] == [sys.executable, "-P", "-m", "sciel.cli.main", "run", request["config"]]
    assert plan["argv"][6:] == ["--outputs", str(output), "--run-id", "native",
                               "--tasks-root", str(source / "tasks"), "--seed", "0", "--budget", "2"]
    assert plan["cwd"] == str(source)
    assert plan["env"]["PYTHONPATH"].split(os.pathsep)[0] == str(source / "src")
    assert (Path(plan["env"]["PYTHONPATH"].split(os.pathsep)[1]) / "arena/frameworks/sciel_evaluate.py").is_file()
    assert plan["input_paths"] == [request["config"], str(source / "tasks")]
    assert "native/checkpoint.json" in plan["expected_artifacts"]
    assert "secret-not-for-result" not in json.dumps(plan)
    assert not output.exists()


def test_prepare_preserves_venv_python_symlink(prepared, tmp_path):
    adapter, source, request, output = prepared
    python = tmp_path / "venv/bin/python"
    python.parent.mkdir(parents=True)
    python.symlink_to(sys.executable)
    request["python"] = str(python)
    assert adapter.prepare(source, request, output)["argv"][0] == str(python)


def test_prepare_rejects_implicit_parent_dotenv_without_reading_secrets(prepared):
    adapter, source, request, output = prepared
    (source.parent / ".env").write_text("OPENROUTER_API_KEY=private-key\n")
    with pytest.raises(ValueError, match="auto-load") as error:
        adapter.prepare(source, request, output)
    assert "private-key" not in str(error.value)


@pytest.mark.parametrize("options", [
    {"budget": True}, {"budget": 0}, {"budget": 1.5}, {"seed": -1}, {"seed": False},
    {"action": "resume"}, {"extra_args": ["--force-identity"]}, {"arm": "../../escape"},
    {"campaign": "a;touch marker"}, {"config": "relative.yaml"}, {"python": "python3"},
    {"config": "/nonexistent/config.yaml"}, {"tasks_root": "/nonexistent/tasks"},
])
def test_prepare_rejects_invalid_native_options(prepared, options):
    adapter, source, request, output = prepared
    with pytest.raises(ValueError):
        adapter.prepare(source, {**request, **options}, output)


def test_prepare_external_tasks_are_explicit_and_existing_runs_are_not_reused(prepared, tmp_path):
    adapter, source, request, output = prepared
    tasks = tmp_path / "external tasks"
    tasks.mkdir()
    plan = adapter.prepare(source, {**request, "tasks_root": str(tasks), "campaign": "research-1", "arm": "A"}, output)
    assert str(tasks) in plan["input_paths"]
    assert plan["argv"][-4:] == ["--campaign", "research-1", "--arm", "A"]
    (output / "native").mkdir(parents=True)
    (output / "native/checkpoint.json").write_text("{}")
    with pytest.raises(ValueError, match="not empty"):
        adapter.prepare(source, request, output)


@pytest.fixture
def native_result(tmp_path):
    output = tmp_path / "result"
    native = output / "native"
    native.mkdir(parents=True)
    marker = tmp_path / "candidate-executed"
    code = f"from pathlib import Path\nPath({str(marker)!r}).touch()\n"
    first = {"event": "run_start", "run_id": "native-uuid", "segment_id": "segment-uuid", "event_seq": 1}
    prefix = (json.dumps(first) + "\n").encode()
    state = {"identity": {"task": "native/task", "task_hash": "task-digest", "engine_contract": "native-engine-contract"},
             "B_evals": 3, "iteration_no": 2, "cost_total": None,
             "provenance": {"schema": "sciel-checkpoint-provenance/1", "checkpoint_id": "checkpoint-uuid",
                            "run_id": "native-uuid", "journal_anchor": {"byte_offset": len(prefix),
                            "prefix_sha256": hashlib.sha256(prefix).hexdigest(), "segment_id": "segment-uuid", "event_seq": 1}},
             "db": {"pop_best_id": "best", "programs": [{"id": "best", "score": -2.0, "code": code}]},
             "config": {"llm": {"api_key": "private-key-must-not-appear"}}}

    def write(updated=None, end_changes=None, tail=b""):
        data = state if updated is None else updated
        raw = json.dumps(data).encode()
        (native / "checkpoint.json").write_bytes(raw)
        end = {"event": "run_end", "run_id": "native-uuid", "segment_id": "segment-uuid", "event_seq": 2,
               "checkpoint_id": "checkpoint-uuid", "checkpoint_sha256": hashlib.sha256(raw).hexdigest(),
               "reason": "budget", "pop_best": -2.0}
        end.update(end_changes or {})
        (native / "sciel_events.jsonl").write_bytes(prefix + (json.dumps(end) + "\n").encode() + tail)
    write()
    return output, state, marker, write


def test_result_binds_native_identity_and_retains_negative_fitness_without_execution(native_result):
    output, state, marker, _ = native_result
    result = SCiELAdapter().read_results(output)
    assert result["status"] == "recorded" and result["canonical_evaluation"] is False
    assert result["native"]["run_id"] == "native-uuid"
    assert result["native"]["task_hash"] == "task-digest"
    assert result["native"]["cost_total"] is None
    best = result["best_candidate"]
    assert best["score"] == -2.0 and best["direction"] == "maximize"
    assert best["score_space"] == "native_engine_fitness" and best["validity"] is None
    assert best["source_sha256"] == hashlib.sha256(state["db"]["programs"][0]["code"].encode()).hexdigest()
    assert len(result["artifacts"]) == 2 and all(len(a["sha256"]) == 64 for a in result["artifacts"])
    assert "private-key-must-not-appear" not in json.dumps(result)
    assert not marker.exists()


@pytest.mark.parametrize("end_changes", [
    {"checkpoint_sha256": "0" * 64}, {"run_id": "different-run"},
    {"segment_id": "different-segment"}, {"checkpoint_id": "different-checkpoint"}, {"pop_best": 7.0},
])
def test_result_does_not_claim_completion_with_mismatched_receipt(native_result, end_changes):
    output, _, marker, write = native_result
    write(end_changes=end_changes)
    result = SCiELAdapter().read_results(output)
    assert result["status"] == "partial" and result["warnings"]
    assert result["canonical_evaluation"] is False and not marker.exists()


def test_result_rejects_unbound_prefix_and_incomplete_tail(native_result):
    output, state, _, write = native_result
    altered = deepcopy(state)
    altered["provenance"]["journal_anchor"]["prefix_sha256"] = "0" * 64
    write(altered)
    result = SCiELAdapter().read_results(output)
    assert result["status"] == "partial" and "prefix" in result["warnings"][0]
    write(tail=b'{"event":')
    assert SCiELAdapter().read_results(output)["status"] == "partial"


def test_unknown_score_stays_unknown_and_duplicate_candidate_ids_fail(native_result):
    output, state, _, write = native_result
    state["db"]["programs"][0]["score"] = float("nan")
    write()
    assert SCiELAdapter().read_results(output)["best_candidate"]["score"] is None
    state["db"]["programs"].append(deepcopy(state["db"]["programs"][0]))
    write()
    with pytest.raises(ValueError, match="duplicated"):
        SCiELAdapter().read_results(output)


def test_missing_artifacts_are_not_success_or_zero(tmp_path):
    result = SCiELAdapter().read_results(tmp_path)
    assert result["status"] == "missing" and result["best_candidate"] is None
    assert result["native"] == {} and result["warnings"]


def test_result_does_not_follow_artifact_symlinks(native_result, tmp_path):
    output, _, _, _ = native_result
    checkpoint = output / "native/checkpoint.json"
    external = tmp_path / "external.json"
    checkpoint.rename(external)
    checkpoint.symlink_to(external)
    with pytest.raises(ValueError, match="symlinks"):
        SCiELAdapter().read_results(output)
