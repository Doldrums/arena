import copy
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import struct
import socket
import tempfile
import threading
import time
from dataclasses import replace

import pytest

from arena import engine_broker as eb
from arena import engine_execution, engine_policy


RUN = "a" * 32
CONTAINER = "b" * 64


@pytest.fixture
def engine(release_fixture, tmp_path, monkeypatch):
    root = tmp_path.resolve()
    paths = {name: root / name for name in ("approvals", "runs", "staging", "registrations", "receipts", "canonical", "configs", "tasks")}
    for path in paths.values(): path.mkdir(mode=0o700)
    key = root / "gateway.key"; secret = "fixture-scoped-key-" + "x" * 64
    key.write_text(secret); key.chmod(0o600)
    fixture = release_fixture
    raw_manifest = fixture["path"].read_bytes()
    (paths["approvals"] / (fixture["digest"] + ".json")).write_bytes(raw_manifest)
    deployment = paths["configs"] / "deployment.json"; deployment.write_bytes(raw_manifest)
    native = paths["configs"] / "native.json"
    native.write_text(json.dumps({"llm": {"models": ["fixture-model"], "api_base": "http://127.0.0.1:8789/v1",
                                          "api_key_env": "OPENAI_API_KEY"}, "embed_grid": True,
                                  "parallel_search": {"enabled": True, "workers": 1}}))
    tasks = paths["tasks"] / "native"; tasks.mkdir()
    (tasks / "initial_program.py").write_text("raise RuntimeError('never import fixture')\n")
    request = {"python": "/approved/python", "release": fixture["reference"], "deployment": str(deployment),
               "config": str(native), "tasks_root": str(tasks), "budget": 2, "seed": 0}
    template = {"framework": "sciel-release", "model": "fixture-model",
                "resources": {"cpus": 2, "memory_mb": 4096, "pids": 256},
                "spec": {"framework": "sciel-release", "source_dir": str(fixture["source"]),
                         "output_dir": "{output_dir}", "timeout_seconds": 60, "request": request}}
    snapshot = {"template": template, "cgroup_root": "/sys/fs/cgroup/arena-workers"}
    run = paths["runs"] / RUN; (run / "artifacts/.arena").mkdir(parents=True)
    snapshot_raw = json.dumps(snapshot).encode(); (run / "snapshot.json").write_bytes(snapshot_raw)
    database = root / "queue.sqlite"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE runs(id TEXT,state TEXT,held INT,cancel_requested INT,snapshot_sha256 TEXT,model TEXT,timeout_seconds INT)")
        db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?)", (RUN, "running", 1, 0, hashlib.sha256(snapshot_raw).hexdigest(), "fixture-model", 60))
    config = eb.Config(Path(fixture["manifest"]["broker"]["socket"]), root / "docker.sock",
                       paths["approvals"], paths["runs"], database, paths["staging"], paths["registrations"],
                       paths["receipts"], paths["canonical"], key, (paths["configs"],), (paths["tasks"],),
                       ("fixture-model",), worker_uid=os.getuid(), worker_gid=os.getgid())
    # Root identity is a Linux integration condition; unit fixtures are owned by
    # the current account. Keep bounded no-follow reads in these tests.
    def root_file(path, maximum=eb.MAX_JSON):
        fd = eb.directory_fd(path.parent)
        try: return eb.read_regular(fd, path.name, maximum, os.getuid())
        finally: os.close(fd)
    monkeypatch.setattr(engine_policy, "root_file", root_file)
    monkeypatch.setattr(engine_execution, "root_file", root_file)
    monkeypatch.setattr(engine_execution.os, "chown", lambda *a: None)
    monkeypatch.setattr(engine_execution.os, "fchown", lambda *a: None)
    actual_rmtree = engine_execution.shutil.rmtree
    def privileged_rmtree(path, *args, **kwargs):
        if Path(path).is_relative_to(paths["staging"]):
            for base, dirs, files in os.walk(path, followlinks=False):
                Path(base).chmod(0o700)
        return actual_rmtree(path, *args, **kwargs)
    monkeypatch.setattr(engine_execution.shutil, "rmtree", privileged_rmtree)
    broker = eb.Broker(config)
    calls = []
    def docker(method, path, body=None, timeout=20):
        calls.append((method, path, copy.deepcopy(body)))
        if path.startswith("/images/"): return 200, copy.deepcopy(fixture["inspection"][0])
        if "/create?" in path: return 201, {"Id": CONTAINER}
        if path.endswith("/start"):
            output = paths["staging"] / RUN / "artifacts/native"; output.mkdir()
            (output / "sciel_events.jsonl").write_text('{"event":"inert-fixture"}\n')
            return 204, {}
        if method == "DELETE":
            # Unprivileged fixture cleanup emulates root's DAC override for the
            # intentionally read-only staged task tree.
            stage = paths["staging"] / RUN / "inputs/tasks"
            if stage.exists():
                for base, dirs, files in os.walk(stage): Path(base).chmod(0o700)
            return 204, {}
        if method == "GET" and "/containers/" in path:
            return 200, {"Id": CONTAINER, "Image": fixture["manifest"]["image"]["image_id"],
                         "State": {"Running": False, "ExitCode": 0}}
        return 204, {}
    monkeypatch.setattr(broker, "docker", docker)
    monkeypatch.setattr(broker, "logs", lambda record, emit: emit({"type": "stdout", "text": "fixture diagnostic\n"}))
    return {"broker": broker, "config": config, "paths": paths, "fixture": fixture, "request": request,
            "snapshot": snapshot, "run": run, "digest": fixture["digest"], "calls": calls, "secret": secret}


