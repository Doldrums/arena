"""Run-scoped Docker SDK capability for the pinned, prebuilt DGM experiment.

This service is deliberately separate from the canonical evaluator and SCiEL
brokers. It never builds/pulls images or mounts host paths into a container.
Native commands execute only inside approved, offline, resource-bound images.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import MISSING, dataclass
from datetime import datetime
import hashlib
import hmac
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import select
import signal
import socket
import socketserver
import sqlite3
import stat
import subprocess
import tarfile
import threading
import time
from urllib.parse import parse_qs, quote, unquote, urlencode, urlsplit
import uuid

from .evaluator_proxy import (Denied, DockerConnection, RUN, _peer_identity,
                              directory_fd, json_object, only_defaults,
                              read_regular, require)

PIN = "a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2"
HEX = re.compile(r"[a-f0-9]{64}\Z")
ALIAS = re.compile(r"(?:dgm|pb\.(?:base|env|eval)\.[a-zA-Z0-9_.-]+):latest\Z")
NATIVE_NAME = re.compile(r"(?:dgm-container-[0-9_]+|pb\.eval\.python__(?:dominoes|beer-song)\.[0-9_]+)\Z")
BOOTSTRAP = "/usr/local/bin/arena-dgm-bootstrap"
MAX_JSON = 1024 * 1024
MAX_TAR = 32 * 1024**2
MAX_EXPANDED = 128 * 1024**2
MAX_ENTRIES = 10000
MAX_STREAM = 4 * 1024**2
REQUEST_TIMEOUT = 30
LABEL = "arena.dgm-proxy"


def encoded(value):
    return json.dumps(value, allow_nan=False, separators=(",", ":")).encode()


def result(value, status=200):
    return status, {"Content-Type": "application/json"}, encoded(value)


def root_file(path, maximum=MAX_JSON):
    path = Path(path)
    fd = directory_fd(path.parent)
    try:
        info = os.stat(path.name, dir_fd=fd, follow_symlinks=False)
        require(info.st_uid == 0 and not info.st_mode & 0o077)
        return read_regular(fd, path.name, maximum, 0)
    finally:
        os.close(fd)


def atomic_record(root, name, value):
    """Persist only metadata through a held, link-free root directory FD."""
    require(re.fullmatch(r"[a-f0-9]{32}\.json", name))
    directory = directory_fd(root)
    temporary = ".pending-" + uuid.uuid4().hex
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=directory)
        try:
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(encoded(value)); stream.flush(); os.fsync(fd)
        finally:
            os.close(fd)
        os.rename(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
        os.fsync(directory)
    finally:
        try: os.unlink(temporary, dir_fd=directory)
        except FileNotFoundError: pass
        os.close(directory)


@dataclass(frozen=True)
class Config:
    socket_path: Path
    docker_socket: Path
    state_root: Path
    runs_root: Path
    queue_database: Path
    source_path: Path
    gateway_key_file: Path
    images: tuple[dict, ...]
    models: tuple[str, ...]
    network_id: str
    relay_url: str = "http://172.30.88.1:8789/v1"
    cgroup_root: str = "/arena-workers"
    worker_uid: int = 998
    worker_gid: int = 998
    max_containers: int = 4
    max_seconds: int = 7200
    container_cpus: int = 1
    container_memory_mb: int = 2048
    container_pids: int = 256

    @classmethod
    def read(cls, path):
        value = json_object(root_file(path))
        required = {key for key, field in cls.__dataclass_fields__.items()
                    if field.default is MISSING and field.default_factory is MISSING}
        require(required <= value.keys() and set(value) <= cls.__dataclass_fields__.keys())
        for key in ("socket_path", "docker_socket", "state_root", "runs_root", "queue_database", "source_path", "gateway_key_file"):
            value[key] = Path(value[key])
            require(value[key].is_absolute() and ".." not in value[key].parts)
        value["images"] = tuple(value["images"])
        value["models"] = tuple(value["models"])
        config = cls(**value)
        config.validate()
        return config

    def validate(self):
        require(HEX.fullmatch(self.network_id))
        endpoint = urlsplit(self.relay_url)
        address = ipaddress.ip_address(endpoint.hostname)
        require(endpoint.scheme == "http" and endpoint.path == "/v1" and not endpoint.query
                and not endpoint.fragment and endpoint.username is None and endpoint.password is None
                and endpoint.port == 8789 and isinstance(address, ipaddress.IPv4Address)
                and address.is_private and not address.is_loopback)
        require(re.fullmatch(r"/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+", self.cgroup_root))
        require(self.models and all(re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", x) for x in self.models))
        require(self.images and len(self.images) <= 8)
        aliases = set()
        for binding in self.images:
            require(set(binding) == {"alias", "reference", "image_id", "parent", "runnable"})
            require(ALIAS.fullmatch(binding["alias"]) and binding["alias"] not in aliases)
            require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[a-f0-9]{64}", binding["reference"]))
            require(re.fullmatch(r"sha256:[a-f0-9]{64}", binding["image_id"]) and type(binding["runnable"]) is bool)
            aliases.add(binding["alias"])
        require("dgm:latest" in aliases)
        require(all(b["parent"] is None or b["parent"] in aliases for b in self.images))
        for key, low, high in (("worker_uid", 1, 2**31), ("worker_gid", 1, 2**31),
                              ("max_containers", 1, 4), ("max_seconds", 1, 86400),
                              ("container_cpus", 1, 4), ("container_memory_mb", 512, 8192),
                              ("container_pids", 64, 512)):
            value = getattr(self, key); require(type(value) is int and low <= value <= high)

    def host_check(self):
        require(os.geteuid() == 0 and hasattr(socket, "SO_PEERCRED"))
        for path in (self.state_root, self.socket_path.parent, self.source_path):
            fd = directory_fd(path); os.close(fd)
            for ancestor in (path, *path.parents):
                info = ancestor.stat()
                require(info.st_uid == 0 and not info.st_mode & 0o022)
        require(stat.S_IMODE(self.state_root.stat().st_mode) == 0o700)
        key = root_file(self.gateway_key_file, 4096).strip()
        require(16 <= len(key) <= 4096 and all(32 < c < 127 for c in key))


def peer_run(connection, config):
    tail = _peer_identity(connection, config)
    require(tail[1:] == ["main"], "Only the admitted native host process may use DGM Docker")
    return tail[0]


def admission(config, run_id):
    require(RUN.fullmatch(run_id))
    require(not config.queue_database.is_symlink())
    with sqlite3.connect("file:" + quote(str(config.queue_database)) + "?mode=ro", uri=True, timeout=3) as db:
        db.row_factory = sqlite3.Row
        row = db.execute("SELECT state,held,cancel_requested,snapshot_sha256,model,timeout_seconds,cpus,memory_mb,pids FROM runs WHERE id=?", (run_id,)).fetchone()
    require(row is not None and row["state"] == "running" and row["held"] == 1 and not row["cancel_requested"],
            "Run is not actively admitted")
    fd = directory_fd(config.runs_root / run_id)
    try: raw = read_regular(fd, "snapshot.json", MAX_JSON, config.worker_uid)
    finally: os.close(fd)
    require(hashlib.sha256(raw).hexdigest() == row["snapshot_sha256"])
    snapshot = json_object(raw); template = snapshot["template"]; spec = template["spec"]
    require(template["framework"] == spec["framework"] == "dgm"
            and spec["source_dir"] == str(config.source_path)
            and spec["request"].get("benchmark") == "polyglot"
            and spec["output_dir"] == "{output_dir}")
    require(snapshot["cgroup_root"] == "/sys/fs/cgroup" + config.cgroup_root)
    require(template["model"] == row["model"] and row["model"] in config.models)
    seconds = row["timeout_seconds"]
    require(type(seconds) is int and 1 <= seconds <= config.max_seconds and spec["timeout_seconds"] == seconds)
    limits = {"cpus": config.container_cpus, "memory_mb": config.container_memory_mb, "pids": config.container_pids}
    for key, minimum in limits.items():
        require(type(row[key]) is int and row[key] >= minimum and template["resources"][key] == row[key])
    return {"model": row["model"], "seconds": seconds, "snapshot_sha256": row["snapshot_sha256"]}


def container_path(value):
    require(type(value) is str and value.isascii() and len(value) <= 512 and not any(ord(c) < 32 for c in value)
            and "\\" not in value)
    path = PurePosixPath(value)
    require(path.is_absolute() and ".." not in path.parts and str(path) == value
            and path.parts[1] in {"dgm", "testbed"})
    return value


def sanitize_tar(raw, expected_root=None):
    """Repack both directions; native DGM calls extractall on downloads."""
    require(len(raw) <= MAX_TAR, "Archive exceeds wire limit")
    output = io.BytesIO(); total = 0; seen = set(); file_paths = set()
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as source, tarfile.open(fileobj=output, mode="w:") as target:
            for member in source:
                name = member.name.rstrip("/")
                path = PurePosixPath(name)
                require(name not in {"", "."} and len(name) <= 4096 and not any(ord(c) < 32 for c in name)
                        and "\\" not in name and not path.is_absolute() and ".." not in path.parts
                        and str(path) == name and name not in seen)
                require(expected_root is None or path.parts[0] == expected_root,
                        "Downloaded archive does not match its requested root")
                require(len(seen) < MAX_ENTRIES and (member.isfile() or member.isdir())
                        and not member.issparse() and not member.linkname)
                require(not any(str(parent) in file_paths for parent in path.parents))
                if member.isfile():
                    require(not any(existing.startswith(name + "/") for existing in seen))
                    file_paths.add(name)
                seen.add(name)
                require(member.size >= 0 and (member.isfile() or member.size == 0))
                total += member.size; require(total <= MAX_EXPANDED)
                clean = tarfile.TarInfo(name)
                clean.type = tarfile.REGTYPE if member.isfile() else tarfile.DIRTYPE
                clean.mode = (member.mode & 0o777) if member.isfile() else 0o755
                clean.size = member.size; clean.mtime = max(0, min(int(member.mtime), 2**31 - 1))
                clean.uid = clean.gid = 0
                stream = source.extractfile(member) if member.isfile() else None
                target.addfile(clean, stream)
                if stream: stream.close()
                require(output.tell() <= MAX_TAR)
    except (tarfile.TarError, OverflowError) as exc:
        raise Denied("Invalid archive") from exc
    require(output.tell() <= MAX_TAR)
    return output.getvalue()


def route(method, target):
    parsed = urlsplit(target)
    require(not parsed.scheme and not parsed.netloc and not parsed.fragment and len(target) <= 16384)
    path = unquote(parsed.path)
    require("%" not in path and ".." not in path.split("/") and "\\" not in path)
    match = re.fullmatch(r"(/v1\.[0-9]{1,3})?(/.*)", path); require(match is not None)
    version, path = match[1] or "", match[2]
    query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
    require(all(len(v) == 1 for v in query.values()))
    query = {k: v[0] for k, v in query.items()}
    query = {k: v.lower() if v in {"True", "False"} else v for k, v in query.items()}
    if path in {"/_ping", "/version", "/info"}:
        require(method in {"GET", "HEAD"} and not query)
        return version, path[1:], None, query
    if path == "/images/json":
        require(method == "GET" and set(query) <= {"all", "filters", "only_ids"})
        require(query.get("all", "0") in {"0", "1", "false", "true"} and query.get("only_ids", "0") in {"0", "false"})
        require(query.get("filters", "{}") == "{}")
        return version, "images", None, {}
    match = re.fullmatch(r"/images/(.+)/json", path)
    if match:
        require(method == "GET" and not query)
        return version, "image", match[1], {}
    if path == "/containers/create":
        require(method == "POST" and "name" in query and set(query) <= {"name", "platform"}
                and query.get("platform", "linux/amd64") in {"linux/amd64", "linux/x86_64"})
        return version, "create", query["name"], {}
    match = re.fullmatch(r"/exec/([a-f0-9]{64})/(start|json)", path)
    if match:
        require(not query and method == ("POST" if match[2] == "start" else "GET"))
        return version, "exec_" + match[2], match[1], {}
    match = re.fullmatch(r"/containers/([^/]+)(?:/(json|start|stop|kill|wait|logs|archive|exec))?", path)
    require(match is not None)
    ident, action = match.groups()
    require(HEX.fullmatch(ident) or NATIVE_NAME.fullmatch(ident) or re.fullmatch(r"arena-dgm-[a-f0-9]{32}-[a-f0-9]{32}", ident))
    if action == "archive":
        require(method in {"GET", "PUT"} and set(query) <= {"path", "noOverwriteDirNonDir", "copyUIDGID"}
                and "path" in query and query.get("copyUIDGID", "0") in {"0", "false"})
        require(query.get("noOverwriteDirNonDir", "0") in {"0", "1", "false", "true"})
        container_path(query["path"])
        action = "archive_get" if method == "GET" else "archive_put"
    elif action == "logs":
        require(method == "GET" and set(query) <= {"stdout", "stderr", "stream", "follow", "timestamps", "tail"})
        require(all(v in {"0", "1", "true", "false"} for k, v in query.items() if k != "tail"))
        require(query.get("tail", "all") == "all" or (query["tail"].isdigit() and int(query["tail"]) <= 10000))
        require(query.get("follow", "0") in {"0", "false"})
    elif action == "stop":
        require(method == "POST" and set(query) <= {"t"} and query.get("t", "10").isdigit() and int(query.get("t", "10")) <= 15)
    elif action == "kill":
        require(method == "POST" and set(query) <= {"signal"} and query.get("signal", "KILL") in {"KILL", "SIGKILL", "9", "TERM", "SIGTERM", "15"})
    elif action == "wait":
        require(method == "POST" and set(query) <= {"condition"} and query.get("condition", "not-running") == "not-running")
    elif action is None:
        require(method == "DELETE" and set(query) <= {"force", "v", "link"}
                and query.get("force", "0") in {"0", "1", "true", "false"}
                and query.get("v", "0") in {"0", "false"} and query.get("link", "0") in {"0", "false"})
        action = "delete"
    else:
        require(not query and method == ("GET" if action == "json" else "POST"))
    return version, action, ident, query


class Proxy:
    def __init__(self, config):
        self.config = config
        self.records = {}; self.execs = {}; self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.gateway_key = None

    def request(self, method, path, body=None, *, maximum=MAX_JSON, timeout=30, content_type="application/json"):
        connection = DockerConnection(self.config.docker_socket, timeout)
        try:
            connection.request(method, path, body=body, headers={"Content-Type": content_type})
            response = connection.getresponse(); raw = response.read(maximum + 1)
            require(len(raw) <= maximum, "Docker response exceeds bound")
            return response.status, dict(response.getheaders()), raw
        finally:
            connection.close()

    def binding(self, alias):
        matches = [item for item in self.config.images if alias in (item["alias"], item["reference"], item["image_id"])]
        require(len(matches) == 1, "Image is not approved")
        return matches[0]

    def image(self, alias):
        binding = self.binding(alias)
        status, _, raw = self.request("GET", "/images/" + quote(binding["reference"], safe="") + "/json")
        require(status == 200, "Approved image is not present; builds and pulls are disabled")
        native = json_object(raw)
        require(native.get("Id") == binding["image_id"] and binding["reference"] in (native.get("RepoDigests") or [])
                and binding["alias"] in (native.get("RepoTags") or []), "Image identity or alias changed")
        # Inspect the alias too: a stale RepoTags field is not an alias authority.
        alias_status, _, alias_raw = self.request("GET", "/images/" + quote(binding["alias"], safe="") + "/json")
        require(alias_status == 200 and json_object(alias_raw).get("Id") == binding["image_id"])
        require(native.get("Os") == "linux" and native.get("Architecture") == "amd64")
        cfg = native.get("Config", {})
        require(not cfg.get("Volumes") and not cfg.get("Healthcheck"))
        if binding["runnable"]:
            require(cfg.get("Entrypoint") == [BOOTSTRAP] and cfg.get("Cmd") == ["tail", "-f", "/dev/null"]
                    and cfg.get("Labels", {}).get("io.arena.dgm.contract") == "dgm-prebuilt-v1"
                    and cfg.get("Labels", {}).get("org.opencontainers.image.revision") == PIN)
        return native

    def preflight(self):
        status, _, raw = self.request("GET", "/info"); data = json_object(raw)
        require(status == 200 and data.get("CgroupDriver") == "cgroupfs" and data.get("CgroupVersion") == "2")
        status, _, raw = self.request("GET", "/networks/" + self.config.network_id)
        network = json_object(raw)
        require(status == 200 and network.get("Id") == self.config.network_id and network.get("Driver") == "bridge"
                and network.get("Internal") is True and not network.get("EnableIPv6"))
        options = network.get("Options") or {}
        require(options.get("com.docker.network.bridge.enable_icc") == "false"
                and options.get("com.docker.network.bridge.name") == "br-arena-dgm")
        gateway = urlsplit(self.config.relay_url).hostname
        require(any(item.get("Gateway") == gateway for item in network.get("IPAM", {}).get("Config", [])))
        # Internal Docker networks alone still permit access to host services.
        # A root-managed INPUT rule is mandatory, including non-gateway host IPs.
        firewall = ["iptables", "-w", "-C", "INPUT", "-i", "br-arena-dgm", "-j", "ARENA_DGM_HOST"]
        require(subprocess.run(firewall, capture_output=True, timeout=10).returncode == 0,
                "DGM bridge host-access firewall is missing")
        input_rules = subprocess.run(["iptables", "-w", "-S", "INPUT"], capture_output=True, timeout=10)
        first_rule = next((line for line in input_rules.stdout.decode().splitlines() if line.startswith("-A ")), None)
        require(input_rules.returncode == 0 and first_rule == "-A INPUT -i br-arena-dgm -j ARENA_DGM_HOST",
                "DGM host-access policy must precede broader host accepts")
        checked = subprocess.run(["iptables", "-w", "-S", "ARENA_DGM_HOST"], capture_output=True, timeout=10)
        expected = ["-N ARENA_DGM_HOST",
                    f"-A ARENA_DGM_HOST -d {gateway}/32 -p tcp -m tcp --dport 8789 -j ACCEPT",
                    "-A ARENA_DGM_HOST -j DROP"]
        require(checked.returncode == 0 and checked.stdout.decode().splitlines() == expected,
                "DGM host firewall differs from the reviewed relay-only policy")
        inspected = {b["alias"]: self.image(b["alias"]) for b in self.config.images}
        for b in self.config.images:
            if b["parent"]:
                child = datetime.fromisoformat(inspected[b["alias"]]["Created"].replace("Z", "+00:00"))
                parent = datetime.fromisoformat(inspected[b["parent"]]["Created"].replace("Z", "+00:00"))
                require(child.tzinfo is not None and parent.tzinfo is not None and child >= parent,
                        "Prebuilt images are older than their native parent")
        self.gateway_key = root_file(self.config.gateway_key_file, 4096).strip().decode("ascii")

    def persist(self, record):
        fields = {k: v for k, v in record.items() if k != "busy"}
        require(len(encoded(fields)) <= MAX_JSON, "Root journal exceeded its recovery bound")
        atomic_record(self.config.state_root, record["record_id"] + ".json", fields)

    def labels(self, record):
        return {LABEL: "dgm-prebuilt-v1", "arena.control-run": record["run"], "arena.record-id": record["record_id"]}

    def verify_owned_inspect(self, native, record):
        labels = native.get("Config", {}).get("Labels") or {}
        # Docker merges image labels (including the required source/contract
        # labels) with the container labels supplied by this service.
        require(all(labels.get(k) == v for k, v in self.labels(record).items())
                and native.get("Image") == record["image_id"])

    def create(self, body, name, run_id, admitted, version):
        require(NATIVE_NAME.fullmatch(name))
        only_defaults(body, {"Image", "Cmd", "User", "HostConfig", "AttachStdout", "AttachStderr", "NetworkDisabled"})
        require(body.get("Cmd") in (None, [], ["tail", "-f", "/dev/null"]))
        require(body.get("User") in (None, "", "root", "0", "0:0") and not body.get("NetworkDisabled"))
        host = body.get("HostConfig") or {}; only_defaults(host, {"NetworkMode", "NanoCpus"})
        hint = host.get("NanoCpus")
        require(host.get("NetworkMode") in (None, "", "default")
                and (hint is None or (type(hint) is int and 0 <= hint <= self.config.container_cpus * 10**9)))
        binding = self.binding(body.get("Image")); require(binding["runnable"])
        self.image(binding["alias"])
        require(self.gateway_key is not None)
        with self.lock:
            require(sum(r["run"] == run_id for r in self.records.values()) < self.config.max_containers
                    and len(self.records) < 32)
            fd = directory_fd(self.config.state_root)
            try:
                names = os.listdir(fd)
                require(len(names) < 8192, "Operator must archive old proxy journals before admitting more containers")
                same_run = 0
                for filename in names:
                    if not re.fullmatch(r"[a-f0-9]{32}\.json", filename): continue
                    old = json_object(read_regular(fd, filename, MAX_JSON, 0))
                    same_run += old.get("run") == run_id
                require(same_run < 128, "Run exhausted its native container creation budget")
            finally: os.close(fd)
            if any(r["run"] == run_id and r["native_name"] == name for r in self.records.values()):
                return result({"message": "Container name is already in use for this run"}, 409)
            rid = uuid.uuid4().hex
            record = {"schema": "arena.dgm-container/1", "record_id": rid, "run": run_id,
                      "name": "arena-dgm-" + run_id + "-" + rid, "native_name": name, "id": None,
                      "image": binding["reference"], "image_id": binding["image_id"], "source_commit": PIN,
                      "model": admitted["model"], "snapshot_sha256": admitted["snapshot_sha256"],
                      "expires": time.time() + admitted["seconds"], "state": "creating", "transfers": []}
            self.records[rid] = record; self.persist(record)
            # Every field below is constructed by the root service, never merged.
            rebuilt = {"Image": binding["image_id"], "Entrypoint": [BOOTSTRAP], "Cmd": ["tail", "-f", "/dev/null"],
                       "User": "0:0", "WorkingDir": "/dgm", "Tty": False, "OpenStdin": False,
                       "Env": ["OPENAI_API_KEY=" + self.gateway_key, "ARENA_DGM_MODEL=" + admitted["model"],
                               "ARENA_DGM_GATEWAY_URL=" + self.config.relay_url, "PYTHONDONTWRITEBYTECODE=1"],
                       "Labels": self.labels(record), "HostConfig": {
                           "ReadonlyRootfs": True, "Privileged": False, "CapDrop": ["ALL"],
                           "SecurityOpt": ["no-new-privileges:true"], "NetworkMode": self.config.network_id,
                           "Dns": ["127.0.0.1"],
                           "CgroupParent": self.config.cgroup_root + "/arena-control-" + run_id,
                           "CgroupnsMode": "private", "NanoCpus": self.config.container_cpus * 10**9,
                           "Memory": self.config.container_memory_mb * 1024**2,
                           "MemorySwap": self.config.container_memory_mb * 1024**2,
                           "PidsLimit": self.config.container_pids, "RestartPolicy": {"Name": "no"},
                           "Tmpfs": {"/dgm": "rw,nosuid,nodev,size=768m,mode=0755", "/testbed": "rw,nosuid,nodev,size=768m,mode=0755",
                                     "/tmp": "rw,nosuid,nodev,size=256m,mode=1777", "/root": "rw,nosuid,nodev,size=64m,mode=0700"},
                           "LogConfig": {"Type": "local", "Config": {"max-size": "4m", "max-file": "1", "compress": "false"}}}}
            status, headers, raw = self.request("POST", version + "/containers/create?" + urlencode({"name": record["name"]}), encoded(rebuilt))
            if status == 201:
                ident = json_object(raw).get("Id"); require(type(ident) is str and HEX.fullmatch(ident))
                record.update(id=ident, state="created"); self.persist(record)
            elif 400 <= status < 500:
                record["state"] = "rejected"; self.persist(record); self.records.pop(rid)
            return status, headers, raw

    def owned(self, ident, run_id):
        with self.lock:
            found = [r for r in self.records.values() if r["run"] == run_id and ident in (r["id"], r["native_name"], r["name"])]
            require(len(found) <= 1)
            return found[0] if found else None

    def delete(self, record):
        ident = record["id"] or record["name"]
        status, _, raw = self.request("GET", "/containers/" + ident + "/json")
        if status != 404:
            require(status == 200)
            native = json_object(raw)
            self.verify_owned_inspect(native, record)
            deleted = self.request("DELETE", "/containers/" + native["Id"] + "?force=1")
            require(deleted[0] in {204, 404}, "Container cleanup is unconfirmed")
        with self.lock:
            record["state"] = "removed"; self.persist(record)
            self.records.pop(record["record_id"], None)
            self.execs = {key: value for key, value in self.execs.items() if value != record["record_id"]}

    def recover(self):
        fd = directory_fd(self.config.state_root)
        try:
            for name in os.listdir(fd):
                if name.startswith(".pending-"): continue
                require(re.fullmatch(r"[a-f0-9]{32}\.json", name))
                record = json_object(read_regular(fd, name, MAX_JSON, 0))
                require(record.get("schema") == "arena.dgm-container/1" and record["record_id"] + ".json" == name
                        and RUN.fullmatch(record["run"]) and record["name"] == "arena-dgm-" + record["run"] + "-" + record["record_id"]
                        and (record["id"] is None or HEX.fullmatch(record["id"]))
                        and record["image_id"] == self.binding(record["image"])["image_id"])
                if record["state"] not in {"removed", "rejected"}:
                    self.delete(record)
        finally: os.close(fd)

    def reap_once(self):
        with self.lock: records = list(self.records.values())
        for record in records:
            try:
                admission(self.config, record["run"])
                require(time.time() < record["expires"])
            except (ValueError, KeyError, OSError, sqlite3.Error):
                try: self.delete(record)
                except (ValueError, OSError, http.client.HTTPException): pass

    def reap(self):
        while not self.stop_event.wait(2): self.reap_once()

    def close(self):
        self.stop_event.set()
        for record in list(self.records.values()):
            try: self.delete(record)
            except (ValueError, OSError, http.client.HTTPException): pass

    def exec_create(self, record, body, version):
        only_defaults(body, {"AttachStdout", "AttachStderr", "Cmd", "Env", "WorkingDir", "User", "Container"})
        require(body.get("Container", record["id"]) == record["id"])
        command = body.get("Cmd")
        require(type(command) is list and command and len(command) <= 1024
                and all(type(v) is str and "\x00" not in v for v in command)
                and sum(len(v.encode()) for v in command) <= 256 * 1024)
        cwd = body.get("WorkingDir") or "/"
        require(cwd == "/" or container_path(cwd))
        require(body.get("User") in (None, "", "root", "0", "0:0"))
        supplied = body.get("Env") or []
        require(type(supplied) is list and len(supplied) <= 6)
        seen = set()
        for value in supplied:
            require(type(value) is str and len(value) <= 8192)
            key, _, value = value.partition("=")
            require(key not in seen and key in {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AWS_REGION", "AWS_REGION_NAME", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"})
            seen.add(key)
            if key == "OPENAI_API_KEY": require(value == self.gateway_key)
            else: require(value in {"", "None"}, "Only the fixed local gateway provider is available")
        rebuilt = {"AttachStdout": True, "AttachStderr": True, "AttachStdin": False,
                   "Tty": False, "Privileged": False, "User": "0:0", "Cmd": command, "WorkingDir": cwd}
        response = self.request("POST", version + "/containers/" + record["id"] + "/exec", encoded(rebuilt))
        if response[0] == 201:
            ident = json_object(response[2]).get("Id"); require(type(ident) is str and HEX.fullmatch(ident))
            with self.lock:
                require(len(self.execs) < 10000)
                self.execs[ident] = record["record_id"]
        return response

    def wait_ready(self, record, version):
        deadline = min(record["expires"], time.time() + 30)
        while time.time() < deadline:
            status, _, raw = self.request("POST", version + "/containers/" + record["id"] + "/exec",
                                           encoded({"Cmd": ["test", "-f", "/tmp/.arena-dgm-ready"],
                                                    "AttachStdout": True, "AttachStderr": True}))
            require(status == 201)
            ident = json_object(raw).get("Id"); require(type(ident) is str and HEX.fullmatch(ident))
            started = self.request("POST", version + "/exec/" + ident + "/start", b'{"Detach":false,"Tty":false}')
            require(started[0] == 200)
            inspected = self.request("GET", version + "/exec/" + ident + "/json")
            require(inspected[0] == 200)
            if json_object(inspected[2]).get("ExitCode") == 0: return
            time.sleep(0.1)
        self.delete(record)
        raise Denied("Approved image bootstrap did not become ready")

    def dispatch(self, method, target, raw, run_id, admitted):
        version, action, ident, query = route(method, target)
        require(action in {"create", "exec", "exec_start", "archive_put"} or not raw)
        if action in {"_ping", "version"}:
            return self.request(method, version + "/" + action)
        if action == "info":
            status, _, native = self.request("GET", "/info"); data = json_object(native)
            return result({k: data[k] for k in ("CgroupDriver", "CgroupVersion")}, status)
        if action == "image":
            native = self.image(ident)
            return result({k: native[k] for k in ("Id", "Created", "RepoTags", "RepoDigests", "Os", "Architecture")})
        if action == "images":
            status, _, native = self.request("GET", "/images/json?all=1")
            require(status == 200)
            rows = json.loads(native); require(type(rows) is list)
            ids = {b["image_id"] for b in self.config.images}; aliases = {b["alias"] for b in self.config.images}
            return result([{**{k: row[k] for k in ("Id", "Created", "Size") if k in row},
                            "RepoTags": [v for v in row.get("RepoTags") or [] if v in aliases]}
                           for row in rows if row.get("Id") in ids])
        if action == "create": return self.create(json_object(raw), ident, run_id, admitted, version)
        if action.startswith("exec_"):
            with self.lock:
                record = self.records.get(self.execs.get(ident))
            require(record is not None and record["run"] == run_id)
            if action == "exec_start":
                body = json_object(raw)
                require(set(body) <= {"Detach", "Tty"} and not body.get("Detach") and not body.get("Tty"))
                return {"stream": version + "/exec/" + ident + "/start", "record": record}
            status, headers, native = self.request("GET", version + "/exec/" + ident + "/json")
            if status != 200: return status, headers, native
            data = json_object(native)
            return result({k: data[k] for k in ("ID", "Running", "ExitCode", "ContainerID") if k in data})
        record = self.owned(ident, run_id)
        if record is None: return result({"message": "No such container in this run"}, 404)
        require(record["id"] is not None and time.time() < record["expires"])
        prefix = version + "/containers/" + record["id"]
        if action == "exec": return self.exec_create(record, json_object(raw), version)
        if action == "delete":
            self.delete(record)
            return 204, {}, b""
        if action.startswith("archive_"):
            native_path = prefix + "/archive?" + urlencode({"path": query["path"]})
            if action == "archive_put":
                clean = sanitize_tar(raw)
                response = self.request("PUT", native_path, clean, content_type="application/x-tar")
            else:
                response = self.request("GET", native_path, maximum=MAX_TAR)
                if response[0] != 200: return response
                headers = {k: v for k, v in response[1].items() if k.lower() in {"content-type", "x-docker-container-path-stat"}}
                stat_headers = [v for k, v in headers.items() if k.lower() == "x-docker-container-path-stat"]
                require(len(stat_headers) == 1 and len(stat_headers[0]) <= 8192)
                item = json_object(base64.b64decode(stat_headers[0], validate=True))
                require(not item.get("linkTarget") and type(item.get("name")) is str
                        and item["name"] == PurePosixPath(query["path"]).name)
                clean = sanitize_tar(response[2], item["name"])
                response = response[0], headers, clean
            with self.lock:
                require(len(record["transfers"]) < 1024)
                record["transfers"].append({"operation": action, "path": query["path"], "bytes": len(clean),
                                            "sha256": hashlib.sha256(clean).hexdigest(), "status": response[0]})
                self.persist(record)
            return response
        suffix = "/" + action + ("?" + urlencode(query) if query else "")
        response = self.request(method, prefix + suffix, maximum=MAX_STREAM if action == "logs" else MAX_JSON,
                                timeout=min(30 if action != "wait" else self.config.max_seconds, max(1, record["expires"] - time.time())))
        if action == "start" and response[0] in {204, 304}:
            self.wait_ready(record, version)
        if action == "json" and response[0] == 200:
            data = json_object(response[2])
            # Do not disclose gateway credentials or host process IDs through SDK inspection.
            return result({"Id": data["Id"], "Name": data["Name"], "Image": data["Image"],
                           "State": {k: v for k, v in data.get("State", {}).items() if k != "Pid"},
                           "Config": {"Image": record["image"], "Labels": self.labels(record)}})
        return response


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args): pass

    def setup(self):
        super().setup(); self.connection.settimeout(30)

    def reply(self, status, headers, raw):
        self.send_response(status)
        for key, value in headers.items():
            if key.lower() in {"content-type", "api-version", "ostype", "docker-experimental", "x-docker-container-path-stat"}:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(raw))); self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD": self.wfile.write(raw)

    def handle_request(self):
        self.close_connection = True; self.upgraded = False
        try:
            proxy = self.server.proxy
            require(not self.headers.get_all("Transfer-Encoding") and not self.headers.get_all("Expect"))
            lengths = self.headers.get_all("Content-Length", []); require(len(lengths) <= 1)
            length = int(lengths[0]) if lengths else 0
            _, action, _, _ = route(self.command, self.path)
            require(0 <= length <= (MAX_TAR if action == "archive_put" else MAX_JSON))
            run_id = peer_run(self.connection, proxy.config)
            admitted = admission(proxy.config, run_id)
            raw = self.rfile.read(length); require(len(raw) == length)
            response = proxy.dispatch(self.command, self.path, raw, run_id, admitted)
            if type(response) is dict: self.stream_exec(response["stream"], response["record"])
            else: self.reply(*response)
        except (ValueError, KeyError, TypeError, OSError, http.client.HTTPException, sqlite3.Error):
            if not self.upgraded:
                try: self.reply(*result({"message": "DGM proxy denied or could not safely complete the request"}, 403))
                except OSError: pass

    def stream_exec(self, path, record):
        """Real Docker hijack, stdout/stderr direction only, no interactive stdin."""
        proxy = self.server.proxy
        upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        upstream.settimeout(30); complete = False
        try:
            upstream.connect(str(proxy.config.docker_socket))
            body = b'{"Detach":false,"Tty":false}'
            request = ("POST " + path + " HTTP/1.1\r\nHost: localhost\r\nConnection: Upgrade\r\nUpgrade: tcp\r\n"
                       "Content-Type: application/json\r\nContent-Length: " + str(len(body)) + "\r\n\r\n").encode() + body
            upstream.sendall(request)
            header = b""
            while b"\r\n\r\n" not in header:
                chunk = upstream.recv(4096); require(chunk and len(header) + len(chunk) <= 32768)
                header += chunk
            first, rest = header.split(b"\r\n\r\n", 1)
            require(first.startswith((b"HTTP/1.1 101 ", b"HTTP/1.1 200 ")))
            upstream.settimeout(1)
            # The upstream raw stream is Docker's native multiplex format.
            self.upgraded = True
            self.connection.sendall(b"HTTP/1.1 101 UPGRADED\r\nContent-Type: application/vnd.docker.raw-stream\r\nConnection: Upgrade\r\nUpgrade: tcp\r\n\r\n" + rest)
            size = len(rest)
            while time.time() < record["expires"] and not proxy.stop_event.is_set():
                if select.select([self.connection], [], [], 0)[0]:
                    # Neither EOF nor caller input is valid during one-way exec.
                    raise Denied("Exec client disconnected or attempted stdin")
                try: chunk = upstream.recv(65536)
                except socket.timeout: continue
                if not chunk: complete = True; return
                size += len(chunk); require(size <= MAX_STREAM, "Native exec output exceeded bound")
                self.connection.sendall(chunk)
        finally:
            upstream.close()
            if not complete:
                # A lost exec transport must not leave an unobserved paid process.
                proxy.delete(record)

    do_GET = do_HEAD = do_POST = do_PUT = do_DELETE = do_PATCH = handle_request


class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    request_queue_size = 32

    def __init__(self, config):
        self.proxy = Proxy(config); self.slots = threading.BoundedSemaphore(32)
        super().__init__(str(config.socket_path), Handler)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False): request.close(); return
        try: super().process_request(request, address)
        except BaseException: self.slots.release(); raise

    def process_request_thread(self, request, address):
        try: super().process_request_thread(request, address)
        finally: self.slots.release()


class RelayHandler(BaseHTTPRequestHandler):
    """Only an owned active container may reach the fixed loopback model API."""
    protocol_version = "HTTP/1.1"

    def setup(self):
        super().setup()
        self.connection.settimeout(REQUEST_TIMEOUT)

    def log_message(self, *args): pass

    def handle_request(self):
        self.close_connection = True; sent = False
        connection = None
        try:
            proxy = self.server.proxy
            require((self.command, self.path) in {("GET", "/v1/models"), ("POST", "/v1/responses"), ("POST", "/v1/chat/completions")})
            require(not self.headers.get_all("Transfer-Encoding") and not self.headers.get_all("Expect"))
            auth = self.headers.get_all("Authorization", [])
            require(len(auth) == 1 and hmac.compare_digest(auth[0], "Bearer " + proxy.gateway_key))
            with proxy.lock: records = list(proxy.records.values())
            found = []
            for record in records:
                if record["id"] is None: continue
                status, _, raw = proxy.request("GET", "/containers/" + record["id"] + "/json")
                if status != 200: continue
                info = json_object(raw)
                proxy.verify_owned_inspect(info, record)
                networks = info.get("NetworkSettings", {}).get("Networks", {}).values()
                if any(v.get("NetworkID") == proxy.config.network_id and v.get("IPAddress") == self.client_address[0] for v in networks):
                    found.append(record)
            require(len(found) == 1 and time.time() < found[0]["expires"])
            admitted = admission(proxy.config, found[0]["run"])
            lengths = self.headers.get_all("Content-Length", []); require(len(lengths) <= 1)
            length = int(lengths[0]) if lengths else 0
            require(0 <= length <= MAX_JSON and (self.command == "POST" or length == 0))
            self.connection.settimeout(30)
            body = self.rfile.read(length); require(len(body) == length)
            if self.command == "POST": require(json_object(body).get("model") == admitted["model"])
            connection = http.client.HTTPConnection("127.0.0.1", 8789, timeout=300)
            connection.request(self.command, self.path, body=body,
                               headers={"Content-Type": "application/json", "Authorization": "Bearer " + proxy.gateway_key})
            response = connection.getresponse()
            self.send_response(response.status)
            self.send_header("Content-Type", response.getheader("Content-Type", "application/json"))
            for key, value in response.getheaders():
                if key.lower().startswith("x-arena-") or key.lower() == "x-request-id":
                    self.send_header(key, value)
            self.send_header("Transfer-Encoding", "chunked"); self.send_header("Connection", "close")
            self.end_headers(); sent = True
            size = 0
            while time.time() < found[0]["expires"]:
                chunk = response.read1(65536)
                if not chunk:
                    self.wfile.write(b"0\r\n\r\n"); return
                size += len(chunk); require(size <= 16 * 1024**2)
                self.wfile.write(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n"); self.wfile.flush()
        except (ValueError, KeyError, TypeError, OSError, http.client.HTTPException, sqlite3.Error):
            if not sent:
                try:
                    raw = b'{"error":{"message":"DGM relay request denied"}}'
                    self.send_response(403); self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(raw))); self.send_header("Connection", "close")
                    self.end_headers(); self.wfile.write(raw)
                except OSError: pass
        finally:
            if connection: connection.close()

    do_GET = do_POST = do_PUT = do_DELETE = do_CONNECT = handle_request


class RelayServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, proxy):
        self.proxy = proxy; self.slots = threading.BoundedSemaphore(16)
        super().__init__((urlsplit(proxy.config.relay_url).hostname, 8789), RelayHandler)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False): request.close(); return
        try: super().process_request(request, address)
        except BaseException: self.slots.release(); raise

    def process_request_thread(self, request, address):
        try: super().process_request_thread(request, address)
        finally: self.slots.release()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    config = Config.read(args.config); config.host_check()
    if config.socket_path.exists() or config.socket_path.is_symlink():
        info = config.socket_path.lstat()
        require(stat.S_ISSOCK(info.st_mode) and info.st_uid == 0)
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            probe.connect(str(config.socket_path))
        except ConnectionRefusedError: config.socket_path.unlink()
        else: raise Denied("DGM proxy is already serving this socket")
        finally: probe.close()
    with Server(config) as server:
        server.proxy.preflight(); server.proxy.recover()
        os.chown(config.socket_path, 0, config.worker_gid); config.socket_path.chmod(0o660)
        threading.Thread(target=server.proxy.reap, daemon=True).start()
        relay = RelayServer(server.proxy)
        threading.Thread(target=relay.serve_forever, daemon=True).start()
        def stop(signum, frame): raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, stop)
        try: server.serve_forever(poll_interval=0.5)
        except KeyboardInterrupt: pass
        finally:
            server.proxy.close(); relay.shutdown(); relay.server_close(); config.socket_path.unlink(missing_ok=True)


if __name__ == "__main__": main()
