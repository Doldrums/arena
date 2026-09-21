import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import socket
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from arena import control
from arena.server import DashboardServer


def template(identifier="fixture", *, slots=4):
    return {"id": identifier, "name": "Inert fixture", "framework": "fixture", "profile": "fixture",
            "model": "fixture-model", "status": "ready", "blocked_reason": None,
            "resources": {"cpus": 2, "memory_mb": 1024, "evaluation_slots": slots, "pids": 32},
            "containment": "cgroup-v2", "evaluation_concurrency_verified": True,
            "spec": {"schema": "arena.native-run/1", "framework": "fixture", "source_dir": "/fixture/source",
                     "output_dir": "{output_dir}", "timeout_seconds": 60,
                     "request": {"python": sys.executable, "profile": "fixture", "arguments": []},
                     "environment_names": ["OPENAI_API_KEY"]}}


@pytest.fixture
def service(tmp_path):
    config = {"schema": "arena.control/1", "state_dir": str(tmp_path / "private"),
              "cgroup_root": "/sys/fs/cgroup/arena-fixture",
              "limits": {"cpus": 8, "memory_mb": 4096, "evaluation_slots": 8, "max_active": 8,
                         "max_queued": 20, "max_runs_per_key": 100, "max_reserved_seconds_per_key": 6000},
              "templates": [template()]}
    path = tmp_path / "control.json"
    path.write_text(json.dumps(config))
    path.chmod(0o600)
    return control.ControlService(path)


def principal(service, owner="alice", scopes=("read", "submit", "cancel"), **kwargs):
    key = service.create_key(owner, scopes, **kwargs)
    return service.authenticate("Bearer " + key["token"]), key


def submit(service, user, **kwargs):
    return service.submit(user, {"schema": "arena.control-submit/1", "template": "fixture", "model": "fixture-model", **kwargs})["run"]


def config_write(service, update):
    config = copy.deepcopy(service.config)
    update(config)
    service.config_path.write_text(json.dumps(config))
    return config


def test_keys_hashed_revocable_and_private(service):
    user, key = principal(service)
    with service._db() as db:
        row = dict(db.execute("SELECT * FROM keys").fetchone())
    assert row["token_hash"] == hashlib.sha256(key["token"].encode()).hexdigest()
    assert key["token"] not in json.dumps(row)
    assert service.db_path.stat().st_mode & 0o077 == 0
    assert service.state_dir.stat().st_mode & 0o077 == 0
    service.revoke_key(key["id"])
    with pytest.raises(control.ControlError, match="Invalid bearer"):
        service.authenticate("Bearer " + key["token"])
    with pytest.raises(control.ControlError, match="revoked"):
        submit(service, user)


@pytest.mark.parametrize("header", [None, "", "Basic whatever", "Bearer wrong", "Bearer " + "x" * 300])
def test_authentication_fails_closed(service, header):
    with pytest.raises(control.ControlError) as caught:
        service.authenticate(header)
    assert caught.value.status == 401


def test_scopes_ownership_and_readonly_shared_overview(service):
    alice, _ = principal(service)
    bob, _ = principal(service, "bob")
    reader, _ = principal(service, "reader", ("read",))
    admin, _ = principal(service, "admin", ("admin",))
    run = submit(service, alice)
    assert service.queue(reader)["runs"][0]["id"] == run["id"]
    for operation in (lambda: submit(service, reader), lambda: service.cancel(reader, run["id"])):
        with pytest.raises(control.ControlError) as caught:
            operation()
        assert caught.value.status == 403
    for operation in (lambda: service.detail(bob, run["id"]), lambda: service.logs(bob, run["id"]), lambda: service.cancel(bob, run["id"])):
        with pytest.raises(control.ControlError) as caught:
            operation()
        assert caught.value.status == 404
    assert service.detail(admin, run["id"])["run"]["owner"] == "alice"
    assert service.cancel(admin, run["id"])["run"]["state"] == "cancelled"


