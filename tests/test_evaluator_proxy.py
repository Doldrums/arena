"""No Docker daemon, candidate execution, model call or privilege is required."""
from copy import deepcopy
from dataclasses import replace
import http.client
import http.server
import json
import os
from pathlib import Path
import socket
import socketserver
import shutil
import subprocess
import struct
import threading
import tempfile

import pytest

from arena import evaluator_proxy as ep
from arena import evaluator_execution, evaluator_http, evaluator_policy


RUN = "b" * 32
EVAL = "a" * 32
IDENT = "d" * 64
NAME = "arena-eval-" + EVAL
IMAGE = "sha256:" + "c" * 64


@pytest.fixture
def setup(tmp_path):
    # resolve() accommodates macOS's /var -> /private/var temporary root.
    root = tmp_path.resolve()
    tasks, runs, stage = root / "tasks", root / "runs", root / "staging"
    tasks.mkdir(); runs.mkdir(); stage.mkdir()
    (tasks / "run.py").write_text("# reviewed evaluator fixture\n")
    receipt = runs / RUN / "artifacts" / "canonical-evaluations" / EVAL
    candidate, output = receipt / "input", receipt / "native-output"
    candidate.mkdir(parents=True); output.mkdir()
    (candidate / "program.py").write_text("# inert generated candidate\n")
    sockets = tempfile.TemporaryDirectory(prefix="ep-", dir="/tmp")
    config = ep.Config(Path(sockets.name) / "d.sock", Path(sockets.name) / "p.sock", stage, tasks, (runs,),
                       (IMAGE,), os.getuid(), os.getgid(), timeout_seconds=120)
    body = json.loads((Path(__file__).parent / "fixtures/evaluator_proxy/docker-cli-create.json").read_text())
    body["User"] = f"{os.getuid()}:{os.getgid()}"
    for mount in body["HostConfig"]["Mounts"]:
        mount["Source"] = str({"/tasks": tasks, "/candidate": candidate, "/results": output}[mount["Target"]])
    yield config, body, candidate, output
    sockets.cleanup()


def test_actual_cli_shape_is_rebuilt_not_forwarded(setup):
    config, body, candidate, output = setup
    checked, cpath, opath = ep.canonical_config(body, NAME, RUN, config)
    assert cpath == candidate and opath == output
    assert checked["HostConfig"]["MemorySwap"] == checked["HostConfig"]["Memory"]
    assert checked["HostConfig"]["LogConfig"] == {"Type": "local", "Config": {"max-size": "1m", "max-file": "1", "compress": "false"}}
    assert checked["Entrypoint"] == [] and checked["HostConfig"]["CgroupnsMode"] == "private"
    assert "Binds" not in checked["HostConfig"] and "NetworkingConfig" not in checked
    assert checked["HostConfig"]["Mounts"] == [
        {"Type": "bind", "Source": str(config.tasks_root), "Target": "/tasks", "ReadOnly": True}]



def test_environment_order_is_canonicalized_without_allowing_duplicates_or_overrides(setup):
    config, body, *_ = setup
    expected = list(body["Env"])
    body["Env"].reverse()
    checked, _, _ = ep.canonical_config(body, NAME, RUN, config)
    assert checked["Env"] == expected
    for environment in ([expected[0], expected[0]], expected + [expected[1]],
                        [expected[0], "PYTHONPYCACHEPREFIX=/tasks"], [expected[0], None]):
        body["Env"] = environment
        with pytest.raises(ep.Denied):
            ep.canonical_config(body, NAME, RUN, config)


