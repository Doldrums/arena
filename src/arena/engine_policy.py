"""Private engine admission, staging, and native configuration validation."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import stat
from urllib.parse import quote
import uuid
from .evaluator_policy import RUN, directory_fd, immutable_task_library, json_object, parse_additional_tasks_roots, read_regular, require
from .release_deployment import validate_manifest


MAX_JSON = 1024 * 1024


MAX_LOG = 4 * 1024 * 1024


MAX_ARTIFACTS = 512 * 1024 * 1024


@dataclass(frozen=True)
class Config:
    socket_path: Path
    docker_socket: Path
    approvals: Path
    runs_root: Path
    queue_database: Path
    staging_root: Path
    registrations: Path
    receipts: Path
    tasks_root: Path
    gateway_key_file: Path
    config_roots: tuple[Path, ...]
    task_roots: tuple[Path, ...]
    models: tuple[str, ...]
    evaluator_socket: Path = Path("/run/arena-evaluator/docker.sock")
    gateway_url: str = "http://127.0.0.1:8789/v1"
    worker_uid: int = 998
    worker_gid: int = 998
    cgroup_root: str = "/arena-workers"
    max_active: int = 4
    max_seconds: int = 7200
    additional_tasks_roots: tuple[Path, ...] = ()

    @property
    def library_roots(self):
        return (self.tasks_root, *self.additional_tasks_roots)

    @classmethod
    def read(cls, path):
        value = json_object(Path(path).read_bytes())
        paths = {"socket_path", "docker_socket", "approvals", "runs_root", "queue_database", "staging_root",
                 "registrations", "receipts", "tasks_root", "gateway_key_file"}
        required = paths | {"config_roots", "task_roots", "models"}
        require(required <= value.keys() and not set(value) - set(cls.__dataclass_fields__))
        value.setdefault("evaluator_socket", "/run/arena-evaluator/docker.sock")
        for name in paths | {"evaluator_socket"}:
            value[name] = Path(value[name])
            require(value[name].is_absolute() and ".." not in value[name].parts)
        value["additional_tasks_roots"] = parse_additional_tasks_roots(
            value.get("additional_tasks_roots", []), value["tasks_root"])
        for name in ("config_roots", "task_roots"):
            require(type(value[name]) is list and value[name])
            value[name] = tuple(Path(p) for p in value[name])
            require(all(p.is_absolute() and ".." not in p.parts and len(p.parts) >= 4 for p in value[name]))
        require(type(value["models"]) is list and value["models"]
                and all(type(m) is str and re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", m) for m in value["models"]))
        value["models"] = tuple(value["models"])
        config = cls(**value)
        require(config.gateway_url == "http://127.0.0.1:8789/v1")
        require(re.fullmatch(r"/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+", config.cgroup_root))
        require(type(config.worker_uid) is int and config.worker_uid > 0
                and type(config.worker_gid) is int and config.worker_gid > 0)
        require(type(config.max_active) is int and 1 <= config.max_active <= 16)
        require(type(config.max_seconds) is int and 1 <= config.max_seconds <= 86400)
        return config

    def host_check(self):
        require(os.geteuid() == 0 and hasattr(socket, "SO_PEERCRED"))
        for path in (self.approvals, self.staging_root, self.registrations, self.receipts, self.socket_path.parent):
            fd = directory_fd(path); os.close(fd)
            require(path.stat().st_uid == 0 and not path.stat().st_mode & 0o022)
            for ancestor in path.parents:
                require(ancestor.stat().st_uid == 0 and not ancestor.stat().st_mode & 0o022)
        for path in (self.approvals, self.staging_root, self.registrations, self.receipts):
            require(stat.S_IMODE(path.stat().st_mode) == 0o700)
        mounts = [line.split(" - ", 1) for line in Path("/proc/self/mountinfo").read_text().splitlines()]
        own_mounts = [(before.split()[2], after.split()) for before, after in mounts
                      if before.split()[4] == str(self.staging_root)]
        # systemd ReadWritePaths can expose the same host mount twice. Both
        # records must refer to the same tmpfs device and filesystem options.
        require(own_mounts and len({device for device, _ in own_mounts}) == 1
                and len({tuple(fs) for _, fs in own_mounts}) == 1,
                "Engine staging must be a dedicated host-visible tmpfs")
        own = [fs for _, fs in own_mounts]
        require(own[0][0] == "tmpfs", "Engine staging must be a dedicated host-visible tmpfs")
        sizes = [part[5:] for part in own[0][2].split(",") if part.startswith("size=")]
        require(len(sizes) == 1 and re.fullmatch(r"\d+[kmg]?", sizes[0]))
        match = re.fullmatch(r"(\d+)([kmg]?)", sizes[0])
        size = int(match[1]) * {"": 1, "k": 1024, "m": 1024**2, "g": 1024**3}[match[2]]
        require(256 * 1024**2 <= size <= 4 * 1024**3)
        for path in self.library_roots:
            immutable_task_library(path)


def root_file(path, maximum=MAX_JSON):
    fd = directory_fd(path.parent)
    try:
        info = os.stat(path.name, dir_fd=fd, follow_symlinks=False)
        require(info.st_uid == 0 and not info.st_mode & 0o077)
        return read_regular(fd, path.name, maximum, 0)
    finally:
        os.close(fd)


def input_file(path, roots, maximum=MAX_JSON):
    path = Path(path)
    require(path.is_absolute() and ".." not in path.parts
            and any(path.is_relative_to(root) and path != root for root in roots))
    fd = directory_fd(path.parent)
    try:
        return read_regular(fd, path.name, maximum)
    finally:
        os.close(fd)


def write_private(path, value):
    raw = (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    finally:
        os.close(fd)


def replace_private(path, value):
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex)
    write_private(temporary, value)
    temporary.replace(path)


def stage_tree(source, destination, *, maximum=MAX_ARTIFACTS, readonly=False):
    """Copy regular files through no-follow directory descriptors, no links."""
    count, size, hashes = 0, 0, {}
    def walk(fd, target, relative=""):
        nonlocal count, size
        target.mkdir(mode=0o700)
        for name in sorted(os.listdir(fd)):
            require(name not in {".", ".."} and "/" not in name)
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            key = relative + name
            count += 1; require(count <= 10000, "Tree has too many files")
            if stat.S_ISDIR(info.st_mode):
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try: walk(child, target / name, key + "/")
                finally: os.close(child)
            else:
                raw = read_regular(fd, name, min(64 * 1024**2, maximum - size))
                size += len(raw); require(size <= maximum)
                (target / name).write_bytes(raw)
                hashes[key] = hashlib.sha256(raw).hexdigest()
                if readonly: (target / name).chmod(0o444)
        if readonly: target.chmod(0o555)
    source_fd = directory_fd(source)
    try: walk(source_fd, destination)
    finally: os.close(source_fd)
    return hashes


def admission(config, run_id, deployment_sha256):
    require(RUN.fullmatch(run_id) and re.fullmatch(r"[a-f0-9]{64}", deployment_sha256))
    approved_raw = root_file(config.approvals / (deployment_sha256 + ".json"))
    require(hashlib.sha256(approved_raw).hexdigest() == deployment_sha256)
    manifest = validate_manifest(json_object(approved_raw))
    require(manifest["broker"]["socket"] == str(config.socket_path))
    # The private broker never queries credentials/access keys from this DB.
    require(not config.queue_database.is_symlink())
    with sqlite3.connect("file:" + quote(str(config.queue_database)) + "?mode=ro", uri=True, timeout=3) as database:
        database.row_factory = sqlite3.Row
        row = database.execute("SELECT state,held,cancel_requested,snapshot_sha256,model,timeout_seconds FROM runs WHERE id=?", (run_id,)).fetchone()
    require(row is not None and row["state"] == "running" and row["held"] == 1 and not row["cancel_requested"])
    directory = config.runs_root / run_id
    fd = directory_fd(directory)
    try: raw = read_regular(fd, "snapshot.json", MAX_JSON, config.worker_uid)
    finally: os.close(fd)
    require(hashlib.sha256(raw).hexdigest() == row["snapshot_sha256"])
    snapshot = json_object(raw); template = snapshot["template"]; spec = template["spec"]; request = spec["request"]
    require(template["framework"] == spec["framework"] == "sciel-release"
            and spec["source_dir"] == manifest["source"]["path"]
            and request["release"] == manifest["release"] and spec["output_dir"] == "{output_dir}")
    require(snapshot["cgroup_root"] == "/sys/fs/cgroup" + config.cgroup_root)
    require(template["model"] == row["model"] and row["model"] in config.models)
    require(type(row["timeout_seconds"]) is int and 1 <= row["timeout_seconds"] <= config.max_seconds
            and spec["timeout_seconds"] == row["timeout_seconds"])
    require(set(request) <= {"python", "release", "deployment", "config", "tasks_root", "seed", "budget", "campaign", "arm"})
    require(hashlib.sha256(input_file(request["deployment"], config.config_roots)).hexdigest() == deployment_sha256)
    resources = template["resources"]
    require(type(resources["cpus"]) is int and 1 <= resources["cpus"] <= 8
            and type(resources["memory_mb"]) is int and 512 <= resources["memory_mb"] <= 32768
            and type(resources["pids"]) is int and 32 <= resources["pids"] <= 2048)
    for key, low, high in (("seed", 0, 10**9), ("budget", 1, 10000)):
        require(key not in request or (type(request[key]) is int and low <= request[key] <= high))
    for key in ("campaign", "arm"):
        require(key not in request or (type(request[key]) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", request[key])))
    return {"manifest": manifest, "request": request, "resources": resources, "model": row["model"],
            "seconds": row["timeout_seconds"], "snapshot_sha256": row["snapshot_sha256"]}


def checked_native_config(raw, model, artifacts, gateway_url):
    value = json_object(raw)
    llm = value.get("llm")
    require(type(llm) is dict and llm.get("models") == [model]
            and llm.get("api_base", "").rstrip("/") == gateway_url
            and llm.get("api_key_env") == "OPENAI_API_KEY")
    def no_credentials(node):
        if type(node) is dict:
            for key, item in node.items():
                require(not re.search(r"(?:^|_)(api_key|access_token|password|secret|authorization)$", key, re.I),
                        "Use only the broker-provided gateway credential environment")
                no_credentials(item)
        elif type(node) is list:
            for item in node: no_credentials(item)
    no_credentials(value)
    require(not value.get("extends") and not value.get("wandb", {}).get("enabled"))
    # These deployment paths are explicit transforms, included in root receipts.
    if value.get("embed_grid"):
        value["embed_grid_path"] = "/opt/sciel/models/code_embed_v3.pt"
        value["embed_axis_path"] = "/opt/sciel/models/behavior_axis/{task}_v3.npz"
    if type(value.get("parallel_search")) is dict:
        value["parallel_search"]["capacity_dir"] = str(artifacts / "capacity")
    return value