def test_idempotency_is_atomic_and_cannot_rebind(service):
    user, _ = principal(service)
    def enqueue(_):
        return submit(service, user, label="Experiment", batch_id="matrix", idempotency_key="cell-1")["id"]
    with ThreadPoolExecutor(max_workers=8) as pool:
        identifiers = list(pool.map(enqueue, range(12)))
    assert len(set(identifiers)) == 1
    assert service.queue(user)["total"] == 1
    with pytest.raises(control.ControlError) as caught:
        submit(service, user, label="Changed", batch_id="matrix", idempotency_key="cell-1")
    assert caught.value.status == 409


def test_no_caller_native_spec_or_model_override(service):
    user, _ = principal(service)
    with pytest.raises(control.ControlError):
        submit(service, user, request={"arguments": ["--workers", "999"]})
    with pytest.raises(control.ControlError, match="mismatched model"):
        service.submit(user, {"schema": "arena.control-submit/1", "template": "fixture", "model": "expensive-model"})


def test_resources_reserved_atomically_across_workers(service):
    user, _ = principal(service)
    for _ in range(8):
        submit(service, user)
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(lambda n: service.claim("worker-" + str(n)), range(8)))
    claimed = [row for row in rows if row]
    assert len(claimed) == 2  # Eight evaluation slots, four per native run.
    overview = service.queue(user)
    assert overview["resources"]["used"] == {"active": 2, "cpus": 4, "memory_mb": 2048, "evaluation_slots": 8}
    row = claimed[0]
    service.finish(row["id"], row["lease_owner"], "completed")
    assert service.claim("worker-next") is not None


@pytest.mark.parametrize("capacity,value,expected", [("cpus", 2, 1), ("memory_mb", 1024, 1), ("max_active", 1, 1)])
def test_each_resource_cap_is_enforced(service, capacity, value, expected):
    config_write(service, lambda config: config["limits"].update({capacity: value}))
    service.reload()
    user, _ = principal(service)
    for _ in range(3):
        submit(service, user)
    assert sum(service.claim("worker-" + str(n)) is not None for n in range(3)) == expected


def test_queue_and_key_count_and_runtime_budgets(service):
    user, _ = principal(service, max_runs=1)
    submit(service, user)
    with pytest.raises(control.ControlError) as caught:
        submit(service, user)
    assert caught.value.status == 429
    other, _ = principal(service, "budget", max_seconds=59)
    with pytest.raises(control.ControlError, match="budget"):
        submit(service, other)
    config_write(service, lambda config: config["limits"].update(max_queued=1))
    service.reload()
    other, _ = principal(service, "queue")
    with pytest.raises(control.ControlError, match="capacity"):
        submit(service, other)


def test_blocked_admin_records_are_real_nonexecution_states(service):
    def blocked(config):
        config["templates"][0].update(status="blocked", blocked_reason="GPU prerequisite unavailable.", spec=None, evaluation_concurrency_verified=False)
    config_write(service, blocked)
    service.reload()
    user, _ = principal(service)
    with pytest.raises(control.ControlError) as caught:
        submit(service, user)
    assert caught.value.status == 403
    admin, _ = principal(service, "admin", ("admin",))
    run = submit(service, admin)
    assert run["state"] == "blocked"
    assert run["reason"] == "GPU prerequisite unavailable."
    assert run["resources_reserved"] is False
    assert service.claim("worker") is None


def test_reload_changes_future_templates_not_queued_snapshots(service):
    user, _ = principal(service)
    run = submit(service, user)
    revision = service.revision
    config_write(service, lambda config: config["templates"][0]["spec"].update(timeout_seconds=120))
    assert service.reload() != revision
    row = service.claim("worker")
    assert row["id"] == run["id"]
    assert service.snapshot(row)["template"]["spec"]["timeout_seconds"] == 60
    next_run = submit(service, user)
    with service._db() as db:
        assert service._get(db, next_run["id"])["timeout_seconds"] == 120
    config_write(service, lambda config: config.update(state_dir="/other/private"))
    with pytest.raises(control.ControlError, match="cannot change"):
        service.reload()


