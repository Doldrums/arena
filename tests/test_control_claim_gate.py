"""Operator drain preserves active work and queued identities without signals."""
import io
import os
from pathlib import Path
import stat
import tempfile

import pytest

from arena import control_claim_gate as gate, control_cli, control_worker
from arena.control_types import ControlError
from control_helpers import FakeGroup, principal, service, submit


@pytest.fixture
def gate_path(monkeypatch):
    # Exercise the real ownership/permissions path under a trusted home tree.
    # Production has a fixed root UID and exposes no owner override.
    monkeypatch.setattr(gate, "_ROOT_UID", os.getuid())
    with tempfile.TemporaryDirectory(prefix=".arena-claim-gate-", dir=Path.home().resolve()) as directory:
        path = Path(directory) / "gate"
        assert gate.operate(path, "initialize")["paused"]
        yield path


def test_initialize_paused_permissions_and_no_lock_replacement(gate_path):
    assert stat.S_IMODE(gate_path.stat().st_mode) == 0o755
    lock = gate_path / "claims.lock"
    identity = (lock.stat().st_dev, lock.stat().st_ino)
    assert stat.S_IMODE(lock.stat().st_mode) == 0o444
    for action, expected in (("resume", False), ("pause", True), ("pause", True), ("status", True)):
        result = gate.operate(gate_path, action)
        assert result["paused"] is expected
        assert result["active_runs_interrupted"] is False
        assert (lock.stat().st_dev, lock.stat().st_ino) == identity
    with pytest.raises(FileExistsError):
        gate.operate(gate_path, "initialize")


@pytest.mark.parametrize("action", ["initialize", "pause", "resume", "status"])
def test_operator_commands_reject_nonroot_before_access(gate_path, monkeypatch, action):
    monkeypatch.setattr(gate.os, "geteuid", lambda: gate._ROOT_UID + 1)
    with pytest.raises(ControlError, match="requires root"):
        gate.operate(gate_path, action)


def test_worker_pause_preserves_queue_and_snapshot_then_resumes_same_id(service, gate_path, monkeypatch):
    user, _ = principal(service)
    submitted = submit(service, user)
    with service._db() as db:
        original = dict(service._get(db, submitted["id"]))
    snapshot = (service.runs_dir / submitted["id"] / "snapshot.json").read_bytes()
    revision, config = service.revision, service.config_path.read_bytes()
    worker = control_worker.Worker(service, claim_gate=gate_path)
    executed = []
    monkeypatch.setattr(worker, "execute", lambda row: executed.append(row))
    assert worker.once() is False
    with service._db() as db:
        assert dict(service._get(db, submitted["id"])) == original
    gate.operate(gate_path, "resume")
    assert worker.once() is True
    assert [row["id"] for row in executed] == [submitted["id"]]
    assert executed[0]["snapshot_sha256"] == original["snapshot_sha256"]
    assert (service.runs_dir / submitted["id"] / "snapshot.json").read_bytes() == snapshot
    assert service.revision == revision and service.config_path.read_bytes() == config


def test_unconfigured_worker_retains_legacy_claim_behavior(service, monkeypatch):
    user, _ = principal(service)
    submitted = submit(service, user)
    worker = control_worker.Worker(service)
    executed = []
    monkeypatch.setattr(worker, "execute", lambda row: executed.append(row["id"]))
    assert worker.claim_gate is None and worker.once()
    assert executed == [submitted["id"]]


@pytest.mark.parametrize("mutation", ["missing-directory", "missing-lock", "lock-symlink", "lock-hardlink",
    "lock-writable", "directory-writable", "marker-symlink", "marker-contents", "marker-writable",
    "lock-inode", "directory-inode", "unsafe-ancestor", "lock-fifo", "marker-fifo", "wrong-owner"])
