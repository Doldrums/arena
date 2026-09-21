import io
import json
import os
from pathlib import Path
import sys

import pytest

from arena import control, control_io, control_logs, control_process, control_service, control_worker
from control_helpers import FakeGroup, config_write, principal, service, stale, submit


def test_stale_live_run_never_requeued_or_releases_capacity(service, monkeypatch):
    user, _ = principal(service)
    run = submit(service, user)
    row = service.claim("dead-worker")
    stale(service, row, state="running", pid=123, pid_identity="boot:123")
    group = FakeGroup(live=True)
    monkeypatch.setattr(control_process.RunCgroup, "existing", lambda *args: group)
    monkeypatch.setattr(control_service, "_pid_alive", lambda *args: True)
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
    monkeypatch.setattr(control_process.RunCgroup, "existing", lambda *args: group)
    monkeypatch.setattr(control_service, "_pid_alive", lambda *args: False)
    control_io._write_private(service.runs_dir / run["id"] / "result.json", {"state": "completed", "returncode": 0})
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
    monkeypatch.setattr(control_process.RunCgroup, "existing", lambda *args: None)
    monkeypatch.setattr(control_service, "_pid_alive", lambda *args: False)
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
    monkeypatch.setattr(control_process.RunCgroup, "existing", inaccessible)
    assert service.reconcile() == []
    assert service.detail(user, run["id"])["run"]["resources_reserved"]


def test_cancel_stale_owned_cgroup_and_release_only_after_empty(service, monkeypatch):
    user, _ = principal(service)
    run = submit(service, user)
    row = service.claim("dead-worker")
    stale(service, row, state="running")
    group = FakeGroup(live=True)
    monkeypatch.setattr(control_process.RunCgroup, "existing", lambda *args: group)
    monkeypatch.setattr(control_service, "_pid_alive", lambda *args: False)
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
    monkeypatch.setattr(control_worker, "RunCgroup", unavailable)
    monkeypatch.setattr(control_worker.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("must not launch"))
    worker = control.Worker(service)
    worker.execute(service.claim(worker.id))
    detail = service.detail(user, run["id"])["run"]
    assert detail["state"] == "blocked" and not detail["resources_reserved"]


def test_execute_gate_eof_never_imports_runtime(monkeypatch):
    monkeypatch.setattr(sys, "stdin", type("Input", (), {"buffer": io.BytesIO(b"")})())
    assert control_worker._execute(Path("/not/read"), "fixture", "hash") == 125


def test_execute_calls_actual_runtime_contract_in_containment(service, monkeypatch):
    from arena.frameworks import runtime
    user, _ = principal(service)
    run = submit(service, user)
    row = service.claim("fixture-worker")
    leaf = service.runs_dir / run["id"] / "fake-main"
    leaf.mkdir()
    group = type("Group", (), {"main": leaf, "path": leaf.parent})()
    monkeypatch.setattr(control_process.RunCgroup, "existing", lambda *args: group)
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
    assert control_worker._execute(service.config_path, run["id"], row["snapshot_sha256"]) == 0
    result = json.loads((service.runs_dir / run["id"] / "result.json").read_text())
    assert result == {"state": "completed", "returncode": 0}


def test_pid_reuse_does_not_identify_live_old_run(monkeypatch):
    monkeypatch.setattr(control_process, "_pid_identity", lambda pid: "new-boot:50")
    assert control_process._pid_alive(123, "old-boot:50") is False
    assert control_process._pid_alive(123, "new-boot:50") is True


def test_reconciliation_does_not_override_a_worker_heartbeat_during_probe(service, monkeypatch):
    user, _ = principal(service)
    run = submit(service, user)
    row = service.claim("worker")
    stale(service, row)
    def renewed(*args):
        service.heartbeat(row["id"], "worker")
        return None
    monkeypatch.setattr(control_process.RunCgroup, "existing", renewed)
    monkeypatch.setattr(control_service, "_pid_alive", lambda *args: False)
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
    monkeypatch.setattr(control_process.sys, "platform", "linux")
    monkeypatch.setattr(control_process.RunCgroup, "kernel_root", kernel)
    group = control_process.RunCgroup(delegated, "a" * 32, {"cpus": 4, "memory_mb": 8192, "pids": 128})
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
    monkeypatch.setattr(control_worker, "RunCgroup", lambda *args: group)
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
    monkeypatch.setattr(control_worker.subprocess, "Popen", Process)
    monkeypatch.setattr(control_worker, "_pid_identity", lambda pid: "fixture-boot:123")
    monkeypatch.setattr(control_worker.os, "killpg", lambda *args: calls.append(args))
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
    monkeypatch.setattr(control_process.RunCgroup, "existing", group)
    monkeypatch.setattr(control_service, "_pid_alive", lambda *args: False)
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
    monkeypatch.setattr(control_worker, "RunCgroup", unavailable)
    worker = control.Worker(service)
    worker.execute(service.claim(worker.id))
    public = service.logs(user, run["id"], stream="stderr")["text"]
    assert "Delegate memory" not in public
    native = service.logs(admin, run["id"], stream="native_stderr")["text"]
    assert "worker_preparation" in native and "Delegate memory controller" in native
    assert "fixture-private-gateway-secret" not in native
    assert "REDACTED" in native


def test_cgroup_entry_failure_publishes_scoped_preparation_diagnostic(service, monkeypatch):
    user, _ = principal(service, scopes=("admin",))
    run = submit(service, user)
    row = service.claim("fixture-worker")
    leaf = service.runs_dir / run["id"] / "invalid-leaf"
    leaf.mkdir()
    (leaf / "cgroup.procs").mkdir()  # Force an inert kernel-write failure.
    group = type("Group", (), {"main": leaf, "path": leaf.parent})()
    monkeypatch.setattr(control_process.RunCgroup, "existing", lambda *args: group)
    monkeypatch.setattr(sys, "stdin", type("Input", (), {"buffer": io.BytesIO(b"G")})())
    assert control_worker._execute(service.config_path, run["id"], row["snapshot_sha256"]) == 1
    control_logs._publish_native_logs(service.runs_dir / run["id"], ())
    text = service.logs(user, run["id"], stream="native_stderr")["text"]
    assert "cgroup_entry" in text and "IsADirectoryError" in text
    assert "cgroup_entry" not in service.logs(user, run["id"], stream="stderr")["text"]
