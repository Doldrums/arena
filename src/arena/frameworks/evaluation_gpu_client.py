"""Exact LMX create admission: wait only on proved, nonexecuted capacity.

Docker CLI drops structured error codes. This client reads the restricted Unix
proxy's create response directly, then leaves streaming/start to the CLI once.
It grants no GPU access; the root proxy and native admission remain separate.
"""
from __future__ import annotations

import http.client
import json
import os
from pathlib import Path
import re
import socket
import threading
import time

from arena.evaluator_gpu import GPU_BUDGET, IMAGE, PROFILE, TASK_IDS

DOCKER_HOST = "unix:///run/arena-evaluator/docker.sock"
MAX_RESPONSE = 64 * 1024
BUSY_RESPONSE = {"code": "arena_gpu_capacity_busy",
                 "message": "GPU capacity is occupied; no evaluator container was created"}


class CapacityUnavailable(Exception):
    """The original deadline expired after only confirmed capacity denials."""


def resources(config):
    execution = config["execution"]
    if execution.get("resource_profile") != PROFILE:
        return None
    if (execution.get("kind") != "docker" or execution.get("image") != IMAGE
            or execution.get("require_control_cgroup") is not True
            or execution.get("python") not in {"python", "python3"}
            or config["task_id"] not in TASK_IDS
            or type(config["timeout_seconds"]) is not int
            or not 1 <= config["timeout_seconds"] <= 600):
        raise ValueError("GPU client requires the exact reviewed, controlled LMX profile")
    return dict(GPU_BUDGET)


def create_body(config, root, candidate, results, context):
    selected = resources(config)
    if selected is None:
        raise ValueError("GPU create requires the explicit LMX profile")
    execution = config["execution"]
    run = context["run_id"]
    if (not re.fullmatch(r"[a-f0-9]{32}", run)
            or context["cgroup_parent"] != "/arena-workers/arena-control-" + run):
        raise ValueError("GPU create requires the authenticated admitted run context")
    python = execution["python"]
    memory = selected["memory_mb"] * 1024 ** 2
    return {"Image": execution["image"], "User": f"{os.getuid()}:{os.getgid()}",
        "WorkingDir": "/tmp", "AttachStdout": True, "AttachStderr": True,
        "Env": ["PYTHONDONTWRITEBYTECODE=1", "PYTHONPYCACHEPREFIX=/tmp/arena-pycache"],
        "Cmd": [python, "/tasks/run.py", "--root", "/tasks", "evaluate", config["task_id"],
                "--candidate", "/candidate/program.py", "--python", python,
                "--timeout", str(config["timeout_seconds"]), "--output", "/results/native.json"],
        "Labels": {"arena.evaluator": "canonical-v1", "arena.control-run": run,
                   "arena.evaluation-profile": PROFILE},
        "HostConfig": {"NetworkMode": "none", "ReadonlyRootfs": True,
            "NanoCpus": selected["cpus"] * 1_000_000_000, "Memory": memory, "MemorySwap": memory,
            "PidsLimit": selected["pids"], "CapDrop": ["ALL"], "SecurityOpt": ["no-new-privileges"],
            "CgroupParent": context["cgroup_parent"], "AutoRemove": True,
            "Tmpfs": {"/tmp": "rw,nosuid,nodev,size=268435456"},
            "Mounts": [{"Type": "bind", "Source": str(path), "Target": target, "ReadOnly": readonly}
                       for path, target, readonly in ((root, "/tasks", True), (candidate, "/candidate", True),
                                                       (results, "/results", False))]}}


class Connection(http.client.HTTPConnection):
    def __init__(self, path, timeout):
        super().__init__("localhost", timeout=timeout)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.deadline_socket = self.sock
        self.sock.settimeout(self.timeout)
        self.sock.connect(str(self.path))


def _json(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError("Duplicate GPU admission response key")
            result[key] = value
        return result
    def constant(value):
        raise ValueError("Nonfinite GPU admission response")
    result = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    if type(result) is not dict:
        raise ValueError("GPU admission response must be an object")
    return result


def _request(path, name, raw, timeout):
    connection = Connection(path, timeout)
    def expire():
        # A socket read timeout restarts for each packet. Shutdown enforces the
        # one absolute request budget even across slowly delivered headers/body.
        active = getattr(connection, "deadline_socket", None)
        if active is not None:
            try:
                active.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
    timer = threading.Timer(timeout, expire)
    timer.daemon = True
    timer.start()
    try:
        connection.request("POST", "/containers/create?name=" + name, raw,
                           {"Content-Type": "application/json"})
        response = connection.getresponse()
        lengths = response.headers.get_all("Content-Length", [])
        if (len(lengths) != 1 or not re.fullmatch(r"0|[1-9][0-9]*", lengths[0])
                or int(lengths[0]) > MAX_RESPONSE or response.headers.get_all("Transfer-Encoding")):
            raise ValueError("GPU admission requires an exact bounded response frame")
        body = response.read(MAX_RESPONSE + 1)
        if len(body) != int(lengths[0]):
            raise ValueError("GPU admission response was truncated")
        return response.status, _json(body)
    finally:
        timer.cancel()
        connection.close()


def create_when_available(body, name, environment, deadline, stats):
    """Retry only exact pre-create denials, never an uncertain Docker outcome."""
    if (environment.get("DOCKER_HOST") != DOCKER_HOST
            or not re.fullmatch(r"arena-eval-[a-f0-9]{32}", name)):
        raise ValueError("GPU admission requires the fixed restricted Unix proxy")
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    path = Path(DOCKER_HOST.removeprefix("unix://"))
    started = time.monotonic()
    stats.update(create_requests=0, busy_responses=0, wait_seconds=0.0)
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                if stats["busy_responses"]:
                    raise CapacityUnavailable("GPU capacity remained occupied until the original deadline")
                raise TimeoutError("Evaluation deadline expired before GPU admission")
            stats["create_requests"] += 1
            status, value = _request(path, name, raw, remaining)
            if status == 201:
                ident = value.get("Id")
                if (type(ident) is not str or not re.fullmatch(r"[a-f0-9]{64}", ident)
                        or set(value) - {"Id", "Warnings"}):
                    raise ValueError("GPU creation returned an uncertain container identity")
                return ident
            if status != 503 or value != BUSY_RESPONSE:
                raise ValueError("GPU creation did not return a verified success or typed capacity denial")
            stats["busy_responses"] += 1
            # No proxy lock or container exists for this denied request.
            time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
    finally:
        stats["wait_seconds"] = round(time.monotonic() - started, 6)
