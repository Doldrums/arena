"""Pinned ordinary SCiEL CLI adapter and inert native-result reader.

Only the shared launcher executes the returned argv. This module never imports
SCiEL, loads a checkpoint into an engine, or executes a saved candidate.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re


COMMIT = "0d67f813dd4ac21dee304f2b0de0b0ce59bf4157"
_MAX_CHECKPOINT = 64 * 1024 * 1024
_MAX_JOURNAL = 1024 * 1024 * 1024
_MAX_LINE = 16 * 1024 * 1024


def _path(value, label, *, directory=False, must_exist=True):
    if not isinstance(value, (str, Path)) or not str(value) or "\x00" in str(value):
        raise ValueError(f"{label}: absolute path required")
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f"{label}: absolute path required")
    if must_exist and not (path.is_dir() if directory else path.is_file()):
        raise ValueError(f"{label}: existing {'directory' if directory else 'file'} required")
    return path.resolve()


def _artifact(root, name):
    """Fixed relative names only; never follow an artifact symlink."""
    path = root / name
    for part in (path, *path.parents):
        if part == root:
            break
        if part.is_symlink():
            raise ValueError("Native artifact symlinks are not permitted")
    if path.exists() and (not path.is_file() or not path.resolve().is_relative_to(root)):
        raise ValueError("Native artifact escapes output directory or is not a file")
    return path


def _dict(value):
    return value if type(value) is dict else {}


def _number(value):
    return value if type(value) in (int, float) and math.isfinite(value) else None


def _text(value):
    return value if type(value) is str and value else None


def _signature(value):
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


class SCiELAdapter:
    id = "sciel"
    commit = COMMIT

    def prepare(self, source_dir: Path, request: dict, output_dir: Path) -> dict:
        allowed = {"python", "config", "tasks_root", "seed", "budget", "campaign", "arm", "action"}
        if type(request) is not dict or set(request) - allowed:
            raise ValueError("Unknown SCiEL request option")
        if request.get("action", "run") != "run":
            raise ValueError("Only native run is supported; resume is not integrated")
        source = _path(source_dir, "source_dir", directory=True)
        if not (source / "src/sciel/cli/main.py").is_file():
            raise ValueError("SCiEL source CLI is missing")
        if (source.parent / ".env").exists() or (source.parent / ".env").is_symlink():
            raise ValueError("SCiEL would auto-load a parent .env file; use an isolated checkout parent and explicit credential environment")
        _path(request.get("python"), "python")
        # A venv executable is commonly a symlink; resolving it would silently
        # switch to the base interpreter and lose the selected environment.
        python = Path(request["python"])
        if not os.access(python, os.X_OK):
            raise ValueError("python: executable file required")
        config = _path(request.get("config"), "config")
        tasks = _path(request.get("tasks_root", source / "tasks"), "tasks_root", directory=True)
        output = _path(output_dir, "output_dir", directory=True, must_exist=False)
        if output.exists() and not output.is_dir():
            raise ValueError("output_dir must be a directory")
        native = output / "native"
        if native.is_symlink() or (native.exists() and (not native.is_dir() or any(native.iterdir()))):
            raise ValueError("Native run directory is not empty; choose a new output directory")
        argv = [str(python), "-P", "-m", "sciel.cli.main", "run", str(config),
                "--outputs", str(output), "--run-id", "native", "--tasks-root", str(tasks)]
        for key, minimum in (("seed", 0), ("budget", 1)):
            if key in request:
                value = request[key]
                if type(value) is not int or value < minimum:
                    raise ValueError(f"{key}: integer ≥ {minimum} required")
                argv += [f"--{key}", str(value)]
        for key in ("campaign", "arm"):
            if key in request:
                value = request[key]
                if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", value):
                    raise ValueError(f"{key}: a short identifier is required")
                argv += [f"--{key}", value]
        arena_import_root = Path(__file__).resolve().parents[2]
        return {"argv": argv, "cwd": str(source),
                "env": {"PYTHONPATH": os.pathsep.join((str(source / "src"), str(arena_import_root)))},
                "expected_artifacts": ["native/sciel_events.jsonl", "native/checkpoint.json", "native/config.yaml"],
                "input_paths": [str(config), str(tasks)]}

    def read_results(self, output_dir: Path) -> dict:
        root = _path(output_dir, "output_dir", directory=True)
        checkpoint = _artifact(root, "native/checkpoint.json")
        journal = _artifact(root, "native/sciel_events.jsonl")
        response = {"schema": "arena.native-result/1", "framework": self.id,
                    "canonical_evaluation": False, "status": "missing", "native": {},
                    "best_candidate": None, "artifacts": [], "warnings": []}
        if not checkpoint.is_file() or not journal.is_file():
            response["status"] = "partial" if checkpoint.exists() or journal.exists() else "missing"
            response["warnings"].append("Native checkpoint and journal are required; a missing result is not a zero score.")
            return response
        if checkpoint.stat().st_size > _MAX_CHECKPOINT or journal.stat().st_size > _MAX_JOURNAL:
            raise ValueError("Native artifacts exceed this reader's size limit")
        checkpoint_before, journal_before = checkpoint.stat(), journal.stat()
        raw = checkpoint.read_bytes()
        state = json.loads(raw)
        if type(state) is not dict:
            raise ValueError("Native checkpoint must be a JSON object")
        checkpoint_digest = hashlib.sha256(raw).hexdigest()
        provenance = _dict(state.get("provenance"))
        identity = _dict(state.get("identity"))
        anchor = _dict(provenance.get("journal_anchor"))
        run_id = _text(provenance.get("run_id"))
        segment_id = _text(anchor.get("segment_id"))
        offset = anchor.get("byte_offset")
        anchor_matches = False
        final = None
        last = None
        digest = hashlib.sha256()
        consumed = 0
        incomplete_tail = False
        with journal.open("rb") as stream:
            while line := stream.readline(_MAX_LINE + 1):
                if len(line) > _MAX_LINE:
                    raise ValueError("Native journal line exceeds this reader's size limit")
                digest.update(line)
                consumed += len(line)
                if consumed > _MAX_JOURNAL:
                    raise ValueError("Native journal exceeds this reader's size limit")
                if not line.endswith(b"\n"):
                    incomplete_tail = True
                    break
                row = json.loads(line)
                if type(row) is not dict:
                    raise ValueError("Native journal rows must be JSON objects")
                last = row
                if type(offset) is int and consumed == offset:
                    anchor_matches = (digest.hexdigest() == anchor.get("prefix_sha256")
                                      and row.get("run_id") == run_id and row.get("segment_id") == segment_id
                                      and row.get("event_seq") == anchor.get("event_seq"))
                if row.get("event") == "run_end" and row.get("run_id") == run_id and row.get("segment_id") == segment_id:
                    final = row
        response["artifacts"] = [
            {"path": "native/checkpoint.json", "sha256": checkpoint_digest},
            {"path": "native/sciel_events.jsonl", "sha256": digest.hexdigest()},
        ]
        if (_signature(checkpoint.stat()) != _signature(checkpoint_before)
                or _signature(journal.stat()) != _signature(journal_before)):
            response["warnings"].append("Native artifacts changed while being read; this is a partial observational snapshot.")
        if provenance.get("schema") != "sciel-checkpoint-provenance/1" or not run_id or not anchor_matches:
            response["warnings"].append("Checkpoint identity or journal-prefix binding is missing or mismatched.")
        terminal_matches = bool(final and final is last and not incomplete_tail
                                and final.get("checkpoint_sha256") == checkpoint_digest
                                and final.get("checkpoint_id") == provenance.get("checkpoint_id"))
        if not terminal_matches:
            response["warnings"].append("No matching final run_end receipt; this snapshot does not prove native completion.")
        response["status"] = "recorded" if not response["warnings"] else "partial"
        response["native"] = {
            "run_id": run_id, "segment_id": segment_id, "checkpoint_id": _text(provenance.get("checkpoint_id")),
            "task": _text(identity.get("task")), "task_hash": _text(identity.get("task_hash")),
            "engine_contract": _text(identity.get("engine_contract")),
            "reason": _text(final.get("reason")) if terminal_matches else None,
            "B_evals": _number(state.get("B_evals")), "iteration_no": _number(state.get("iteration_no")),
            "cost_total": _number(state.get("cost_total")), "pop_best": None,
        }
        db = _dict(state.get("db"))
        programs = db.get("programs", [])
        if type(programs) is not list:
            raise ValueError("Native checkpoint programs must be a list")
        matches = [(index, row) for index, row in enumerate(programs)
                   if type(row) is dict and row.get("id") == db.get("pop_best_id") and row.get("id") is not None]
        if len(matches) > 1:
            raise ValueError("Native best candidate identity is duplicated")
        if matches:
            index, best = matches[0]
            score = _number(best.get("score"))
            response["native"]["pop_best"] = score
            code = best.get("code")
            response["best_candidate"] = {
                "id": best["id"], "score": score, "score_space": "native_engine_fitness",
                "direction": "maximize", "validity": None,
                "source_sha256": hashlib.sha256(code.encode()).hexdigest() if type(code) is str else None,
                "source": {"path": "native/checkpoint.json", "locator": f"#/db/programs/{index}/code"},
            }
            if terminal_matches and _number(final.get("pop_best")) != score:
                response["status"] = "partial"
                response["warnings"].append("Final native fitness differs from checkpoint best fitness.")
        return response
