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
from arena import dgm_execution, dgm_policy


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


@pytest.fixture
def setup(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    state = root / "state"; state.mkdir()
    runs = root / "runs"; runs.mkdir()
    source = root / "source"; source.mkdir()
    sockets = tempfile.TemporaryDirectory(prefix="dgm-", dir="/tmp")
    config = dp.Config(Path(sockets.name) / "proxy.sock", Path(sockets.name) / "docker.sock",
                       state, runs, root / "queue.sqlite", source, root / "key",
                       ({"alias": "dgm:latest", "reference": IMAGE, "image_id": IMAGE_ID, "parent": None, "runnable": True},),
                       ("gpt-5.6-sol",), NETWORK, worker_uid=os.getuid(), worker_gid=os.getgid())
    original_read = dp.read_regular
    monkeypatch.setattr(dgm_policy, "read_regular", lambda fd, name, limit, owner=None: original_read(fd, name, limit, os.getuid()))
    monkeypatch.setattr(dgm_execution, "read_regular", lambda fd, name, limit, owner=None: original_read(fd, name, limit, os.getuid()))
    yield config
    sockets.cleanup()


class FakeDocker:
    def __init__(self, proxy):
        self.proxy = proxy; self.calls = []; self.container = None; self.exec_running = False
        self.image = {"Id": IMAGE_ID, "RepoDigests": [IMAGE], "RepoTags": ["dgm:latest"],
                      "Created": "2026-09-21T00:00:00Z", "Os": "linux", "Architecture": "amd64",
                      "Config": {"Entrypoint": [dp.BOOTSTRAP], "Cmd": ["tail", "-f", "/dev/null"],
                                 "Labels": {"io.arena.dgm.contract": "dgm-prebuilt-v1", "org.opencontainers.image.revision": dp.PIN}}}
        self.tar = archive([("report.md", b"native evidence")])

    def request(self, method, path, body=None, **kwargs):
        self.calls.append((method, path, body))
        if path.startswith("/v1.45"): path = path[6:]
        if path.startswith("/images/") and path.endswith("/json"): return dp.result(self.image)
        if path == "/images/json?all=1":
            return dp.result([{"Id": IMAGE_ID, "RepoTags": ["dgm:latest", "private/unrelated:latest"], "Created": 1, "Size": 123},
                              {"Id": "sha256:" + "0" * 64, "RepoTags": ["foreign:latest"]}])
        if path == "/info": return dp.result({"CgroupDriver": "cgroupfs", "CgroupVersion": "2"})
        if path.startswith("/containers/create"):
            self.container = json.loads(body)
            self.container["Labels"] = {**self.image["Config"]["Labels"], **self.container["Labels"]}
            return dp.result({"Id": ID, "Warnings": []}, 201)
        if path.endswith("/exec"):
            return dp.result({"Id": EXEC}, 201)
        if path == "/exec/" + EXEC + "/json":
            return dp.result({"ID": EXEC, "Running": False, "ExitCode": 0, "ContainerID": ID, "Pid": 123})
        if path == "/exec/" + EXEC + "/start": return 200, {}, b""
        if path.endswith("/start"): return 204, {}, b""
        if path.endswith("/json") and path.startswith("/containers/"):
            if self.container is None: return dp.result({"message": "No such container"}, 404)
            return dp.result({"Id": ID, "Name": "/real-container-name", "Image": IMAGE_ID, "Config": self.container,
                              "State": {"Pid": 1234, "Running": True},
                              "NetworkSettings": {"Networks": {"private": {"NetworkID": NETWORK, "IPAddress": "172.30.88.2"}}}})
        if method == "DELETE": self.container = None; return 204, {}, b""
        if "/archive?" in path:
            if method == "PUT": return 200, {}, b""
            return 200, {"Content-Type": "application/x-tar", "X-Docker-Container-Path-Stat": base64.b64encode(dp.encoded({"name": "report.md", "size": 15, "mode": 420, "linkTarget": ""})).decode()}, self.tar
        raise AssertionError((method, path))


def create(config):
    proxy = dp.Proxy(config); proxy.gateway_key = KEY
    fake = FakeDocker(proxy); proxy.request = fake.request
    response = proxy.dispatch("POST", "/v1.45/containers/create?name=" + NAME, dp.encoded(SDK_CREATE), RUN, ADMITTED)
    assert response[0] == 201
    return proxy, fake, next(iter(proxy.records.values()))


def archive(entries, *, kind=tarfile.REGTYPE, linkname=""):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:") as stream:
        for name, raw in entries:
            info = tarfile.TarInfo(name); info.type = kind; info.linkname = linkname
            info.size = len(raw) if kind == tarfile.REGTYPE else 0
            stream.addfile(info, io.BytesIO(raw) if info.size else None)
    return output.getvalue()


def seed_admission(config):
    directory = config.runs_root / RUN; directory.mkdir()
    snapshot = {"cgroup_root": "/sys/fs/cgroup/arena-workers", "template": {
        "framework": "dgm", "model": ADMITTED["model"], "resources": {"cpus": 2, "memory_mb": 8192, "pids": 512},
        "spec": {"framework": "dgm", "source_dir": str(config.source_path), "output_dir": "{output_dir}",
                 "timeout_seconds": 300, "request": {"benchmark": "polyglot"}}}}
    raw = dp.encoded(snapshot); (directory / "snapshot.json").write_bytes(raw)
    with sqlite3.connect(config.queue_database) as db:
        db.execute("CREATE TABLE runs(id TEXT,state TEXT,held INTEGER,cancel_requested INTEGER,snapshot_sha256 TEXT,model TEXT,timeout_seconds INTEGER,cpus INTEGER,memory_mb INTEGER,pids INTEGER)")
        db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?)", (RUN, "running", 1, 0, hashlib.sha256(raw).hexdigest(), ADMITTED["model"], 300, 2, 8192, 512))
    return snapshot
