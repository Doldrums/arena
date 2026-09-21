"""Root-owned broker for an operator-approved private SCiEL image.

Only explicit admitted runs reach Docker. Clients supply an existing run ID and
deployment digest, never an image, mount, command, credential, or Docker option.
"""
from __future__ import annotations

import argparse
import codecs
from dataclasses import dataclass
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import re
import select
import shutil
import signal
import socket
import socketserver
import sqlite3
import stat
import struct
import threading
import time
from types import SimpleNamespace
from urllib.parse import quote
import uuid

from .evaluator_proxy import (Denied, DockerConnection, RUN, directory_fd, json_object,
                              peer_run, read_regular, require)
from .release_deployment import inspect_image_evidence, validate_manifest


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
        for path in (self.approvals, self.staging_root, self.registrations, self.receipts, self.socket_path.parent, self.tasks_root):
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
        for root, directories, files in os.walk(self.tasks_root, followlinks=False):
            for name in directories + files:
                info = (Path(root) / name).lstat()
                require(not stat.S_ISLNK(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022)


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


class Broker:
    def __init__(self, config):
        self.config = config
        self.lock = threading.RLock()
        self.active = {}

    def docker(self, method, path, body=None, timeout=20):
        connection = DockerConnection(self.config.docker_socket, timeout)
        try:
            connection.request(method, path, body=json.dumps(body).encode() if body is not None else None,
                               headers={"Content-Type": "application/json"})
            response = connection.getresponse(); raw = response.read(MAX_JSON + 1)
            require(len(raw) <= MAX_JSON)
            return response.status, json_object(raw) if raw else {}
        finally: connection.close()

    def plan(self, run_id, digest):
        admitted = admission(self.config, run_id, digest)
        manifest = admitted["manifest"]
        status, actual = self.docker("GET", "/images/" + quote(manifest["image"]["reference"], safe="") + "/json")
        require(status == 200 and inspect_image_evidence([actual], manifest["binding"]) == manifest["image"],
                "Installed image differs from its approved deployment")
        raw = input_file(admitted["request"]["config"], self.config.config_roots)
        logical = self.config.runs_root / run_id / "artifacts"
        native_config = checked_native_config(raw, admitted["model"], logical, self.config.gateway_url)
        tasks = Path(admitted["request"]["tasks_root"])
        require(tasks.is_absolute() and ".." not in tasks.parts
                and any(tasks.is_relative_to(root) and tasks != root for root in self.config.task_roots))
        return {**admitted, "run_id": run_id, "deployment_sha256": digest, "logical": logical,
                "config": native_config, "original_config_sha256": hashlib.sha256(raw).hexdigest(), "tasks": tasks}

    def prepare(self, plan):
        run_id, config = plan["run_id"], self.config
        stage = config.staging_root / run_id
        stage.mkdir(mode=0o700)
        (stage / "inputs").mkdir(mode=0o755); (stage / "inputs").chmod(0o755)
        raw = (json.dumps(plan["config"], sort_keys=True, allow_nan=False) + "\n").encode()
        (stage / "inputs/config.json").write_bytes(raw); (stage / "inputs/config.json").chmod(0o444)
        plan["staged_config_sha256"] = hashlib.sha256(raw).hexdigest()
        plan["task_hashes"] = stage_tree(plan["tasks"], stage / "inputs/tasks", readonly=True)
        artifacts = stage / "artifacts"; artifacts.mkdir(mode=0o700)
        os.chown(artifacts, config.worker_uid, config.worker_gid)
        for name in ("home", "canonical-evaluations"):
            (artifacts / name).mkdir(mode=0o700); os.chown(artifacts / name, config.worker_uid, config.worker_gid)
        # Hold publication destination before any Docker request; replacements
        # of its ancestors cannot redirect root's later artifact publication.
        key = root_file(config.gateway_key_file, 1024).decode("ascii").strip()
        require(32 <= len(key) <= 512 and all(33 <= ord(c) <= 126 for c in key))
        command = ["run", "/arena-input/config.json", "--outputs", str(plan["logical"]),
                   "--run-id", "native", "--tasks-root", "/arena-input/tasks"]
        for name in ("seed", "budget", "campaign", "arm"):
            if name in plan["request"]: command.extend(["--" + name, str(plan["request"][name])])
        mount = lambda source, target, readonly=True: {"Type": "bind", "Source": str(source), "Target": str(target), "ReadOnly": readonly}
        environment = ["OPENAI_API_KEY=" + key, "HOME=" + str(plan["logical"] / "home"),
                       "PYTHONDONTWRITEBYTECODE=1", "DOCKER_HOST=unix:///run/arena-evaluator/docker.sock",
                       "ARENA_CONTROL_RUN_ID=" + run_id,
                       "ARENA_EVALUATION_BROKER_CONTEXT=/run/arena-engine/context.json",
                       *[name + "=1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")]]
        resources = plan["resources"]
        body = {"Image": plan["manifest"]["image"]["reference"], "Entrypoint": plan["manifest"]["image"]["entrypoint"],
                "Cmd": command, "User": f"{config.worker_uid}:{config.worker_gid}", "Env": environment,
                "WorkingDir": "/opt/sciel", "Tty": False, "OpenStdin": False,
                "Labels": {"arena.engine": "sciel-release-v1", "arena.control-run": run_id,
                           "arena.deployment": plan["deployment_sha256"]},
                "HostConfig": {"NetworkMode": "host", "ReadonlyRootfs": True, "CgroupnsMode": "private",
                               "CgroupParent": config.cgroup_root + "/arena-control-" + run_id,
                               "NanoCpus": resources["cpus"] * 10**9, "Memory": resources["memory_mb"] * 1024**2,
                               "MemorySwap": resources["memory_mb"] * 1024**2, "PidsLimit": resources["pids"],
                               "CapDrop": ["ALL"], "SecurityOpt": ["no-new-privileges"], "AutoRemove": False,
                               "Tmpfs": {"/tmp": "rw,nosuid,nodev,size=536870912"},
                               "LogConfig": {"Type": "local", "Config": {"max-size": "4m", "max-file": "1", "compress": "false"}},
                               "Mounts": [mount(stage / "inputs", "/arena-input"), mount(artifacts, plan["logical"], False),
                                          mount(config.tasks_root, config.tasks_root),
                                          mount(config.evaluator_socket, "/run/arena-evaluator/docker.sock"),
                                          mount(stage / "context.json", "/run/arena-engine/context.json")]}}
        # ID is available after create and before start; the bind source exists
        # now and is rewritten root-only with that actual ID before any code runs.
        (stage / "context.json").write_text("{}"); (stage / "context.json").chmod(0o444)
        output_fd = directory_fd(plan["logical"])
        if os.fstat(output_fd).st_uid != config.worker_uid:
            os.close(output_fd)
            raise Denied("Private engine output must be worker-owned")
        return {"plan": plan, "stage": stage, "output_fd": output_fd, "key": key, "body": body,
                "cancel": threading.Event(), "created": time.monotonic(), "id": None}

    def cancel(self, run_id):
        with self.lock:
            record = self.active.get(run_id)
        require(record is not None, "No active private engine for this run")
        record["cancel"].set()
        if record.get("id"):
            try:
                status, _ = self.docker("POST", "/containers/" + record["id"] + "/kill?signal=KILL")
                require(status in (204, 404, 409), "Engine termination was not acknowledged")
            except (OSError, ValueError, http.client.HTTPException):
                # Root can terminate only this authenticated run's whole group.
                group = Path("/sys/fs/cgroup") / self.config.cgroup_root.lstrip("/") / ("arena-control-" + run_id)
                (group / "cgroup.kill").write_text("1")

    def publish(self, record):
        hashes, total, count = {}, 0, 0
        output_fd = record["output_fd"]
        def copy(source_fd, destination_fd, relative):
            nonlocal total, count
            for name in sorted(os.listdir(source_fd)):
                count += 1; require(count <= 10000)
                info = os.stat(name, dir_fd=source_fd, follow_symlinks=False)
                path = relative + name
                if stat.S_ISDIR(info.st_mode):
                    os.mkdir(name, 0o700, dir_fd=destination_fd)
                    src = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=source_fd)
                    dst = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=destination_fd)
                    try:
                        copy(src, dst, path + "/")
                        os.fchown(dst, self.config.worker_uid, self.config.worker_gid)
                    finally:
                        os.close(src); os.close(dst)
                else:
                    raw = read_regular(source_fd, name, min(64 * 1024**2, MAX_ARTIFACTS - total))
                    total += len(raw); require(total <= MAX_ARTIFACTS)
                    dst = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=destination_fd)
                    try:
                        with os.fdopen(dst, "wb", closefd=False) as stream: stream.write(raw)
                        os.fchown(dst, self.config.worker_uid, self.config.worker_gid)
                    finally: os.close(dst)
                    hashes[path] = hashlib.sha256(raw).hexdigest()
        for name in ("native", "canonical-evaluations"):
            source = record["stage"] / "artifacts" / name
            if not source.exists(): continue
            require(not source.is_symlink() and source.is_dir())
            temporary = ".engine-publish-" + uuid.uuid4().hex
            os.mkdir(temporary, 0o700, dir_fd=output_fd)
            destination_fd = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=output_fd)
            source_fd = directory_fd(source)
            try:
                copy(source_fd, destination_fd, name + "/")
                os.fchown(destination_fd, self.config.worker_uid, self.config.worker_gid)
            finally:
                os.close(source_fd); os.close(destination_fd)
            try:
                os.stat(name, dir_fd=output_fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise Denied("Private engine artifacts already exist; refusing to replace them")
            os.rename(temporary, name, src_dir_fd=output_fd, dst_dir_fd=output_fd)
        return hashes

    def logs(self, record, emit):
        connection = DockerConnection(self.config.docker_socket, record["plan"]["seconds"] + 45)
        decoders = {stream: codecs.getincrementaldecoder("utf-8")("replace") for stream in (1, 2)}
        pending, total, received = {1: "", 2: ""}, 0, 0
        def deliver(text, stream, final=False):
            nonlocal total
            pending[stream] += text
            # Replace on the whole buffer before choosing an emission boundary.
            # Otherwise a key straddling that boundary could leak its prefix.
            pending[stream] = pending[stream].replace(record["key"], "[REDACTED]")
            # Retain more than the entire secret length across read boundaries.
            safe = pending[stream] if final else pending[stream][:-1024]
            pending[stream] = "" if final else pending[stream][-1024:]
            if not safe: return
            safe = safe.replace(record["key"], "[REDACTED]")
            safe = re.sub(r"(?i)(bearer\s+)[^\s\"']+", r"\1[REDACTED]", safe)
            total += len(safe.encode())
            if total > MAX_LOG:
                raise Denied("Private engine log bound exceeded")
            # The client enforces a 64 KiB NDJSON frame limit. JSON escaping can
            # expand a single character to six bytes, so keep chunks smaller.
            for offset in range(0, len(safe), 4096):
                emit({"type": "stdout" if stream == 1 else "stderr", "text": safe[offset:offset + 4096]})
        try:
            connection.request("GET", "/containers/" + record["id"] + "/logs?stdout=1&stderr=1&follow=1&tail=all")
            response = connection.getresponse(); require(response.status == 200)
            while True:
                header = response.read(8)
                if not header: break
                require(len(header) == 8 and header[0] in (1, 2) and header[1:4] == b"\0\0\0")
                length = struct.unpack(">I", header[4:])[0]
                received += length
                require(received <= MAX_LOG)
                raw = response.read(length); require(len(raw) == length)
                deliver(decoders[header[0]].decode(raw), header[0])
            for stream in (1, 2):
                deliver(decoders[stream].decode(b"", final=True), stream, final=True)
        finally:
            connection.close()

    def run(self, run_id, digest, emit, disconnected):
        with self.lock:
            require(run_id not in self.active and len(self.active) < self.config.max_active)
            require(not (self.config.receipts / (run_id + ".json")).exists(), "Private image runs are not retried")
            self.active[run_id] = {"cancel": threading.Event(), "id": None}
        record, final, plan, journal = None, None, None, None
        failure = None
        timed_out, monitor_done = threading.Event(), threading.Event()
        try:
            plan = self.plan(run_id, digest)
            record = self.prepare(plan)
            with self.lock:
                record["cancel"] = self.active[run_id]["cancel"]
                self.active[run_id] = record
            require(not record["cancel"].is_set() and not disconnected(), "Private engine start was cancelled")
            write_private(record["stage"] / "owner.json", {"run_id": run_id, "container_id": None, "deployment_sha256": digest})
            status, result = self.docker("POST", "/containers/create?name=arena-engine-" + run_id, record["body"])
            require(status == 201 and re.fullmatch(r"[a-f0-9]{64}", result.get("Id", "")))
            record["id"] = result["Id"]
            # Never persist the Docker body, which contains the scoped key.
            del record["body"]
            replace_private(record["stage"] / "owner.json", {"run_id": run_id, "container_id": record["id"], "deployment_sha256": digest})
            context = {"schema": "arena.engine-context/1", "run_id": run_id, "container_id": record["id"],
                       "cgroup_parent": self.config.cgroup_root + "/arena-control-" + run_id,
                       "receipts_dir": str(plan["logical"] / "canonical-evaluations")}
            context_new = record["stage"] / "context.new.json"
            write_private(context_new, context); context_new.chmod(0o444)
            context_new.replace(record["stage"] / "context.json")
            write_private(self.config.registrations / (run_id + ".json"),
                          {"schema": "arena.engine-peer/1", "run_id": run_id, "container_id": record["id"],
                           "artifact_root": str(record["stage"] / "artifacts")})
            require(not record["cancel"].is_set() and not disconnected(), "Private engine start was cancelled")
            status, _ = self.docker("POST", "/containers/" + record["id"] + "/start")
            require(status == 204)
            emit({"type": "started", "run_id": run_id})
            def monitor():
                while not monitor_done.wait(0.5):
                    try:
                        if time.monotonic() - record["created"] > plan["seconds"]:
                            timed_out.set(); self.cancel(run_id); return
                        if disconnected():
                            self.cancel(run_id); return
                    except (OSError, ValueError):
                        return  # Main path still requires confirmed removal.
            watcher = threading.Thread(target=monitor, daemon=True); watcher.start()
            self.logs(record, emit)
            status, inspection = self.docker("GET", "/containers/" + record["id"] + "/json")
            require(status == 200 and inspection.get("Image") == plan["manifest"]["image"]["image_id"]
                    and not inspection["State"]["Running"])
            code = inspection["State"]["ExitCode"]; require(type(code) is int)
            state = "completed" if code == 0 else "failed"
            if timed_out.is_set(): state, code = "timed_out", 124
            elif record["cancel"].is_set(): state, code = "cancelled", 130
            final = {"type": "result", "run_id": run_id, "status": state, "returncode": code,
                     "deployment_sha256": digest, "image": plan["manifest"]["image"]["reference"],
                     "image_id": plan["manifest"]["image"]["image_id"],
                     "source_commit": plan["manifest"]["binding"]["repository"]["commit"],
                     "receipt_id": run_id}
            journal = {**final, "schema": "arena.engine-execution/1", "snapshot_sha256": plan["snapshot_sha256"],
                           "original_config_sha256": plan["original_config_sha256"],
                           "staged_config_sha256": plan["staged_config_sha256"], "task_hashes": plan["task_hashes"],
                           "container_id": record["id"], "model": plan["model"],
                           "network": "host", "canonical_evaluation": False}
        except (ValueError, KeyError, TypeError, OSError, sqlite3.Error, http.client.HTTPException) as error:
            failure = type(error).__name__
            if plan is not None:
                final = {"type": "result", "run_id": run_id,
                         "status": "timed_out" if timed_out.is_set() else
                                   "cancelled" if record is not None and record["cancel"].is_set() else "failed",
                         "returncode": 124 if timed_out.is_set() else 1, "deployment_sha256": digest,
                         "image": plan["manifest"]["image"]["reference"], "image_id": plan["manifest"]["image"]["image_id"],
                         "source_commit": plan["manifest"]["binding"]["repository"]["commit"], "receipt_id": run_id}
            journal = {"schema": "arena.engine-execution/1", "run_id": run_id, "deployment_sha256": digest,
                       "status": "failed", "error_type": failure, **(final or {})}
        finally:
            monitor_done.set()
            cleaned = False
            if record is not None:
                if record.get("id"):
                    try:
                        status, _ = self.docker("DELETE", "/containers/" + record["id"] + "?force=1")
                        cleaned = status in (204, 404)
                    except (OSError, ValueError, http.client.HTTPException): pass
                else:
                    # A create transport error may leave an unstarted container.
                    try:
                        status, inspection = self.docker("GET", "/containers/arena-engine-" + run_id + "/json")
                        if status == 404: cleaned = True
                        elif status == 200:
                            require(inspection["Config"]["Labels"] == {
                                "arena.engine": "sciel-release-v1", "arena.control-run": run_id, "arena.deployment": digest})
                            require(re.fullmatch(r"[a-f0-9]{64}", inspection["Id"]))
                            status, _ = self.docker("DELETE", "/containers/" + inspection["Id"] + "?force=1")
                            cleaned = status in (204, 404)
                    except (OSError, ValueError, KeyError, http.client.HTTPException): pass
                if cleaned:
                    # Preserve completed research/evaluation evidence even when
                    # the client stops reading logs. Only copy once termination
                    # is confirmed, and never convert a failed run to success.
                    try:
                        hashes = self.publish(record)
                        if journal is not None: journal["artifact_hashes"] = hashes
                    except (OSError, ValueError) as error:
                        if journal is not None:
                            journal["publication_error_type"] = type(error).__name__
                        if final is not None and final["status"] == "completed":
                            final.update(status="failed", returncode=1)
                            if journal is not None: journal.update(status="failed", returncode=1)
                    (self.config.registrations / (run_id + ".json")).unlink(missing_ok=True)
                    shutil.rmtree(record["stage"])
                os.close(record["output_fd"])
                record.pop("key", None)
            elif (self.config.staging_root / run_id).exists():
                shutil.rmtree(self.config.staging_root / run_id)
                cleaned = True
            else: cleaned = True
            if record is not None and not cleaned:
                group = Path("/sys/fs/cgroup") / self.config.cgroup_root.lstrip("/") / ("arena-control-" + run_id)
                (group / "cgroup.kill").write_text("1")
                raise Denied("Private engine cleanup was not confirmed")
        if journal is not None:
            journal["cleanup_confirmed"] = True
            write_private(self.config.receipts / (run_id + ".json"), journal)
        with self.lock: self.active.pop(run_id, None)
        require(final is not None)
        emit(final)

    def recover(self):
        for stage in self.config.staging_root.iterdir():
            require(stage.is_dir() and not stage.is_symlink() and RUN.fullmatch(stage.name))
            owner = stage / "owner.json"
            if owner.exists():
                record = json_object(root_file(owner, 4096))
                require(record["run_id"] == stage.name and (record["container_id"] is None
                        or re.fullmatch(r"[a-f0-9]{64}", record["container_id"])))
                ident = record["container_id"] or "arena-engine-" + stage.name
                status, result = self.docker("GET", "/containers/" + ident + "/json")
                if status != 404:
                    require(status == 200 and result["Config"]["Labels"] == {
                        "arena.engine": "sciel-release-v1", "arena.control-run": stage.name,
                        "arena.deployment": record["deployment_sha256"]})
                    require(re.fullmatch(r"[a-f0-9]{64}", result["Id"]))
                    deleted, _ = self.docker("DELETE", "/containers/" + result["Id"] + "?force=1")
                    require(deleted in (204, 404))
                receipt = self.config.receipts / (stage.name + ".json")
                if not receipt.exists():
                    output_fd = directory_fd(self.config.runs_root / stage.name / "artifacts")
                    try:
                        require(os.fstat(output_fd).st_uid == self.config.worker_uid)
                        hashes = self.publish({"stage": stage, "output_fd": output_fd})
                    finally:
                        os.close(output_fd)
                    write_private(receipt, {"schema": "arena.engine-execution/1", "run_id": stage.name,
                        "deployment_sha256": record["deployment_sha256"], "status": "failed",
                        "error_type": "BrokerInterrupted", "cleanup_confirmed": True,
                        "artifact_hashes": hashes})
            (self.config.registrations / (stage.name + ".json")).unlink(missing_ok=True)
            shutil.rmtree(stage)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *args): pass
    def setup(self):
        super().setup(); self.connection.settimeout(20)
    def caller(self):
        config = self.server.broker.config
        return peer_run(self.connection, SimpleNamespace(worker_uid=config.worker_uid,
                        cgroup_root=config.cgroup_root, engine_registry=None))
    def disconnected(self):
        try:
            ready, _, _ = select.select([self.connection], [], [], 0)
            return bool(ready) and self.connection.recv(1, socket.MSG_PEEK) == b""
        except OSError: return True
    def emit(self, value):
        self.wfile.write(json.dumps(value, allow_nan=False).encode() + b"\n"); self.wfile.flush()
    def error(self, status=403):
        self.send_response(status); self.send_header("Content-Type", "application/json")
        self.send_header("Connection", "close"); self.end_headers()
        self.wfile.write(b'{"error":"Private image broker could not safely admit or complete this run"}\n')
    def do_POST(self):
        self.close_connection = True; streaming = False
        try:
            require(self.path == "/v1/run" and not self.headers.get_all("Transfer-Encoding"))
            lengths = self.headers.get_all("Content-Length", []); require(len(lengths) == 1)
            length = int(lengths[0]); require(1 <= length <= 4096)
            request = json_object(self.rfile.read(length)); require(set(request) == {"run_id", "deployment_sha256"})
            run_id = self.caller(); require(request["run_id"] == run_id)
            require(re.fullmatch(r"[a-f0-9]{64}", request["deployment_sha256"]))
            self.send_response(200); self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Connection", "close"); self.end_headers(); streaming = True
            self.server.broker.run(run_id, request["deployment_sha256"], self.emit, self.disconnected)
        except (ValueError, KeyError, TypeError, OSError, sqlite3.Error, http.client.HTTPException):
            if not streaming:
                try: self.error()
                except OSError: pass
            # Missing authenticated terminal result is failure in the driver.
    def do_DELETE(self):
        self.close_connection = True
        try:
            run_id = self.caller()
            require(self.path == "/v1/run/" + run_id and not self.headers.get("Transfer-Encoding")
                    and self.headers.get("Content-Length", "0") == "0")
            self.server.broker.cancel(run_id)
            self.send_response(204); self.send_header("Connection", "close"); self.end_headers()
        except (ValueError, OSError):
            try: self.error()
            except OSError: pass


