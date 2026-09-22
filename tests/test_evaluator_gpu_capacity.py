"""Lease contention is infrastructure capacity, never a candidate verdict."""
import json
import subprocess
import threading

import pytest

from arena import evaluator_execution as execution, evaluator_http as http
from arena import evaluator_gpu_leases as leases, evaluator_policy as policy
from evaluator_gpu_helpers import IDENT, NAME, RUN, abandon, lease_root, prepared, setup


def owner(config, body, monkeypatch, *, known=True):
    monkeypatch.setattr(execution.os, "chown", lambda *args: None)
    proxy = execution.Proxy(config)
    proxy.request = lambda *a, **k: (201 if known else 500, {}, json.dumps({"Id": IDENT}).encode())
    proxy.create(body, NAME, RUN, "")
    return proxy


def http_create(server, body, name):
    connection = policy.DockerConnection(server.proxy.config.socket_path)
    try:
        connection.request("POST", "/containers/create?name=" + name,
                           json.dumps(body).encode(), {"Content-Type": "application/json"})
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


@pytest.mark.parametrize("other_proxy", [False, True])
def test_known_lease_contention_returns_typed_503_without_docker_or_evaluation(
        prepared, lease_root, monkeypatch, other_proxy):
    config, body, candidate, output = prepared
    active = owner(config, body, monkeypatch)
    metadata = (lease_root / leases.RECORD_NAME).read_bytes()
    initial_stages = set(config.staging_root.iterdir())
    candidate.joinpath("program.py").write_text("raise AssertionError('must not execute')\n")
    monkeypatch.setattr(http, "peer_run", lambda *a: RUN)
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("No child or model call is allowed"))
    server = http.Server(config)
    if not other_proxy:
        server.proxy = active
    server.proxy.request = lambda *a, **k: pytest.fail("Contention must be reported before any Docker POST")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, response = http_create(server, body, "arena-eval-" + "c" * 32)
        assert status == 503
        assert response == {"code": "arena_gpu_capacity_busy",
                            "message": "GPU capacity is occupied; no evaluator container was created"}
        assert not ({"score", "raw_score", "fitness", "validity", "status"} & response.keys())
        assert not list(output.iterdir()) and set(config.staging_root.iterdir()) == initial_stages
        assert (lease_root / leases.RECORD_NAME).read_bytes() == metadata
        assert NAME in active.records and active.gpu_leases.current is not None
    finally:
        server.shutdown(); server.server_close(); thread.join()
        abandon(active)


@pytest.mark.parametrize("state", ["local-unknown", "remote-unknown", "persisted-known", "invalid-request"])
def test_unknown_ownership_or_invalid_request_is_never_relabelled_as_capacity(
        prepared, lease_root, monkeypatch, state):
    config, body, _, output = prepared
    known = state in {"persisted-known", "invalid-request"}
    active = owner(config, body, monkeypatch, known=known)
    metadata = (lease_root / leases.RECORD_NAME).read_bytes()
    monkeypatch.setattr(http, "peer_run", lambda *a: RUN)
    server = http.Server(config)
    if state == "local-unknown":
        server.proxy = active
    elif state == "persisted-known":
        abandon(active)
    elif state == "invalid-request":
        body["HostConfig"]["Privileged"] = True
    server.proxy.request = lambda *a, **k: pytest.fail("No Docker call is allowed")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, response = http_create(server, body, "arena-eval-" + "c" * 32)
        assert status == 403 and "code" not in response
        assert not ({"score", "raw_score", "fitness", "validity"} & response.keys())
        assert not list(output.iterdir())
        assert (lease_root / leases.RECORD_NAME).read_bytes() == metadata
    finally:
        server.shutdown(); server.server_close(); thread.join()
        if state != "persisted-known":
            abandon(active)


def test_initial_unknown_daemon_reply_is_preserved_without_retry(prepared, lease_root, monkeypatch):
    config, body, *_ = prepared
    monkeypatch.setattr(execution.os, "chown", lambda *args: None)
    monkeypatch.setattr(http, "peer_run", lambda *a: RUN)
    server = http.Server(config)
    calls = []
    def request(method, path, *args, **kwargs):
        calls.append((method, path))
        return 503, {}, b'{"message":"Daemon response is uncertain"}'
    server.proxy.request = request
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, response = http_create(server, body, NAME)
        assert status == 503 and response == {"message": "Daemon response is uncertain"}
        assert calls == [("POST", "/containers/create?name=" + NAME)]
        saved = json.loads((lease_root / leases.RECORD_NAME).read_text())
        assert saved["id"] is None and server.proxy.gpu_leases.current is not None
    finally:
        server.shutdown(); server.server_close(); thread.join()
        abandon(server.proxy)