def test_private_image_run_uses_verified_digest_fixed_mounts_and_authoritative_receipt(engine):
    e = engine; frames = []
    e["broker"].run(RUN, e["digest"], frames.append, lambda: False)
    assert frames[0] == {"type": "started", "run_id": RUN}
    assert frames[-1]["status"] == "completed" and frames[-1]["returncode"] == 0
    create = next(body for method, path, body in e["calls"] if "/create?" in path)
    assert create["Image"] == e["fixture"]["manifest"]["image"]["reference"]
    assert create["Entrypoint"] == ["/opt/venv/bin/python", "-m", "sciel.cli.main"]
    assert create["HostConfig"]["NetworkMode"] == "host" and create["HostConfig"]["CgroupnsMode"] == "private"
    assert create["HostConfig"]["CapDrop"] == ["ALL"] and create["HostConfig"]["ReadonlyRootfs"]
    assert all("/var/run/docker.sock" != m["Source"] for m in create["HostConfig"]["Mounts"])
    assert all(str(e["fixture"]["source"]) != m["Source"] for m in create["HostConfig"]["Mounts"])
    assert (e["run"] / "artifacts/native/sciel_events.jsonl").is_file()
    receipt = json.loads((e["paths"]["receipts"] / (RUN + ".json")).read_text())
    assert receipt["cleanup_confirmed"] and receipt["container_id"] == CONTAINER
    assert receipt["original_config_sha256"] != receipt["staged_config_sha256"]
    assert e["secret"] not in json.dumps(receipt) + json.dumps(frames)
    assert not list(e["paths"]["staging"].iterdir()) and not list(e["paths"]["registrations"].iterdir())
    assert e["calls"][-1][:2] == ("DELETE", "/containers/" + CONTAINER + "?force=1")
    with pytest.raises(eb.Denied): e["broker"].run(RUN, e["digest"], frames.append, lambda: False)


@pytest.mark.parametrize("field,value", [("state", "queued"), ("held", 0), ("cancel_requested", 1),
                                          ("model", "unapproved-model"), ("snapshot_sha256", "0" * 64)])
def test_queue_state_mismatches_never_reach_docker(engine, field, value):
    e = engine
    with sqlite3.connect(e["config"].queue_database) as db:
        db.execute(f"UPDATE runs SET {field}=?", (value,))
    with pytest.raises(eb.Denied): e["broker"].plan(RUN, e["digest"])
    assert e["calls"] == []


def test_model_mismatch_and_embedded_credentials_fail_before_create(engine):
    e = engine; path = Path(e["request"]["config"])
    native = json.loads(path.read_text()); native["llm"]["models"] = ["another-model"]
    path.write_text(json.dumps(native))
    with pytest.raises(eb.Denied): e["broker"].plan(RUN, e["digest"])
    native["llm"]["models"] = ["fixture-model"]; native["llm"]["api_key"] = "forbidden-value"
    path.write_text(json.dumps(native))
    with pytest.raises(eb.Denied): e["broker"].plan(RUN, e["digest"])
    assert not any(method == "POST" for method, *_ in e["calls"])


def test_worker_manifest_cannot_substitute_for_root_approval(engine):
    e = engine
    approval = e["paths"]["approvals"] / (e["digest"] + ".json")
    approval.write_bytes(approval.read_bytes() + b" ")
    with pytest.raises(eb.Denied): e["broker"].plan(RUN, e["digest"])
    assert e["calls"] == []


