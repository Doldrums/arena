"""Inert Docker API fixtures: no daemon, containers, models or root required."""
from copy import deepcopy
from dataclasses import replace
import base64
import hashlib
import io
import json
from http.server import ThreadingHTTPServer
import os
from pathlib import Path
import socket
import socketserver
import sqlite3
import struct
import tarfile
import tempfile
import threading
import time
from types import SimpleNamespace

import pytest

from arena import dgm_proxy as dp
from arena import dgm_http


RUN = "a" * 32
OTHER_RUN = "b" * 32
ID = "c" * 64
EXEC = "e" * 64
NETWORK = "f" * 64
IMAGE_ID = "sha256:" + "d" * 64
IMAGE = "127.0.0.1:5000/empira/dgm@sha256:" + "8" * 64
NAME = "dgm-container-20260921_010101_111111"
ADMITTED = {"model": "gpt-5.6-sol", "seconds": 300, "snapshot_sha256": "7" * 64}
KEY = "inert-gateway-key-for-tests"

# Captured from Docker SDK in the prepared DGM environment by replacing only
# its HTTP transport. No SDK request reached a daemon (2026-09-21).
SDK_CREATE = {"Tty": False, "OpenStdin": False, "StdinOnce": False, "AttachStdin": False,
              "AttachStdout": False, "AttachStderr": False, "Image": "dgm:latest", "NetworkDisabled": False}
SDK_EXEC = {"Container": ID, "User": "", "Privileged": False, "Tty": False, "AttachStdin": False,
            "AttachStdout": True, "AttachStderr": True, "Cmd": ["python", "hello.py"], "WorkingDir": "/",
            "Env": ["OPENAI_API_KEY=" + KEY, "ANTHROPIC_API_KEY", "AWS_REGION", "AWS_REGION_NAME", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]}

from _dgm_proxy_helpers import setup, FakeDocker, create, archive, seed_admission


def test_real_unix_upgrade_preserves_native_docker_multiplex_and_exit_inspection(setup, monkeypatch):
    frame = bytes([1, 0, 0, 0]) + struct.pack(">I", 13) + b"native output"
    class DockerHandler(socketserver.StreamRequestHandler):
        def handle(self):
            first = self.rfile.readline(); assert b"/exec/" + EXEC.encode() + b"/start" in first
            length = 0
            while (line := self.rfile.readline()) != b"\r\n":
                if line.lower().startswith(b"content-length:"): length = int(line.split(b":")[1])
            assert json.loads(self.rfile.read(length)) == {"Detach": False, "Tty": False}
            self.wfile.write(b"HTTP/1.1 101 UPGRADED\r\nConnection: Upgrade\r\nUpgrade: tcp\r\n\r\n" + frame)
            self.wfile.flush()
    daemon = socketserver.UnixStreamServer(str(setup.docker_socket), DockerHandler)
    worker = threading.Thread(target=daemon.serve_forever, daemon=True); worker.start()
    server = dp.Server(setup)
    proxy, fake, record = create(setup)
    server.proxy = proxy; proxy.execs[EXEC] = record["record_id"]
    monkeypatch.setattr(dgm_http, "peer_run", lambda *a: RUN)
    monkeypatch.setattr(dgm_http, "admission", lambda *a: ADMITTED)
    serving = threading.Thread(target=server.serve_forever, daemon=True); serving.start()
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); client.settimeout(3); client.connect(str(setup.socket_path))
        body = b'{"Detach":false,"Tty":false}'
        client.sendall((f"POST /exec/{EXEC}/start HTTP/1.1\r\nHost: localhost\r\nContent-Length: {len(body)}\r\n\r\n").encode() + body)
        response = b""
        while chunk := client.recv(65536): response += chunk
        assert response.startswith(b"HTTP/1.1 101") and response.split(b"\r\n\r\n", 1)[1] == frame
        assert fake.container is not None  # ordinary end-of-exec does not cancel the native container
        client.close()
    finally:
        server.shutdown(); server.server_close(); daemon.shutdown(); daemon.server_close()