def test_registered_engine_identity_requires_actual_container_cgroup(setup, monkeypatch):
    config, *_ = setup
    registry = config.staging_root.parent / "engine-registry"; registry.mkdir()
    engine_stage = config.staging_root.parent / "engine-staging"; engine_stage.mkdir()
    config = replace(config, engine_registry=registry, engine_staging_root=engine_stage)
    record = {"schema": "arena.engine-peer/1", "run_id": RUN, "container_id": IDENT,
              "artifact_root": str(engine_stage / RUN / "artifacts")}
    (registry / (RUN + ".json")).write_text(json.dumps(record))
    actual_read = ep.read_regular
    monkeypatch.setattr(evaluator_policy, "read_regular", lambda fd, name, limit, owner=None: actual_read(fd, name, limit, os.getuid()))
    monkeypatch.setattr(evaluator_policy, "_peer_identity", lambda *a: [RUN, IDENT])
    assert ep.engine_binding(None, config) == record
    assert ep.peer_run(None, config) == RUN
    monkeypatch.setattr(evaluator_policy, "_peer_identity", lambda *a: [RUN, "e" * 64])
    with pytest.raises(ep.Denied): ep.engine_binding(None, config)
    monkeypatch.setattr(evaluator_policy, "_peer_identity", lambda *a: [RUN, "main"])
    assert ep.engine_binding(None, config) is None


def test_engine_candidate_and_results_are_mapped_only_to_root_registered_stage(setup, monkeypatch):
    config, body, candidate, output = setup
    engine_stage = config.staging_root.parent / "engine-staging"; engine_stage.mkdir()
    config = replace(config, engine_staging_root=engine_stage)
    physical = engine_stage / RUN / "artifacts"
    logical = config.run_roots[0] / RUN / "artifacts"
    actual_candidate = physical / candidate.relative_to(logical)
    actual_output = physical / output.relative_to(logical)
    actual_candidate.mkdir(parents=True); actual_output.mkdir()
    (actual_candidate / "program.py").write_text("# private image candidate\n")
    proxy = ep.Proxy(config); captures = []; fake_create(proxy, captures)
    monkeypatch.setattr(evaluator_execution.os, "chown", lambda *a: None)
    monkeypatch.setattr(evaluator_execution.os, "fchown", lambda *a: None)
    binding = {"run_id": RUN, "artifact_root": str(physical)}
    proxy.create(body, NAME, RUN, "", binding)
    record = proxy.records[NAME]
    assert (record["stage"] / "candidate/program.py").read_text() == "# private image candidate\n"
    (record["stage"] / "results/native.json").write_text('{"valid":true}')
    proxy.publish(record)
    assert (actual_output / "native.json").is_file() and not (output / "native.json").exists()
    proxy.remove(NAME, record)
    with pytest.raises(ep.Denied):
        proxy.create(body, NAME, RUN, "", {"run_id": RUN, "artifact_root": str(config.tasks_root)})


@pytest.mark.parametrize("location,key,value", [
    ("", "Image", "ubuntu:latest"), ("", "User", "0:0"),
    ("", "Env", ["SECRET=anything"]), ("", "Entrypoint", ["/bin/sh"]),
    ("", "OpenStdin", True), ("", "Tty", True),
    ("", "NetworkingConfig", {"EndpointsConfig": {"host": {}}}),
    ("HostConfig", "Privileged", True), ("HostConfig", "PidMode", "host"),
    ("HostConfig", "IpcMode", "host"), ("HostConfig", "UsernsMode", "host"),
    ("HostConfig", "NetworkMode", "host"), ("HostConfig", "CapAdd", ["SYS_ADMIN"]),
    ("HostConfig", "Devices", [{"PathOnHost": "/dev/sda"}]),
    ("HostConfig", "DeviceRequests", [{"Count": -1}]),
    ("HostConfig", "Binds", ["/:/host"]), ("HostConfig", "ReadonlyRootfs", False),
    ("HostConfig", "NanoCpus", 2_000_000_000), ("HostConfig", "Memory", 4 * 1024 ** 3),
    ("HostConfig", "PidsLimit", -1), ("HostConfig", "SecurityOpt", ["seccomp=unconfined"]),
    ("HostConfig", "CgroupParent", "/"), ("HostConfig", "Runtime", "nvidia"),
    ("HostConfig", "LogConfig", {"Type": "syslog", "Config": {"syslog-address": "tcp://elsewhere"}}),
])
def test_escalation_config_is_denied(setup, location, key, value):
    config, body, *_ = setup
    (body[location] if location else body)[key] = value
    with pytest.raises(ep.Denied):
        ep.canonical_config(body, NAME, RUN, config)


