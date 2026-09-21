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

from _dgm_proxy_helpers import setup, FakeDocker, create, archive, seed_admission


def test_actual_sdk_create_is_rebuilt_with_no_host_paths_or_runtime_internet(setup):
    proxy, fake, record = create(setup)
    native = fake.container; host = native["HostConfig"]
    assert native["Image"] == IMAGE_ID and native["Entrypoint"] == [dp.BOOTSTRAP]
    assert all(native["Labels"][k] == v for k, v in proxy.labels(record).items())
    assert host["NetworkMode"] == NETWORK and host["Dns"] == ["127.0.0.1"]
    assert host["ReadonlyRootfs"] and host["CapDrop"] == ["ALL"] and host["CgroupnsMode"] == "private"
    assert host["CgroupParent"] == "/arena-workers/arena-control-" + RUN
    assert host["Memory"] == host["MemorySwap"] == 2048 * 1024**2 and host["PidsLimit"] == 256
    assert set(host["Tmpfs"]) == {"/dgm", "/testbed", "/tmp", "/root"}
    assert not set(host) & {"Binds", "Mounts", "VolumesFrom", "Devices", "DeviceRequests", "PortBindings"}
    assert "ARENA_DGM_MODEL=gpt-5.6-sol" in native["Env"]
    assert KEY not in next(setup.state_root.glob("*.json")).read_text()


def test_operator_pilot_allocation_is_explicit_and_accepts_native_cpu_hint(setup):
    config = replace(setup, container_cpus=4, container_memory_mb=8192)
    proxy = dp.Proxy(config); proxy.gateway_key = KEY
    fake = FakeDocker(proxy); proxy.request = fake.request
    body = {**SDK_CREATE, "HostConfig": {"NetworkMode": "default", "NanoCpus": 1000000000}}
    proxy.create(body, NAME, RUN, ADMITTED, "")
    assert fake.container["HostConfig"]["NanoCpus"] == 4_000_000_000
    assert fake.container["HostConfig"]["Memory"] == 8192 * 1024**2


@pytest.mark.parametrize("location,key,value", [
    ("", "Entrypoint", ["sh"]), ("", "Cmd", ["sleep", "infinity"]), ("", "Env", ["X=1"]),
    ("", "Tty", True), ("", "OpenStdin", True), ("", "User", "1000"), ("", "Volumes", {"/host": {}}),
    ("HostConfig", "Binds", ["/:/host"]), ("HostConfig", "Privileged", True), ("HostConfig", "CapAdd", ["SYS_ADMIN"]),
    ("HostConfig", "NetworkMode", "host"), ("HostConfig", "PidMode", "host"), ("HostConfig", "IpcMode", "host"),
    ("HostConfig", "DeviceRequests", [{"Count": -1}]), ("HostConfig", "CgroupParent", "/"),
    ("HostConfig", "SecurityOpt", ["seccomp=unconfined"]), ("HostConfig", "LogConfig", {"Type": "syslog"}),
])
def test_escalation_fields_never_reach_daemon(setup, location, key, value):
    proxy = dp.Proxy(setup); proxy.gateway_key = KEY
    fake = FakeDocker(proxy); proxy.request = fake.request
    body = deepcopy(SDK_CREATE)
    (body.setdefault(location, {}) if location else body)[key] = value
    with pytest.raises(dp.Denied): proxy.create(body, NAME, RUN, ADMITTED, "")
    assert not any(path.startswith("/containers/create") for _, path, _ in fake.calls)


@pytest.mark.parametrize("method,path", [
    ("POST", "/build"), ("POST", "/images/create?fromImage=ubuntu"), ("DELETE", "/images/dgm:latest"),
    ("POST", "/networks/create"), ("POST", "/volumes/create"), ("GET", "/containers/json"),
    ("POST", "/containers/" + ID + "/attach"), ("POST", "/exec/" + EXEC + "/resize?h=1&w=1"),
    ("PUT", "/containers/" + ID + "/archive?path=/etc"), ("GET", "/containers/" + ID + "/archive?path=/dgm/../etc"),
])
def test_noncapability_routes_denied(method, path):
    with pytest.raises(dp.Denied): dp.route(method, path)