def test_actual_daemon_image_must_match_approved_repo_digest(engine, monkeypatch):
    e = engine; inspection = copy.deepcopy(e["fixture"]["inspection"][0]); inspection["RepoDigests"] = []
    monkeypatch.setattr(e["broker"], "docker", lambda *a: (200, inspection))
    with pytest.raises(ValueError): e["broker"].plan(RUN, e["digest"])


def test_nonregular_task_input_never_reaches_engine_create(engine):
    e = engine; task = Path(e["request"]["tasks_root"])
    (task / "escape").symlink_to(e["config"].gateway_key_file)
    frames = []
    e["broker"].run(RUN, e["digest"], frames.append, lambda: False)
    assert not any("/create?" in path for _, path, _ in e["calls"])
    assert frames[-1]["status"] == "failed"
    assert e["secret"] not in json.dumps(frames)


def test_disconnect_prevents_engine_start_and_records_failure(engine):
    e = engine; frames = []
    # Before creation: do not manufacture a container in the cleanup lookup.
    original = e["broker"].docker
    e["broker"].docker = lambda method, path, *a, **kw: (404, {}) if path.startswith("/containers/arena-engine-") else original(method, path, *a, **kw)
    e["broker"].run(RUN, e["digest"], frames.append, lambda: True)
    assert not any(path.endswith("/start") for _, path, _ in e["calls"])
    assert frames[-1]["status"] == "failed"


def test_log_parser_redacts_key_across_native_frames_and_preserves_stderr(engine, monkeypatch):
    e = engine; key = e["secret"]
    def frame(channel, text):
        raw = text.encode(); return bytes([channel, 0, 0, 0]) + struct.pack(">I", len(raw)) + raw
    chunks = [frame(1, "x" * 1200 + key[:17]), frame(1, key[17:] + " tail"), frame(2, "native error\n")]
    class Response(io.BytesIO): status = 200
    class Connection:
        def __init__(self, *a): pass
        def request(self, *a): pass
        def getresponse(self): return Response(b"".join(chunks))
        def close(self): pass
    monkeypatch.setattr(engine_execution, "DockerConnection", Connection)
    frames = []
    eb.Broker.logs(e["broker"], {"key": key, "plan": {"seconds": 10}, "id": CONTAINER}, frames.append)
    text = "".join(f["text"] for f in frames)
    assert key not in text and key[:17] not in text and "[REDACTED]" in text
    assert any(f["type"] == "stderr" and "native error" in f["text"] for f in frames)


def test_failure_during_native_logs_kills_container_without_success_receipt(engine, monkeypatch):
    e = engine
    def fail(record, emit): raise eb.Denied("bounded log failure")
    monkeypatch.setattr(e["broker"], "logs", fail)
    frames = []; e["broker"].run(RUN, e["digest"], frames.append, lambda: False)
    assert frames[-1]["status"] == "failed" and frames[-1]["returncode"] != 0
    receipt = json.loads((e["paths"]["receipts"] / (RUN + ".json")).read_text())
    assert receipt["status"] == "failed" and receipt["cleanup_confirmed"]
    assert any(method == "DELETE" for method, *_ in e["calls"])


def test_large_native_log_frame_is_split_below_driver_bound(engine, monkeypatch):
    e = engine
    payload = ("𝄞\n" * 18000).encode()
    raw = b"\1\0\0\0" + struct.pack(">I", len(payload)) + payload
    class Response(io.BytesIO): status = 200
    class Connection:
        def __init__(self, *a): pass
        def request(self, *a): pass
        def getresponse(self): return Response(raw)
        def close(self): pass
    monkeypatch.setattr(engine_execution, "DockerConnection", Connection)
    frames = []
    eb.Broker.logs(e["broker"], {"key": e["secret"], "plan": {"seconds": 10}, "id": CONTAINER}, frames.append)
    assert "".join(frame["text"] for frame in frames) == payload.decode()
    assert all(len(json.dumps(frame).encode()) + 1 < 65536 for frame in frames)


def test_artifact_symlink_fails_closed_and_cleans_container(engine, monkeypatch):
    e = engine; original = e["broker"].docker
    def docker(method, path, *a, **kw):
        result = original(method, path, *a, **kw)
        if path.endswith("/start"):
            (e["paths"]["staging"] / RUN / "artifacts/native/leak").symlink_to(e["config"].gateway_key_file)
        return result
    monkeypatch.setattr(e["broker"], "docker", docker)
    frames = []; e["broker"].run(RUN, e["digest"], frames.append, lambda: False)
    assert frames[-1]["status"] == "failed"
    assert not (e["run"] / "artifacts/native/leak").exists()
    assert e["secret"] not in json.dumps(frames)
    assert not list(e["paths"]["staging"].iterdir())