def test_command_and_other_run_paths_cannot_be_selected(setup):
    config, body, *_ = setup
    bad = deepcopy(body); bad["Cmd"] = ["sh", "-c", "cat /host/etc/shadow"]
    with pytest.raises(ep.Denied): ep.canonical_config(bad, NAME, RUN, config)
    bad = deepcopy(body); bad["HostConfig"]["Mounts"][1]["Source"] = "/etc/arena/provider/input"
    with pytest.raises(ep.Denied): ep.canonical_config(bad, NAME, RUN, config)
    with pytest.raises(ep.Denied): ep.canonical_config(body, NAME, "e" * 32, config)
    bad = deepcopy(body); bad["Cmd"][11] = "121"
    with pytest.raises(ep.Denied): ep.canonical_config(bad, NAME, RUN, config)


def fake_create(proxy, captures):
    def request(method, path, body=None, timeout=30):
        captures.append((method, path, json.loads(body) if body else None))
        return 201, {"Content-Type": "application/json"}, json.dumps({"Id": IDENT}).encode()
    proxy.request = request


def test_mutable_paths_are_snapshotted_and_output_uses_held_directory(setup, monkeypatch):
    config, body, candidate, output = setup
    proxy = ep.Proxy(config); captures = []; fake_create(proxy, captures)
    # chown-to-self is allowed normally; leave tests runnable on restricted hosts.
    monkeypatch.setattr(evaluator_execution.os, "chown", lambda *args: None)
    monkeypatch.setattr(evaluator_execution.os, "fchown", lambda *args: None)
    assert proxy.create(body, NAME, RUN, "/v1.48")[0] == 201
    record = proxy.records[NAME]
    mounts = captures[0][2]["HostConfig"]["Mounts"]
    snapshot = Path(mounts[1]["Source"]) / "program.py"
    (candidate / "program.py").write_text("# changed after validation\n")
    assert snapshot.read_text() == "# inert generated candidate\n"
    assert Path(mounts[2]["Source"]) != output
    relocated = output.with_name("relocated")
    output.rename(relocated)
    output.symlink_to(config.tasks_root, target_is_directory=True)
    (record["stage"] / "results" / "native.json").write_text('{"status":"completed"}')
    proxy.publish(record)
    assert json.loads((relocated / "native.json").read_text()) == {"status": "completed"}
    assert not (config.tasks_root / "native.json").exists()
    proxy.remove(NAME, record)


def test_private_service_umask_keeps_candidate_mount_readable(setup, monkeypatch):
    config, body, *_ = setup
    proxy = ep.Proxy(config); fake_create(proxy, [])
    monkeypatch.setattr(evaluator_execution.os, "chown", lambda *args: None)
    previous = os.umask(0o077)
    try:
        proxy.create(body, NAME, RUN, "")
    finally:
        os.umask(previous)
    record = proxy.records[NAME]
    assert (record["stage"] / "candidate").stat().st_mode & 0o777 == 0o755
    assert (record["stage"] / "candidate/program.py").stat().st_mode & 0o777 == 0o444
    proxy.remove(NAME, record)


@pytest.mark.parametrize("kind", ["symlink-file", "symlink-directory", "hardlink", "fifo", "oversize"])
def test_candidate_file_attacks_never_reach_daemon(setup, monkeypatch, kind):
    config, body, candidate, output = setup
    proxy = ep.Proxy(config); captures = []; fake_create(proxy, captures)
    file = candidate / "program.py"
    if kind == "symlink-file":
        file.unlink(); file.symlink_to(config.tasks_root / "run.py")
    elif kind == "symlink-directory":
        candidate.rename(candidate.with_name("elsewhere")); candidate.symlink_to(candidate.with_name("elsewhere"), target_is_directory=True)
    elif kind == "hardlink":
        os.link(file, candidate / "second.py")
    elif kind == "fifo":
        file.unlink(); os.mkfifo(file)
    else:
        with file.open("wb") as stream: stream.truncate(16 * 1024 ** 2 + 1)
    with pytest.raises((ep.Denied, OSError)):
        proxy.create(body, NAME, RUN, "")
    assert captures == [] and not list(config.staging_root.iterdir())