def test_missing_or_unsafe_configured_gate_blocks_new_claims(gate_path, mutation, monkeypatch):
    gate.operate(gate_path, "resume")
    barrier = gate.ClaimGate(gate_path)
    with barrier.claim_window() as allowed:
        assert allowed
    lock = gate_path / "claims.lock"
    if mutation == "missing-directory": gate_path.rename(gate_path.with_name("old-gate"))
    elif mutation == "missing-lock": lock.unlink()
    elif mutation == "lock-symlink":
        target = gate_path / "old-lock"
        lock.rename(target); lock.symlink_to(target)
    elif mutation == "lock-hardlink": os.link(lock, gate_path / "other-lock")
    elif mutation == "lock-writable": lock.chmod(0o644)
    elif mutation == "directory-writable": gate_path.chmod(0o775)
    elif mutation == "marker-symlink": (gate_path / "paused").symlink_to(lock)
    elif mutation == "marker-contents":
        (gate_path / "paused").write_bytes(b"x" * len(gate._PAUSED)); (gate_path / "paused").chmod(0o444)
    elif mutation == "marker-writable":
        gate.operate(gate_path, "pause"); (gate_path / "paused").chmod(0o644)
    elif mutation == "lock-inode":
        lock.rename(gate_path / "old-lock"); lock.touch(mode=0o444)
    elif mutation == "directory-inode":
        gate_path.rename(gate_path.with_name("old-gate"))
        gate.operate(gate_path, "initialize"); gate.operate(gate_path, "resume")
    elif mutation == "unsafe-ancestor": gate_path.parent.chmod(0o777)
    elif mutation == "lock-fifo": lock.unlink(); os.mkfifo(lock, 0o444)
    elif mutation == "marker-fifo": os.mkfifo(gate_path / "paused", 0o444)
    elif mutation == "wrong-owner": monkeypatch.setattr(gate, "_ROOT_UID", os.getuid() + 1)
    with barrier.claim_window() as allowed:
        assert not allowed


def test_symlink_ancestor_and_invalid_marker_fail_closed(gate_path):
    alias = gate_path.parent / "alias"
    alias.symlink_to(gate_path, target_is_directory=True)
    with gate.ClaimGate(alias).claim_window() as allowed:
        assert not allowed
    marker = gate_path / "paused"
    marker.chmod(0o644)
    for action in ("pause", "resume", "status"):
        with pytest.raises(ControlError):
            gate.operate(gate_path, action)


def test_preexisting_claim_continues_heartbeats_and_cleanup_after_pause(service, gate_path, monkeypatch):
    user, _ = principal(service)
    first = submit(service, user)
    second = submit(service, user)
    gate.operate(gate_path, "resume")
    worker = control_worker.Worker(service, claim_gate=gate_path)
    group = FakeGroup()
    group.path = Path("/sys/fs/cgroup/arena-fixture/arena-control-" + first["id"])
    monkeypatch.setattr(control_worker, "RunCgroup", lambda *args: group)
    heartbeat = service.heartbeat
    calls = []
    def observed_heartbeat(run_id, worker_id):
        calls.append((run_id, gate.operate(gate_path, "status")["paused"]))
        return heartbeat(run_id, worker_id)
    monkeypatch.setattr(service, "heartbeat", observed_heartbeat)
    class Process:
        pid = 12345
        def __init__(self, *args, **kwargs):
            self.stdin = io.BytesIO()
            self.polls = 0
            # Called after the claim's SH window. EX pause must not wait for
            # this engine process or its upcoming heartbeat to finish.
            assert gate.operate(gate_path, "pause", timeout=0.2)["paused"]
        def poll(self):
            self.polls += 1
            return None if self.polls == 1 else 0
        def wait(self, timeout): return 0
    monkeypatch.setattr(control_worker.subprocess, "Popen", Process)
    monkeypatch.setattr(control_worker, "_pid_identity", lambda _: "inert-pid")
    monkeypatch.setattr(control_worker, "_completed_result", lambda _: ("completed", None, 0))
    monkeypatch.setattr(control_worker.os, "killpg", lambda *_: pytest.fail("Drain must not signal active work"))
    assert worker.once()
    assert not worker.stopping.is_set() and not group.killed and group.closed
    assert calls == [(first["id"], False), (first["id"], True)]
    assert service.detail(user, first["id"])["run"]["state"] == "completed"
    assert service.detail(user, second["id"])["run"]["state"] == "queued"
    assert worker.once() is False


def test_cli_gate_does_not_construct_control_service(gate_path, monkeypatch, capsys):
    monkeypatch.setattr(control_cli, "ControlService", lambda *_: pytest.fail("Gate command must not touch queue"))
    assert control_cli.main(["claim-gate", "--path", str(gate_path), "--action", "status"]) == 0
    assert '"paused":true' in capsys.readouterr().out.replace(" ", "")


@pytest.mark.parametrize("exception", [KeyboardInterrupt, RuntimeError])
def test_acquisition_exception_closes_descriptors_and_releases_shared_lock(gate_path, monkeypatch, exception):
    gate.operate(gate_path, "resume")
    barrier = gate.ClaimGate(gate_path)
    descriptors = []
    def interrupted(path, directory, lock):
        descriptors.extend((directory, lock))
        raise exception("Injected after successful flock acquisition")
    with monkeypatch.context() as patch:
        patch.setattr(gate, "_recheck", interrupted)
        with pytest.raises(exception):
            with barrier.claim_window():
                pytest.fail("Acquisition must not reach the claim body")
    assert len(descriptors) == 2
    for descriptor in descriptors:
        with pytest.raises(OSError):
            os.fstat(descriptor)
    assert gate.operate(gate_path, "pause", timeout=0.1)["paused"]
