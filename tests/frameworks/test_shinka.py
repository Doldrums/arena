"""Fixtures model the pinned native schema; no Shinka code is imported or run."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys

import pytest

from arena.frameworks.shinka import COMMIT, MAX_FIELD_CHARS, MAX_RECORDS, ShinkaAdapter


# shinka/database/dbase.py:_create_tables at 9912af12. Includes unselected native
# columns to prove the reader does not need code, embeddings or model traces.
PROGRAMS_SCHEMA = """
CREATE TABLE programs (
 id TEXT PRIMARY KEY, code TEXT NOT NULL, language TEXT NOT NULL, parent_id TEXT,
 archive_inspiration_ids TEXT, top_k_inspiration_ids TEXT,
 generation INTEGER NOT NULL, timestamp REAL NOT NULL, code_diff TEXT,
 combined_score REAL, public_metrics TEXT, private_metrics TEXT, text_feedback TEXT,
 complexity REAL, embedding TEXT, embedding_pca_2d TEXT, embedding_pca_3d TEXT,
 embedding_cluster_id INTEGER, correct BOOLEAN DEFAULT 0,
 children_count INTEGER NOT NULL DEFAULT 0, metadata TEXT,
 migration_history TEXT, island_idx INTEGER, system_prompt_id TEXT
)
"""


@pytest.fixture
def adapter():
    return ShinkaAdapter()


@pytest.fixture
def plan_inputs(tmp_path):
    source = tmp_path / "Shinka source"
    cli = source / "shinka/cli/run.py"
    cli.parent.mkdir(parents=True)
    cli.write_text("raise AssertionError('Do not execute source while planning')\n")
    task = tmp_path / "task with spaces"
    task.mkdir()
    (task / "evaluate.py").write_text("raise AssertionError('Do not import evaluator')\n")
    (task / "initial.py").write_text("raise AssertionError('Do not import candidate')\n")
    request = {
        "python": sys.executable, "task_dir": str(task), "num_generations": 12,
        "native_config": {"llm_models": ["openai/test-model"], "embedding_model": None,
                          "max_api_costs": 0.5, "evaluation_timeout": "00:02:00",
                          "max_evaluation_jobs": 1, "max_proposal_jobs": 2, "max_db_workers": 1,
                          "llm_kwargs": {"temperatures": [0.2], "max_tokens": 1000},
                          "num_islands": 2, "archive_size": 10},
    }
    return source, request, tmp_path / "not-created-output"


def test_prepare_uses_pinned_native_module_and_literal_argv_without_side_effects(adapter, plan_inputs):
    source, request, output = plan_inputs
    original = deepcopy(request)
    plan = adapter.prepare(source, request, output)
    assert adapter.id == "shinka" and adapter.commit == COMMIT
    assert plan["argv"][:9] == [sys.executable, "-m", "shinka.cli.run", "--task-dir", request["task_dir"],
                               "--results_dir", str(output), "--num_generations", "12"]
    assert plan["argv"][9:15] == ["--max-evaluation-jobs", "1", "--max-proposal-jobs", "2", "--max-db-workers", "1"]
    overrides = dict(plan["argv"][index + 1].split("=", 1) for index, value in enumerate(plan["argv"]) if value == "--set")
    assert json.loads(overrides["evo.llm_models"]) == ["openai/test-model"]
    assert overrides["evo.embedding_model"] == "null"
    assert overrides["evo.max_api_costs"] == "0.5"
    assert overrides["job.time"] == "00:02:00"
    assert json.loads(overrides["evo.llm_kwargs"]) == request["native_config"]["llm_kwargs"]
    assert plan["cwd"] == str(source)
    assert plan["env"]["SHINKA_PRICING_MODE"] == "offline"
    assert plan["env"]["PYTHONPATH"].split(os.pathsep) == [str(source), str(Path(__file__).resolve().parents[2] / "src")]
    assert plan["expected_artifacts"][0] == "programs.sqlite"
    assert set(plan["input_paths"]) == {str(Path(request["task_dir"]) / name) for name in ("initial.py", "evaluate.py")}
    assert request == original
    assert not output.exists()


def test_interpreter_symlink_is_preserved_to_keep_venv_identity(adapter, plan_inputs, tmp_path):
    source, request, output = plan_inputs
    interpreter = tmp_path / "venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.symlink_to(sys.executable)
    request["python"] = str(interpreter)
    assert adapter.prepare(source, request, output)["argv"][0] == str(interpreter)


def test_local_gateway_uses_only_an_environment_name_and_explicit_numeric_threads(adapter, plan_inputs):
    source, request, output = plan_inputs
    model = "local/gpt-5.6-sol@http://127.0.0.1:8789/v1?api_key_env=OPENAI_API_KEY"
    request["native_config"].update(llm_models=[model], numeric_threads_per_job=1)
    plan = adapter.prepare(source, request, output)
    overrides = dict(plan["argv"][i + 1].split("=", 1) for i, value in enumerate(plan["argv"]) if value == "--set")
    assert overrides["job.numeric_threads_per_job"] == "1"
    assert json.loads(overrides["evo.llm_models"]) == [model]
    assert not output.exists()


@pytest.mark.parametrize("query", ["api_key_env=", "api_key_env=not-secret-key", "api_key_env=OPENAI_API_KEY&token=SECRET",
                                    "api_key_env=OPENAI_API_KEY&api_key_env=OTHER_KEY", "token=SECRET"])
def test_local_gateway_query_must_be_exactly_one_valid_environment_name(adapter, plan_inputs, query):
    source, request, output = plan_inputs
    request["native_config"]["llm_models"] = ["local/model@http://127.0.0.1:8789/v1?" + query]
    with pytest.raises(ValueError):
        adapter.prepare(source, request, output)


@pytest.mark.parametrize("threads", [True, 0, 65, 1.5, "1"])
def test_native_numeric_thread_limit_is_a_bounded_integer(adapter, plan_inputs, threads):
    source, request, output = plan_inputs
    request["native_config"]["numeric_threads_per_job"] = threads
    with pytest.raises(ValueError, match="numeric_threads_per_job"):
        adapter.prepare(source, request, output)


@pytest.mark.parametrize("kind", ["file", "directory", "symlink", "broken_symlink"])
def test_source_dotenv_is_rejected_without_reading_values(adapter, plan_inputs, tmp_path, monkeypatch, kind):
    source, request, output = plan_inputs
    dotenv = source / ".env"
    target = tmp_path / "dotenv-target"
    if kind == "file":
        dotenv.write_text("SECRET=must-not-be-disclosed\n")
    elif kind == "directory":
        dotenv.mkdir()
    else:
        if kind == "symlink":
            target.write_text("SECRET=must-not-be-disclosed\n")
        dotenv.symlink_to(target)
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        if path in {dotenv, target}:
            raise AssertionError("Preparation must not read dotenv contents")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    with pytest.raises(ValueError, match=r"must not contain \.env") as error:
        adapter.prepare(source, request, output)
    assert "must-not-be-disclosed" not in str(error.value)
    assert not output.exists()


@pytest.mark.parametrize("change", [
    lambda r: r.update(python="python"),
    lambda r: r.update(task_dir="relative"),
    lambda r: r.update(num_generations=True),
    lambda r: r.update(num_generations=0),
    lambda r: r.update(num_generations=100001),
    lambda r: r.pop("native_config"),
    lambda r: r["native_config"].pop("embedding_model"),
    lambda r: r["native_config"].update(llm_models=[]),
    lambda r: r["native_config"].update(max_api_costs=float("inf")),
    lambda r: r["native_config"].update(max_api_costs=10 ** 400),
    lambda r: r["native_config"].update(llm_kwargs={"temperatures": [10 ** 400]}),
    lambda r: r["native_config"].update(llm_kwargs={"reasoning_effort": []}),
    lambda r: r["native_config"].update(max_evaluation_jobs=True),
    lambda r: r["native_config"].update(evaluation_timeout="00:00:00"),
    lambda r: r["native_config"].update(evaluation_timeout="25:00:00"),
    lambda r: r["native_config"].update(llm_kwargs={"api_key": "must-not-be-disclosed"}),
    lambda r: r["native_config"].update(llm_models=["provider/model?api_key=must-not-be-disclosed"]),
    lambda r: r["native_config"].update(embedding_model="local/model@https://user:must-not-be-disclosed@example.com"),
    lambda r: r["native_config"].update(results_dir="/redirect"),
])
def test_invalid_or_credential_bearing_requests_fail_before_any_framework_execution(adapter, plan_inputs, change):
    source, request, output = plan_inputs
    change(request)
    with pytest.raises(ValueError) as error:
        adapter.prepare(source, request, output)
    assert "must-not-be-disclosed" not in str(error.value)
    assert not output.exists()


def test_task_entrypoints_are_required_and_ambiguous_initial_programs_are_rejected(adapter, plan_inputs):
    source, request, output = plan_inputs
    task = Path(request["task_dir"])
    (task / "initial.rs").write_text("fn main() {}")
    with pytest.raises(ValueError, match="exactly one"):
        adapter.prepare(source, request, output)
    (task / "initial.rs").unlink()
    (task / "evaluate.py").unlink()
    with pytest.raises(ValueError, match="evaluate.py"):
        adapter.prepare(source, request, output)


def database(output, rows):
    output.mkdir(exist_ok=True)
    path = output / "programs.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute(PROGRAMS_SCHEMA)
        for data in rows:
            row = {"id": "candidate", "code": "raise AssertionError('never execute')", "language": "python",
                   "parent_id": None, "generation": 0, "timestamp": 1.0, "island_idx": 0,
                   "combined_score": 0.0, "correct": 1, "public_metrics": "{}", "private_metrics": "{}",
                   "archive_inspiration_ids": "[]", "top_k_inspiration_ids": "[]", "metadata": "{}", **data}
            columns = list(row)
            connection.execute("INSERT INTO programs (" + ",".join(columns) + ") VALUES (" + ",".join("?" for _ in columns) + ")", list(row.values()))
    return path


def test_native_reader_preserves_zero_negative_scores_unknown_validity_and_island_identity(adapter, tmp_path):
    path = database(tmp_path, [
        {"id": "seed", "correct": 0, "combined_score": 0.0, "public_metrics": '{"error": 0.0}'},
        {"id": "child", "timestamp": 2.0, "parent_id": "seed", "generation": 1,
         "correct": None, "combined_score": -2.5, "private_metrics": '{"held_out": 4}',
         "archive_inspiration_ids": '["seed"]'},
        {"id": "island-copy", "timestamp": 3.0, "parent_id": "seed", "island_idx": 1,
         "metadata": '{"_is_island_copy": true, "_original_program_id": "seed", "unneeded_trace": "not exported"}'},
    ])
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    result = adapter.read_results(tmp_path)
    assert result["schema"] == "arena.native-result/1"
    assert result["framework"] == "shinka" and result["status"] == "recorded"
    assert result["canonical_evaluation"] is False
    native = result["native"]
    assert native["direction"] == "maximize" and native["evaluation_scope"] == "native"
    assert native["total_program_rows"] == 3 and native["evaluation_count"] is None
    copy, child, seed = native["records"]
    assert copy["id"] == "island-copy" and copy["island_idx"] == 1 and copy["is_island_copy"] is True
    assert copy["copy_metadata"]["_original_program_id"] == "seed"
    assert "unneeded_trace" not in str(result)
    assert child["parent_id"] == "seed" and child["combined_score"] == -2.5
    assert child["correct"] is None and child["validity"] is None
    assert child["private_metrics"] == {"held_out": 4} and child["archive_inspiration_ids"] == ["seed"]
    assert seed["combined_score"] == 0.0 and seed["correct"] == 0 and seed["validity"] is False
    assert seed["public_metrics"] == {"error": 0.0}
    assert result["artifacts"] == [{"path": "programs.sqlite", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}]
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before
    json.dumps(result, allow_nan=False)


def test_reader_handles_missing_corrupt_wrong_schema_and_symlink_without_writes(adapter, tmp_path):
    output = tmp_path / "missing"
    assert adapter.read_results(output)["status"] == "missing"
    assert not output.exists()
    output.mkdir()
    db = output / "programs.sqlite"
    db.write_bytes(b"not sqlite")
    assert adapter.read_results(output)["status"] == "partial"
    assert db.read_bytes() == b"not sqlite"
    db.unlink()
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE programs(id TEXT)")
    assert adapter.read_results(output)["status"] == "partial"
    db.unlink()
    target = tmp_path / "elsewhere"
    target.write_bytes(b"private unrelated content")
    db.symlink_to(target)
    result = adapter.read_results(output)
    assert result["status"] == "partial" and not result["artifacts"]
    assert "private unrelated" not in str(result)


def test_reader_requires_checkpointed_database_instead_of_ignoring_live_wal(adapter, tmp_path):
    db = database(tmp_path, [])
    with sqlite3.connect(db) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("INSERT INTO programs(id,code,language,generation,timestamp) VALUES ('pending','','python',0,1)")
        writer.commit()
        before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
        result = adapter.read_results(tmp_path)
        assert result["status"] == "partial" and result["native"]["records"] == []
        assert any("WAL" in warning for warning in result["warnings"])
        assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_reader_bounds_rows_and_reports_omitted_or_malformed_fields(adapter, tmp_path):
    database(tmp_path, [{"id": f"row-{i}", "timestamp": float(i)} for i in range(MAX_RECORDS + 2)])
    with sqlite3.connect(tmp_path / "programs.sqlite") as connection:
        connection.execute("UPDATE programs SET public_metrics=?, private_metrics=?, correct=7 WHERE id=?",
                           ('{"too_big":"' + "x" * MAX_FIELD_CHARS + '"}', '{"invalid": NaN}', f"row-{MAX_RECORDS + 1}"))
    result = adapter.read_results(tmp_path)
    assert result["status"] == "partial" and result["native"]["truncated"] is True
    assert result["native"]["total_program_rows"] == MAX_RECORDS + 2
    assert len(result["native"]["records"]) == MAX_RECORDS
    latest = result["native"]["records"][0]
    assert latest["id"] == f"row-{MAX_RECORDS + 1}"
    assert latest["correct"] == 7 and latest["validity"] is None
    assert latest["public_metrics"] is None and latest["private_metrics"] is None
    assert len(latest["issues"]) == 3
    json.dumps(result, allow_nan=False)
