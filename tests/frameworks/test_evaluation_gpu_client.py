"""Structured GPU admission without a daemon, model, or candidate execution."""
import http.client
import json
from pathlib import Path
import socketserver
import threading
import tempfile
import time

import pytest

from arena.frameworks import evaluation_gpu_client as client

NAME = "arena-eval-" + "a" * 32
IDENT = "d" * 64


class Clock:
    def __init__(self): self.now, self.sleeps = 0.0, []
    def monotonic(self): return self.now
    def sleep(self, duration):
        assert duration >= 0
        self.sleeps.append(duration)
        self.now += duration


@pytest.fixture
def clock(monkeypatch):
    value = Clock()
    monkeypatch.setattr(client, "time", value)
    return value


def config():
    return {"task_id": client.TASK_IDS[0], "timeout_seconds": 600,
            "execution": {"kind": "docker", "image": client.IMAGE, "python": "python",
                          "resource_profile": client.PROFILE, "require_control_cgroup": True}}


def test_exact_profile_body_has_no_caller_devices_or_model_credentials():
    value = config()
    context = {"run_id": "b" * 32, "cgroup_parent": "/arena-workers/arena-control-" + "b" * 32}
    body = client.create_body(value, Path("/tasks"), Path("/input"), Path("/results"), context)
    assert body["Image"] == client.IMAGE and body["Labels"]["arena.evaluation-profile"] == client.PROFILE
    assert body["HostConfig"]["NanoCpus"] == 2_000_000_000
    assert body["HostConfig"]["Memory"] == body["HostConfig"]["MemorySwap"] == 16 * 1024 ** 3
    assert body["HostConfig"]["PidsLimit"] == 256
    assert "Devices" not in body["HostConfig"] and "DeviceRequests" not in body["HostConfig"]
    assert len(body["HostConfig"]["Mounts"]) == 3 and len(body["Env"]) == 2
    assert body["Cmd"][5] == value["task_id"] and body["Cmd"][11] == "600"


@pytest.mark.parametrize("field,value", [("image", "sha256:" + "f" * 64), ("kind", "local_trusted"),
    ("python", "sh"), ("require_control_cgroup", False), ("require_control_cgroup", 1),
    ("task_id", "other"), ("timeout_seconds", 601), ("timeout_seconds", True)])
def test_profile_scope_cannot_be_expanded(field, value):
    selected = config()
    if field in {"task_id", "timeout_seconds"}: selected[field] = value
    else: selected["execution"][field] = value
    with pytest.raises(ValueError): client.resources(selected)


def test_busy_busy_then_one_success_uses_identical_create_and_one_deadline(clock, monkeypatch):
    replies = [(503, client.BUSY_RESPONSE), (503, client.BUSY_RESPONSE), (201, {"Id": IDENT})]
    calls = []
    def request(path, name, raw, timeout):
        calls.append((path, name, raw, timeout))
        return replies.pop(0)
    monkeypatch.setattr(client, "_request", request)
    stats = {}
    assert client.create_when_available({"Image": client.IMAGE}, NAME,
        {"DOCKER_HOST": client.DOCKER_HOST}, 10, stats) == IDENT
    assert [call[3] for call in calls] == [10, 9, 8]
    assert len({call[2] for call in calls}) == 1 and clock.sleeps == [1, 1]
    assert stats == {"create_requests": 3, "busy_responses": 2, "wait_seconds": 2.0}


def test_capacity_deadline_never_restarts_timeout_or_performs_late_create(clock, monkeypatch):
    calls = []
    def request(path, name, raw, timeout):
        calls.append(timeout)
        return 503, client.BUSY_RESPONSE
    monkeypatch.setattr(client, "_request", request)
    stats = {}
    with pytest.raises(client.CapacityUnavailable):
        client.create_when_available({}, NAME, {"DOCKER_HOST": client.DOCKER_HOST}, 2.25, stats)
    assert calls == [2.25, 1.25, 0.25] and clock.sleeps == [1, 1, 0.25]
    assert stats == {"create_requests": 3, "busy_responses": 3, "wait_seconds": 2.25}