def test_actual_container_image_mismatch_never_records_success(engine, monkeypatch):
    e = engine; original = e["broker"].docker
    def docker(method, path, *a, **kw):
        status, value = original(method, path, *a, **kw)
        if method == "GET" and "/containers/" in path: value["Image"] = "sha256:" + "0" * 64
        return status, value
    monkeypatch.setattr(e["broker"], "docker", docker)
    frames = []; e["broker"].run(RUN, e["digest"], frames.append, lambda: False)
    assert frames[-1]["status"] == "failed"
    assert (e["run"] / "artifacts/native/sciel_events.jsonl").exists()


def test_recovery_records_interrupted_attempt_and_refuses_retry(engine):
    e = engine; stage = e["paths"]["staging"] / RUN; stage.mkdir()
    native = stage / "artifacts/native"; native.mkdir(parents=True)
    (native / "sciel_events.jsonl").write_text('{"event":"before-service-crash"}\n')
    canonical = stage / "artifacts/canonical-evaluations" / ("c" * 32); canonical.mkdir(parents=True)
    (canonical / "receipt.json").write_text('{"raw_score":1.0}')
    eb.write_private(stage / "owner.json", {"run_id": RUN, "container_id": CONTAINER, "deployment_sha256": e["digest"]})
    e["broker"].docker = lambda method, path, *a, **kw: (404, {})
    e["broker"].recover()
    receipt = json.loads((e["paths"]["receipts"] / (RUN + ".json")).read_text())
    assert receipt["status"] == "failed" and receipt["error_type"] == "BrokerInterrupted"
    assert receipt["cleanup_confirmed"]
    assert (e["run"] / "artifacts/native/sciel_events.jsonl").exists()
    assert json.loads((e["run"] / "artifacts/canonical-evaluations" / ("c" * 32) / "receipt.json").read_text())["raw_score"] == 1.0
    assert len(receipt["artifact_hashes"]) == 2 and not stage.exists()
    with pytest.raises(eb.Denied): e["broker"].run(RUN, e["digest"], lambda f: None, lambda: False)


def test_real_unix_client_disconnect_retains_completed_canonical_evidence(engine, monkeypatch):
    e = engine; disconnected = threading.Event()
    original = e["broker"].docker
    def docker(method, path, *args, **kwargs):
        result = original(method, path, *args, **kwargs)
        if path.endswith("/start"):
            evidence = e["paths"]["staging"] / RUN / "artifacts/canonical-evaluations" / ("c" * 32)
            evidence.mkdir(); (evidence / "receipt.json").write_text('{"validity":true,"raw_score":1.0}')
        return result
    monkeypatch.setattr(e["broker"], "docker", docker)
    def logs(record, emit):
        assert disconnected.wait(3)
        emit({"type": "stdout", "text": "already evaluated"})
    monkeypatch.setattr(e["broker"], "logs", logs)
    monkeypatch.setattr(eb.Handler, "caller", lambda self: RUN)
    with tempfile.TemporaryDirectory(prefix="eng-", dir="/tmp") as sockets:
        path = Path(sockets) / "broker.sock"
        with eb.Server(replace(e["config"], socket_path=path)) as server:
            server.broker = e["broker"]
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            client = socket.socket(socket.AF_UNIX); client.settimeout(3); client.connect(str(path))
            body = json.dumps({"run_id": RUN, "deployment_sha256": e["digest"]}).encode()
            client.sendall(b"POST /v1/run HTTP/1.1\r\nHost: local\r\nContent-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body)
            received = b""
            while b'"type": "started"' not in received: received += client.recv(4096)
            client.shutdown(socket.SHUT_RDWR); client.close(); disconnected.set()
            receipt = e["paths"]["receipts"] / (RUN + ".json")
            deadline = time.monotonic() + 3
            while not receipt.exists() and time.monotonic() < deadline: time.sleep(0.01)
            server.shutdown(); thread.join(3)
    recorded = json.loads(receipt.read_text())
    assert recorded["status"] in {"failed", "cancelled"} and recorded["cleanup_confirmed"]
    assert recorded["error_type"] in {"BrokenPipeError", "ConnectionResetError"}
    evidence = e["run"] / "artifacts/canonical-evaluations" / ("c" * 32) / "receipt.json"
    assert json.loads(evidence.read_text())["raw_score"] == 1.0
    assert (e["run"] / "artifacts/native/sciel_events.jsonl").exists()
    assert "canonical-evaluations/" + "c" * 32 + "/receipt.json" in recorded["artifact_hashes"]
    assert not list(e["paths"]["staging"].iterdir())
