"""Identity, filesystem, and canonical profile validation for the evaluator."""
from __future__ import annotations
from dataclasses import dataclass, replace
import http.client
import json
import os
from pathlib import Path
import re
import socket
import stat
import struct
from urllib.parse import parse_qs, urlsplit


MAX_BODY = 128 * 1024


MAX_RESPONSE = 4 * 1024 * 1024


MAX_STREAM = 16 * 1024 * 1024


RUN = re.compile(r"[0-9a-f]{32}\Z")


IMAGE = re.compile(r"(?:[A-Za-z0-9][A-Za-z0-9._/:\-]*@)?sha256:[0-9a-f]{64}\Z")


class Denied(ValueError):
    """A request outside the evaluator capability."""


class GPUCapacityUnavailable(Denied):
    """A known GPU lease blocked this request before Docker creation."""


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


def parse_additional_tasks_roots(value, primary):
    """An explicit finite list of disjoint libraries, never a path prefix grant."""
    require(type(value) is list and len(value) <= 16)
    require(all(type(item) is str for item in value))
    roots = (primary, *(Path(item) for item in value))
    require(all(path.is_absolute() and ".." not in path.parts and len(path.parts) >= 2 for path in roots))
    require(all(not left.is_relative_to(right) and not right.is_relative_to(left)
                for index, left in enumerate(roots) for right in roots[index + 1:]),
            "Task library roots must be distinct and non-overlapping")
    return roots[1:]


def immutable_task_library(path):
    """Apply the same host trust boundary to every approved task revision."""
    descriptor = directory_fd(path)
    os.close(descriptor)
    for ancestor in (path, *path.parents):
        info = ancestor.stat()
        require(info.st_uid == 0 and not info.st_mode & 0o022,
                "Task libraries must have root-owned non-writable ancestors")
    for base, directories, files in os.walk(path, followlinks=False):
        for name in directories + files:
            info = (Path(base) / name).lstat()
            require((stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode))
                    and info.st_uid == 0 and not info.st_mode & 0o022,
                    "Task libraries must be root-owned, link-free and not group/world writable")


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
    engine_registry: Path | None = None
    engine_staging_root: Path | None = None
    additional_tasks_roots: tuple[Path, ...] = ()
    resource_grants: tuple[tuple[str, str, tuple[str, ...]], ...] = ()
    lmx_gpu: object | None = None

    @property
    def library_roots(self):
        return (self.tasks_root, *self.additional_tasks_roots)

    @classmethod
    def read(cls, path):
        data = json_object(Path(path).read_bytes())
        required = {"docker_socket", "socket_path", "staging_root", "tasks_root", "run_roots",
                    "images", "worker_uid", "worker_gid"}
        require(required <= data.keys() and not set(data) - required -
                {"cgroup_root", "max_containers", "timeout_seconds", "engine_registry", "engine_staging_root",
                 "additional_tasks_roots", "resource_grants", "lmx_gpu"})
        for key in ("docker_socket", "socket_path", "staging_root", "tasks_root"):
            data[key] = Path(data[key])
            require(data[key].is_absolute() and ".." not in data[key].parts)
        data["additional_tasks_roots"] = parse_additional_tasks_roots(
            data.get("additional_tasks_roots", []), data["tasks_root"])
        require(type(data["run_roots"]) is list and data["run_roots"])
        data["run_roots"] = tuple(Path(p) for p in data["run_roots"])
        require(all(p.is_absolute() and len(p.parts) >= 4 and ".." not in p.parts for p in data["run_roots"]))
        require(type(data["images"]) is list and data["images"] and all(IMAGE.fullmatch(p) for p in data["images"]))
        data["images"] = tuple(data["images"])
        from .evaluation_resources import parse_grants
        data["resource_grants"] = parse_grants(data.get("resource_grants", []), data["images"])
        require(("engine_registry" in data) == ("engine_staging_root" in data))
        for key in ("engine_registry", "engine_staging_root"):
            if key in data:
                data[key] = Path(data[key])
                require(data[key].is_absolute() and ".." not in data[key].parts)
        for key in ("worker_uid", "worker_gid"):
            require(type(data[key]) is int and data[key] > 0)
        config = cls(**data)
        if "lmx_gpu" in data:
            from .evaluator_gpu import LmxGpu
            config = replace(config, lmx_gpu=LmxGpu.parse(data["lmx_gpu"], config))
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
        for path in (self.staging_root, self.socket_path.parent):
            fd = directory_fd(path)
            os.close(fd)
            for ancestor in (path, *path.parents):
                info = ancestor.stat()
                require(info.st_uid == 0 and not info.st_mode & 0o022,
                        "Proxy and task paths must have root-owned non-writable ancestors")
        require(stat.S_IMODE(self.staging_root.stat().st_mode) == 0o700)
        if self.engine_registry is not None:
            for path in (self.engine_registry, self.engine_staging_root):
                fd = directory_fd(path)
                os.close(fd)
                require(path.stat().st_uid == 0 and stat.S_IMODE(path.stat().st_mode) == 0o700)
                for parent in path.parents:
                    require(parent.stat().st_uid == 0 and not parent.stat().st_mode & 0o022)
        for path in self.library_roots:
            immutable_task_library(path)
        if self.lmx_gpu is not None:
            self.lmx_gpu.validate_host()