def test_output_symlink_is_not_followed_and_run_ownership_is_enforced(setup, monkeypatch):
    config, body, candidate, output = setup
    proxy = ep.Proxy(config); fake_create(proxy, [])
    monkeypatch.setattr(evaluator_execution.os, "chown", lambda *args: None)
    proxy.create(body, NAME, RUN, "")
    record = proxy.records[NAME]
    (record["stage"] / "results" / "native.json").symlink_to(config.tasks_root / "run.py")
    proxy.publish(record)
    assert not (output / "native.json").exists()
    with pytest.raises(ep.Denied): proxy.owned(IDENT, "e" * 32)
    with pytest.raises(ep.Denied): proxy.owned("f" * 64, RUN)
    proxy.remove(NAME, record)


@pytest.mark.parametrize("method,path", [
    ("POST", "/images/create?fromImage=ubuntu"), ("POST", "/build"),
    ("POST", "/containers/" + IDENT + "/exec"), ("POST", "/exec/" + IDENT + "/start"),
    ("GET", "/containers/json"), ("GET", "/images/json"), ("GET", "/info?anything=1"),
    ("GET", "/containers/" + IDENT + "/archive?path=/etc/shadow"),
    ("POST", "/containers/" + IDENT + "/attach?stdin=1"),
    ("DELETE", "/containers/" + IDENT + "?force=1&v=1"),
    ("POST", "/containers/" + IDENT + "/kill?signal=HUP"),
    ("GET", "/containers/" + IDENT + "/logs?tail=all"),
    ("POST", "/containers/create?name=a&name=b"),
    ("GET", "/v1.48/containers/%2e%2e/info"), ("GET", "http://host/version"),
])
def test_other_docker_capabilities_denied(method, path):
    with pytest.raises(ep.Denied): ep.route(method, path)


def test_supported_cli_routes():
    assert ep.route("HEAD", "/_ping")[1] == "info"
    assert ep.route("GET", "/v1.48/version")[1] == "info"
    assert ep.route("POST", "/v1.48/containers/create?name=" + NAME)[1] == "create"
    assert ep.route("POST", "/v1.48/containers/" + IDENT + "/attach?stream=1&stdout=1&stderr=1")[1] == "attach"
    assert ep.route("POST", "/v1.48/containers/" + IDENT + "/wait?condition=next-exit")[1] == "wait"
    assert ep.route("DELETE", "/v1.48/containers/" + NAME + "?force=1")[1] == "delete"


def test_duplicate_and_nonfinite_json_rejected():
    for raw in (b'{"HostConfig":{},"HostConfig":{}}', b'{"limit":NaN}'):
        with pytest.raises(ep.Denied): ep.json_object(raw)


def test_info_preflight_exposes_only_validated_cgroup_contract(setup):
    config, *_ = setup
    proxy = ep.Proxy(config)
    native = {"CgroupDriver": "cgroupfs", "CgroupVersion": "2", "DockerRootDir": "/private", "Swarm": {"secret": "not forwarded"}}
    proxy.request = lambda *a: (200, {}, json.dumps(native).encode())
    assert json.loads(proxy.cgroup_info()[2]) == {"CgroupDriver": "cgroupfs", "CgroupVersion": "2"}
    native["CgroupDriver"] = "systemd"
    with pytest.raises(ep.Denied): proxy.cgroup_info()


def test_restart_recovers_create_transport_uncertainty_by_verified_name(setup):
    config, *_ = setup
    stage = config.staging_root / EVAL; stage.mkdir()
    (stage / "record.json").write_text(json.dumps({"id": None, "run": RUN, "name": NAME}))
    proxy = ep.Proxy(config); calls = []
    def request(method, path, **kw):
        calls.append((method, path))
        if method == "GET":
            return 200, {}, json.dumps({"Id": IDENT, "Config": {"Labels": {"arena.evaluator": "canonical-v1", "arena.control-run": RUN}}}).encode()
        return 204, {}, b""
    proxy.request = request
    proxy.recover()
    assert calls == [("GET", "/containers/" + NAME + "/json"), ("DELETE", "/containers/" + IDENT + "?force=1")]
    assert not stage.exists()


