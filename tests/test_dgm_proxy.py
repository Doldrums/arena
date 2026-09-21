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
    monkeypatch.setattr(dp, "read_regular", lambda fd, name, limit, owner=None: original_read(fd, name, limit, os.getuid()))
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


def test_upload_download_evidence_and_malicious_native_extractall_payload(setup):
    proxy, fake, record = create(setup)
    safe = archive([("parent_patch.txt", b"native patch")])
    assert proxy.dispatch("PUT", "/containers/" + ID + "/archive?path=/dgm", safe, RUN, ADMITTED)[0] == 200
    response = proxy.dispatch("GET", "/containers/" + ID + "/archive?path=/dgm/report.md", b"", RUN, ADMITTED)
    assert response[0] == 200 and len(record["transfers"]) == 2
    assert record["transfers"][1]["sha256"] == hashlib.sha256(response[2]).hexdigest()
    fake.tar = archive([("../../escape", b"malicious")])
    with pytest.raises(dp.Denied): proxy.dispatch("GET", "/containers/" + ID + "/archive?path=/dgm/report.md", b"", RUN, ADMITTED)
    fake.tar = archive([(".git/config", b"wrong root")])
    with pytest.raises(dp.Denied): proxy.dispatch("GET", "/containers/" + ID + "/archive?path=/dgm/report.md", b"", RUN, ADMITTED)
    assert len(record["transfers"]) == 2


def test_archive_bounds(monkeypatch):
    monkeypatch.setattr(dp, "MAX_ENTRIES", 1)
    with pytest.raises(dp.Denied): dp.sanitize_tar(archive([("a", b"a"), ("b", b"b")]))
    monkeypatch.setattr(dp, "MAX_EXPANDED", 1)
    with pytest.raises(dp.Denied): dp.sanitize_tar(archive([("a", b"aa")]))
    monkeypatch.setattr(dp, "MAX_TAR", 100)
    with pytest.raises(dp.Denied): dp.sanitize_tar(archive([("a", b"a")]))


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
    monkeypatch.setattr(dp, "admission", lambda *a: (_ for _ in ()).throw(dp.Denied("cancelled")))
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
    monkeypatch.setattr(dp, "_peer_identity", lambda *a: [RUN, "main"])
    assert dp.peer_run(None, setup) == RUN
    for tail in ([RUN, ID], [RUN, "main", "child"]):
        monkeypatch.setattr(dp, "_peer_identity", lambda *a: tail)
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
    monkeypatch.setattr(dp.subprocess, "run", commands)
    monkeypatch.setattr(dp, "root_file", lambda *args: KEY.encode())
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
    monkeypatch.setattr(dp, "peer_run", lambda *a: RUN)
    monkeypatch.setattr(dp, "admission", lambda *a: ADMITTED)
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
    monkeypatch.setattr(dp, "peer_run", lambda *a: RUN)
    monkeypatch.setattr(dp, "admission", lambda *a: ADMITTED)
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
    monkeypatch.setattr(dp, "admission", lambda *a: ADMITTED)
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
    monkeypatch.setattr(dp.http.client, "HTTPConnection", Connection)
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
    monkeypatch.setattr(dp, "REQUEST_TIMEOUT", 0.1)
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