def test_sdk_bool_urls_image_projection_and_foreign_containers(setup):
    proxy, fake, record = create(setup)
    assert dp.route("DELETE", "/containers/" + ID + "?force=True&link=False&v=False")[1] == "delete"
    listing = json.loads(proxy.dispatch("GET", "/images/json?all=0&only_ids=0", b"", RUN, ADMITTED)[2])
    assert listing == [{"Id": IMAGE_ID, "Created": 1, "Size": 123, "RepoTags": ["dgm:latest"]}]
    fake.image["RepoTags"].append("private/build-tag:latest")
    inspected = json.loads(proxy.dispatch("GET", "/images/" + IMAGE_ID + "/json", b"", RUN, ADMITTED)[2])
    assert inspected["RepoTags"] == ["dgm:latest"] and inspected["RepoDigests"] == [IMAGE]
    assert proxy.dispatch("GET", "/containers/" + NAME + "/json", b"", OTHER_RUN, ADMITTED)[0] == 404
    body = json.loads(proxy.dispatch("GET", "/containers/" + ID + "/json", b"", RUN, ADMITTED)[2])
    assert "Pid" not in body["State"] and "Env" not in body["Config"] and KEY not in json.dumps(body)
    before = len(fake.calls)
    assert proxy.dispatch("GET", "/containers/" + "9" * 64 + "/json", b"", RUN, ADMITTED)[0] == 404
    assert len(fake.calls) == before


def test_real_native_exec_environment_is_validated_but_credentials_never_forwarded_again(setup):
    proxy, fake, record = create(setup)
    response = proxy.dispatch("POST", "/containers/" + ID + "/exec", dp.encoded(SDK_EXEC), RUN, ADMITTED)
    assert response[0] == 201
    forwarded = json.loads(fake.calls[-1][2])
    assert "Env" not in forwarded and not forwarded["Privileged"] and not forwarded["AttachStdin"]
    assert forwarded["Cmd"] == SDK_EXEC["Cmd"]
    inspection = json.loads(proxy.dispatch("GET", "/exec/" + EXEC + "/json", b"", RUN, ADMITTED)[2])
    assert inspection["ExitCode"] == 0 and "Pid" not in inspection
    with pytest.raises(dp.Denied): proxy.dispatch("GET", "/exec/" + EXEC + "/json", b"", OTHER_RUN, ADMITTED)
    for change in ({"Env": ["OPENAI_API_KEY=foreign"]}, {"Env": ["AWS_ACCESS_KEY_ID=secret"]},
                   {"Env": ["ARENA_DGM_MODEL=other"]}, {"Env": ["LD_PRELOAD=/dgm/malicious.so"]},
                   {"Privileged": True}, {"Container": "f" * 64}, {"WorkingDir": "/etc"}):
        with pytest.raises(dp.Denied): proxy.exec_create(record, {**SDK_EXEC, **change}, "")


def test_image_alias_and_digest_identity_mismatch_never_creates(setup):
    proxy = dp.Proxy(setup); proxy.gateway_key = KEY
    fake = FakeDocker(proxy); proxy.request = fake.request
    for key, bad in (("Id", "sha256:" + "0" * 64), ("RepoTags", []), ("RepoDigests", []), ("Architecture", "arm64")):
        old = fake.image[key]; fake.image[key] = bad
        with pytest.raises(dp.Denied): proxy.create(SDK_CREATE, NAME, RUN, ADMITTED, "")
        fake.image[key] = old
    fake.image["Config"]["Volumes"] = {"/host": {}}
    with pytest.raises(dp.Denied): proxy.image("dgm:latest")
    assert not any("/containers/create" in path for _, path, _ in fake.calls)


def test_bootstrap_must_finish_before_native_start_returns(setup):
    proxy, fake, record = create(setup)
    assert proxy.dispatch("POST", "/containers/" + ID + "/start", b"", RUN, ADMITTED)[0] == 204
    operations = [(method, path) for method, path, _ in fake.calls]
    assert ("POST", "/exec/" + EXEC + "/start") in operations and operations[-1] == ("GET", "/exec/" + EXEC + "/json")
    assert EXEC not in proxy.execs  # internal readiness exec is not a caller capability


def test_cancel_and_recovery_only_delete_root_recorded_label_verified_containers(setup, monkeypatch):
    proxy, fake, record = create(setup)
    monkeypatch.setattr(dgm_execution, "admission", lambda *a: (_ for _ in ()).throw(dp.Denied("cancelled")))
    proxy.reap_once()
    assert not proxy.records and fake.container is None
    assert json.loads(next(setup.state_root.glob("*.json")).read_text())["state"] == "removed"
    # A fresh interrupted creation is recovered after restart without trusting client IDs.
    proxy2, fake2, rec2 = create(setup)
    restarted = dp.Proxy(setup); restarted.request = fake2.request
    restarted.recover()
    assert fake2.container is None
    proxy3, fake3, rec3 = create(setup)
    fake3.container["Labels"]["arena.control-run"] = OTHER_RUN
    restarted.request = fake3.request
    with pytest.raises(dp.Denied): restarted.recover()
    assert fake3.container is not None


