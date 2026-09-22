"""Canonical receipts remain empty until one admitted GPU evaluation executes."""
import http.client
import io
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from arena.frameworks import evaluation, evaluation_gpu_client as client
from test_evaluation import digest, evaluation_inputs, native_result
from test_evaluation_gpu_client import Clock, IDENT


@pytest.fixture
def gpu_inputs(evaluation_inputs, monkeypatch):
    config, candidate, old_output, catalog = evaluation_inputs
    task = catalog["tasks"][0]
    source = Path(config["tasks_dir"])
    task["id"] = config["task_id"] = client.TASK_IDS[0]
    (source / "suite/fixture-task").rename(source / "suite" / task["id"])
    task["contract_source"]["path"] = f"suite/{task['id']}/problem.json"
    manifest = old_output.parent / "registry/task-library-manifest.json"
    manifest.write_text(json.dumps({"schema": "arena.task-library/1", "files": {
        path.relative_to(source).as_posix(): digest(path) for path in source.rglob("*") if path.is_file()}}))
    catalog["sources"][0]["manifest_sha256"] = digest(manifest)
    config["timeout_seconds"] = 10
    config["execution"] = {"kind": "docker", "python": "python3", "image": client.IMAGE,
        "require_control_cgroup": True, "resource_profile": client.PROFILE}
    run = "b" * 32
    receipts = old_output.parent / "runs" / run / "artifacts/canonical-evaluations"
    output = receipts / ("a" * 32)
    context = {"run_id": run, "cgroup_parent": "/arena-workers/arena-control-" + run,
               "receipts_dir": str(receipts)}
    monkeypatch.setattr(evaluation, "_control_context", lambda: context)
    monkeypatch.setenv("DOCKER_HOST", client.DOCKER_HOST)
    clock = Clock()
    clock.time = lambda: 1700000000 + clock.now
    monkeypatch.setattr(client, "time", clock)
    monkeypatch.setattr(evaluation, "time", clock)
    return config, candidate, output, clock


def fake_clients(inputs, monkeypatch, replies, *, start_error=False, wait_error=False):
    config, candidate, output, clock = inputs
    prepared = evaluation.prepare_evaluation(config, candidate, output)
    creates, commands, waits, stops = [], [], [], []
    def request(path, name, raw, timeout):
        creates.append((path, name, json.loads(raw), timeout))
        reply = replies.pop(0) if len(replies) > 1 else replies[0]
        if isinstance(reply, Exception): raise reply
        return reply
    monkeypatch.setattr(client, "_request", request)
    class Process:
        pid = 99999999
        returncode = None
        def __init__(self, argv, **kwargs):
            commands.append((argv, kwargs))
            assert argv == ["docker", "start", "--attach", IDENT]
            assert "APP_SECRET" not in kwargs["env"]
            if start_error: raise OSError("Start transport failed; never replay")
            self.stdout, self.stderr = io.BytesIO(b"inert fixture"), io.BytesIO()
            (output / "native-output/native.json").write_text(json.dumps(native_result(prepared)))
        def wait(self, timeout=None):
            waits.append(timeout)
            if wait_error: raise subprocess.TimeoutExpired("start", timeout)
            self.returncode = 0
    def run(argv, **kwargs):
        commands.append((argv, kwargs))
        assert argv[:2] in (["docker", "info"], ["docker", "rm"])
        return subprocess.CompletedProcess(argv, 0, b"cgroupfs 2\n", b"")
    monkeypatch.setattr(evaluation, "subprocess", SimpleNamespace(Popen=Process, run=run,
        TimeoutExpired=subprocess.TimeoutExpired, SubprocessError=subprocess.SubprocessError,
        DEVNULL=subprocess.DEVNULL, PIPE=subprocess.PIPE))
    monkeypatch.setattr(evaluation, "_stop", lambda process: stops.append(process.pid))
    return creates, commands, waits, stops