def test_restart_never_deletes_unowned_container(setup):
    config, *_ = setup
    stage = config.staging_root / EVAL; stage.mkdir()
    (stage / "record.json").write_text(json.dumps({"id": IDENT, "run": RUN, "name": NAME}))
    proxy = ep.Proxy(config); calls = []
    def request(method, path, **kw):
        calls.append(method)
        return 200, {}, json.dumps({"Id": IDENT, "Config": {"Labels": {}}}).encode()
    proxy.request = request
    with pytest.raises(ep.Denied): proxy.recover()
    assert calls == ["GET"] and stage.exists()


def test_peer_identity_comes_from_kernel_cgroup_not_headers(monkeypatch, setup):
    config, *_ = setup
    class Peer:
        def getsockopt(self, *args): return struct.pack("3i", 1234, config.worker_uid, config.worker_gid)
    monkeypatch.setattr(evaluator_policy.socket, "SO_PEERCRED", 17, raising=False)
    original = Path.read_text
    group = "0::/arena-workers/arena-control-" + RUN + "/main/native\n"
    monkeypatch.setattr(Path, "read_text", lambda self, *a, **kw: group if str(self) == "/proc/1234/cgroup" else original(self, *a, **kw))
    assert ep.peer_run(Peer(), config) == RUN
    group = "0::/system.slice/arena-worker.service\n"
    with pytest.raises(ep.Denied): ep.peer_run(Peer(), config)


def test_http_proxy_rejects_before_forwarding_and_accepts_safe_ping(setup, monkeypatch):
    config, *_ = setup
    monkeypatch.setattr(evaluator_http, "peer_run", lambda *args: RUN)
    server = ep.Server(config)
    forwarded = []
    server.proxy.request = lambda *a, **kw: (forwarded.append(a) or (200, {"Api-Version": "1.48"}, b"OK"))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        for method, path, expected in [("POST", "/images/create?fromImage=ubuntu", 403), ("GET", "/_ping", 200)]:
            connection = ep.DockerConnection(config.socket_path)
            connection.request(method, path)
            response = connection.getresponse()
            assert response.status == expected
            response.read(); connection.close()
        assert len(forwarded) == 1 and forwarded[0] == ("GET", "/_ping")
    finally:
        server.shutdown(); server.server_close(); thread.join()


def test_streaming_attach_forwards_multiplexed_bytes_only(setup, monkeypatch):
    config, _, _, output = setup
    payload = b"\x01\x00\x00\x00\x00\x00\x00\x03OK\n"
    class Daemon(socketserver.BaseRequestHandler):
        def handle(self):
            header = self.request.recv(8192)
            assert b"Upgrade: tcp" in header and b"stdin=1" not in header
            self.request.sendall(b"HTTP/1.1 101 UPGRADED\r\nConnection: Upgrade\r\nUpgrade: tcp\r\n\r\n" + payload)
    daemon = socketserver.UnixStreamServer(str(config.docker_socket), Daemon)
    dthread = threading.Thread(target=daemon.serve_forever, daemon=True); dthread.start()
    monkeypatch.setattr(evaluator_http, "peer_run", lambda *args: RUN)
    monkeypatch.setattr(evaluator_execution.os, "fchown", lambda *args: None)
    server = ep.Server(config)
    staged = config.staging_root / EVAL
    (staged / "results").mkdir(parents=True)
    (staged / "results" / "native.json").write_text('{"status":"completed"}')
    record = {"id": IDENT, "run": RUN, "stage": staged, "output_fd": ep.directory_fd(output)}
    server.proxy.records[NAME] = record
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); client.settimeout(3)
        client.connect(str(config.socket_path))
        client.sendall(("POST /v1.48/containers/" + IDENT + "/attach?stream=1&stdout=1&stderr=1 HTTP/1.1\r\nHost: docker\r\nContent-Length: 0\r\n\r\n").encode())
        chunks = []
        while chunk := client.recv(4096): chunks.append(chunk)
        response = b"".join(chunks)
        assert response.startswith(b"HTTP/1.1 101") and response.split(b"\r\n\r\n", 1)[1] == payload
        # Receiving attach EOF is sufficient: do not race the separate /wait.
        assert json.loads((output / "native.json").read_text()) == {"status": "completed"}
        client.close()
    finally:
        server.shutdown(); server.server_close(); thread.join()
        server.proxy.remove(NAME, record)
        daemon.shutdown(); daemon.server_close(); dthread.join()


