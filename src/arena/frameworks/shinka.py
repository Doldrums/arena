"""Plan pinned Shinka runs and inspect inert native SQLite artifacts.

This module never imports Shinka, loads candidate code, or starts a process.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import time
from urllib.parse import parse_qsl, urlsplit


COMMIT = "9912af12d423504b8d580f4179fd15f5f88b8c50"
MAX_RECORDS = 500
MAX_FIELD_CHARS = 16_384
# Native metadata includes model replies/diffs that are not exported. Bound
# parsing separately so ordinary traces do not erase small copy-origin fields.
MAX_METADATA_CHARS = 128 * 1024
MAX_DATABASE_BYTES = 256 * 1024 * 1024
INITIAL_EXTENSIONS = {".py", ".jl", ".go", ".sv", ".rs", ".swift", ".cpp", ".cc", ".cxx", ".cu", ".json", ".f90", ".f95", ".f03", ".f08"}
_SCALARS = ("id", "parent_id", "language", "generation", "timestamp", "island_idx", "combined_score", "correct")
_JSON_FIELDS = ("public_metrics", "private_metrics", "archive_inspiration_ids", "top_k_inspiration_ids", "metadata")
_COPY_KEYS = ("_is_island_copy", "_spawned_island", "_original_program_id")


def _integer(value, name, maximum):
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(f"{name} must be an integer between 1 and {maximum}")
    return value


def _number(value, name, minimum, maximum, *, positive=False):
    if type(value) not in (int, float) or not minimum <= value <= maximum or not math.isfinite(value) or (positive and value == 0):
        raise ValueError(f"Invalid finite value for {name}")
    return value


def _absolute(value, name, *, directory=False, executable=False):
    if not isinstance(value, (str, Path)) or "\x00" in str(value):
        raise ValueError(f"{name} must be an absolute path")
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f"{name} must be an absolute path")
    if directory and not path.is_dir():
        raise ValueError(f"{name} must be an existing directory")
    if executable and (not path.is_file() or not os.access(path, os.X_OK)):
        raise ValueError(f"{name} must be an existing executable")
    # Keep a venv interpreter's symlink path: resolving it would lose the venv.
    return path if executable else path.resolve()


def _model(value, name):
    if not isinstance(value, str) or not value or len(value) > 512 or any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError(f"{name} must be a nonempty model identifier")
    if re.search(r"(?i)(api[_-]?key|token|password|secret|authorization)=", value):
        raise ValueError(f"{name} must not contain credential values")
    for match in re.finditer(r"https?://[^\s]+", value):
        parsed = urlsplit(match.group())
        query = parse_qsl(parsed.query, keep_blank_values=True)
        safe_key_reference = (value.startswith("local/") and len(query) == 1
                              and query[0][0] == "api_key_env"
                              and re.fullmatch(r"[A-Z][A-Z0-9_]*", query[0][1]) is not None)
        if (parsed.username is not None or parsed.password is not None or parsed.fragment
                or parsed.query and not safe_key_reference):
            raise ValueError(f"{name} URLs must not contain credentials, queries or fragments")
    return value


def _native_options(config):
    required = {"llm_models", "embedding_model", "max_api_costs", "evaluation_timeout", "max_evaluation_jobs", "max_proposal_jobs", "max_db_workers"}
    allowed = required | {"llm_kwargs", "num_islands", "archive_size", "numeric_threads_per_job"}
    if type(config) is not dict or not required <= config.keys() or config.keys() - allowed:
        raise ValueError("native_config requires explicit models, embedding, API budget, evaluation timeout and concurrency; unknown options are not supported")
    models = config["llm_models"]
    if type(models) is not list or not 1 <= len(models) <= 16:
        raise ValueError("llm_models must contain 1 to 16 model identifiers")
    models = [_model(value, "llm_models") for value in models]
    embedding = config["embedding_model"]
    if embedding is not None:
        embedding = _model(embedding, "embedding_model")
    budget = _number(config["max_api_costs"], "max_api_costs", 0, 1_000_000, positive=True)
    timeout = config["evaluation_timeout"]
    if not isinstance(timeout, str) or not re.fullmatch(r"\d{2}:[0-5]\d:[0-5]\d", timeout):
        raise ValueError("evaluation_timeout must be HH:MM:SS")
    hours, minutes, seconds = map(int, timeout.split(":"))
    if not 1 <= hours * 3600 + minutes * 60 + seconds <= 86400:
        raise ValueError("evaluation_timeout must be between one second and 24 hours")
    concurrency = {key: _integer(config[key], key, 64) for key in ("max_evaluation_jobs", "max_proposal_jobs", "max_db_workers")}
    options = {"evo.llm_models": models, "evo.embedding_model": embedding, "evo.max_api_costs": budget, "job.time": timeout}
    if "numeric_threads_per_job" in config:
        options["job.numeric_threads_per_job"] = _integer(config["numeric_threads_per_job"], "numeric_threads_per_job", 64)
    if "llm_kwargs" in config:
        kwargs = config["llm_kwargs"]
        if type(kwargs) is not dict or kwargs.keys() - {"temperatures", "max_tokens", "top_p", "reasoning_effort"}:
            raise ValueError("llm_kwargs supports only temperatures, max_tokens, top_p and reasoning_effort; credentials belong in the environment")
        if "temperatures" in kwargs:
            temperatures = kwargs["temperatures"]
            if type(temperatures) is not list or not 1 <= len(temperatures) <= 16:
                raise ValueError("temperatures must contain 1 to 16 numbers")
            for value in temperatures:
                _number(value, "temperature", 0, 2)
        if "max_tokens" in kwargs:
            _integer(kwargs["max_tokens"], "max_tokens", 1_000_000)
        if "top_p" in kwargs:
            _number(kwargs["top_p"], "top_p", 0, 1, positive=True)
        if "reasoning_effort" in kwargs and (not isinstance(kwargs["reasoning_effort"], str)
                                             or kwargs["reasoning_effort"] not in {"none", "minimal", "low", "medium", "high", "xhigh"}):
            raise ValueError("Unsupported reasoning_effort")
        options["evo.llm_kwargs"] = kwargs
    for key, maximum in (("num_islands", 64), ("archive_size", 100_000)):
        if key in config:
            options["db." + key] = _integer(config[key], key, maximum)
    return options, concurrency


def _artifact(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Artifact must be a regular file, not a symlink")
    before = path.stat()
    if before.st_size > MAX_DATABASE_BYTES:
        raise ValueError("Artifact exceeds the 256 MiB inspection limit")
    digest = hashlib.sha256()
    read_bytes = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            read_bytes += len(block)
            if read_bytes > MAX_DATABASE_BYTES:
                raise ValueError("Artifact grew beyond the inspection limit")
            digest.update(block)
    if _version(path.stat()) != _version(before):
        raise ValueError("Artifact changed while hashing")
    return {"path": path.name, "sha256": digest.hexdigest()}, before


def _version(stat):
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def _json_field(value, field, issues):
    if value is None:
        return None
    maximum = MAX_METADATA_CHARS if field == "metadata" else MAX_FIELD_CHARS
    if not isinstance(value, str) or len(value) > maximum:
        issues.append(f"{field} omitted: oversized or non-text native JSON")
        return None
    try:
        def reject_constant(_):
            raise ValueError("Non-finite JSON")
        def finite_float(value):
            number = float(value)
            if not math.isfinite(number):
                raise ValueError("Non-finite JSON")
            return number
        decoded = json.loads(value, parse_constant=reject_constant, parse_float=finite_float)
        expected = list if field.endswith("_ids") else dict
        if type(decoded) is not expected:
            raise ValueError("Unexpected JSON shape")
        return decoded
    except (ValueError, RecursionError):
        issues.append(f"{field} omitted: invalid native JSON")
        return None


class ShinkaAdapter:
    id = "shinka"
    commit = COMMIT

    def prepare(self, source_dir: Path, request: dict, output_dir: Path) -> dict:
        if type(request) is not dict or set(request) != {"python", "task_dir", "num_generations", "native_config"}:
            raise ValueError("Shinka request requires python, task_dir, num_generations and native_config")
        source = _absolute(source_dir, "source_dir", directory=True)
        # Pinned shinka.env loads package-root/cwd .env with override=True.
        # Both resolve to this checkout; never read or inherit its contents.
        dotenv = source / ".env"
        if dotenv.exists() or dotenv.is_symlink():
            raise ValueError("Shinka source_dir must not contain .env; pass explicit environment_names instead")
        if not (source / "shinka/cli/run.py").is_file():
            raise ValueError("Pinned Shinka CLI module is missing")
        python = _absolute(request["python"], "python", executable=True)
        task = _absolute(request["task_dir"], "task_dir", directory=True)
        output = _absolute(output_dir, "output_dir")
        evaluate = task / "evaluate.py"
        initial = list(task.glob("initial.*"))
        if not evaluate.is_file() or len(initial) != 1 or not initial[0].is_file() or initial[0].suffix not in INITIAL_EXTENSIONS:
            raise ValueError("task_dir needs evaluate.py and exactly one supported initial.<ext> file")
        generations = _integer(request["num_generations"], "num_generations", 100_000)
        options, concurrency = _native_options(request["native_config"])
        argv = [str(python), "-m", "shinka.cli.run", "--task-dir", str(task), "--results_dir", str(output), "--num_generations", str(generations)]
        for key, value in concurrency.items():
            argv.extend(["--" + key.replace("_", "-"), str(value)])
        for key, value in options.items():
            encoded = value if isinstance(value, str) else json.dumps(value, separators=(",", ":"), allow_nan=False)
            argv.extend(["--set", key + "=" + encoded])
        inputs = [str(evaluate), str(initial[0])]
        if (task / "evaluation.json").is_file():
            inputs.append(str(task / "evaluation.json"))
        return {"argv": argv, "cwd": str(source),
                "env": {"PYTHONPATH": os.pathsep.join((str(source), str(Path(__file__).resolve().parents[2]))), "SHINKA_PRICING_MODE": "offline"},
                "expected_artifacts": ["programs.sqlite", "evolution_run.log", "pricing_snapshot.json"],
                "input_paths": inputs}

    def read_results(self, output_dir: Path) -> dict:
        output = Path(output_dir)
        database = output / "programs.sqlite"
        result = {"schema": "arena.native-result/1", "framework": self.id,
                  "canonical_evaluation": False, "status": "missing", "artifacts": [], "warnings": [],
                  "native": {"framework_commit": self.commit, "metric": "combined_score", "direction": "maximize",
                             "evaluation_scope": "native", "total_program_rows": None,
                             "records": [], "record_limit": MAX_RECORDS, "truncated": False,
                             "order": "timestamp_desc_id_desc", "evaluation_count": None}}
        warnings, native = result["warnings"], result["native"]
        if not database.exists() and not database.is_symlink():
            warnings.append("No native programs.sqlite artifact is recorded")
            return result
        result["status"] = "partial"
        connection = None
        try:
            artifact, before = _artifact(database)
            result["artifacts"].append(artifact)
            wal = output / "programs.sqlite-wal"
            if wal.exists() or wal.is_symlink():
                wal_artifact, wal_stat = _artifact(wal)
                if wal_stat.st_size:
                    result["artifacts"].append(wal_artifact)
                    warnings.append("Uncheckpointed WAL detected; inspect after the native writer closes. No potentially stale main-database records were returned")
                    return result
            # immutable prevents SQLite creating or changing WAL/shared-memory files.
            connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro&immutable=1", uri=True, timeout=0.1)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only=ON")
            connection.execute("PRAGMA trusted_schema=OFF")
            connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 2 * 1024 * 1024)
            deadline = time.monotonic() + 2.0
            connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
            table = connection.execute("SELECT type, sql FROM sqlite_schema WHERE name='programs'").fetchone()
            if table is None or table["type"] != "table" or not re.match(r"(?is)^\s*CREATE\s+TABLE\b", table["sql"] or ""):
                raise ValueError("Missing ordinary native programs table")
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(programs)")}
            if not set(_SCALARS + _JSON_FIELDS) <= columns:
                raise ValueError("Native programs table lacks required pinned-schema columns")
            native["total_program_rows"] = connection.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
            selected = list(_SCALARS) + [
                f"substr({field},1,{(MAX_METADATA_CHARS if field == 'metadata' else MAX_FIELD_CHARS) + 1}) AS {field}"
                for field in _JSON_FIELDS]
            rows = connection.execute("SELECT " + ",".join(selected) + " FROM programs ORDER BY timestamp DESC, id DESC LIMIT ?", (MAX_RECORDS + 1,)).fetchall()
            native["truncated"] = len(rows) > MAX_RECORDS
            for row in rows[:MAX_RECORDS]:
                issues = []
                record = {field: row[field] for field in _SCALARS}
                for field, value in record.items():
                    if isinstance(value, float) and not math.isfinite(value):
                        record[field] = None
                        issues.append(f"{field} omitted: non-finite native number")
                    elif isinstance(value, (bytes, str)) and (not isinstance(value, str) or len(value) > MAX_FIELD_CHARS):
                        record[field] = None
                        issues.append(f"{field} omitted: oversized or non-text native value")
                for field in _JSON_FIELDS:
                    record[field] = _json_field(row[field], field, issues)
                metadata = record.pop("metadata")
                record["copy_metadata"] = {key: metadata[key] for key in _COPY_KEYS if key in metadata} if metadata is not None else None
                record["is_island_copy"] = bool(metadata.get("_is_island_copy") or metadata.get("_spawned_island")) if metadata is not None else None
                record["validity"] = bool(row["correct"]) if type(row["correct"]) is int and row["correct"] in (0, 1) else None
                if record["validity"] is None and row["correct"] is not None:
                    issues.append("correct is not a native boolean; validity remains unknown")
                record["issues"] = issues
                native["records"].append(record)
            if _version(database.stat()) != _version(before) or (wal.exists() and wal.stat().st_size):
                native["records"] = []
                native["total_program_rows"] = None
                raise ValueError("Native database changed during inspection; records withheld")
            if native["truncated"]:
                warnings.append(f"Only the latest {MAX_RECORDS} native program rows are included")
            if any(record["issues"] for record in native["records"]):
                warnings.append("Some native fields could not be represented; inspect per-record issues and the source artifact")
            warnings.append("Program rows include administrative island copies; they are not a count of evaluations. Native correctness and scores have not been canonically re-evaluated")
            result["status"] = "partial" if native["truncated"] or any(record["issues"] for record in native["records"]) else "recorded"
        except (OSError, ValueError, sqlite3.Error) as exc:
            warnings.append(f"Native artifact inspection unavailable: {type(exc).__name__}: {exc}")
        finally:
            if connection is not None:
                connection.close()
        return result


adapter = ShinkaAdapter()