def test_real_client_disconnect_cancels_quiet_native_exec(setup, monkeypatch):
    release = threading.Event()
    class DockerHandler(socketserver.StreamRequestHandler):
        def handle(self):
            self.rfile.readline(); length = 0
            while (line := self.rfile.readline()) != b"\r\n":
                if line.lower().startswith(b"content-length:"): length = int(line.split(b":")[1])
            self.rfile.read(length)
            self.wfile.write(b"HTTP/1.1 101 UPGRADED\r\nConnection: Upgrade\r\nUpgrade: tcp\r\n\r\n"); self.wfile.flush()
            release.wait(5)
    daemon = socketserver.UnixStreamServer(str(setup.docker_socket), DockerHandler)
    threading.Thread(target=daemon.serve_forever, daemon=True).start()
    server = dp.Server(setup); proxy, fake, record = create(setup); server.proxy = proxy
    proxy.execs[EXEC] = record["record_id"]
    monkeypatch.setattr(dgm_http, "peer_run", lambda *a: RUN)
    monkeypatch.setattr(dgm_http, "admission", lambda *a: ADMITTED)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); client.settimeout(3); client.connect(str(setup.socket_path))
        body = b'{"Detach":false,"Tty":false}'
        client.sendall((f"POST /exec/{EXEC}/start HTTP/1.1\r\nHost: localhost\r\nContent-Length: {len(body)}\r\n\r\n").encode() + body)
        assert b"101" in client.recv(1024)
        client.close()
        deadline = time.monotonic() + 3
        while fake.container is not None and time.monotonic() < deadline: time.sleep(0.02)
        assert fake.container is None and record["state"] == "removed"
    finally:
        release.set(); server.shutdown(); server.server_close(); daemon.shutdown(); daemon.server_close()


def test_bridge_relay_pins_route_model_key_and_upstream_and_keeps_policy_headers(setup, monkeypatch):
    proxy, fake, record = create(setup)
    actual = fake.request
    def inspector(*args, **kwargs):
        status, headers, raw = actual(*args, **kwargs)
        if args[1].endswith("/json") and args[1].startswith("/containers/"):
            data = json.loads(raw); data["NetworkSettings"]["Networks"]["private"]["IPAddress"] = "127.0.0.1"
            return dp.result(data)
        return status, headers, raw
    proxy.request = inspector
    monkeypatch.setattr(dgm_http, "admission", lambda *a: ADMITTED)
    calls = []
    class Response:
        status = 200
        def __init__(self): self.parts = [b'{"output":"native"}', b""]
        def getheader(self, name, default=None): return "application/json"
        def getheaders(self): return [("X-Arena-Compatibility-Policy", "codex-native")]
        def read1(self, size): return self.parts.pop(0)
    class Connection:
        def __init__(self, host, port, **kwargs): assert (host, port) == ("127.0.0.1", 8789)
        def request(self, method, path, **kwargs): calls.append((method, path, kwargs))
        def getresponse(self): return Response()
        def close(self): pass
    monkeypatch.setattr(dgm_http.http.client, "HTTPConnection", Connection)
    server = ThreadingHTTPServer(("127.0.0.1", 0), dp.RelayHandler); server.proxy = proxy
    threading.Thread(target=server.serve_forever, daemon=True).start()
    def request(path, model, key=KEY):
        client = socket.create_connection(server.server_address, timeout=3)
        body = dp.encoded({"model": model, "messages": [{"role": "user", "content": "inert"}]})
        client.sendall((f"POST {path} HTTP/1.1\r\nHost: ignored\r\nAuthorization: Bearer {key}\r\nContent-Length: {len(body)}\r\n\r\n").encode() + body)
        raw = b""
        while part := client.recv(65536): raw += part
        client.close(); return raw
    try:
        assert b"200 OK" in request("/v1/responses", ADMITTED["model"])
        assert len(calls) == 1 and calls[0][2]["headers"]["Authorization"] == "Bearer " + KEY
        assert b"X-Arena-Compatibility-Policy: codex-native" in request("/v1/chat/completions", ADMITTED["model"])
        for path, model, key in [("/v1/responses", "different-model", KEY), ("/admin", ADMITTED["model"], KEY),
                                 ("/v1/responses", ADMITTED["model"], "wrong")]:
            assert b"403" in request(path, model, key)
        assert len(calls) == 2
    finally: server.shutdown(); server.server_close()


def test_quiet_relay_headers_release_connection_before_authentication(monkeypatch):
    monkeypatch.setattr(dgm_http, "REQUEST_TIMEOUT", 0.1)
    server = ThreadingHTTPServer(("127.0.0.1", 0), dp.RelayHandler)
    # No proxy attribute: the timeout must happen while reading the headers,
    # before any authorization/model/Docker inspection can be reached.
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        client = socket.create_connection(server.server_address, timeout=2)
        client.sendall(b"POST /v1/responses HTTP/1.1\r\nHost: unfinished")
        assert client.recv(1024) == b""
        client.close()
    finally: server.shutdown(); server.server_close()
