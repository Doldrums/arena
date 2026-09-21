"""Private, authenticated native-run queue with conservative resource admission.

Serving the board never executes participant code. Only the explicit ``worker``
command starts isolated subprocesses, inside an operator-delegated cgroup v2.
The queue is not a security sandbox for hostile code or a remote Docker daemon.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import signal
import sqlite3
import stat
import subprocess
import sys
import threading
import time
from urllib.parse import parse_qs, urlsplit
import uuid

SCHEMA = "arena.control/1"
ACTIVE = ("preparing", "running")
TERMINAL = ("completed", "failed", "cancelled", "blocked")
SCOPES = {"read", "submit", "cancel", "logs:native", "admin"}
MAX_CONFIG = 8 * 1024 * 1024
MAX_LOG = 64 * 1024
MAX_NATIVE_LOG = 8 * 1024 * 1024
LEASE_SECONDS = 30
ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}\Z")
MODEL = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,199}\Z")
SECRET_KEY = re.compile(r"(?:password|secret|api[_-]?key|access[_-]?token|auth[_-]?token|credential)", re.I)
SECRET_VALUE = re.compile(r"(?:sk-[A-Za-z0-9_-]{12,}|arena_[A-Za-z0-9_-]{20,}|Bearer\s+\S+|-----BEGIN .*PRIVATE KEY)", re.I)


class ControlError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ControlError("Duplicate JSON fields are not allowed")
        result[key] = value
    return result


def _decode(data):
    try:
        return json.loads(data, object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (UnicodeError, ValueError) as exc:
        if isinstance(exc, ControlError):
            raise
        raise ControlError("Invalid JSON") from None


def _int(value, name, low=1, high=10**9):
    if type(value) is not int or not low <= value <= high:
        raise ControlError(f"Invalid {name}")
    return value


def _id(value, name="identifier"):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ControlError(f"Invalid {name}")
    return value


def _plain(value, name, maximum=240):
    if not isinstance(value, str) or not 1 <= len(value) <= maximum or any(ord(c) < 32 for c in value):
        raise ControlError(f"Invalid {name}")
    if SECRET_VALUE.search(value):
        raise ControlError(f"Credentials are not permitted in {name}")
    return value


def _private_dir(path, *, create=False):
    path = Path(path)
    if not path.is_absolute() or path.is_symlink():
        raise ControlError("Private directories must be absolute and must not be symlinks")
    # Reject any symlink ancestor; resolving and then checking the leaf is insufficient.
    if any(parent.is_symlink() for parent in path.parents):
        raise ControlError("Private directory ancestors must not be symlinks")
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise ControlError("Private directories must be owned by this user with mode 0700")
    # Prevent accidental publication by the repository static server or a wheel.
    public_root = Path(__file__).resolve().parents[2]
    if any(path.is_relative_to(public_root / name) for name in ("web", "registry", "_assets")):
        raise ControlError("Control state must be outside public assets and registry")
    return path


def _read_regular(path, maximum=MAX_CONFIG, *, private=False):
    path = Path(path).absolute()
    if ".." in path.parts:
        raise ControlError("Parent traversal is not allowed")
    # Walk open directory descriptors rather than checking paths and following
    # them later. This also closes ancestor-symlink replacement races.
    parent = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = child
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            raise ControlError("File must be a bounded regular file")
        if private and (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077):
            raise ControlError("Private files must be owned by this user with mode 0600")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(maximum + 1)
        if len(data) > maximum:
            raise ControlError("File exceeds size limit")
        return data
    finally:
        os.close(fd)


def _write_private(path, value):
    data = (_json(value) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)
    return hashlib.sha256(data).hexdigest()


def _secret_values():
    """Worker credentials stay in memory; only redacted snapshots leave here."""
    return tuple(sorted({value for name, value in os.environ.items()
                         if value and re.search(r"(?:KEY|TOKEN|PASSWORD|SECRET|CREDENTIAL|AUTH)", name, re.I)},
                        key=len, reverse=True))


def _partial_secret_suffix(text, secret):
    # Linear-time prefix-function search; credential values can be long JWTs.
    if len(secret) < 2 or not text:
        return 0
    pattern = secret + "\x00" + text[-(len(secret) - 1):]
    prefix = [0] * len(pattern)
    for index in range(1, len(pattern)):
        matched = prefix[index - 1]
        while matched and pattern[index] != pattern[matched]:
            matched = prefix[matched - 1]
        if pattern[index] == pattern[matched]:
            matched += 1
        prefix[index] = matched
    return prefix[-1]


def _redact_native(data, values):
    text = data.decode("utf-8", errors="replace")
    for secret in values:
        text = text.replace(secret, "[REDACTED]")
        # A still-growing log may end halfway through a credential. Do not
        # publish that prefix and reveal its remaining suffix on the next poll.
        size = _partial_secret_suffix(text, secret)
        if size:
            text = text[:-size] + "[REDACTED]"
    text = re.sub(r"(?i)Bearer\s+[^\s\"'<>]+", "Bearer [REDACTED]", text)
    text = re.sub(r"\beyJ[A-Za-z0-9_-]{4,}(?:\.[A-Za-z0-9_-]+){0,2}", "[REDACTED JWT]", text)
    text = re.sub(r"\b(?:sk-[A-Za-z0-9_-]{4,}|arena_[A-Za-z0-9_-]{8,}|gh[pousr]_[A-Za-z0-9_]{8,}|AKIA[A-Z0-9]{8,})", "[REDACTED KEY]", text)
    text = re.sub(r"(?im)((?:api[_-]?key|access[_-]?token|auth[_-]?token|password|secret)\s*[=:]\s*)[^\s,;]+", r"\1[REDACTED]", text)
    return text.encode("utf-8")[:MAX_NATIVE_LOG]


def _replace_private_bytes(path, data):
    temporary = path.parent / (".log-" + uuid.uuid4().hex)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
        os.replace(temporary, path)
    finally:
        os.close(fd)
        temporary.unlink(missing_ok=True)


def _publish_native_logs(directory, values):
    """Only this worker-side redactor reads raw native diagnostic streams."""
    _private_dir(directory)
    for stream in ("stdout", "stderr"):
        chunks = []
        try:
            raw = _read_regular(directory / "artifacts" / ".arena" / f"{stream}.log", maximum=MAX_NATIVE_LOG)
            chunks.append(raw)
        except (OSError, ControlError):
            # Missing, oversized, nonregular or symlinked artifacts are never
            # copied. The API cannot use the raw file as a fallback.
            pass
        if stream == "stderr":
            try:
                diagnostic = _read_regular(directory / "preparation.stderr", maximum=16384, private=True)
                chunks.insert(0, diagnostic)
            except (OSError, ControlError):
                pass
        if chunks:
            _replace_private_bytes(directory / f"native_{stream}.log", _redact_native(b"\n".join(chunks)[:MAX_NATIVE_LOG], values))


def _diagnostic(directory, stage, error, values):
    """Bounded scoped diagnostic, never a traceback or a public lifecycle event."""
    try:
        message = f"Stage: {stage}\n{type(error).__name__}: {str(error)[:4096]}\n"
        _replace_private_bytes(directory / "preparation.stderr", _redact_native(message.encode("utf-8", errors="replace"), values))
    except (OSError, ControlError):
        pass


def _spec_no_secrets(value, name="spec"):
    """Refuse credential fields and inline code; environment names are references."""
    if name == "environment_names":
        if type(value) is not list or any(not isinstance(item, str) or re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", item) is None for item in value):
            raise ControlError("environment_names must contain variable names, never values")
        return
    if isinstance(value, dict):
        for key, child in value.items():
            if SECRET_KEY.search(key) or key in {"code", "program", "source_code", "env", "environment"}:
                raise ControlError("Template specs must not contain credentials, environment values or code")
            _spec_no_secrets(child, key)
    elif isinstance(value, list):
        for child in value:
            _spec_no_secrets(child, name)
    elif isinstance(value, str):
        if SECRET_VALUE.search(value) or "\n" in value or "\x00" in value:
            raise ControlError("Template spec values must not contain credentials or inline code")
        if name == "arguments" and value.startswith("-") and SECRET_KEY.search(value):
            raise ControlError("Pass model credentials through explicitly named worker environment variables")


def validate_config(config):
    required = {"schema", "state_dir", "cgroup_root", "limits", "templates"}
    if type(config) is not dict or set(config) != required or config["schema"] != SCHEMA:
        raise ControlError("Expected arena.control/1 configuration")
    for name in ("state_dir", "cgroup_root"):
        if not isinstance(config[name], str) or not Path(config[name]).is_absolute():
            raise ControlError(f"{name} must be absolute")
    limits = config["limits"]
    names = {"cpus", "memory_mb", "evaluation_slots", "max_active", "max_queued", "max_runs_per_key", "max_reserved_seconds_per_key"}
    if type(limits) is not dict or set(limits) != names:
        raise ControlError("Resource, queue and key budget limits must be explicit")
    for key, value in limits.items():
        _int(value, key)
    _int(limits["evaluation_slots"], "evaluation_slots", high=32)
    if type(config["templates"]) is not list or len(config["templates"]) > 10000:
        raise ControlError("Invalid templates")
    seen = set()
    for template in config["templates"]:
        required = {"id", "name", "framework", "profile", "model", "status", "blocked_reason", "resources", "containment", "evaluation_concurrency_verified", "spec"}
        if type(template) is not dict or set(template) != required:
            raise ControlError("A template has missing or unknown fields")
        for name in ("id", "framework", "profile"):
            _id(template[name], name)
        _plain(template["name"], "template name")
        if template["id"] in seen:
            raise ControlError("Duplicate template id")
        seen.add(template["id"])
        if not isinstance(template["model"], str) or not MODEL.fullmatch(template["model"]):
            raise ControlError("A template needs an explicit model identifier")
        if template["status"] not in {"ready", "blocked"} or template["containment"] != "cgroup-v2":
            raise ControlError("Unsupported template status or containment")
        if type(template["evaluation_concurrency_verified"]) is not bool:
            raise ControlError("Evaluation concurrency verification must be explicit")
        resources = template["resources"]
        if type(resources) is not dict or set(resources) != {"cpus", "memory_mb", "evaluation_slots", "pids"}:
            raise ControlError("Each template needs explicit CPU, RAM, evaluation slots and process limits")
        for key, value in resources.items():
            _int(value, key)
        if template["status"] == "blocked":
            _plain(template["blocked_reason"], "blocked reason", 500)
        elif template["blocked_reason"] is not None or not template["evaluation_concurrency_verified"]:
            raise ControlError("Ready templates require verified native evaluation concurrency")
        if template["status"] == "ready":
            if any(resources[key] > limits[key] for key in ("cpus", "memory_mb", "evaluation_slots")):
                raise ControlError("Ready template resources exceed global capacity")
            spec = template["spec"]
            if type(spec) is not dict or spec.get("schema") != "arena.native-run/1" or spec.get("framework") != template["framework"]:
                raise ControlError("Ready templates require a matching native run spec")
            if set(spec) - {"schema", "framework", "source_dir", "output_dir", "timeout_seconds", "request", "environment_names"}:
                raise ControlError("Unknown native run spec fields")
            _int(spec.get("timeout_seconds"), "timeout_seconds", high=604800)
            if type(spec.get("request")) is not dict or not isinstance(spec.get("source_dir"), str) or not Path(spec["source_dir"]).is_absolute():
                raise ControlError("Native source and request must be explicit")
            if spec.get("output_dir") != "{output_dir}":
                raise ControlError("The control service must allocate output_dir")
            _spec_no_secrets(spec)
        elif template["spec"] is not None:
            _spec_no_secrets(template["spec"])
    return config


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


def _pid_identity(pid):
    if sys.platform != "linux" or not pid:
        return None
    try:
        start = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]
        boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        return f"{boot}:{start}"
    except (OSError, IndexError):
        return None


def _pid_alive(pid, identity):
    if not pid:
        return False
    actual = _pid_identity(pid)
    if actual is not None:
        try:
            if Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] == "Z":
                return False  # A zombie cannot run; cgroup descendants are checked separately.
        except (OSError, IndexError):
            pass
        return identity is None or hmac.compare_digest(actual, identity)
    try:
        os.kill(pid, 0)
        return True  # Cannot disprove identity; retain the reservation.
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _kill_recorded_process(pid, identity):
    """Stop a gated helper outside its leaf only with its exact recorded identity."""
    if not pid or not identity or _pid_identity(pid) != identity:
        return
    try:
        if os.getpgid(pid) == pid:
            os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


class RunCgroup:
    """Whole-run CPU/RAM/pid enforcement, including new sessions and descendants."""

    kernel_root = Path("/sys/fs/cgroup")

    @classmethod
    def _root(cls, root):
        root = Path(root)
        if sys.platform != "linux" or not root.is_absolute() or root.is_symlink() or any(p.is_symlink() for p in root.parents):
            raise ControlError("A delegated Linux cgroup v2 root is required")
        if root == cls.kernel_root or not root.is_relative_to(cls.kernel_root) or not (root / "cgroup.controllers").is_file():
            raise ControlError("A dedicated delegated child cgroup is required")
        return root

    @classmethod
    def existing(cls, root, run_id):
        root = cls._root(root)
        _id(run_id, "run id")
        path = root / ("arena-control-" + run_id)
        if path.is_symlink():
            raise ControlError("Run cgroup must not be a symlink")
        if not path.exists():
            return None
        obj = cls.__new__(cls)
        obj.path, obj.main = path, path / "main"
        return obj

    def __init__(self, root, run_id, resources):
        root = self._root(root)
        _id(run_id, "run id")
        self.path = root / ("arena-control-" + run_id)
        self.main = self.path / "main"
        self.path.mkdir(mode=0o700)
        try:
            settings = {"memory.max": str(resources["memory_mb"] * 1024**2),
                        "memory.swap.max": "0", "cpu.max": f"{resources['cpus'] * 100000} 100000",
                        "pids.max": str(resources["pids"])}
            for name in (*settings, "cgroup.kill", "cgroup.events", "cgroup.subtree_control"):
                if not (self.path / name).is_file():
                    raise ControlError("Delegate cpu, memory, pids and cgroup.kill before running")
            for name, value in settings.items():
                (self.path / name).write_text(value)
            # Empty parent with a main leaf supports native drivers that create
            # bounded child cgroups (e.g. Station) beneath the same run caps.
            (self.path / "cgroup.subtree_control").write_text("+cpu +memory +pids")
            self.main.mkdir(mode=0o700)
            self.kill()  # Prove kill permission before executing anything.
        except BaseException:
            try:
                self.close()
            except (OSError, ControlError):
                pass
            raise

    def kill(self):
        (self.path / "cgroup.kill").write_text("1")

    def populated(self):
        data = dict(line.split() for line in (self.path / "cgroup.events").read_text().splitlines())
        if data.get("populated") not in {"0", "1"}:
            raise ControlError("Cannot establish cgroup liveness")
        return data["populated"] == "1"

    def wait_empty(self, timeout=3):
        until = time.monotonic() + timeout
        while self.populated():
            if time.monotonic() >= until:
                return False
            time.sleep(0.05)
        return True

    def close(self):
        self.kill()
        if not self.wait_empty():
            raise ControlError("Run processes have not exited")
        for base, directories, _ in os.walk(self.path, topdown=False, followlinks=False):
            for directory in directories:
                (Path(base) / directory).rmdir()
        self.path.rmdir()


def _completed_result(directory):
    try:
        result = _decode(_read_regular(directory / "result.json", maximum=4096, private=True))
        if result.get("state") in {"completed", "failed"} and type(result.get("returncode")) is int:
            return result["state"], None if result["state"] == "completed" else "Native process failed; inspect private worker artifacts.", result["returncode"]
    except (OSError, ControlError, AttributeError):
        pass
    return "blocked", "Worker interrupted without a confirmed terminal result; no automatic relaunch.", None


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
    def __init__(self, service):
        self.service = service
        self.id = "worker-" + uuid.uuid4().hex
        self.stopping = threading.Event()

    def once(self):
        self.service.reconcile()
        row = self.service.claim(self.id)
        if row is None:
            return False
        self.execute(row)
        return True

    def execute(self, row):
        service, run_id = self.service, row["id"]
        process, group, released = None, None, True
        values = _secret_values()
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
                    _publish_native_logs(directory, values)
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
            _publish_native_logs(service.runs_dir / run_id, values)
            service.finish(run_id, self.id, state, reason=reason, returncode=code, release=released)

    def loop(self):
        while not self.stopping.is_set():
            try:
                worked = self.once()
            except (OSError, ControlError, sqlite3.Error):
                worked = False
            if not worked:
                self.stopping.wait(1)


def dispatch_http(handler, service):
    """Return True only for dedicated authenticated control endpoints."""
    parsed = urlsplit(handler.path)
    parts = parsed.path.strip("/").split("/")
    if parts[:2] not in (["api", "queue"], ["api", "control"]):
        return False
    try:
        principal = service.authenticate(handler.headers.get("Authorization"))
        method = handler.command
        if method == "GET" and parts == ["api", "control", "templates"]:
            value = service.templates(principal)
        elif method == "GET" and parts == ["api", "control", "results"]:
            from .results import results
            value = results(service, principal)
        elif method == "GET" and parts == ["api", "queue"]:
            query = parse_qs(parsed.query)
            value = service.queue(principal, limit=int(query.get("limit", ["200"])[0]), offset=int(query.get("offset", ["0"])[0]))
        elif method == "GET" and len(parts) == 3 and parts[:2] == ["api", "queue"]:
            value = service.detail(principal, parts[2])
        elif method == "GET" and len(parts) == 4 and parts[:2] == ["api", "queue"] and parts[3] == "logs":
            query = parse_qs(parsed.query)
            value = service.logs(principal, parts[2], stream=query.get("stream", ["stdout"])[0], cursor=int(query.get("cursor", ["0"])[0]), limit=int(query.get("limit", ["16384"])[0]), tail=query.get("tail", ["false"])[0] == "true")
        elif method == "POST":
            if handler.headers.get("Transfer-Encoding"):
                raise ControlError("Chunked control requests are not supported")
            length = int(handler.headers.get("Content-Length", "0"))
            if not 0 <= length <= 32768:
                raise ControlError("Request body exceeds limit", 413)
            handler.connection.settimeout(10)
            body = _decode(handler.rfile.read(length)) if length else {}
            if parts == ["api", "queue"]:
                value = service.submit(principal, body)
            elif len(parts) == 4 and parts[:2] == ["api", "queue"] and parts[3] == "cancel":
                if body:
                    raise ControlError("Cancel takes an empty object")
                value = service.cancel(principal, parts[2])
            elif parts == ["api", "control", "reload"]:
                service._scope(principal, "admin")
                if body:
                    raise ControlError("Reload takes an empty object")
                value = {"schema": "arena.control-reload/1", "revision": service.reload()}
            else:
                raise ControlError("Control route not found", 404)
        else:
            raise ControlError("Control route not found", 404)
        handler.reply(value)
    except ControlError as exc:
        handler.close_connection = True
        handler.reply({"error": str(exc)}, exc.status)
    except (ValueError, TypeError):
        handler.close_connection = True
        handler.reply({"error": "Invalid control request"}, 400)
    except Exception:
        handler.close_connection = True
        handler.reply({"error": "Control service is unavailable"}, 503)
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("serve", "worker", "create-key", "revoke-key", "check", "_execute"):
        child = sub.add_parser(command)
        child.add_argument("--config", required=True, type=Path)
        if command == "serve":
            child.add_argument("--port", type=int, default=8080)
            child.add_argument("--observe", action="append", default=[], type=Path)
        elif command == "worker":
            child.add_argument("--once", action="store_true")
            child.add_argument("--concurrency", type=int, default=1)
        elif command == "create-key":
            child.add_argument("--owner", required=True)
            child.add_argument("--scope", required=True, action="append", choices=sorted(SCOPES))
            child.add_argument("--max-runs", type=int)
            child.add_argument("--max-seconds", type=int)
        elif command == "revoke-key":
            child.add_argument("--key-id", required=True)
        elif command == "_execute":
            child.add_argument("--run-id", required=True)
            child.add_argument("--snapshot-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "_execute":
            return _execute(args.config, args.run_id, args.snapshot_sha256)
        service = ControlService(args.config)
        if args.command == "check":
            print(_json({"schema": SCHEMA, "revision": service.revision, "templates": len(service.config["templates"])}))
        elif args.command == "create-key":
            print(_json(service.create_key(args.owner, args.scope, max_runs=args.max_runs, max_seconds=args.max_seconds)))
        elif args.command == "revoke-key":
            service.revoke_key(args.key_id)
            print(_json({"revoked": True}))
        elif args.command == "serve":
            from .server import DashboardServer
            server = DashboardServer(("127.0.0.1", args.port), args.observe, control=service)
            try:
                server.serve_forever(poll_interval=0.25)
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
        elif args.command == "worker":
            _int(args.concurrency, "worker concurrency", high=64)
            workers = [Worker(service) for _ in range(args.concurrency)]
            for number in (signal.SIGTERM, signal.SIGINT):
                signal.signal(number, lambda *_: [worker.stopping.set() for worker in workers])
            if args.once:
                if args.concurrency != 1:
                    raise ControlError("--once requires concurrency 1")
                workers[0].once()
            else:
                threads = [threading.Thread(target=worker.loop, name=worker.id) for worker in workers]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
        return 0
    except (ControlError, OSError, sqlite3.Error):
        # Configuration exceptions can include private paths; do not echo them.
        print("Control operation failed; verify private configuration and permissions.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    # Keep the service and HTTP dispatch on one canonical module identity.
    # Otherwise ``python -m`` creates a second ControlError class under
    # __main__, and lazy server imports incorrectly downgrade 401/403 to 400.
    from arena.control import main as cli_main
    raise SystemExit(cli_main())
