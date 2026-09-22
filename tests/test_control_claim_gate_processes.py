"""Real cross-process flock barriers; no containers or research execution."""
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile

import pytest

from arena import control_claim_gate as gate


@pytest.fixture
def gate_path(monkeypatch):
    monkeypatch.setattr(gate, "_ROOT_UID", os.getuid())
    with tempfile.TemporaryDirectory(prefix=".arena-gate-process-", dir=Path.home().resolve()) as directory:
        path = Path(directory) / "gate"
        gate.operate(path, "initialize")
        gate.operate(path, "resume")
        yield path


def child(path, source):
    bootstrap = "import os,sys,json\nfrom arena import control_claim_gate as gate\ngate._ROOT_UID=os.getuid()\npath=sys.argv[1]\n"
    return subprocess.Popen([sys.executable, "-c", bootstrap + source, str(path)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")})


def line(process):
    assert select.select([process.stdout], [], [], 5)[0], "Child did not reach its barrier"
    return process.stdout.readline().strip()


def close(process):
    if process.poll() is None:
        process.kill()
    process.communicate(timeout=5)


def test_pause_acknowledges_only_after_existing_claim_window_closes(gate_path):
    holder = child(gate_path, """
with gate.ClaimGate(path).claim_window() as allowed:
    print(json.dumps({'allowed':allowed}),flush=True)
    sys.stdin.readline()
print('released',flush=True)
""")
    operator = None
    try:
        assert json.loads(line(holder))["allowed"]
        operator = child(gate_path, """
print('attempting',flush=True)
print(json.dumps(gate.operate(path,'pause',timeout=5)),flush=True)
""")
        assert line(operator) == "attempting"
        assert not select.select([operator.stdout], [], [], 0.15)[0]
        assert not (gate_path / "paused").exists()
        holder.stdin.write("release\n"); holder.stdin.flush()
        assert line(holder) == "released"
        assert json.loads(line(operator))["paused"]
        assert holder.wait(timeout=5) == operator.wait(timeout=5) == 0
        # Future independent worker processes see the acknowledged pause.
        observer = child(gate_path, """
with gate.ClaimGate(path).claim_window() as allowed: print(json.dumps(allowed),flush=True)
""")
        try:
            assert json.loads(line(observer)) is False
            assert observer.wait(timeout=5) == 0
        finally: close(observer)
    finally:
        close(holder)
        if operator is not None: close(operator)


def test_exclusive_operator_barrier_blocks_claim_without_waiting_for_release(gate_path):
    holder = child(gate_path, """
import fcntl
fd=os.open(os.path.join(path,'claims.lock'),os.O_RDONLY)
fcntl.flock(fd,fcntl.LOCK_EX)
print('exclusive',flush=True)
sys.stdin.readline()
os.close(fd)
""")
    try:
        assert line(holder) == "exclusive"
        with gate.ClaimGate(gate_path).claim_window() as allowed:
            assert not allowed
        with pytest.raises(gate.ControlError, match="did not become available"):
            gate.operate(gate_path, "pause", timeout=0.05)
        assert not (gate_path / "paused").exists()
        holder.stdin.write("release\n"); holder.stdin.flush()
        assert holder.wait(timeout=5) == 0
        with gate.ClaimGate(gate_path).claim_window() as allowed:
            assert allowed
    finally: close(holder)


def test_closing_one_claim_window_does_not_unlock_another(gate_path):
    barrier = gate.ClaimGate(gate_path)
    with barrier.claim_window() as outer:
        assert outer
        with barrier.claim_window() as inner:
            assert inner
        operator = child(gate_path, """
try:
    gate.operate(path,'pause',timeout=0.1)
except gate.ControlError:
    print('barrier-still-held',flush=True)
else:
    raise RuntimeError('An inner window unlocked another claim')
""")
        try:
            assert line(operator) == "barrier-still-held"
            assert operator.wait(timeout=5) == 0
        finally: close(operator)
    assert gate.operate(gate_path, "pause")["paused"]