class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    def __init__(self, config):
        self.broker = Broker(config)
        self.slots = threading.BoundedSemaphore(32)
        super().__init__(str(config.socket_path), Handler)
    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False): request.close(); return
        try: super().process_request(request, address)
        except BaseException:
            self.slots.release()
            raise
    def process_request_thread(self, request, address):
        try: super().process_request_thread(request, address)
        finally: self.slots.release()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    root_file(args.config)
    config = Config.read(args.config); config.host_check()
    if config.socket_path.exists():
        require(stat.S_ISSOCK(config.socket_path.lstat().st_mode) and config.socket_path.lstat().st_uid == 0)
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try: probe.connect(str(config.socket_path))
        except ConnectionRefusedError: config.socket_path.unlink()
        else: raise Denied("A private engine broker is already running")
        finally: probe.close()
    with Server(config) as server:
        status, info = server.broker.docker("GET", "/info")
        require(status == 200 and info.get("CgroupDriver") == "cgroupfs" and info.get("CgroupVersion") == "2")
        server.broker.recover()
        os.chown(config.socket_path, 0, config.worker_gid); config.socket_path.chmod(0o660)
        def stop(signum, frame): raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, stop)
        try: server.serve_forever(poll_interval=0.5)
        except KeyboardInterrupt: pass
        finally:
            for run_id in list(server.broker.active):
                try: server.broker.cancel(run_id)
                except (OSError, ValueError): pass
            config.socket_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