def test_snapshot_tampering_prevents_execution(service):
    user, _ = principal(service)
    run = submit(service, user)
    row = service.claim("worker")
    (service.runs_dir / run["id"] / "snapshot.json").write_text("{}")
    with pytest.raises(control.ControlError, match="changed"):
        service.snapshot(row)


def test_public_views_do_not_publish_specs_private_paths_or_key_hashes(service):
    user, key = principal(service)
    run = submit(service, user)
    rendered = json.dumps([service.queue(user), service.detail(user, run["id"]), service.templates(user)])
    for forbidden in (str(service.state_dir), "/fixture/source", sys.executable, key["token"], "OPENAI_API_KEY", "token_hash", "snapshot_sha256"):
        assert forbidden not in rendered
    with service._db() as db:
        raw_row = dict(service._get(db, run["id"]))
    assert "spec" not in raw_row
    assert "request" not in raw_row


def test_logs_cursor_tail_and_native_secret_exclusion(service):
    user, _ = principal(service)
    run = submit(service, user)
    directory = service.runs_dir / run["id"]
    raw = directory / "artifacts" / ".arena"
    raw.mkdir(parents=True)
    (raw / "stdout.log").write_text("sk-this-is-a-native-model-secret\nprint('generated code')")
    first = service.logs(user, run["id"], limit=12)
    second = service.logs(user, run["id"], cursor=first["next_cursor"], limit=32)
    whole = service.logs(user, run["id"])
    assert (first["text"] + second["text"]) == whole["text"][:44]
    assert "sk-" not in whole["text"] and "generated code" not in whole["text"]
    tail = service.logs(user, run["id"], tail=True, limit=10)
    assert tail["text"] == whole["text"][-10:]
    assert tail["eof"] is True
    with pytest.raises(control.ControlError):
        service.logs(user, run["id"], stream="../snapshot.json")
    with pytest.raises(control.ControlError):
        service.logs(user, run["id"], limit=65537)


def test_log_symlink_hardlink_and_directory_traversal_rejected(service, tmp_path):
    user, _ = principal(service)
    run = submit(service, user)
    log = service.runs_dir / run["id"] / "stdout.log"
    outside = tmp_path / "secret"
    outside.write_text("secret")
    log.unlink()
    log.symlink_to(outside)
    with pytest.raises(OSError):
        service.logs(user, run["id"])
    log.unlink()
    os.link(outside, log)
    with pytest.raises(control.ControlError):
        service.logs(user, run["id"])
    with pytest.raises(control.ControlError):
        service.logs(user, "../secret")


@pytest.mark.parametrize("change", [
    lambda c: c["limits"].update(evaluation_slots=33),
    lambda c: c["templates"][0].update(evaluation_concurrency_verified=False),
    lambda c: c["templates"][0]["resources"].update(evaluation_slots=9),
    lambda c: c["templates"][0]["spec"]["request"].update(api_key="value"),
    lambda c: c["templates"][0]["spec"]["request"].update(env={"OPENAI_API_KEY": "value"}),
    lambda c: c["templates"][0]["spec"]["request"].update(code="print(1)"),
    lambda c: c["templates"][0]["spec"]["request"].update(arguments=["--api-key", "value"]),
    lambda c: c["templates"][0]["spec"].update(output_dir="/operator/shared"),
])
def test_config_refuses_unbounded_or_secret_bearing_templates(service, change):
    config = copy.deepcopy(service.config)
    change(config)
    with pytest.raises(control.ControlError):
        control.validate_config(config)


def test_private_configuration_required_and_duplicate_fields_rejected(service):
    service.config_path.chmod(0o644)
    with pytest.raises(control.ControlError, match="0600"):
        service.reload()
    with pytest.raises(control.ControlError, match="Duplicate"):
        control._decode('{"a":1,"a":2}')


