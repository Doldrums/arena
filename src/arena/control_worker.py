"""Explicit worker execution; serving the board never launches native code."""
from __future__ import annotations

import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import uuid

from .control_io import _write_private
from .control_logs import _diagnostic, _publish_native_logs, _secret_values
from .control_process import RunCgroup, _completed_result, _pid_identity
from .control_service import ControlService
from .control_types import ControlError, LEASE_SECONDS


def _replace_paths(value, output, cgroup):
    if isinstance(value, dict):
        return {key: _replace_paths(child, output, cgroup) for key, child in value.items()}
    if isinstance(value, list):
        return [_replace_paths(child, output, cgroup) for child in value]
    if isinstance(value, str):
        return value.replace("{output_dir}", str(output)).replace("{control_cgroup}", str(cgroup))
    return value


def _execute(config_path, run_id, expected_hash):
    # The parent records PID identity and cgroup before granting execution. If
    # it dies before the grant, EOF exits without importing the native runtime.
    if sys.stdin.buffer.read(1) != b"G":
        return 125
    service = ControlService(config_path)
    with service._db() as db:
        row = service._get(db, run_id)
    if row["snapshot_sha256"] != expected_hash or row["cancel_requested"] or row["state"] != "preparing":
        return 125
    snapshot = service.snapshot(row)
    directory = service.runs_dir / run_id
    try:
        group = RunCgroup.existing(Path(snapshot["cgroup_root"]), run_id)
        if group is None:
            raise ControlError("Admitted run cgroup is missing")
        (group.main / "cgroup.procs").write_text(str(os.getpid()))
    except (OSError, ControlError) as error:
        _diagnostic(directory, "cgroup_entry", error, _secret_values())
        _write_private(directory / "result.json", {"state": "failed", "returncode": 1})
        return 1
    spec = _replace_paths(snapshot["template"]["spec"], directory / "artifacts", group.path)
    # Reserved control metadata is overwritten after admission, never accepted
    # from an API body or inherited stale worker environment. Canonical Docker
    # evaluation can require this verified parent to contain its owned container.
    os.environ["ARENA_EVALUATION_CGROUP_PARENT"] = str(group.path)
    os.environ["ARENA_CONTROL_RUN_ID"] = run_id
    os.environ["ARENA_EVALUATION_RECEIPTS_DIR"] = str(directory / "artifacts" / "canonical-evaluations")
    spec["environment_names"] = list(dict.fromkeys([*spec.get("environment_names", []),
                                                   "ARENA_EVALUATION_CGROUP_PARENT", "ARENA_CONTROL_RUN_ID",
                                                   "ARENA_EVALUATION_RECEIPTS_DIR"]))
    with service._db(write=True) as db:
        current = service._get(db, run_id)
        if current["cancel_requested"] or current["state"] != "preparing" or not current["held"] or current["lease_until"] < time.time():
            return 125
        db.execute("UPDATE runs SET state='running',started=?,updated=?,lease_until=? WHERE id=?", (time.time(), time.time(), time.time() + LEASE_SECONDS, run_id))
    service._event(run_id, "Native runtime started in its reserved cgroup.")
    try:
        from .frameworks.runtime import run
        receipt = run(spec)
        completed = receipt.get("status") == "process_completed" and receipt.get("returncode") == 0
        result = {"state": "completed" if completed else "failed", "returncode": 0 if completed else 1}
    except BaseException as error:
        # Exceptions may embed prompts, generated code, paths and secrets.
        _diagnostic(directory, "native_runtime", error, _secret_values())
        result = {"state": "failed", "returncode": 1}
    _write_private(directory / "result.json", result)
    return result["returncode"]