@pytest.mark.parametrize("reply", [
    (503, {"message": "upstream unavailable"}), (500, client.BUSY_RESPONSE),
    (403, client.BUSY_RESPONSE), (200, client.BUSY_RESPONSE),
    (503, {**client.BUSY_RESPONSE, "extra": True}), (503, {"code": "arena_gpu_capacity_busy"}),
    (201, {"Id": "invalid"}), (201, {"Id": IDENT, "unknown": True}),
    OSError("transport outcome unknown"), http.client.IncompleteRead(b"partial"),
])
def test_only_exact_typed_precreate_capacity_can_repeat(clock, monkeypatch, reply):
    calls = []
    def request(*args):
        calls.append(args)
        if isinstance(reply, Exception): raise reply
        return reply
    monkeypatch.setattr(client, "_request", request)
    with pytest.raises((ValueError, OSError, http.client.HTTPException)):
        client.create_when_available({}, NAME, {"DOCKER_HOST": client.DOCKER_HOST}, 10, {})
    assert len(calls) == 1 and clock.sleeps == []


@pytest.mark.parametrize("raw", [b'{"code":"first","code":"arena_gpu_capacity_busy"}',
    b'{"x":NaN}', b'[]', b'invalid'])
def test_response_parser_rejects_ambiguous_json(raw):
    with pytest.raises(ValueError): client._json(raw)


def test_slow_response_body_cannot_extend_the_original_http_deadline():
    # Headers arrive immediately; a read timeout alone would restart per packet.
    temporary = tempfile.TemporaryDirectory(prefix="gpu-http-", dir="/tmp")
    socket_path = str(Path(temporary.name) / "proxy.sock")
    ended = threading.Event()
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            self.request.recv(65536)
            try:
                self.request.sendall(b"HTTP/1.1 503 Busy\r\nContent-Length: 100\r\n\r\n")
                while not ended.wait(0.02): self.request.sendall(b" ")
            except OSError:
                pass
    server = socketserver.UnixStreamServer(socket_path, Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    started = time.monotonic()
    try:
        with pytest.raises((ValueError, OSError, http.client.HTTPException)):
            client._request(socket_path, NAME, b"{}", 0.15)
        assert time.monotonic() - started < 0.8
    finally:
        ended.set(); server.shutdown(); server.server_close(); thread.join(); temporary.cleanup()


@pytest.mark.parametrize("framing", ["truncated", "missing", "duplicate", "chunked", "oversized"])
def test_even_exact_busy_json_is_not_accepted_from_incomplete_or_ambiguous_http(framing):
    raw = json.dumps(client.BUSY_RESPONSE).encode()
    headers = {"truncated": f"Content-Length: {len(raw) + 10}\r\n", "missing": "",
        "duplicate": f"Content-Length: {len(raw)}\r\nContent-Length: {len(raw)}\r\n",
        "chunked": f"Content-Length: {len(raw)}\r\nTransfer-Encoding: chunked\r\n",
        "oversized": f"Content-Length: {client.MAX_RESPONSE + 1}\r\n"}[framing]
    with tempfile.TemporaryDirectory(prefix="gpu-frame-", dir="/tmp") as temporary:
        socket_path = str(Path(temporary) / "proxy.sock")
        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                while self.rfile.readline() != b"\r\n":
                    pass
                assert self.rfile.read(2) == b"{}"
                self.request.sendall(b"HTTP/1.1 503 Busy\r\n" + headers.encode() + b"\r\n" + raw)
        server = socketserver.UnixStreamServer(socket_path, Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with pytest.raises((ValueError, http.client.HTTPException)):
                client._request(socket_path, NAME, b"{}", 1)
        finally:
            server.shutdown(); server.server_close(); thread.join()
