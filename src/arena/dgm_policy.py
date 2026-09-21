"""Admission, run identity, and archive validation for the DGM Docker capability."""
from __future__ import annotations
from dataclasses import MISSING, dataclass
import hashlib
import io
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import socket
import sqlite3
import stat
import tarfile
from urllib.parse import parse_qs, quote, unquote, urlsplit
import uuid
from .evaluator_policy import Denied, RUN, _peer_identity, directory_fd, json_object, read_regular, require


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
    if spec["request"].get("profile") == "gateway-polyglot-pilot":
        require(spec["request"].get("model") == row["model"],
                "Native outer-loop model differs from the admitted container model")
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
        require(query.get("noOverwriteDirNonDir", "0") in {"0", "false"})
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