def test_snapshot_model_framework_and_admission_bindings(setup):
    snapshot = seed_admission(setup)
    assert dp.admission(setup, RUN)["model"] == ADMITTED["model"]
    with sqlite3.connect(setup.queue_database) as db: db.execute("UPDATE runs SET cancel_requested=1")
    with pytest.raises(dp.Denied): dp.admission(setup, RUN)
    with sqlite3.connect(setup.queue_database) as db: db.execute("UPDATE runs SET cancel_requested=0,model='unapproved'")
    with pytest.raises(dp.Denied): dp.admission(setup, RUN)
    with sqlite3.connect(setup.queue_database) as db: db.execute("UPDATE runs SET model=?", (ADMITTED["model"],))
    (setup.runs_root / RUN / "snapshot.json").write_text("{}")
    with pytest.raises(dp.Denied): dp.admission(setup, RUN)


def test_peer_must_be_host_native_main_not_sibling_container(setup, monkeypatch):
    monkeypatch.setattr(dgm_policy, "_peer_identity", lambda *a: [RUN, "main"])
    assert dp.peer_run(None, setup) == RUN
    for tail in ([RUN, ID], [RUN, "main", "child"]):
        monkeypatch.setattr(dgm_policy, "_peer_identity", lambda *a: tail)
        with pytest.raises(dp.Denied): dp.peer_run(None, setup)


def test_preflight_requires_real_internal_network_and_first_exact_host_firewall(setup, monkeypatch):
    proxy = dp.Proxy(setup); fake = FakeDocker(proxy)
    network = {"Id": NETWORK, "Driver": "bridge", "Internal": True, "EnableIPv6": False,
               "Options": {"com.docker.network.bridge.enable_icc": "false", "com.docker.network.bridge.name": "br-arena-dgm"},
               "IPAM": {"Config": [{"Gateway": "172.30.88.1"}]}}
    def request(method, path, *args, **kwargs):
        if path == "/networks/" + NETWORK: return dp.result(network)
        return fake.request(method, path, *args, **kwargs)
    proxy.request = request
    first = "-A INPUT -i br-arena-dgm -j ARENA_DGM_HOST"
    def commands(argv, **kwargs):
        if "-C" in argv: return SimpleNamespace(returncode=0, stdout=b"")
        if argv[-1] == "INPUT": return SimpleNamespace(returncode=0, stdout=("-P INPUT ACCEPT\n" + first + "\n").encode())
        return SimpleNamespace(returncode=0, stdout=b"-N ARENA_DGM_HOST\n-A ARENA_DGM_HOST -d 172.30.88.1/32 -p tcp -m tcp --dport 8789 -j ACCEPT\n-A ARENA_DGM_HOST -j DROP\n")
    monkeypatch.setattr(dgm_execution.subprocess, "run", commands)
    monkeypatch.setattr(dgm_execution, "root_file", lambda *args: KEY.encode())
    proxy.preflight()
    assert proxy.gateway_key == KEY
    network["Internal"] = False
    with pytest.raises(dp.Denied): proxy.preflight()
    network["Internal"] = True
    network["Options"]["com.docker.network.bridge.enable_icc"] = "true"
    with pytest.raises(dp.Denied): proxy.preflight()
    network["Options"]["com.docker.network.bridge.enable_icc"] = "false"
    first = "-A INPUT -j ACCEPT\n" + first
    with pytest.raises(dp.Denied): proxy.preflight()


def test_gateway_pilot_outer_and_container_model_identity_must_match(setup):
    snapshot = seed_admission(setup)
    request = snapshot["template"]["spec"]["request"]
    request.update(profile="gateway-polyglot-pilot", model=ADMITTED["model"])
    def write_snapshot():
        raw = dp.encoded(snapshot)
        (setup.runs_root / RUN / "snapshot.json").write_bytes(raw)
        with sqlite3.connect(setup.queue_database) as db:
            db.execute("UPDATE runs SET snapshot_sha256=?", (hashlib.sha256(raw).hexdigest(),))
    write_snapshot()
    assert dp.admission(setup, RUN)["model"] == ADMITTED["model"]
    request["model"] = "gpt-5.6-terra"
    write_snapshot()
    with pytest.raises(dp.Denied, match="outer-loop model"): dp.admission(setup, RUN)