def test_reserved_control_environment_names_are_not_credential_values(service):
    config = copy.deepcopy(service.config)
    config["templates"][0]["spec"]["environment_names"] = ["OPENAI_API_KEY", "ARENA_EVALUATION_CGROUP_PARENT", "ARENA_EVALUATION_RECEIPTS_DIR", "ARENA_CONTROL_RUN_ID"]
    assert control.validate_config(config) is config
    config["templates"][0]["spec"]["environment_names"].append("arena_this-is-a-bearer-value-123456789")
    with pytest.raises(control.ControlError, match="variable names"):
        control.validate_config(config)


def stale(service, row, **kwargs):
    with service._db(write=True) as db:
        fields = {"lease_until": 0, **kwargs}
        db.execute("UPDATE runs SET " + ",".join(key + "=?" for key in fields) + " WHERE id=?", (*fields.values(), row["id"]))


class FakeGroup:
    def __init__(self, *, live=False):
        self.live, self.killed, self.closed = live, False, False
    def populated(self):
        return self.live
    def kill(self):
        self.killed = True
        self.live = False
    def wait_empty(self, _timeout=3):
        return not self.live
    def close(self):
        assert not self.live
        self.closed = True


def test_stale_live_run_never_requeued_or_releases_capacity(service, monkeypatch):
    user, _ = principal(service)
    run = submit(service, user)
    row = service.claim("dead-worker")
    stale(service, row, state="running", pid=123, pid_identity="boot:123")
    group = FakeGroup(live=True)
    monkeypatch.setattr(control.RunCgroup, "existing", lambda *args: group)
    monkeypatch.setattr(control, "_pid_alive", lambda *args: True)
    assert service.reconcile() == []
    detail = service.detail(user, run["id"])["run"]
    assert detail["state"] == "blocked" and detail["resources_reserved"]
    assert service.claim("new-worker") is None
    assert not group.killed


def test_stale_dead_run_with_result_recovers_without_relaunch(service, monkeypatch):
    user, _ = principal(service)
    run = submit(service, user)
    row = service.claim("dead-worker")
    stale(service, row)
    group = FakeGroup()
    monkeypatch.setattr(control.RunCgroup, "existing", lambda *args: group)
    monkeypatch.setattr(control, "_pid_alive", lambda *args: False)
    control._write_private(service.runs_dir / run["id"] / "result.json", {"state": "completed", "returncode": 0})
    assert service.reconcile() == [run["id"]]
    detail = service.detail(user, run["id"])["run"]
    assert detail["state"] == "completed" and not detail["resources_reserved"]
    assert group.closed
    assert service.claim("new-worker") is None


def test_stale_dead_run_without_result_is_blocked_not_retried(service, monkeypatch):
    user, _ = principal(service)
    run = submit(service, user)
    row = service.claim("dead-worker")
    stale(service, row)
    monkeypatch.setattr(control.RunCgroup, "existing", lambda *args: None)
    monkeypatch.setattr(control, "_pid_alive", lambda *args: False)
    service.reconcile()
    detail = service.detail(user, run["id"])["run"]
    assert detail["state"] == "blocked" and not detail["resources_reserved"]
    assert service.claim("new-worker") is None


def test_reconciliation_retains_resources_if_cgroup_unreadable(service, monkeypatch):
    user, _ = principal(service)
    run = submit(service, user)
    row = service.claim("dead-worker")
    stale(service, row)
    def inaccessible(*args):
        raise PermissionError()
    monkeypatch.setattr(control.RunCgroup, "existing", inaccessible)
    assert service.reconcile() == []
    assert service.detail(user, run["id"])["run"]["resources_reserved"]


def test_cancel_stale_owned_cgroup_and_release_only_after_empty(service, monkeypatch):
    user, _ = principal(service)
    run = submit(service, user)
    row = service.claim("dead-worker")
    stale(service, row, state="running")
    group = FakeGroup(live=True)
    monkeypatch.setattr(control.RunCgroup, "existing", lambda *args: group)
    monkeypatch.setattr(control, "_pid_alive", lambda *args: False)
    service.cancel(user, run["id"])
    assert service.reconcile() == [run["id"]]
    assert group.killed and group.closed
    assert service.detail(user, run["id"])["run"]["state"] == "cancelled"


