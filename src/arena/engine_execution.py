"""Private engine container lifecycle, bounded logs, and artifact publication."""
from __future__ import annotations
import codecs
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import struct
import threading
import time
from urllib.parse import quote
import uuid
from .evaluator_policy import Denied, DockerConnection, RUN, directory_fd, json_object, read_regular, require
from .release_deployment import inspect_image_evidence
from .engine_policy import MAX_ARTIFACTS, MAX_JSON, MAX_LOG, admission, checked_native_config, input_file, replace_private, root_file, stage_tree, write_private


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
        for path in config.library_roots:
            descriptor = directory_fd(path)
            os.close(descriptor)
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
                                          *[mount(path, path) for path in config.library_roots],
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