def _peer_identity(connection, config):
    pid, uid, gid = struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
    require(uid == config.worker_uid, "Only the evaluator worker UID may connect")
    data = Path(f"/proc/{pid}/cgroup").read_text()
    prefix = config.cgroup_root + "/arena-control-"
    matches = [line[3:] for line in data.splitlines() if line.startswith("0::")]
    require(len(matches) == 1 and matches[0].startswith(prefix))
    tail = matches[0][len(prefix):].split("/")
    require(len(tail) >= 2 and RUN.fullmatch(tail[0]))
    return tail


def engine_binding(connection, config):
    tail = _peer_identity(connection, config)
    if tail[1] == "main":
        return None
    require(config.engine_registry is not None, "Caller is not an admitted native worker")
    fd = directory_fd(config.engine_registry)
    try:
        raw = read_regular(fd, tail[0] + ".json", 4096, 0)
    finally:
        os.close(fd)
    record = json_object(raw)
    require(set(record) == {"schema", "run_id", "container_id", "artifact_root"}
            and record["schema"] == "arena.engine-peer/1" and record["run_id"] == tail[0]
            and re.fullmatch(r"[a-f0-9]{64}", record["container_id"])
            and tail[1] == record["container_id"], "Caller does not match the registered engine container")
    expected = config.engine_staging_root / tail[0] / "artifacts"
    require(record["artifact_root"] == str(expected))
    return record