def test_wrong_worker_cannot_heartbeat_or_finish(service):
    user, _ = principal(service)
    run = submit(service, user)
    service.claim("worker-one")
    with pytest.raises(control.ControlError):
        service.heartbeat(run["id"], "worker-two")
    with pytest.raises(control.ControlError):
        service.finish(run["id"], "worker-two", "completed")


def test_worker_fail_closed_before_native_launch_without_containment(service, monkeypatch):
    user, _ = principal(service)
    run = submit(service, user)
    def unavailable(*args):
        raise control.ControlError("No cgroup delegation")
    monkeypatch.setattr(control, "RunCgroup", unavailable)
    monkeypatch.setattr(control.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("must not launch"))
    worker = control.Worker(service)
    worker.execute(service.claim(worker.id))
    detail = service.detail(user, run["id"])["run"]
    assert detail["state"] == "blocked" and not detail["resources_reserved"]


def test_execute_gate_eof_never_imports_runtime(monkeypatch):
    monkeypatch.setattr(sys, "stdin", type("Input", (), {"buffer": io.BytesIO(b"")})())
    assert control._execute(Path("/not/read"), "fixture", "hash") == 125


def test_execute_calls_actual_runtime_contract_in_containment(service, monkeypatch):
    from arena.frameworks import runtime
    user, _ = principal(service)
    run = submit(service, user)
    row = service.claim("fixture-worker")
    leaf = service.runs_dir / run["id"] / "fake-main"
    leaf.mkdir()
    group = type("Group", (), {"main": leaf, "path": leaf.parent})()
    monkeypatch.setattr(control.RunCgroup, "existing", lambda *args: group)
    monkeypatch.setattr(sys, "stdin", type("Input", (), {"buffer": io.BytesIO(b"G")})())
    monkeypatch.setenv("ARENA_EVALUATION_CGROUP_PARENT", "overwritten-in-child")
    monkeypatch.setenv("ARENA_CONTROL_RUN_ID", "overwritten-in-child")
    monkeypatch.setenv("ARENA_EVALUATION_RECEIPTS_DIR", "overwritten-in-child")
    def inert_run(spec):
        assert (leaf / "cgroup.procs").read_text() == str(os.getpid())
        assert spec["output_dir"] == str(service.runs_dir / run["id"] / "artifacts")
        assert spec["framework"] == "fixture"
        assert os.environ["ARENA_EVALUATION_CGROUP_PARENT"] == str(group.path)
        assert os.environ["ARENA_CONTROL_RUN_ID"] == run["id"]
        assert os.environ["ARENA_EVALUATION_RECEIPTS_DIR"] == str(service.runs_dir / run["id"] / "artifacts" / "canonical-evaluations")
        assert "ARENA_EVALUATION_CGROUP_PARENT" in spec["environment_names"]
        assert service.detail(user, run["id"])["run"]["state"] == "running"
        return {"status": "process_completed", "returncode": 0}
    monkeypatch.setattr(runtime, "run", inert_run)
    assert control._execute(service.config_path, run["id"], row["snapshot_sha256"]) == 0
    result = json.loads((service.runs_dir / run["id"] / "result.json").read_text())
    assert result == {"state": "completed", "returncode": 0}


@pytest.fixture
def http(service):
    server = DashboardServer(("127.0.0.1", 0), [], control=service)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "http://127.0.0.1:" + str(server.server_port)
    server.shutdown()
    thread.join(timeout=3)
    server.server_close()