@pytest.mark.skipif(shutil.which("docker") is None, reason="Optional installed Docker CLI interoperability check")
def test_real_docker_cli_completes_against_inert_daemon_and_publishes_before_exit(setup, monkeypatch):
    """The real CLI is used, but never the real daemon or candidate execution."""
    config, body, _, output = setup
    monkeypatch.setattr(evaluator_http, "peer_run", lambda *args: RUN)
    monkeypatch.setattr(evaluator_execution.os, "chown", lambda *args: None)
    monkeypatch.setattr(evaluator_execution.os, "fchown", lambda *args: None)
    finished = threading.Event()
    created, calls = {}, []
    routes = []
    original_route = ep.route
    def capture_route(method, path):
        routes.append((method, path))
        return original_route(method, path)
    monkeypatch.setattr(evaluator_http, "route", capture_route)
    class Daemon(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
        daemon_threads = True
    class Native(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        def log_message(self, *args): pass
        def reply(self, status, value=None):
            raw = json.dumps(value).encode() if value is not None else b""
            self.send_response(status); self.send_header("Api-Version", "1.48")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw))); self.end_headers()
            if raw: self.wfile.write(raw)
        def do_HEAD(self): self.reply(200)
        def do_GET(self):
            self.reply(200, {"Id": IDENT, "Config": {"Tty": False}, "HostConfig": {"AutoRemove": True},
                             "State": {"Running": not finished.is_set(), "ExitCode": 0}})
        def do_POST(self):
            calls.append(self.path)
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if "/create?" in self.path:
                created.update(json.loads(raw)); self.reply(201, {"Id": IDENT, "Warnings": []})
            elif "/attach?" in self.path:
                self.send_response(101); self.send_header("Connection", "Upgrade")
                self.send_header("Upgrade", "tcp"); self.end_headers(); self.wfile.flush()
                assert finished.wait(5)
                self.connection.sendall(b"\x01\0\0\0\0\0\0\x03OK\n")
                self.close_connection = True
            elif "/wait?" in self.path:
                raw = json.dumps({"StatusCode": 0}).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.flush()
                assert finished.wait(5)
                self.wfile.write(raw)
            elif self.path.endswith("/start"):
                target = next(m["Source"] for m in created["HostConfig"]["Mounts"] if m["Target"] == "/results")
                Path(target, "native.json").write_text('{"status":"completed"}')
                finished.set(); self.reply(204)
            else: self.reply(404, {})
        def do_DELETE(self): self.reply(204)
    daemon = Daemon(str(config.docker_socket), Native)
    dthread = threading.Thread(target=daemon.serve_forever, daemon=True); dthread.start()
    server = ep.Server(config)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    argv = ["docker", "run", "--rm", "--pull=never", "--name", NAME, "--network", "none",
            "--read-only", "--cpus", "1", "--memory", "2g", "--pids-limit", "128", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--user", body["User"],
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=268435456", "--env", "PYTHONDONTWRITEBYTECODE=1",
            "--env", "PYTHONPYCACHEPREFIX=/tmp/arena-pycache",
            "--workdir", "/tmp", "--cgroup-parent", "/arena-workers/arena-control-" + RUN,
            "--label", "arena.evaluator=canonical-v1", "--label", "arena.control-run=" + RUN]
    for mount in body["HostConfig"]["Mounts"]:
        argv.extend(["--mount", f"type=bind,src={mount['Source']},dst={mount['Target']}" +
                     (",readonly" if mount.get("ReadOnly") else "")])
    argv.extend([IMAGE, *body["Cmd"]])
    try:
        process = subprocess.run(argv, env={**os.environ, "DOCKER_HOST": "unix://" + str(config.socket_path)},
                                 capture_output=True, timeout=15)
        assert process.returncode == 0, process.stderr.decode() + repr(routes) + repr(calls)
        assert process.stdout == b"OK\n"
        assert json.loads((output / "native.json").read_text()) == {"status": "completed"}
        assert any("/attach?" in p for p in calls) and any("/wait?" in p for p in calls)
    finally:
        server.proxy.close(); server.shutdown(); server.server_close(); thread.join()
        daemon.shutdown(); daemon.server_close(); dthread.join()