def peer_run(connection, config):
    tail = _peer_identity(connection, config)
    if tail[1] != "main":
        engine_binding(connection, config)
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
    # Docker CLI versions may serialize environment entries in either order.
    # Accept the exact pair once each; values and all extra names remain denied.
    environment = ["PYTHONDONTWRITEBYTECODE=1", "PYTHONPYCACHEPREFIX=/tmp/arena-pycache"]
    require(type(body.get("Env")) is list and len(body["Env"]) == len(environment)
            and all(type(value) is str for value in body["Env"]) and set(body["Env"]) == set(environment))
    labels = body.get("Labels")
    expected_labels = {"arena.evaluator": "canonical-v1", "arena.control-run": run_id}
    resource_profile = labels.get("arena.evaluation-profile") if type(labels) is dict else None
    if resource_profile is not None:
        expected_labels["arena.evaluation-profile"] = resource_profile
    require(labels == expected_labels)
    command = body.get("Cmd")
    require(type(command) is list and len(command) == 14 and all(type(v) is str for v in command))
    python = command[0]
    require(python in {"python", "python3"} and command[1:5] == ["/tasks/run.py", "--root", "/tasks", "evaluate"])
    require(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,180}", command[5]))
    require(command[6:11] == ["--candidate", "/candidate/program.py", "--python", python, "--timeout"])
    require(command[11].isdigit() and 1 <= int(command[11]) <= config.timeout_seconds)
    require(command[12:] == ["--output", "/results/native.json"])
    from .evaluation_resources import granted_budget, require_parent_budget, require_gpu_parent_budget
    from .evaluator_gpu import GPU_BUDGET, IMAGE as GPU_IMAGE, PROFILE as GPU_PROFILE, selected as gpu_selected
    require(body["Image"] != GPU_IMAGE or resource_profile == GPU_PROFILE)
    gpu = gpu_selected(config, resource_profile)
    try:
        resources = GPU_BUDGET if gpu else granted_budget(resource_profile, body["Image"], command[5], config.resource_grants)
    except ValueError as error:
        raise Denied(str(error)) from None
    memory = resources["memory_mb"] * 1024 ** 2
    host = body.get("HostConfig")
    allowed = {"NetworkMode", "ReadonlyRootfs", "NanoCpus", "Memory", "PidsLimit", "CapDrop", "SecurityOpt",
               "Tmpfs", "Mounts", "AutoRemove", "CgroupParent", "LogConfig", "RestartPolicy", "ConsoleSize",
               "ShmSize", "Runtime", "CgroupnsMode", "MemorySwap", "MemorySwappiness", "MaskedPaths", "ReadonlyPaths"}
    only_defaults(host, allowed)
    require(host.get("NetworkMode") == "none" and host.get("ReadonlyRootfs") is True)
    require(host.get("NanoCpus") == resources["cpus"] * 1_000_000_000 and host.get("Memory") == memory)
    require(host.get("PidsLimit") == resources["pids"] and host.get("CapDrop") == ["ALL"])
    require(host.get("SecurityOpt") in (["no-new-privileges"], ["no-new-privileges=true"]))
    require(host.get("CgroupParent") == config.cgroup_root + "/arena-control-" + run_id)
    if resource_profile is not None:
        try:
            (require_gpu_parent_budget if gpu else require_parent_budget)(host["CgroupParent"], resources)
        except (ValueError, OSError) as error:
            raise Denied("Evaluator resources exceed the admitted parent envelope") from None
    require(host.get("Tmpfs") == {"/tmp": "rw,nosuid,nodev,size=268435456"})
    require(host.get("AutoRemove") is True)
    require(host.get("LogConfig", {}) in ({}, {"Type": "", "Config": {}}))
    require(host.get("RestartPolicy", {}) in ({}, {"Name": "no", "MaximumRetryCount": 0}))
    require(host.get("ConsoleSize", [0, 0]) == [0, 0])
    require(host.get("ShmSize", 0) in (0, 64 * 1024 ** 2))
    require(host.get("Runtime", "") in ("", "runc"))
    require(host.get("CgroupnsMode", "") in ("", "private"))
    require(host.get("MemorySwap", 0) in (0, memory))
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
    task_source = selected["/tasks"].get("Source")
    require(type(task_source) is str and task_source in {str(path) for path in config.library_roots},
            "Task library source is not explicitly approved")
    descriptor = directory_fd(Path(task_source))
    os.close(descriptor)
    candidate, result = Path(selected["/candidate"]["Source"]), Path(selected["/results"]["Source"])
    require(candidate.is_absolute() and result.is_absolute() and ".." not in candidate.parts and ".." not in result.parts)
    require(candidate.name in {"input", "candidate"} and result.name == "native-output" and candidate.parent == result.parent)
    require(RUN.fullmatch(candidate.parent.name))
    require(any(candidate.parent.parent == root / run_id / "artifacts" / "canonical-evaluations"
                for root in config.run_roots), "Evaluation paths must belong to this admitted run")
    rebuilt = {"Image": body["Image"], "Cmd": command, "User": body["User"], "Env": environment,
               "WorkingDir": "/tmp", "Labels": body["Labels"], "AttachStdout": True, "AttachStderr": True,
               "Tty": False, "OpenStdin": False, "Entrypoint": [], "HostConfig": {
                   "NetworkMode": "none", "ReadonlyRootfs": True, "NanoCpus": resources["cpus"] * 1_000_000_000,
                   "Memory": memory, "MemorySwap": memory, "PidsLimit": resources["pids"],
                   "CapDrop": ["ALL"], "SecurityOpt": ["no-new-privileges"], "AutoRemove": True,
                   "CgroupParent": host["CgroupParent"], "CgroupnsMode": "private",
                   "Tmpfs": {"/tmp": "rw,nosuid,nodev,size=268435456"},
                   "LogConfig": {"Type": "local", "Config": {"max-size": "1m", "max-file": "1", "compress": "false"}},
                   "Mounts": [{"Type": "bind", "Source": task_source, "Target": "/tasks", "ReadOnly": True}]}}
    if gpu:
        gpu.authorize(body["Image"], command[5], task_source, int(command[11]))
        gpu.rebuild(rebuilt)
    return rebuilt, candidate, result


class DockerConnection(http.client.HTTPConnection):
    def __init__(self, path, timeout=30):
        super().__init__("localhost", timeout=timeout)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(str(self.path))


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