def request(url, *, token=None, body=None, method=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = Request(url, data=None if body is None else json.dumps(body).encode(), headers=headers, method=method)
    try:
        with urlopen(req, timeout=3) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.load(exc)


def test_http_same_port_authentication_submission_read_and_cancel(service, http):
    user, key = principal(service)
    assert request(http + "/api/queue")[0] == 401
    assert request(http + "/api/control/templates")[0] == 401
    assert request(http + "/api/health")[1]["mode"] == "private_control"
    assert request(http + "/api/control/templates", token=key["token"])[1]["templates"][0]["id"] == "fixture"
    code, value = request(http + "/api/queue", token=key["token"], body={"schema": "arena.control-submit/1", "template": "fixture", "model": "fixture-model"})
    assert code == 200
    run_id = value["run"]["id"]
    assert request(http + "/api/queue/" + run_id, token=key["token"])[1]["run"]["state"] == "queued"
    assert request(http + "/api/queue/" + run_id + "/logs", token=key["token"])[1]["policy"] == "safe_control_events"
    assert request(http + "/api/queue/" + run_id + "/cancel", token=key["token"], body={})[1]["run"]["state"] == "cancelled"
    assert request(http + "/api/runs", token=key["token"], body={})[0] == 404


def test_control_server_refuses_nonloopback_binding(service):
    with pytest.raises(ValueError, match="loopback"):
        DashboardServer(("0.0.0.0", 0), [], control=service)


def test_pid_reuse_does_not_identify_live_old_run(monkeypatch):
    monkeypatch.setattr(control, "_pid_identity", lambda pid: "new-boot:50")
    assert control._pid_alive(123, "old-boot:50") is False
    assert control._pid_alive(123, "new-boot:50") is True


def test_sample_configuration_is_blocked_and_valid():
    path = Path(__file__).resolve().parents[1] / "docs/control.example.json"
    config = control.validate_config(json.loads(path.read_text()))
    assert config["limits"]["evaluation_slots"] == 32
    assert all(item["status"] == "blocked" for item in config["templates"])


def test_native_log_scope_redacts_worker_secrets_before_pagination(service, monkeypatch):
    user, _ = principal(service)
    run = submit(service, user)
    native, _ = principal(service, scopes=("read", "logs:native"))
    directory = service.runs_dir / run["id"]
    raw = directory / "artifacts" / ".arena"
    raw.mkdir(parents=True)
    secret = "fixture-gateway-credential-0123456789"
    monkeypatch.setenv("ARENA_PROVIDER_CLIENT_KEY", secret)
    payload = "diagnostic " + secret + "\n" + "Bearer abc123\n" + "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJyb290In0.signature\n"
    (raw / "stdout.log").write_text(payload)
    with pytest.raises(control.ControlError) as caught:
        service.logs(user, run["id"], stream="native_stdout")
    assert caught.value.status == 403
    assert service.logs(native, run["id"], stream="native_stdout")["pending"]
    control._publish_native_logs(directory, control._secret_values())
    # The HTTP process can now lack all worker credentials; it reads only the
    # already redacted snapshot and cannot fall back to the raw source file.
    monkeypatch.delenv("ARENA_PROVIDER_CLIENT_KEY")
    text = ""
    cursor = 0
    while True:
        page = service.logs(native, run["id"], stream="native_stdout", cursor=cursor, limit=7)
        text += page["text"]
        cursor = page["next_cursor"]
        if page["eof"]:
            break
    assert secret not in text and "abc123" not in text and "eyJ" not in text
    assert "diagnostic" in text and "REDACTED" in text
    assert (directory / "native_stdout.log").stat().st_mode & 0o077 == 0
    assert secret not in service.db_path.read_bytes().decode(errors="replace")


def test_growing_partial_native_credential_is_not_published(service):
    user, _ = principal(service, scopes=("admin",))
    run = submit(service, user)
    directory = service.runs_dir / run["id"]
    raw = directory / "artifacts" / ".arena"
    raw.mkdir(parents=True)
    secret = "private-value-abcdefghijklmnop"
    for length in (3, 10, len(secret)):
        (raw / "stderr.log").write_text("message " + secret[:length])
        control._publish_native_logs(directory, (secret,))
        result = service.logs(user, run["id"], stream="native_stderr")
        assert secret[:length] not in result["text"]
        assert "message [REDACTED]" in result["text"]


def test_native_log_redactor_never_follows_raw_symlinks(service, tmp_path):
    user, _ = principal(service, scopes=("admin",))
    run = submit(service, user)
    directory = service.runs_dir / run["id"]
    raw = directory / "artifacts" / ".arena"
    raw.mkdir(parents=True)
    target = tmp_path / "private-other-file"
    target.write_text("unrelated private data")
    (raw / "stdout.log").symlink_to(target)
    control._publish_native_logs(directory, ())
    result = service.logs(user, run["id"], stream="native_stdout")
    assert result["pending"] is True and result["text"] == ""


def test_reconciliation_does_not_override_a_worker_heartbeat_during_probe(service, monkeypatch):
    user, _ = principal(service)
    run = submit(service, user)
    row = service.claim("worker")
    stale(service, row)
    def renewed(*args):
        service.heartbeat(row["id"], "worker")
        return None
    monkeypatch.setattr(control.RunCgroup, "existing", renewed)
    monkeypatch.setattr(control, "_pid_alive", lambda *args: False)
    assert service.reconcile() == []
    detail = service.detail(user, run["id"])["run"]
    assert detail["state"] == "preparing" and detail["resources_reserved"]


def test_cgroup_limits_cover_descendants_and_keep_parent_empty(tmp_path, monkeypatch):
    kernel = tmp_path / "kernel"
    delegated = kernel / "delegated"
    delegated.mkdir(parents=True)
    (delegated / "cgroup.controllers").write_text("cpu memory pids")
    original_mkdir = Path.mkdir
    def mkdir(path, *args, **kwargs):
        original_mkdir(path, *args, **kwargs)
        if path.parent == delegated:
            for name in ("memory.max", "memory.swap.max", "cpu.max", "pids.max", "cgroup.kill", "cgroup.subtree_control"):
                (path / name).touch()
            (path / "cgroup.events").write_text("populated 0\nfrozen 0\n")
        elif path.name == "main":
            (path / "cgroup.procs").touch()
    monkeypatch.setattr(Path, "mkdir", mkdir)
    monkeypatch.setattr(control.sys, "platform", "linux")
    monkeypatch.setattr(control.RunCgroup, "kernel_root", kernel)
    group = control.RunCgroup(delegated, "a" * 32, {"cpus": 4, "memory_mb": 8192, "pids": 128})
    assert (group.path / "cpu.max").read_text() == "400000 100000"
    assert (group.path / "memory.max").read_text() == str(8192 * 1024**2)
    assert (group.path / "memory.swap.max").read_text() == "0"
    assert (group.path / "pids.max").read_text() == "128"
    assert (group.path / "cgroup.subtree_control").read_text() == "+cpu +memory +pids"
    assert (group.path / "cgroup.kill").read_text() == "1"
    assert (group.main / "cgroup.procs").read_text() == ""
    assert group.populated() is False
    (group.path / "cgroup.events").write_text("populated 1\n")
    assert group.populated() is True
    assert group.wait_empty(0) is False


def test_worker_cancels_entire_group_and_records_terminal_state(service, monkeypatch):
    user, _ = principal(service)
    run = submit(service, user)
    worker = control.Worker(service)
    row = service.claim(worker.id)
    group = FakeGroup(live=True)
    group.path = Path("/sys/fs/cgroup/arena-fixture/arena-control-" + run["id"])
    monkeypatch.setattr(control, "RunCgroup", lambda *args: group)
    calls = []
    class Process:
        pid = 12345
        stdin = io.BytesIO()
        def __init__(self, argv, **kwargs):
            assert argv[1:4] == ["-m", "arena.control", "_execute"]
            assert kwargs["start_new_session"] is True
            service.cancel(user, run["id"])
        def poll(self):
            return -9 if group.killed else None
        def wait(self, timeout):
            return -9
    monkeypatch.setattr(control.subprocess, "Popen", Process)
    monkeypatch.setattr(control, "_pid_identity", lambda pid: "fixture-boot:123")
    monkeypatch.setattr(control.os, "killpg", lambda *args: calls.append(args))
    worker.execute(row)
    detail = service.detail(user, run["id"])["run"]
    assert group.killed and group.closed
    assert detail["state"] == "cancelled" and not detail["resources_reserved"]


def test_reconcile_uses_original_snapshot_root_after_restart(service, monkeypatch):
    user, _ = principal(service)
    run = submit(service, user)
    row = service.claim("worker")
    stale(service, row)
    original = service.config["cgroup_root"]
    config_write(service, lambda config: config.update(cgroup_root="/sys/fs/cgroup/new-root"))
    restarted = control.ControlService(service.config_path)
    seen = []
    def group(root, run_id):
        seen.append(str(root))
        return FakeGroup(live=True)
    monkeypatch.setattr(control.RunCgroup, "existing", group)
    monkeypatch.setattr(control, "_pid_alive", lambda *args: False)
    restarted.reconcile()
    assert seen == [original]
    assert restarted.detail(user, run["id"])["run"]["resources_reserved"]


def test_worker_preparation_errors_are_actionable_only_in_scoped_redacted_log(service, monkeypatch):
    user, _ = principal(service)
    admin, _ = principal(service, "admin", ("admin",))
    run = submit(service, user)
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-private-gateway-secret")
    def unavailable(*args):
        raise control.ControlError("Delegate memory controller; credential fixture-private-gateway-secret")
    monkeypatch.setattr(control, "RunCgroup", unavailable)
    worker = control.Worker(service)
    worker.execute(service.claim(worker.id))
    public = service.logs(user, run["id"], stream="stderr")["text"]
    assert "Delegate memory" not in public
    native = service.logs(admin, run["id"], stream="native_stderr")["text"]
    assert "worker_preparation" in native and "Delegate memory controller" in native
    assert "fixture-private-gateway-secret" not in native
    assert "REDACTED" in native


def test_python_module_serve_preserves_http_error_classes(service):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(Path(control.__file__).resolve().parents[1])
    process = subprocess.Popen([sys.executable, "-m", "arena.control", "serve", "--config", str(service.config_path), "--port", str(port)],
                               env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 5
        while True:
            try:
                code, body = request(f"http://127.0.0.1:{port}/api/queue")
                break
            except OSError:
                if time.monotonic() > deadline or process.poll() is not None:
                    raise
                time.sleep(0.025)
        assert code == 401 and body["error"] == "A bearer key is required"
        reader, key = principal(service, "reader", ("read",))
        code, _ = request(f"http://127.0.0.1:{port}/api/queue", token=key["token"], body={"schema": "arena.control-submit/1", "template": "fixture", "model": "fixture-model"})
        assert code == 403
    finally:
        process.terminate()
        process.wait(timeout=5)


def test_cgroup_entry_failure_publishes_scoped_preparation_diagnostic(service, monkeypatch):
    user, _ = principal(service, scopes=("admin",))
    run = submit(service, user)
    row = service.claim("fixture-worker")
    leaf = service.runs_dir / run["id"] / "invalid-leaf"
    leaf.mkdir()
    (leaf / "cgroup.procs").mkdir()  # Force an inert kernel-write failure.
    group = type("Group", (), {"main": leaf, "path": leaf.parent})()
    monkeypatch.setattr(control.RunCgroup, "existing", lambda *args: group)
    monkeypatch.setattr(sys, "stdin", type("Input", (), {"buffer": io.BytesIO(b"G")})())
    assert control._execute(service.config_path, run["id"], row["snapshot_sha256"]) == 1
    control._publish_native_logs(service.runs_dir / run["id"], ())
    text = service.logs(user, run["id"], stream="native_stderr")["text"]
    assert "cgroup_entry" in text and "IsADirectoryError" in text
    assert "cgroup_entry" not in service.logs(user, run["id"], stream="stderr")["text"]
