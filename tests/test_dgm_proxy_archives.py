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
from arena import dgm_http, dgm_policy


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


@pytest.mark.parametrize("name", ["/etc/shadow", "../escape", "a/../../escape", "a/../file", "a\\..\\escape", "a\nfile", "."])
def test_traversal_archives_are_rejected_in_both_directions(name):
    with pytest.raises(dp.Denied): dp.sanitize_tar(archive([(name, b"bad")]))


@pytest.mark.parametrize("kind", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE])
def test_links_devices_and_fifos_are_not_extractable(kind):
    with pytest.raises(dp.Denied): dp.sanitize_tar(archive([("file", b"")], kind=kind, linkname="../../secret"))


def test_tar_repack_preserves_contents_but_strips_privileged_metadata_and_rejects_collisions():
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w:") as stream:
        item = tarfile.TarInfo("tools/run.sh"); item.size = 5; item.mode = 0o6755; item.uid = 12345
        item.pax_headers = {"SCHILY.xattr.security.capability": "bad"}
        stream.addfile(item, io.BytesIO(b"hello"))
    safe = dp.sanitize_tar(raw.getvalue())
    with tarfile.open(fileobj=io.BytesIO(safe), mode="r:") as stream:
        item = stream.next()
        assert item.uid == 0 and item.mode == 0o755 and not item.pax_headers
        assert stream.extractfile(item).read() == b"hello"
    for entries in ([('file', b'1'), ('file', b'2')], [('dir', b'1'), ('dir/file', b'2')], [('dir/file', b'1'), ('dir', b'2')]):
        with pytest.raises(dp.Denied): dp.sanitize_tar(archive(entries))


def test_upload_download_evidence_uses_fixed_exec_and_actual_stat(setup):
    proxy, fake, record = create(setup)
    calls = []
    def execute(rec, command, **kwargs):
        calls.append((command, kwargs))
        if command[0] == "/usr/bin/stat": return b"15 81a4 1758400000\n"
        return fake.tar if "-cf" in command else b""
    proxy.fixed_exec = execute
    safe = archive([("parent_patch.txt", b"native patch")])
    assert proxy.dispatch("PUT", "/containers/" + ID + "/archive?path=/dgm", safe, RUN, ADMITTED)[0] == 200
    response = proxy.dispatch("GET", "/containers/" + ID + "/archive?path=/dgm/report.md", b"", RUN, ADMITTED)
    assert response[0] == 200 and len(record["transfers"]) == 2
    assert record["transfers"][1]["sha256"] == hashlib.sha256(response[2]).hexdigest()
    info = json.loads(base64.b64decode(response[1]["X-Docker-Container-Path-Stat"]))
    assert info["size"] == 15 and info["mode"] == 0o644 and info["name"] == "report.md"
    assert calls[0][0] == ["/bin/tar", "--no-same-owner", "-xf", "-", "-C", "/dgm"]
    assert calls[0][1]["input_bytes"] == dp.sanitize_tar(safe)
    assert calls[2][0] == ["/bin/tar", "--format=pax", "-cf", "-", "-C", "/dgm", "--", "report.md"]
    assert not any("/archive?" in path for _, path, _ in fake.calls)


@pytest.mark.parametrize("entry", ["../../escape", ".git/config"])
def test_malicious_export_never_reaches_native_extractall(setup, entry):
    proxy, fake, record = create(setup)
    proxy.fixed_exec = lambda rec, command, **kwargs: (b"15 81a4 1758400000\n" if command[0] == "/usr/bin/stat" else archive([(entry, b"bad")]))
    with pytest.raises(dp.Denied): proxy.dispatch("GET", "/containers/" + ID + "/archive?path=/dgm/report.md", b"", RUN, ADMITTED)
    assert record["transfers"][0]["status"] == "failed" and record["state"] == "removed"
    saved = json.loads((setup.state_root / (record["record_id"] + ".json")).read_text())
    assert saved["state"] == "removed" and saved["transfers"][0]["status"] == "failed"
    assert record["record_id"] not in proxy.records and not proxy.execs
    assert fake.container is None


@pytest.mark.parametrize("mode", ["a1ff", "21a4"])
def test_export_stat_symlink_or_device_is_not_faked_as_regular_file(setup, mode):
    proxy, fake, record = create(setup)
    proxy.fixed_exec = lambda *args, **kwargs: f"15 {mode} 1758400000\n".encode()
    with pytest.raises(dp.Denied): proxy.archive(record, "archive_get", "/dgm/report.md", b"")
    assert fake.container is None


def test_archive_bounds(monkeypatch):
    monkeypatch.setattr(dgm_policy, "MAX_ENTRIES", 1)
    with pytest.raises(dp.Denied): dp.sanitize_tar(archive([("a", b"a"), ("b", b"b")]))
    monkeypatch.setattr(dgm_policy, "MAX_EXPANDED", 1)
    with pytest.raises(dp.Denied): dp.sanitize_tar(archive([("a", b"aa")]))
    monkeypatch.setattr(dgm_policy, "MAX_TAR", 100)
    with pytest.raises(dp.Denied): dp.sanitize_tar(archive([("a", b"a")]))


