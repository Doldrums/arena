"""Canonical evaluator container lifecycle and result publication."""
from __future__ import annotations
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import threading
import time
import uuid
from .evaluator_policy import Denied, DockerConnection, MAX_RESPONSE, RUN, canonical_config, directory_fd, json_object, read_regular, require


class Proxy:
    def __init__(self, config):
        self.config = config
        self.records = {}
        self.lock = threading.RLock()
        self.gpu_leases = None
        if config.lmx_gpu is not None:
            from .evaluator_gpu_leases import GpuLeases
            self.gpu_leases = GpuLeases(config.staging_root)

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

    def create(self, body, name, run_id, version, binding=None):
        rebuilt, candidate, output = canonical_config(body, name, run_id, self.config)
        if binding is not None:
            # The body still uses its admitted logical paths. Only root-issued
            # engine identity can map them to protected engine staging storage.
            logical = next(root / run_id / "artifacts" for root in self.config.run_roots
                           if candidate.is_relative_to(root / run_id / "artifacts"))
            require(binding["run_id"] == run_id)
            physical = Path(binding["artifact_root"])
            require(physical == self.config.engine_staging_root / run_id / "artifacts")
            candidate, output = physical / candidate.relative_to(logical), physical / output.relative_to(logical)
        with self.lock:
            require(len(self.records) < self.config.max_containers and name not in self.records,
                    "Evaluator container capacity reached")
            candidate_fd, output_fd, stage = None, None, None
            gpu_lease = None
            keep_stage = False
            try:
                candidate_fd, output_fd = directory_fd(candidate), directory_fd(output)
                require(os.fstat(candidate_fd).st_uid == self.config.worker_uid
                        and os.fstat(output_fd).st_uid == self.config.worker_uid)
                program = read_regular(candidate_fd, "program.py", 16 * 1024 ** 2, self.config.worker_uid)
                stage = self.config.staging_root / uuid.uuid4().hex
                stage.mkdir(mode=0o755)
                (stage / "candidate").mkdir(mode=0o755)
                # The service's restrictive umask must not make the bind root
                # unreadable to the non-root container user.
                (stage / "candidate").chmod(0o755)
                (stage / "candidate" / "program.py").write_bytes(program)
                (stage / "candidate" / "program.py").chmod(0o444)
                (stage / "results").mkdir(mode=0o700)
                os.chown(stage / "results", self.config.worker_uid, self.config.worker_gid)
                # Persist the name before asking Docker to create. If transport
                # fails after daemon creation, restart recovery still knows it.
                recovery = {"id": None, "run": run_id, "name": name}
                if "arena.evaluation-profile" in rebuilt["Labels"]:
                    recovery["resource_profile"] = rebuilt["Labels"]["arena.evaluation-profile"]
                if "arena.gpu-capability" in rebuilt["Labels"]:
                    require(self.gpu_leases is not None)
                    recovery["gpu"] = {"device_uuid": rebuilt["Labels"]["arena.gpu-device"],
                                       "image": rebuilt["Image"], "labels": rebuilt["Labels"]}
                    # Durable ownership precedes both the transient staging
                    # record and Docker POST. A lost response still owns GPU.
                    gpu_lease = self.gpu_leases.reserve(recovery, stage)
                (stage / "record.json").write_text(json.dumps(recovery))
                # Retain only the trusted library mount rebuilt by policy;
                # caller-writable candidate/results paths are always replaced.
                rebuilt["HostConfig"]["Mounts"] = [*rebuilt["HostConfig"]["Mounts"],
                    {"Type": "bind", "Source": str(stage / "candidate"), "Target": "/candidate", "ReadOnly": True},
                    {"Type": "bind", "Source": str(stage / "results"), "Target": "/results", "ReadOnly": False}]
                keep_stage = True
                result = self.request("POST", version + "/containers/create?name=" + name, json.dumps(rebuilt).encode())
                if result[0] == 201:
                    ident = json_object(result[2]).get("Id")
                    require(type(ident) is str and re.fullmatch(r"[a-f0-9]{64}", ident))
                    if gpu_lease is not None:
                        self.gpu_leases.identify(gpu_lease, ident)
                    recovery["id"] = ident
                    (stage / "record.json").write_text(json.dumps(recovery))
                    self.records[name] = {"id": ident, "run": run_id, "stage": stage, "output_fd": output_fd,
                                          "expires": time.monotonic() + int(rebuilt["Cmd"][11]) + 60,
                                          "candidate_sha256": hashlib.sha256(program).hexdigest()}
                    if gpu_lease is not None:
                        self.records[name]["gpu_lease"] = gpu_lease
                    stage, output_fd = None, None
                elif 400 <= result[0] < 500 and gpu_lease is None:
                    keep_stage = False
                return result
            finally:
                for descriptor in (candidate_fd, output_fd):
                    if descriptor is not None:
                        os.close(descriptor)
                if stage is not None and not keep_stage:
                    if self.gpu_leases is None or not self.gpu_leases.owns_stage(stage):
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

    def remove(self, name, record, *, daemon_status=None):
        with self.lock:
            if "gpu_lease" in record:
                require(daemon_status in (204, 404), "GPU cleanup requires confirmed daemon deletion")
            self.publish(record)
            if not record.get("closed"):
                shutil.rmtree(record["stage"])
                if "gpu_lease" in record:
                    self.gpu_leases.release(record["gpu_lease"], daemon_status)
                record["closed"] = True
                os.close(record["output_fd"])
                self.records.pop(name, None)

    def reap(self):
        while True:
            time.sleep(10)
            with self.lock:
                expired = [(name, record) for name, record in self.records.items()
                           if time.monotonic() > record["expires"]]
            for name, record in expired:
                try:
                    result = self.request("DELETE", "/containers/" + record["id"] + "?force=1")
                    if result[0] in {204, 404}:
                        self.remove(name, record, daemon_status=result[0])
                except (OSError, ValueError, http.client.HTTPException):
                    pass

    def recover(self):
        """On restart, kill only persisted, label-verified owned containers."""
        if self.gpu_leases is not None:
            self.gpu_leases.recover(self.request)
        for stage in self.config.staging_root.iterdir():
            require(not stage.is_symlink() and stage.is_dir() and RUN.fullmatch(stage.name))
            metadata = stage / "record.json"
            if metadata.exists():
                require(metadata.is_file() and not metadata.is_symlink() and metadata.stat().st_size <= 4096)
                record = json_object(metadata.read_bytes())
                require(set(record) in ({"id", "run", "name"}, {"id", "run", "name", "resource_profile"})
                        and RUN.fullmatch(record["run"])
                        and (record["id"] is None or re.fullmatch(r"[a-f0-9]{64}", record["id"]))
                        and re.fullmatch(r"arena-eval-[a-f0-9]{32}", record["name"]))
                labels = {"arena.evaluator": "canonical-v1", "arena.control-run": record["run"]}
                if "resource_profile" in record:
                    from .evaluation_resources import PROFILES
                    profile = record["resource_profile"]
                    require(type(profile) is str and profile in PROFILES)
                    labels["arena.evaluation-profile"] = profile
                status, _, raw = self.request("GET", "/containers/" + (record["id"] or record["name"]) + "/json")
                if status != 404:
                    require(status == 200)
                    native = json_object(raw)
                    ident = native.get("Id")
                    require(type(ident) is str and re.fullmatch(r"[a-f0-9]{64}", ident)
                            and (record["id"] is None or ident == record["id"])
                            and native.get("Config", {}).get("Labels") == labels)
                    deleted = self.request("DELETE", "/containers/" + ident + "?force=1")
                    require(deleted[0] in {204, 404})
            shutil.rmtree(stage)

    def close(self):
        for name, record in list(self.records.items()):
            try:
                result = self.request("DELETE", "/containers/" + record["id"] + "?force=1")
                if result[0] in {204, 404}:
                    self.remove(name, record, daemon_status=result[0])
            except (OSError, ValueError, http.client.HTTPException):
                pass  # Preserve the root-owned record for restart recovery.