def test_busy_then_success_produces_only_one_measurement_with_remaining_execution_time(gpu_inputs, monkeypatch):
    config, candidate, output, _ = gpu_inputs
    monkeypatch.setenv("APP_SECRET", "never-pass-this")
    replies = [(503, client.BUSY_RESPONSE), (503, client.BUSY_RESPONSE), (201, {"Id": IDENT})]
    creates, commands, waits, _ = fake_clients(gpu_inputs, monkeypatch, replies)
    receipt = evaluation.evaluate(config, candidate, output)
    assert [item[3] for item in creates] == [10, 9, 8]
    assert waits == [8] and len([argv for argv, _ in commands if argv[1] == "start"]) == 1
    assert receipt["status"] == "completed" and receipt["raw_score"] == 4.25
    assert receipt["evaluation_attempts"] == 1 and receipt["retries"] == 0
    assert receipt["capacity_wait"] == {"create_requests": 3, "busy_responses": 2, "wait_seconds": 2.0}
    assert receipt["container_id"] == IDENT
    request = json.loads((output / "request.json").read_text())
    assert request["argv"] == ["docker", "start", "--attach", IDENT]
    assert request["create"] == creates[0][2]
    assert json.loads((output / "receipt.json").read_text()) == receipt


def test_capacity_deadline_persists_no_candidate_verdict_attempt_or_native_result(gpu_inputs, monkeypatch):
    config, candidate, output, clock = gpu_inputs
    config["timeout_seconds"] = 3
    creates, commands, waits, stops = fake_clients(gpu_inputs, monkeypatch, [(503, client.BUSY_RESPONSE)])
    receipt = evaluation.evaluate(config, candidate, output)
    assert len(creates) == 3 and clock.now == 3
    assert [argv[1] for argv, _ in commands] == ["info"] and waits == stops == []
    assert receipt["status"] == "capacity_unavailable" and receipt["evaluation_attempts"] == receipt["retries"] == 0
    assert all(receipt[key] is None for key in ("raw_score", "fitness", "validity"))
    assert not (output / "native-output/native.json").exists() and not (output / "stdout.log").exists()
    assert "container_id" not in receipt and json.loads((output / "receipt.json").read_text()) == receipt


@pytest.mark.parametrize("reply", [(503, {"message": "unknown upstream failure"}),
    OSError("lost create reply"), http.client.IncompleteRead(b"partial"), (201, {"Id": "wrong"})])
def test_unknown_create_outcome_is_not_waited_replayed_or_given_a_result(gpu_inputs, monkeypatch, reply):
    config, candidate, output, clock = gpu_inputs
    creates, commands, waits, stops = fake_clients(gpu_inputs, monkeypatch, [reply])
    receipt = evaluation.evaluate(config, candidate, output)
    assert len(creates) == 1 and clock.sleeps == waits == stops == []
    assert [argv[1] for argv, _ in commands] == ["info"]
    assert receipt["status"] == "error" and receipt["evaluation_attempts"] == 0
    assert all(receipt[key] is None for key in ("raw_score", "fitness", "validity"))


@pytest.mark.parametrize("start_error,wait_error", [(True, False), (False, True)])
def test_failure_after_create_never_repeats_creation_and_still_requests_cleanup(
        gpu_inputs, monkeypatch, start_error, wait_error):
    config, candidate, output, _ = gpu_inputs
    creates, commands, _, _ = fake_clients(gpu_inputs, monkeypatch, [(201, {"Id": IDENT})],
        start_error=start_error, wait_error=wait_error)
    receipt = evaluation.evaluate(config, candidate, output)
    assert len(creates) == 1 and [argv[1] for argv, _ in commands] == ["info", "start", "rm"]
    assert receipt["status"] == ("error" if start_error else "timeout")
    assert receipt["evaluation_attempts"] == (0 if start_error else 1) and receipt["retries"] == 0
    assert receipt["fitness"] is None


def test_deadline_after_created_response_never_starts_container(gpu_inputs, monkeypatch):
    config, candidate, output, clock = gpu_inputs
    creates, commands, waits, _ = fake_clients(gpu_inputs, monkeypatch, [(201, {"Id": IDENT})])
    original = client._request
    def expired(*args):
        reply = original(*args)
        clock.now = config["timeout_seconds"]
        return reply
    monkeypatch.setattr(client, "_request", expired)
    receipt = evaluation.evaluate(config, candidate, output)
    assert len(creates) == 1 and [argv[1] for argv, _ in commands] == ["info", "rm"] and waits == []
    assert receipt["status"] == "timeout" and receipt["evaluation_attempts"] == 0
    assert all(receipt[key] is None for key in ("raw_score", "fitness", "validity"))
