"""Restricted, Linux-only Docker socket for canonical Arena evaluations.

This is a privileged boundary, not a general Docker proxy. Requests are rebuilt
from a fixed evaluator profile. No caller-provided Docker configuration is
forwarded, and mutable candidate/output paths are never passed to the daemon.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import socketserver
import stat
import struct
import threading
import time
from urllib.parse import parse_qs, urlsplit
import uuid


MAX_BODY = 128 * 1024
MAX_RESPONSE = 4 * 1024 * 1024
MAX_STREAM = 16 * 1024 * 1024
RUN = re.compile(r"[0-9a-f]{32}\Z")
IMAGE = re.compile(r"(?:[A-Za-z0-9][A-Za-z0-9._/:\-]*@)?sha256:[0-9a-f]{64}\Z")


class Denied(ValueError):
    """A request outside the evaluator capability."""


def require(condition, message="Request is outside the canonical evaluator profile"):
    if not condition:
        raise Denied(message)


def json_object(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    def invalid(value):
        raise Denied("Nonfinite JSON value")
    result = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)
    require(type(result) is dict)
    return result


def directory_fd(path):
    """Walk every component without following links, including ancestors."""
    path = Path(path)
    require(path.is_absolute() and ".." not in path.parts)
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in path.parts[1:]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def read_regular(descriptor, name, limit, owner=None):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= limit)
        require(owner is None or before.st_uid == owner)
        chunks, size = [], 0
        while size <= limit:
            chunk = os.read(fd, min(65536, limit + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        after = os.fstat(fd)
        require(size <= limit and (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                == (after.st_size, after.st_mtime_ns, after.st_ctime_ns))
        return b"".join(chunks)
    finally:
        os.close(fd)


@dataclass(frozen=True)
class Config:
    docker_socket: Path
    socket_path: Path
    staging_root: Path
    tasks_root: Path
    run_roots: tuple[Path, ...]
    images: tuple[str, ...]
    worker_uid: int
    worker_gid: int
    cgroup_root: str = "/arena-workers"
    max_containers: int = 16
    timeout_seconds: int = 3600

    @classmethod
    def read(cls, path):
        data = json_object(Path(path).read_bytes())
        required = {"docker_socket", "socket_path", "staging_root", "tasks_root", "run_roots",
                    "images", "worker_uid", "worker_gid"}
        require(required <= data.keys() and not set(data) - required -
                {"cgroup_root", "max_containers", "timeout_seconds"})
        for key in ("docker_socket", "socket_path", "staging_root", "tasks_root"):
            data[key] = Path(data[key])
            require(data[key].is_absolute() and ".." not in data[key].parts)
        require(type(data["run_roots"]) is list and data["run_roots"])
        data["run_roots"] = tuple(Path(p) for p in data["run_roots"])
        require(all(p.is_absolute() and len(p.parts) >= 4 and ".." not in p.parts for p in data["run_roots"]))
        require(type(data["images"]) is list and data["images"] and all(IMAGE.fullmatch(p) for p in data["images"]))
        data["images"] = tuple(data["images"])
        for key in ("worker_uid", "worker_gid"):
            require(type(data[key]) is int and data[key] > 0)
        config = cls(**data)
        require(re.fullmatch(r"/(?:[a-zA-Z0-9_-]+/)*[a-zA-Z0-9_-]+", config.cgroup_root)
                and config.cgroup_root != "/")
        require(type(config.max_containers) is int and 1 <= config.max_containers <= 64)
        require(type(config.timeout_seconds) is int and 1 <= config.timeout_seconds <= 86400)
        return config

    def validate_host(self):
        require(os.geteuid() == 0 and hasattr(socket, "SO_PEERCRED"), "Proxy requires Linux root")
        # A host-visible dedicated bounded tmpfs also bounds malicious output.
        mount = None
        for line in Path("/proc/self/mountinfo").read_text().splitlines():
            before, after = line.split(" - ", 1)
            fields, filesystem = before.split(), after.split()
            if fields[4] == str(self.staging_root):
                mount = filesystem
        require(mount is not None and mount[0] == "tmpfs", "Staging must be a dedicated host-visible tmpfs")
        sizes = [p[5:] for p in mount[2].split(",") if p.startswith("size=")]
        require(len(sizes) == 1)
        match = re.fullmatch(r"([0-9]+)([kmg]?)", sizes[0].lower())
        require(match is not None)
        size = int(match[1]) * {"": 1, "k": 1024, "m": 1024 ** 2, "g": 1024 ** 3}[match[2]]
        require(16 * 1024 ** 2 <= size <= 256 * 1024 ** 2, "Staging tmpfs must be 16–256 MiB")
        for path in (self.staging_root, self.socket_path.parent, self.tasks_root):
            fd = directory_fd(path)
            os.close(fd)
            for ancestor in (path, *path.parents):
                info = ancestor.stat()
                require(info.st_uid == 0 and not info.st_mode & 0o022,
                        "Proxy and task paths must have root-owned non-writable ancestors")
        require(stat.S_IMODE(self.staging_root.stat().st_mode) == 0o700)
        # The caller must not be able to mutate the reviewed task implementation.
        for base, directories, files in os.walk(self.tasks_root, followlinks=False):
            for name in directories + files:
                info = (Path(base) / name).lstat()
                require(not stat.S_ISLNK(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
                        "Task checkout must be root-owned, link-free and not group/world writable")


def peer_run(connection, config):
    pid, uid, gid = struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
    require(uid == config.worker_uid, "Only the evaluator worker UID may connect")
    data = Path(f"/proc/{pid}/cgroup").read_text()
    prefix = config.cgroup_root + "/arena-control-"
    matches = [line[3:] for line in data.splitlines() if line.startswith("0::")]
    require(len(matches) == 1 and matches[0].startswith(prefix))
    tail = matches[0][len(prefix):].split("/")
    require(len(tail) >= 2 and RUN.fullmatch(tail[0]) and tail[1] == "main",
            "Caller must be in an admitted run's main cgroup")
    return tail[0]


def only_defaults(mapping, allowed):
    require(type(mapping) is dict)
    for key, value in mapping.items():
        if key not in allowed:
            require(value in (None, False, "", 0, [], {}), "Unsupported non-default Docker option")


def canonical_config(body, name, run_id, config):
    """Validate actual Docker CLI JSON and rebuild a minimal safe config."""
    require(re.fullmatch(r"arena-eval-[0-9a-f]{32}", name) and RUN.fullmatch(run_id))
    only_defaults(body, {"Image", "Cmd", "User", "Env", "WorkingDir", "Labels", "HostConfig", "NetworkingConfig",
                         "AttachStdout", "AttachStderr"})
    require(body.get("NetworkingConfig", {}) in ({}, {"EndpointsConfig": {}}))
    require(body.get("Image") in config.images)
    require(body.get("User") == f"{config.worker_uid}:{config.worker_gid}")
    require(body.get("WorkingDir") == "/tmp")
    require(body.get("Env") == ["PYTHONDONTWRITEBYTECODE=1"])
    require(body.get("Labels") == {"arena.evaluator": "canonical-v1", "arena.control-run": run_id})
    command = body.get("Cmd")
    require(type(command) is list and len(command) == 14 and all(type(v) is str for v in command))
    python = command[0]
    require(python in {"python", "python3"} and command[1:5] == ["/tasks/run.py", "--root", "/tasks", "evaluate"])
    require(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,180}", command[5]))
    require(command[6:11] == ["--candidate", "/candidate/program.py", "--python", python, "--timeout"])
    require(command[11].isdigit() and 1 <= int(command[11]) <= config.timeout_seconds)
    require(command[12:] == ["--output", "/results/native.json"])
    host = body.get("HostConfig")
    allowed = {"NetworkMode", "ReadonlyRootfs", "NanoCpus", "Memory", "PidsLimit", "CapDrop", "SecurityOpt",
               "Tmpfs", "Mounts", "AutoRemove", "CgroupParent", "LogConfig", "RestartPolicy", "ConsoleSize",
               "ShmSize", "Runtime", "CgroupnsMode", "MemorySwap", "MemorySwappiness", "MaskedPaths", "ReadonlyPaths"}
    only_defaults(host, allowed)
    require(host.get("NetworkMode") == "none" and host.get("ReadonlyRootfs") is True)
    require(host.get("NanoCpus") == 1_000_000_000 and host.get("Memory") == 2 * 1024 ** 3)
    require(host.get("PidsLimit") == 128 and host.get("CapDrop") == ["ALL"])
    require(host.get("SecurityOpt") in (["no-new-privileges"], ["no-new-privileges=true"]))
    require(host.get("CgroupParent") == config.cgroup_root + "/arena-control-" + run_id)
    require(host.get("Tmpfs") == {"/tmp": "rw,nosuid,nodev,size=268435456"})
    require(host.get("AutoRemove") is True)
    require(host.get("LogConfig", {}) in ({}, {"Type": "", "Config": {}}))
    require(host.get("RestartPolicy", {}) in ({}, {"Name": "no", "MaximumRetryCount": 0}))
    require(host.get("ConsoleSize", [0, 0]) == [0, 0])
    require(host.get("ShmSize", 0) in (0, 64 * 1024 ** 2))
    require(host.get("Runtime", "") in ("", "runc"))
    require(host.get("CgroupnsMode", "") in ("", "private"))
    require(host.get("MemorySwap", 0) in (0, 2 * 1024 ** 3))
    require(host.get("MemorySwappiness", -1) == -1)
    # These are discarded, never propagated; our fixed daemon defaults apply.
    require(host.get("MaskedPaths") is None and host.get("ReadonlyPaths") is None)
    mounts = host.get("Mounts")
    require(type(mounts) is list and len(mounts) == 3)
    selected = {}
    for mount in mounts:
        require(type(mount) is dict and set(mount) <= {"Type", "Source", "Target", "ReadOnly", "Consistency", "BindOptions"})
        require(mount.get("Type") == "bind" and mount.get("Target") not in selected)
        require(mount.get("Consistency", "") == "" and mount.get("BindOptions", {}) in ({}, {"Propagation": "rprivate"}))
        selected[mount["Target"]] = mount
    require(set(selected) == {"/tasks", "/candidate", "/results"})
    require(selected["/tasks"].get("ReadOnly") is True and selected["/candidate"].get("ReadOnly") is True)
    require(selected["/results"].get("ReadOnly", False) is False)
    require(selected["/tasks"].get("Source") == str(config.tasks_root))
    candidate, result = Path(selected["/candidate"]["Source"]), Path(selected["/results"]["Source"])
    require(candidate.is_absolute() and result.is_absolute() and ".." not in candidate.parts and ".." not in result.parts)
    require(candidate.name in {"input", "candidate"} and result.name == "native-output" and candidate.parent == result.parent)
    require(RUN.fullmatch(candidate.parent.name))
    require(any(candidate.parent.parent == root / run_id / "artifacts" / "canonical-evaluations"
                for root in config.run_roots), "Evaluation paths must belong to this admitted run")
    rebuilt = {"Image": body["Image"], "Cmd": command, "User": body["User"], "Env": body["Env"],
               "WorkingDir": "/tmp", "Labels": body["Labels"], "AttachStdout": True, "AttachStderr": True,
               "Tty": False, "OpenStdin": False, "Entrypoint": [], "HostConfig": {
                   "NetworkMode": "none", "ReadonlyRootfs": True, "NanoCpus": 1_000_000_000,
                   "Memory": 2 * 1024 ** 3, "MemorySwap": 2 * 1024 ** 3, "PidsLimit": 128,
                   "CapDrop": ["ALL"], "SecurityOpt": ["no-new-privileges"], "AutoRemove": True,
                   "CgroupParent": host["CgroupParent"], "CgroupnsMode": "private",
                   "Tmpfs": {"/tmp": "rw,nosuid,nodev,size=268435456"},
                   "LogConfig": {"Type": "local", "Config": {"max-size": "1m", "max-file": "1"}},
                   "Mounts": []}}
    return rebuilt, candidate, result


class DockerConnection(http.client.HTTPConnection):
    def __init__(self, path, timeout=30):
        super().__init__("localhost", timeout=timeout)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(str(self.path))


class Proxy:
    def __init__(self, config):
        self.config = config
        self.records = {}
        self.lock = threading.RLock()

    def request(self, method, path, body=None, timeout=30):
        connection = DockerConnection(self.config.docker_socket, timeout)
        try:
            connection.request(method, path, body=body, headers={"Content-Type": "application/json"})
            response = connection.getresponse()
            raw = response.read(MAX_RESPONSE + 1)
            require(len(raw) <= MAX_RESPONSE, "Docker response exceeds limit")
            return response.status, dict(response.getheaders()), raw
        finally:
            connection.close()

    def create(self, body, name, run_id, version):
        rebuilt, candidate, output = canonical_config(body, name, run_id, self.config)
        with self.lock:
            require(len(self.records) < self.config.max_containers and name not in self.records,
                    "Evaluator container capacity reached")
            candidate_fd, output_fd, stage = None, None, None
            keep_stage = False
            try:
                candidate_fd, output_fd = directory_fd(candidate), directory_fd(output)
                require(os.fstat(candidate_fd).st_uid == self.config.worker_uid
                        and os.fstat(output_fd).st_uid == self.config.worker_uid)
                program = read_regular(candidate_fd, "program.py", 16 * 1024 ** 2, self.config.worker_uid)
                stage = self.config.staging_root / uuid.uuid4().hex
                stage.mkdir(mode=0o755)
                (stage / "candidate").mkdir(mode=0o755)
                (stage / "candidate" / "program.py").write_bytes(program)
                (stage / "candidate" / "program.py").chmod(0o444)
                (stage / "results").mkdir(mode=0o700)
                os.chown(stage / "results", self.config.worker_uid, self.config.worker_gid)
                # Persist the name before asking Docker to create. If transport
                # fails after daemon creation, restart recovery still knows it.
                (stage / "record.json").write_text(json.dumps({"id": None, "run": run_id, "name": name}))
                rebuilt["HostConfig"]["Mounts"] = [
                    {"Type": "bind", "Source": str(self.config.tasks_root), "Target": "/tasks", "ReadOnly": True},
                    {"Type": "bind", "Source": str(stage / "candidate"), "Target": "/candidate", "ReadOnly": True},
                    {"Type": "bind", "Source": str(stage / "results"), "Target": "/results", "ReadOnly": False}]
                keep_stage = True
                result = self.request("POST", version + "/containers/create?name=" + name, json.dumps(rebuilt).encode())
                if result[0] == 201:
                    ident = json_object(result[2]).get("Id")
                    require(type(ident) is str and re.fullmatch(r"[a-f0-9]{64}", ident))
                    (stage / "record.json").write_text(json.dumps({"id": ident, "run": run_id, "name": name}))
                    self.records[name] = {"id": ident, "run": run_id, "stage": stage, "output_fd": output_fd,
                                          "expires": time.monotonic() + int(rebuilt["Cmd"][11]) + 60,
                                          "candidate_sha256": hashlib.sha256(program).hexdigest()}
                    stage, output_fd = None, None
                elif 400 <= result[0] < 500:
                    keep_stage = False
                return result
            finally:
                for descriptor in (candidate_fd, output_fd):
                    if descriptor is not None:
                        os.close(descriptor)
                if stage is not None and not keep_stage:
                    shutil.rmtree(stage)

    def cgroup_info(self):
        status, _, raw = self.request("GET", "/info")
        require(status == 200)
        data = json_object(raw)
        require(data.get("CgroupDriver") == "cgroupfs" and data.get("CgroupVersion") == "2",
                "Canonical evaluator requires Docker cgroupfs on cgroup v2")
        return 200, {"Content-Type": "application/json"}, json.dumps(
            {"CgroupDriver": "cgroupfs", "CgroupVersion": "2"}).encode()

    def owned(self, ident, run_id):
        with self.lock:
            for name, record in self.records.items():
                if ident in (name, record["id"]):
                    require(record["run"] == run_id, "Container belongs to a different run")
                    return name, record
        raise Denied("Container is not owned by this proxy")

    def publish(self, record):
        """Only one bounded regular artifact crosses back; never follow links."""
        with self.lock:
            if record.get("closed"):
                return
            fd = directory_fd(record["stage"] / "results")
            try:
                raw = read_regular(fd, "native.json", MAX_RESPONSE, self.config.worker_uid)
                json_object(raw)
            except (OSError, ValueError, UnicodeError):
                return
            finally:
                os.close(fd)
            name = ".arena-proxy-" + uuid.uuid4().hex
            target = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=record["output_fd"])
            try:
                os.fchown(target, self.config.worker_uid, self.config.worker_gid)
                with os.fdopen(target, "wb", closefd=False) as stream:
                    stream.write(raw)
                os.rename(name, "native.json", src_dir_fd=record["output_fd"], dst_dir_fd=record["output_fd"])
            finally:
                os.close(target)
                try:
                    os.unlink(name, dir_fd=record["output_fd"])
                except FileNotFoundError:
                    pass

    def remove(self, name, record):
        with self.lock:
            self.publish(record)
            if not record.get("closed"):
                record["closed"] = True
                os.close(record["output_fd"])
                shutil.rmtree(record["stage"])
                self.records.pop(name, None)

    def reap(self):
        while True:
            time.sleep(10)
            with self.lock:
                expired = [(name, record) for name, record in self.records.items()
                           if time.monotonic() > record["expires"]]
            for name, record in expired:
                try:
                    self.request("DELETE", "/containers/" + record["id"] + "?force=1")
                    self.remove(name, record)
                except (OSError, ValueError, http.client.HTTPException):
                    pass

    def recover(self):
        """On restart, kill only persisted, label-verified owned containers."""
        for stage in self.config.staging_root.iterdir():
            require(not stage.is_symlink() and stage.is_dir() and RUN.fullmatch(stage.name))
            metadata = stage / "record.json"
            if metadata.exists():
                require(metadata.is_file() and not metadata.is_symlink() and metadata.stat().st_size <= 4096)
                record = json_object(metadata.read_bytes())
                require(set(record) == {"id", "run", "name"} and RUN.fullmatch(record["run"])
                        and (record["id"] is None or re.fullmatch(r"[a-f0-9]{64}", record["id"]))
                        and re.fullmatch(r"arena-eval-[a-f0-9]{32}", record["name"]))
                status, _, raw = self.request("GET", "/containers/" + (record["id"] or record["name"]) + "/json")
                if status != 404:
                    require(status == 200)
                    native = json_object(raw)
                    ident = native.get("Id")
                    require(type(ident) is str and re.fullmatch(r"[a-f0-9]{64}", ident)
                            and (record["id"] is None or ident == record["id"])
                            and native.get("Config", {}).get("Labels") ==
                            {"arena.evaluator": "canonical-v1", "arena.control-run": record["run"]})
                    deleted = self.request("DELETE", "/containers/" + ident + "?force=1")
                    require(deleted[0] in {204, 404})
            shutil.rmtree(stage)

    def close(self):
        for name, record in list(self.records.items()):
            try:
                result = self.request("DELETE", "/containers/" + record["id"] + "?force=1")
                if result[0] in {204, 404}:
                    self.remove(name, record)
            except (OSError, ValueError, http.client.HTTPException):
                pass  # Preserve the root-owned record for restart recovery.


def route(method, target):
    parsed = urlsplit(target)
    require(not parsed.scheme and not parsed.netloc and not parsed.fragment and "%" not in parsed.path)
    match = re.fullmatch(r"(?P<version>/v1\.[0-9]{1,3})?(?P<path>/[A-Za-z0-9_./-]+)", parsed.path)
    require(match is not None)
    version, path = match["version"] or "", match["path"]
    query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
    require(all(len(values) == 1 for values in query.values()))
    query = {key: values[0] for key, values in query.items()}
    if path in {"/_ping", "/version"}:
        require(method in {"GET", "HEAD"} and not query)
        return version, "info", None, None
    if path == "/info":
        require(method == "GET" and not query)
        return version, "cgroup_info", None, None
    if path == "/containers/create":
        require(method == "POST" and set(query) == {"name"})
        return version, "create", query["name"], None
    match = re.fullmatch(r"/containers/(arena-eval-[a-f0-9]{32}|[a-f0-9]{64})(?:/(json|start|attach|wait|logs|kill))?", path)
    require(match is not None)
    ident, action = match.groups()
    if action == "json":
        require(method == "GET" and not query)
    elif action == "start":
        require(method == "POST" and not query)
    elif action == "wait":
        require(method == "POST" and set(query) <= {"condition"}
                and query.get("condition", "not-running") in {"not-running", "next-exit", "removed"})
    elif action in {"attach", "logs"}:
        require(method == ("POST" if action == "attach" else "GET"))
        require(set(query) <= {"stream", "stdout", "stderr", "logs", "stdin", "follow", "tail", "timestamps"})
        require(query.get("stdin", "0") in {"0", "false"})
        require(all(value in {"0", "1", "true", "false"} for key, value in query.items() if key != "tail"))
        require(query.get("tail", "1000").isdigit() and int(query.get("tail", "1000")) <= 1000)
    elif action == "kill":
        require(method == "POST" and set(query) <= {"signal"} and query.get("signal", "KILL") in {"KILL", "SIGKILL", "9", "TERM", "SIGTERM", "15"})
    else:
        require(action is None and method == "DELETE" and set(query) <= {"force", "v", "link"})
        require(query.get("force", "0") in {"0", "1", "false", "true"}
                and query.get("v", "0") in {"0", "false"} and query.get("link", "0") in {"0", "false"})
        action = "delete"
    return version, action, ident, parsed.query


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(20)

    def reply(self, status, headers, raw):
        self.send_response(status)
        for key, value in headers.items():
            if key.lower() in {"content-type", "api-version", "docker-experimental", "ostype", "builder-version"}:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(raw)

    def handle_request(self):
        self.close_connection = True
        self.upgraded = False
        try:
            require(not self.headers.get_all("Transfer-Encoding") and not self.headers.get_all("Expect"))
            lengths = self.headers.get_all("Content-Length", [])
            require(len(lengths) <= 1)
            length = int(lengths[0]) if lengths else 0
            require(0 <= length <= MAX_BODY)
            run_id = peer_run(self.connection, self.server.proxy.config)
            version, action, ident, query = route(self.command, self.path)
            raw = self.rfile.read(length)
            require(len(raw) == length and (action == "create" or not raw))
            proxy = self.server.proxy
            if action == "info":
                result = proxy.request(self.command, self.path)
            elif action == "cgroup_info":
                result = proxy.cgroup_info()
            elif action == "create":
                result = proxy.create(json_object(raw), ident, run_id, version)
            else:
                name, record = proxy.owned(ident, run_id)
                suffix = "" if action == "delete" else "/" + action
                path = version + "/containers/" + record["id"] + suffix + ("?" + query if query else "")
                if action == "attach":
                    self.attach(path, record)
                    return
                if action == "wait":
                    self.wait(path, record)
                    return
                result = proxy.request(self.command, path, timeout=proxy.config.timeout_seconds + 30)
                if action in {"wait", "json", "delete"}:
                    proxy.publish(record)
                if action == "delete" and result[0] in {204, 404}:
                    proxy.remove(name, record)
            self.reply(*result)
        except (Denied, ValueError, KeyError, TypeError, UnicodeError, OSError, http.client.HTTPException):
            if not self.upgraded:
                try:
                    self.reply(403, {"Content-Type": "application/json"}, b'{"message":"Evaluator proxy denied or could not safely complete the request"}')
                except OSError:
                    pass

    def wait(self, path, record):
        # Docker CLI establishes /wait before /start and waits for its HTTP
        # headers. Buffering those headers until exit deadlocks that handshake.
        proxy = self.server.proxy
        connection = DockerConnection(proxy.config.docker_socket, proxy.config.timeout_seconds + 30)
        try:
            connection.request("POST", path, body=b"")
            response = connection.getresponse()
            self.send_response(response.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Transfer-Encoding", "chunked")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.flush()
            self.upgraded = True
            raw = response.read(MAX_RESPONSE + 1)
            require(len(raw) <= MAX_RESPONSE)
            proxy.publish(record)
            if raw:
                self.wfile.write(f"{len(raw):x}\r\n".encode() + raw + b"\r\n")
            self.wfile.write(b"0\r\n\r\n")
        finally:
            connection.close()

    def attach(self, path, record):
        # Docker uses an HTTP upgrade for multiplexed stdout/stderr. Only the
        # daemon-to-client direction is relayed: stdin/exec are never allowed.
        upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        upstream.settimeout(30)
        started = time.monotonic()
        try:
            upstream.connect(str(self.server.proxy.config.docker_socket))
            upstream.sendall(("POST " + path + " HTTP/1.1\r\nHost: localhost\r\nConnection: Upgrade\r\n"
                              "Upgrade: tcp\r\nContent-Length: 0\r\n\r\n").encode("ascii"))
            header = b""
            while b"\r\n\r\n" not in header:
                chunk = upstream.recv(4096)
                require(chunk and len(header) + len(chunk) <= 32768)
                header += chunk
            first, remainder = header.split(b"\r\n\r\n", 1)
            require(first.startswith((b"HTTP/1.1 101 ", b"HTTP/1.1 200 ")))
            self.upgraded = True
            self.connection.sendall(first + b"\r\n\r\n" + remainder)
            size = len(remainder)
            while time.monotonic() - started <= self.server.proxy.config.timeout_seconds + 30:
                try:
                    chunk = upstream.recv(65536)
                except socket.timeout:
                    continue
                if not chunk:
                    # Docker CLI can finish as soon as attach closes, before its
                    # concurrent wait handler finishes. Publish before that EOF.
                    self.server.proxy.publish(record)
                    return
                size += len(chunk)
                require(size <= MAX_STREAM, "Evaluator output exceeded its stream limit")
                self.connection.sendall(chunk)
        finally:
            upstream.close()

    do_GET = do_HEAD = do_POST = do_DELETE = do_PUT = do_PATCH = handle_request


class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    request_queue_size = 32

    def __init__(self, config):
        self.proxy = Proxy(config)
        self.slots = threading.BoundedSemaphore(64)
        super().__init__(str(config.socket_path), Handler)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    info = args.config.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
            "Proxy config must be a root-owned non-writable regular file")
    config = Config.read(args.config)
    config.validate_host()
    if config.socket_path.exists() or config.socket_path.is_symlink():
        info = config.socket_path.lstat()
        require(stat.S_ISSOCK(info.st_mode) and info.st_uid == 0, "Refusing to replace an unsafe socket path")
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            probe.connect(str(config.socket_path))
        except ConnectionRefusedError:
            config.socket_path.unlink()
        else:
            raise Denied("An evaluator proxy is already serving this socket")
        finally:
            probe.close()
    with Server(config) as server:
        server.proxy.cgroup_info()
        server.proxy.recover()
        os.chown(config.socket_path, 0, config.worker_gid)
        config.socket_path.chmod(0o660)
        threading.Thread(target=server.proxy.reap, daemon=True).start()
        def stop(signum, frame):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, stop)
        try:
            server.serve_forever(poll_interval=0.5)
        except KeyboardInterrupt:
            pass
        finally:
            server.proxy.close()
            config.socket_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