@pytest.mark.parametrize("failure", [None, "exit", "partial", "overflow", "timeout"])
def test_fixed_archive_exec_transports_stdin_demultiplexes_and_requires_real_success(setup, failure):
    proxy, fake, record = create(setup)
    upload = archive([("parent_patch.txt", b"native patch")])
    received = []
    class DockerHandler(socketserver.StreamRequestHandler):
        def handle(self):
            assert self.rfile.readline().startswith(b"POST /exec/" + EXEC.encode() + b"/start ")
            length = 0
            while (line := self.rfile.readline()) != b"\r\n":
                if line.lower().startswith(b"content-length:"): length = int(line.split(b":")[1])
            assert json.loads(self.rfile.read(length)) == {"Detach": False, "Tty": False}
            self.wfile.write(b"HTTP/1.1 101 UPGRADED\r\nConnection: Upgrade\r\nUpgrade: tcp\r\n\r\n"); self.wfile.flush()
            received.append(self.rfile.read())
            if failure == "timeout": time.sleep(0.3); return
            payload = b"native export" if failure != "overflow" else b"x" * 33
            frame = struct.pack(">BxxxI", 2, 7) + b"warning" + struct.pack(">BxxxI", 1, len(payload)) + payload
            if failure == "partial": frame = frame[:-1]
            try:
                for n in range(0, len(frame), 3): self.wfile.write(frame[n:n + 3]); self.wfile.flush()
            except BrokenPipeError: pass
    actual = fake.request
    def request(method, path, *args, **kwargs):
        if failure == "exit" and path == "/exec/" + EXEC + "/json": return dp.result({"Running": False, "ExitCode": 2})
        return actual(method, path, *args, **kwargs)
    proxy.request = request
    daemon = socketserver.UnixStreamServer(str(setup.docker_socket), DockerHandler)
    threading.Thread(target=daemon.serve_forever, daemon=True).start()
    try:
        command = ["/bin/tar", "--no-same-owner", "-xf", "-", "-C", "/dgm"]
        if failure:
            with pytest.raises(dp.Denied): proxy.fixed_exec(record, command, input_bytes=upload, maximum=32, seconds=0.1 if failure == "timeout" else 3)
            assert fake.container is None and record["state"] == "removed"
        else:
            assert proxy.fixed_exec(record, command, input_bytes=upload, maximum=32) == b"native export"
            assert fake.container is not None
        assert received == [upload]
        body = next(json.loads(raw) for method, path, raw in fake.calls if path == "/containers/" + ID + "/exec")
        assert body["AttachStdin"] is True and body["Cmd"] == command and not body["Privileged"]
        assert EXEC not in proxy.execs
    finally: daemon.shutdown(); daemon.server_close()


def test_archive_client_disconnect_cancels_quiet_fixed_exec(setup, monkeypatch):
    proxy, fake, record = create(setup)
    started = threading.Event(); release = threading.Event()
    class DockerHandler(socketserver.StreamRequestHandler):
        def handle(self):
            self.rfile.readline(); length = 0
            while (line := self.rfile.readline()) != b"\r\n":
                if line.lower().startswith(b"content-length:"): length = int(line.split(b":")[1])
            self.rfile.read(length)
            self.wfile.write(b"HTTP/1.1 101 UPGRADED\r\nConnection: Upgrade\r\nUpgrade: tcp\r\n\r\n"); self.wfile.flush()
            self.rfile.read(); started.set(); release.wait(4)
    daemon = socketserver.UnixStreamServer(str(setup.docker_socket), DockerHandler)
    threading.Thread(target=daemon.serve_forever, daemon=True).start()
    server = dp.Server(setup); server.proxy = proxy
    monkeypatch.setattr(dgm_http, "peer_run", lambda *a: RUN)
    monkeypatch.setattr(dgm_http, "admission", lambda *a: ADMITTED)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); client.connect(str(setup.socket_path))
        body = archive([("fixture.txt", b"no model calls")])
        client.sendall((f"PUT /containers/{ID}/archive?path=/dgm HTTP/1.1\r\nHost: localhost\r\nContent-Length: {len(body)}\r\n\r\n").encode() + body)
        assert started.wait(3)
        client.close()
        deadline = time.monotonic() + 3
        while fake.container is not None and time.monotonic() < deadline: time.sleep(0.02)
        assert fake.container is None and record["transfers"][0]["status"] == "failed"
    finally:
        release.set(); server.shutdown(); server.server_close(); daemon.shutdown(); daemon.server_close()


def test_concurrent_archive_reservations_do_not_exceed_transfer_budget(setup):
    proxy, fake, record = create(setup)
    record["transfers"] = [{"status": 200}] * 1023
    rendezvous = threading.Barrier(3)
    class GateLock:
        def __init__(self): self.lock = threading.Lock()
        def __enter__(self): rendezvous.wait(timeout=3); self.lock.acquire()
        def __exit__(self, *args): self.lock.release()
    proxy.lock = GateLock()
    proxy.fixed_exec = lambda *args, **kwargs: b""
    results = []
    def put():
        try: results.append(proxy.archive(record, "archive_put", "/dgm", archive([("one.txt", b"one")]))[0])
        except dp.Denied: results.append("denied")
    workers = [threading.Thread(target=put) for _ in range(2)]
    for worker in workers: worker.start()
    rendezvous.wait(timeout=3)
    for worker in workers: worker.join(timeout=3)
    assert sorted(map(str, results)) == ["200", "denied"]
    assert len(record["transfers"]) == 1024
