"""Authenticated durable queue, ownership and conservative resource admission."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import sqlite3
import stat
import threading
import time
import uuid

from .control_config import validate_config
from .control_io import _private_dir, _read_regular, _write_private
from .control_process import (RunCgroup, _completed_result, _kill_recorded_process,
                              _pid_alive)
from .control_types import (ControlError, LEASE_SECONDS, MAX_LOG, MAX_NATIVE_LOG,
                            SCOPES, TERMINAL, _decode, _id, _int, _json, _plain)


class ControlService:
    """One private queue shared by HTTP services and independent worker processes."""

    def __init__(self, config_path):
        self.config_path = Path(config_path)
        self.lock = threading.RLock()
        self.config = None
        self.reload()
        self.state_dir = _private_dir(self.config["state_dir"], create=True)
        self.runs_dir = _private_dir(self.state_dir / "runs", create=True)
        self.db_path = self.state_dir / "queue.sqlite"
        if self.db_path.exists() or self.db_path.is_symlink():
            info = self.db_path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
                raise ControlError("Queue database must be an owned private regular file")
        else:
            fd = os.open(self.db_path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            os.close(fd)
        with self._db() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS keys (
                    id TEXT PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE, owner TEXT NOT NULL,
                    scopes TEXT NOT NULL, created REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0,
                    max_runs INTEGER NOT NULL, max_seconds INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, key_id TEXT NOT NULL,
                    template TEXT NOT NULL, framework TEXT NOT NULL, profile TEXT NOT NULL, model TEXT NOT NULL,
                    label TEXT, batch_id TEXT, idempotency_key TEXT,
                    revision TEXT NOT NULL, snapshot_sha256 TEXT NOT NULL,
                    state TEXT NOT NULL, reason TEXT, created REAL NOT NULL, updated REAL NOT NULL,
                    cpus INTEGER NOT NULL, memory_mb INTEGER NOT NULL, evaluation_slots INTEGER NOT NULL,
                    pids INTEGER NOT NULL, timeout_seconds INTEGER NOT NULL,
                    held INTEGER NOT NULL DEFAULT 0, lease_owner TEXT, lease_until REAL,
                    cancel_requested INTEGER NOT NULL DEFAULT 0, pid INTEGER, pid_identity TEXT,
                    cgroup TEXT, started REAL, ended REAL, returncode INTEGER,
                    UNIQUE(key_id, idempotency_key)
                );
                CREATE INDEX IF NOT EXISTS runs_state ON runs(state, created);
            """)

    def reload(self):
        data = _read_regular(self.config_path, private=True)
        config = validate_config(_decode(data))
        revision = hashlib.sha256(_json(config).encode()).hexdigest()
        with self.lock:
            if self.config is not None and (config["state_dir"] != self.config["state_dir"] or config["cgroup_root"] != self.config["cgroup_root"]):
                raise ControlError("State directory and cgroup root cannot change during reload")
            self.config, self.revision = config, revision
        return revision

    @contextmanager
    def _db(self, *, write=False):
        # Parent directory is private. Never follow a replaced SQLite sidecar.
        for path in (self.db_path, Path(str(self.db_path) + "-wal"), Path(str(self.db_path) + "-shm")):
            if path.is_symlink():
                raise ControlError("Queue database symlinks are not allowed", 503)
        db = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA busy_timeout=10000")
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            if write:
                db.commit()
        except BaseException:
            if write:
                db.rollback()
            raise
        finally:
            db.close()

    def create_key(self, owner, scopes, *, max_runs=None, max_seconds=None):
        _id(owner, "owner")
        if not scopes or not set(scopes) <= SCOPES:
            raise ControlError("Key scopes must be read, submit, cancel, logs:native or admin")
        limits = self.config["limits"]
        max_runs = _int(max_runs if max_runs is not None else limits["max_runs_per_key"], "max_runs")
        max_seconds = _int(max_seconds if max_seconds is not None else limits["max_reserved_seconds_per_key"], "max_seconds")
        token, key_id = "arena_" + secrets.token_urlsafe(32), uuid.uuid4().hex
        with self._db(write=True) as db:
            db.execute("INSERT INTO keys VALUES (?,?,?,?,?,0,?,?)", (key_id, hashlib.sha256(token.encode()).hexdigest(), owner, _json(sorted(set(scopes))), time.time(), max_runs, max_seconds))
        return {"id": key_id, "owner": owner, "scopes": sorted(set(scopes)), "token": token}

    def revoke_key(self, key_id):
        with self._db(write=True) as db:
            if db.execute("UPDATE keys SET revoked=1 WHERE id=?", (key_id,)).rowcount != 1:
                raise ControlError("Key not found", 404)

    def authenticate(self, authorization):
        if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
            raise ControlError("A bearer key is required", 401)
        token = authorization[7:]
        if len(token) > 256 or not token:
            raise ControlError("Invalid bearer key", 401)
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self._db() as db:
            row = db.execute("SELECT * FROM keys WHERE token_hash=? AND revoked=0", (digest,)).fetchone()
        if row is None or not hmac.compare_digest(row["token_hash"], digest):
            raise ControlError("Invalid bearer key", 401)
        principal = dict(row)
        principal["scopes"] = set(_decode(principal["scopes"]))
        return principal

    @staticmethod
    def _scope(principal, scope):
        if "admin" not in principal["scopes"] and scope not in principal["scopes"]:
            raise ControlError("Key scope does not allow this operation", 403)

    @staticmethod
    def _owned(principal, row):
        if "admin" not in principal["scopes"] and principal["owner"] != row["owner"]:
            raise ControlError("Run not found", 404)

    def templates(self, principal):
        self._scope(principal, "read")
        with self.lock:
            return {"schema": "arena.control-templates/1", "revision": self.revision,
                    "limits": dict(self.config["limits"]),
                    "templates": [{key: item[key] for key in ("id", "name", "framework", "profile", "model", "status", "blocked_reason", "resources")} for item in self.config["templates"]]}

    @staticmethod
    def _public(row):
        result = {key: row[key] for key in ("id", "owner", "template", "framework", "profile", "model", "label", "batch_id", "state", "reason", "created", "updated", "started", "ended", "returncode", "revision")}
        result["resources"] = {key: row[key] for key in ("cpus", "memory_mb", "evaluation_slots", "pids")}
        result["cancel_requested"] = bool(row["cancel_requested"])
        result["resources_reserved"] = bool(row["held"])
        result["canonical_evaluation"] = False
        return result

    def queue(self, principal, *, limit=200, offset=0):
        self._scope(principal, "read")
        _int(limit, "limit", high=500)
        _int(offset, "offset", low=0, high=10**7)
        with self._db() as db:
            # Shared overview contains only sanitized control metadata, never specs or paths.
            rows = db.execute("SELECT * FROM runs ORDER BY created DESC,id DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
            counts = {row["state"]: row["n"] for row in db.execute("SELECT state,COUNT(*) n FROM runs GROUP BY state")}
            used = db.execute("SELECT COUNT(*) active,COALESCE(SUM(cpus),0) cpus,COALESCE(SUM(memory_mb),0) memory_mb,COALESCE(SUM(evaluation_slots),0) evaluation_slots FROM runs WHERE held=1").fetchone()
        return {"schema": "arena.control-queue/1", "revision": self.revision,
                "runs": [self._public(row) for row in rows], "counts": counts,
                "resources": {"used": dict(used), "limits": dict(self.config["limits"])},
                "offset": offset, "limit": limit, "total": sum(counts.values()),
                "log_policy": "Lifecycle streams are sanitized; worker-redacted native diagnostics require logs:native scope or admin."}

    def detail(self, principal, run_id):
        self._scope(principal, "read")
        with self._db() as db:
            row = self._get(db, run_id)
        self._owned(principal, row)
        return {"schema": "arena.control-run/1", "run": self._public(row)}

    @staticmethod
    def _get(db, run_id):
        _id(run_id, "run id")
        row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise ControlError("Run not found", 404)
        return row

    def submit(self, principal, body):
        self._scope(principal, "submit")
        required = {"schema", "template", "model"}
        optional = {"label", "batch_id", "idempotency_key"}
        if type(body) is not dict or not required <= body.keys() or set(body) - required - optional or body["schema"] != "arena.control-submit/1":
            raise ControlError("Expected arena.control-submit/1")
        _id(body["template"], "template")
        for name in ("batch_id", "idempotency_key"):
            if name in body:
                _id(body[name], name)
        if "label" in body:
            _plain(body["label"], "label", 128)
        with self.lock:
            template = next((item for item in self.config["templates"] if item["id"] == body["template"]), None)
            if template is None or template["model"] != body["model"]:
                raise ControlError("Unknown template or mismatched model")
            if template["status"] == "blocked" and "admin" not in principal["scopes"]:
                raise ControlError("Only an administrator may record a blocked template", 403)
            snapshot = {"revision": self.revision, "template": template, "cgroup_root": self.config["cgroup_root"]}
            limits = dict(self.config["limits"])
        with self._db(write=True) as db:
            existing = None
            if body.get("idempotency_key"):
                existing = db.execute("SELECT * FROM runs WHERE key_id=? AND idempotency_key=?", (principal["id"], body["idempotency_key"])).fetchone()
            if existing is not None:
                if any(existing[name] != body.get(name) for name in ("template", "model", "label", "batch_id")):
                    raise ControlError("Idempotency key is already bound to a different submission", 409)
                return {"schema": "arena.control-run/1", "run": self._public(existing), "duplicate": True}
            key = db.execute("SELECT * FROM keys WHERE id=? AND revoked=0", (principal["id"],)).fetchone()
            if key is None:
                raise ControlError("Key has been revoked", 401)
            count, seconds = db.execute("SELECT COUNT(*),COALESCE(SUM(timeout_seconds),0) FROM runs WHERE key_id=?", (principal["id"],)).fetchone()
            timeout = template["spec"]["timeout_seconds"] if template["status"] == "ready" else 0
            if count >= min(key["max_runs"], limits["max_runs_per_key"]) or seconds + timeout > min(key["max_seconds"], limits["max_reserved_seconds_per_key"]):
                raise ControlError("Key run-count or reserved-runtime budget is exhausted", 429)
            if db.execute("SELECT COUNT(*) FROM runs WHERE state='queued'").fetchone()[0] >= limits["max_queued"]:
                raise ControlError("Queue capacity is exhausted", 429)
            run_id, now = uuid.uuid4().hex, time.time()
            directory = self.runs_dir / run_id
            directory.mkdir(mode=0o700)
            sha = _write_private(directory / "snapshot.json", snapshot)
            for stream in ("stdout", "stderr"):
                fd = os.open(directory / f"{stream}.log", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.close(fd)
            resources = template["resources"]
            state = "queued" if template["status"] == "ready" else "blocked"
            db.execute("""INSERT INTO runs
                (id,owner,key_id,template,framework,profile,model,label,batch_id,idempotency_key,
                 revision,snapshot_sha256,state,reason,created,updated,cpus,memory_mb,evaluation_slots,pids,timeout_seconds)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (run_id, principal["owner"], principal["id"], template["id"], template["framework"], template["profile"], template["model"],
                 body.get("label"), body.get("batch_id"), body.get("idempotency_key"), snapshot["revision"], sha, state, template["blocked_reason"], now, now,
                 resources["cpus"], resources["memory_mb"], resources["evaluation_slots"], resources["pids"], timeout))
            row = self._get(db, run_id)
        self._event(run_id, "Run admitted." if state == "queued" else "Run recorded as blocked.")
        return {"schema": "arena.control-run/1", "run": self._public(row), "duplicate": False}

    def cancel(self, principal, run_id):
        self._scope(principal, "cancel")
        with self._db(write=True) as db:
            row = self._get(db, run_id)
            self._owned(principal, row)
            if row["state"] == "queued":
                db.execute("UPDATE runs SET state='cancelled',cancel_requested=1,updated=?,ended=? WHERE id=?", (time.time(), time.time(), run_id))
            elif row["held"]:
                db.execute("UPDATE runs SET cancel_requested=1,updated=? WHERE id=?", (time.time(), run_id))
            row = self._get(db, run_id)
        self._event(run_id, "Cancellation requested.")
        return {"schema": "arena.control-run/1", "run": self._public(row)}

    def _event(self, run_id, message, *, error=False):
        # Only internal fixed strings reach this file. Native output and exception
        # messages are deliberately not copied into the agent-facing log channel.
        path = self.runs_dir / run_id / ("stderr.log" if error else "stdout.log")
        try:
            directory = _private_dir(path.parent)
            fd = os.open(directory / path.name, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                info = os.fstat(fd)
                if stat.S_ISREG(info.st_mode) and info.st_size < 1024 * 1024:
                    os.write(fd, f"{time.time():.3f} {message}\n".encode())
            finally:
                os.close(fd)
        except (OSError, ControlError):
            pass

    def logs(self, principal, run_id, *, stream="stdout", cursor=0, limit=16384, tail=False):
        self.detail(principal, run_id)
        native = stream in {"native_stdout", "native_stderr"}
        if native:
            self._scope(principal, "logs:native")
        elif stream not in {"stdout", "stderr"}:
            raise ControlError("Unknown log stream")
        _int(cursor, "cursor", low=0, high=2**40)
        _int(limit, "limit", high=MAX_LOG)
        directory = _private_dir(self.runs_dir / run_id)
        if native and not (directory / f"{stream}.log").exists() and not (directory / f"{stream}.log").is_symlink():
            return {"schema": "arena.control-log/1", "run_id": run_id, "stream": stream, "cursor": 0,
                    "next_cursor": 0, "size": 0, "text": "", "truncated": False, "eof": True,
                    "policy": "worker_redacted_native", "pending": True}
        # Open relative to an already opened nonsymlink directory to avoid leaf races.
        dfd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            fd = os.open(f"{stream}.log", os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=dfd)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > (MAX_NATIVE_LOG if native else 1024 * 1024):
                    raise ControlError("Control log is unavailable", 503)
                start = max(0, info.st_size - limit) if tail else min(cursor, info.st_size)
                os.lseek(fd, start, os.SEEK_SET)
                data = os.read(fd, limit)
            finally:
                os.close(fd)
        finally:
            os.close(dfd)
        return {"schema": "arena.control-log/1", "run_id": run_id, "stream": stream,
                "cursor": start, "next_cursor": start + len(data), "size": info.st_size,
                "text": data.decode("utf-8", errors="replace"), "truncated": start > 0,
                "policy": "worker_redacted_native" if native else "safe_control_events", "eof": start + len(data) >= info.st_size}

    def claim(self, worker_id):
        """Atomically reserve all resources. Expired leases are never re-queued."""
        _id(worker_id, "worker id")
        self.reload()
        limits = self.config["limits"]
        with self._db(write=True) as db:
            used = db.execute("SELECT COUNT(*) active,COALESCE(SUM(cpus),0) cpus,COALESCE(SUM(memory_mb),0) memory_mb,COALESCE(SUM(evaluation_slots),0) evaluation_slots FROM runs WHERE held=1").fetchone()
            if used["active"] >= limits["max_active"]:
                return None
            for row in db.execute("SELECT * FROM runs WHERE state='queued' ORDER BY created,id"):
                if any(row[name] + used[name] > limits[name] for name in ("cpus", "memory_mb", "evaluation_slots")):
                    continue
                now = time.time()
                db.execute("UPDATE runs SET state='preparing',held=1,lease_owner=?,lease_until=?,updated=? WHERE id=? AND state='queued'", (worker_id, now + LEASE_SECONDS, now, row["id"]))
                return dict(self._get(db, row["id"]))
        return None

    def heartbeat(self, run_id, worker_id):
        with self._db(write=True) as db:
            row = self._get(db, run_id)
            if row["lease_owner"] != worker_id or not row["held"]:
                raise ControlError("Worker does not own the run lease", 409)
            db.execute("UPDATE runs SET lease_until=?,updated=? WHERE id=?", (time.time() + LEASE_SECONDS, time.time(), run_id))
            return bool(row["cancel_requested"])

    def snapshot(self, row):
        data = _read_regular(self.runs_dir / row["id"] / "snapshot.json", private=True)
        if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), row["snapshot_sha256"]):
            raise ControlError("Run snapshot changed after submission", 409)
        return _decode(data)

    def finish(self, run_id, worker_id, state, *, reason=None, returncode=None, release=True):
        if state not in TERMINAL:
            raise ControlError("Invalid terminal state")
        with self._db(write=True) as db:
            row = self._get(db, run_id)
            if row["lease_owner"] != worker_id:
                raise ControlError("Worker does not own the run lease", 409)
            db.execute("UPDATE runs SET state=?,reason=?,returncode=?,held=?,updated=?,ended=?,lease_until=NULL WHERE id=?", (state, reason, returncode, 0 if release else 1, time.time(), time.time(), run_id))
        self._event(run_id, "Run " + state + ".", error=state in {"failed", "blocked"})

    def reconcile(self):
        """Recover terminal state only after proving the recorded cgroup empty.

        Unknown or live runs retain resource reservations and are never launched
        again. A stale lease is an observation, not permission to duplicate work.
        """
        with self._db() as db:
            rows = [dict(row) for row in db.execute("SELECT * FROM runs WHERE held=1 AND (lease_until IS NULL OR lease_until<?)", (time.time(),))]
        reconciled = []
        for row in rows:
            try:
                # A restarted service may use a new configured root. The run
                # snapshot records the original containment and remains binding.
                group = RunCgroup.existing(Path(self.snapshot(row)["cgroup_root"]), row["id"])
                populated = group.populated() if group is not None else False
                alive = _pid_alive(row["pid"], row["pid_identity"])
                if row["cancel_requested"] and group is not None:
                    group.kill()
                    populated = group.wait_empty(3)
                    populated = not populated
                if row["cancel_requested"] and alive:
                    _kill_recorded_process(row["pid"], row["pid_identity"])
                    alive = _pid_alive(row["pid"], row["pid_identity"])
                if populated or alive:
                    with self._db(write=True) as db:
                        current = self._get(db, row["id"])
                        if current["updated"] != row["updated"] or (current["lease_until"] is not None and current["lease_until"] >= time.time()):
                            continue
                        db.execute("UPDATE runs SET state='blocked',reason='Worker lease expired while a process remains live; resources retained.',updated=? WHERE id=?", (time.time(), row["id"]))
                    continue
                if group is not None:
                    group.close()
                state, reason, code = _completed_result(self.runs_dir / row["id"])
                if row["cancel_requested"]:
                    state, reason = "cancelled", "Cancelled after worker interruption."
                with self._db(write=True) as db:
                    current = self._get(db, row["id"])
                    if current["updated"] != row["updated"] or (current["lease_until"] is not None and current["lease_until"] >= time.time()):
                        continue
                    db.execute("UPDATE runs SET state=?,reason=?,returncode=?,held=0,ended=?,updated=?,lease_until=NULL WHERE id=?", (state, reason, code, time.time(), time.time(), row["id"]))
                reconciled.append(row["id"])
                self._event(row["id"], "Interrupted worker reconciled without relaunch.")
            except (OSError, ControlError):
                # Unreadable containment is not evidence that a process has exited.
                continue
        return reconciled
