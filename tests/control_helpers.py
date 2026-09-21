"""Inert control-service fixtures shared by queue, worker and log tests."""
import copy
import json
import sys
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from arena import control
from arena.server import DashboardServer


def template(identifier="fixture", *, slots=4):
    return {"id": identifier, "name": "Inert fixture", "framework": "fixture", "profile": "fixture",
            "model": "fixture-model", "status": "ready", "blocked_reason": None,
            "resources": {"cpus": 2, "memory_mb": 1024, "evaluation_slots": slots, "pids": 32},
            "containment": "cgroup-v2", "evaluation_concurrency_verified": True,
            "spec": {"schema": "arena.native-run/1", "framework": "fixture", "source_dir": "/fixture/source",
                     "output_dir": "{output_dir}", "timeout_seconds": 60,
                     "request": {"python": sys.executable, "profile": "fixture", "arguments": []},
                     "environment_names": ["OPENAI_API_KEY"]}}


@pytest.fixture
def service(tmp_path):
    config = {"schema": "arena.control/1", "state_dir": str(tmp_path / "private"),
              "cgroup_root": "/sys/fs/cgroup/arena-fixture",
              "limits": {"cpus": 8, "memory_mb": 4096, "evaluation_slots": 8, "max_active": 8,
                         "max_queued": 20, "max_runs_per_key": 100, "max_reserved_seconds_per_key": 6000},
              "templates": [template()]}
    path = tmp_path / "control.json"
    path.write_text(json.dumps(config))
    path.chmod(0o600)
    return control.ControlService(path)


def principal(service, owner="alice", scopes=("read", "submit", "cancel"), **kwargs):
    key = service.create_key(owner, scopes, **kwargs)
    return service.authenticate("Bearer " + key["token"]), key


def submit(service, user, **kwargs):
    return service.submit(user, {"schema": "arena.control-submit/1", "template": "fixture", "model": "fixture-model", **kwargs})["run"]


def config_write(service, update):
    config = copy.deepcopy(service.config)
    update(config)
    service.config_path.write_text(json.dumps(config))
    return config


def stale(service, row, **kwargs):
    with service._db(write=True) as db:
        fields = {"lease_until": 0, **kwargs}
        db.execute("UPDATE runs SET " + ",".join(key + "=?" for key in fields) + " WHERE id=?", (*fields.values(), row["id"]))


class FakeGroup:
    def __init__(self, *, live=False):
        self.live, self.killed, self.closed = live, False, False
    def populated(self):
        return self.live
    def kill(self):
        self.killed = True
        self.live = False
    def wait_empty(self, _timeout=3):
        return not self.live
    def close(self):
        assert not self.live
        self.closed = True


@pytest.fixture
def http(service):
    server = DashboardServer(("127.0.0.1", 0), [], control=service)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "http://127.0.0.1:" + str(server.server_port)
    server.shutdown()
    thread.join(timeout=3)
    server.server_close()


def request(url, *, token=None, body=None, method=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = Request(url, data=None if body is None else json.dumps(body).encode(), headers=headers, method=method)
    try:
        with urlopen(req, timeout=3) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.load(exc)