class Worker:
    def __init__(self, service, *, claim_gate=None):
        self.service = service
        self.id = "worker-" + uuid.uuid4().hex
        self.stopping = threading.Event()
        self.claim_gate = None
        if claim_gate is not None:
            from .control_claim_gate import ClaimGate
            self.claim_gate = ClaimGate(claim_gate)

    def once(self):
        self.service.reconcile()
        if self.claim_gate is None:
            row = self.service.claim(self.id)
        else:
            with self.claim_gate.claim_window() as allowed:
                if not allowed:
                    return False
                row = self.service.claim(self.id)
        if row is None:
            return False
        self.execute(row)
        return True

    def execute(self, row):
        service, run_id = self.service, row["id"]
        process, group, released = None, None, True
        values = _secret_values()
        log_cache = {}
        state, reason, code = "blocked", "Worker preparation failed; inspect private configuration.", None
        try:
            snapshot = service.snapshot(row)
            if service.heartbeat(run_id, self.id):
                state, reason = "cancelled", None
                return
            group = RunCgroup(Path(snapshot["cgroup_root"]), run_id, snapshot["template"]["resources"])
            directory = service.runs_dir / run_id
            # No key values are serialized. Inherited environment is further
            # filtered to explicit names by the native runtime itself.
            process = subprocess.Popen([sys.executable, "-m", "arena.control", "_execute", "--config", str(service.config_path),
                                        "--run-id", run_id, "--snapshot-sha256", row["snapshot_sha256"]],
                                       stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       start_new_session=True)
            with service._db(write=True) as db:
                changed = db.execute("UPDATE runs SET pid=?,pid_identity=?,cgroup=?,updated=?,lease_until=? WHERE id=? AND lease_owner=? AND state='preparing' AND held=1 AND lease_until>?", (process.pid, _pid_identity(process.pid), str(group.path), time.time(), time.time() + LEASE_SECONDS, run_id, self.id, time.time())).rowcount
                if changed != 1:
                    raise ControlError("Worker lease expired before execution", 409)
            process.stdin.write(b"G")
            process.stdin.close()
            service._event(run_id, "Worker granted execution.")
            started = time.monotonic()
            published = 0
            heartbeat_at = 0
            while process.poll() is None:
                if time.monotonic() - published >= 1:
                    _publish_native_logs(directory, values, cache=log_cache)
                    published = time.monotonic()
                cancelled = False
                if time.monotonic() - heartbeat_at >= 1:
                    cancelled = service.heartbeat(run_id, self.id)
                    heartbeat_at = time.monotonic()
                if cancelled or self.stopping.is_set():
                    state, reason = "cancelled", "Cancellation or worker shutdown requested."
                    group.kill()
                    break
                # Includes planning and workspace preparation, unlike native
                # runtime's subprocess-only timeout.
                if time.monotonic() - started > row["timeout_seconds"]:
                    state, reason = "failed", "Whole-run wall time limit exceeded."
                    group.kill()
                    break
                self.stopping.wait(0.25)
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            code = process.wait(timeout=5)
            if reason == "Worker preparation failed; inspect private configuration.":
                state, reason, result_code = _completed_result(directory)
                code = result_code if result_code is not None else code
            with service._db() as db:
                if service._get(db, run_id)["cancel_requested"]:
                    state, reason = "cancelled", "Cancellation requested before worker completion."
        except (OSError, ControlError, subprocess.SubprocessError) as error:
            _diagnostic(service.runs_dir / run_id, "worker_preparation", error, values)
            service._event(run_id, "Worker could not execute the admitted template.", error=True)
        finally:
            if group is not None:
                try:
                    group.close()
                except (OSError, ControlError):
                    released = False
                    state, reason = "blocked", "Process containment cleanup is unconfirmed; resources retained."
            if process is not None and process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
                except (OSError, subprocess.SubprocessError):
                    released = False
                    state, reason = "blocked", "Worker process exit is unconfirmed; resources retained."
            _publish_native_logs(service.runs_dir / run_id, values, cache=log_cache)
            service.finish(run_id, self.id, state, reason=reason, returncode=code, release=released)

    def loop(self):
        while not self.stopping.is_set():
            try:
                worked = self.once()
            except (OSError, ControlError, sqlite3.Error):
                worked = False
            if not worked:
                self.stopping.wait(1)
