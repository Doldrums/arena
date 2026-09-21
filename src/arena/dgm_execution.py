"""Container lifecycle and bounded Docker operations for admitted DGM runs."""
from __future__ import annotations
import base64
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import PurePosixPath
import re
import select
import socket
import sqlite3
import stat
import struct
import subprocess
import threading
import time
from urllib.parse import quote, urlencode, urlsplit
import uuid
from .evaluator_policy import Denied, DockerConnection, RUN, directory_fd, json_object, only_defaults, read_regular, require
from .dgm_policy import BOOTSTRAP, HEX, LABEL, MAX_EXPANDED, MAX_JSON, MAX_STREAM, MAX_TAR, NATIVE_NAME, PIN, admission, atomic_record, container_path, encoded, result, root_file, route, sanitize_tar


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

    def fixed_exec(self, record, command, *, input_bytes=b"", maximum=4096, seconds=120, client=None):
        """Trusted archive I/O only; this is never a caller-selected stdin API.

        Docker's archive endpoints cannot access the live tmpfs view of an RO
        container. Execute fixed stat/tar commands inside that owned container,
        retaining the actual daemon exit status and multiplex protocol.
        """
        require(len(input_bytes) <= MAX_TAR and maximum <= MAX_TAR)
        deadline = min(record["expires"], time.time() + seconds)
        def connected():
            require(client is None or not select.select([client], [], [], 0)[0],
                    "Archive client disconnected or attempted extra input")
        upstream = None; completed = False
        try:
            connected()
            status, _, raw = self.request("POST", "/containers/" + record["id"] + "/exec", encoded({
                "User": "0:0", "Privileged": False, "Tty": False, "WorkingDir": "/",
                "AttachStdin": bool(input_bytes), "AttachStdout": True, "AttachStderr": True, "Cmd": command}))
            require(status == 201)
            ident = json_object(raw).get("Id"); require(type(ident) is str and HEX.fullmatch(ident))
            upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            upstream.settimeout(min(30, max(0.1, deadline - time.time())))
            upstream.connect(str(self.config.docker_socket))
            body = b'{"Detach":false,"Tty":false}'
            upstream.sendall(("POST /exec/" + ident + "/start HTTP/1.1\r\nHost: localhost\r\n"
                              "Connection: Upgrade\r\nUpgrade: tcp\r\nContent-Type: application/json\r\n"
                              "Content-Length: " + str(len(body)) + "\r\n\r\n").encode() + body)
            header = b""
            while b"\r\n\r\n" not in header:
                connected()
                require(time.time() < deadline, "Archive command exceeded its deadline")
                if not select.select([upstream], [], [], min(1, max(0, deadline - time.time())))[0]: continue
                part = upstream.recv(4096); require(part and len(header) + len(part) <= 32768)
                header += part
            first, buffer = header.split(b"\r\n\r\n", 1)
            require(first.startswith((b"HTTP/1.1 101 ", b"HTTP/1.1 200 ")))
            upstream.setblocking(False)
            output = bytearray(); errors = 0; wire_size = len(buffer); sent = 0; shut = False
            while time.time() < deadline and not self.stop_event.is_set():
                connected()
                while len(buffer) >= 8:
                    stream, size = struct.unpack(">BxxxI", buffer[:8])
                    require(stream in {1, 2} and size <= (maximum if stream == 1 else 65536))
                    if len(buffer) < 8 + size: break
                    payload = buffer[8:8 + size]; buffer = buffer[8 + size:]
                    if stream == 1:
                        output.extend(payload); require(len(output) <= maximum)
                    else:
                        errors += len(payload); require(errors <= 65536)
                if sent == len(input_bytes) and not shut:
                    upstream.shutdown(socket.SHUT_WR); shut = True
                reads, writes, _ = select.select([upstream], [upstream] if sent < len(input_bytes) else [], [], min(1, max(0, deadline - time.time())))
                if writes:
                    try: sent += upstream.send(input_bytes[sent:sent + 65536])
                    except BlockingIOError: pass
                if reads:
                    try: part = upstream.recv(65536)
                    except BlockingIOError: continue
                    if not part:
                        require(not buffer and sent == len(input_bytes), "Incomplete Docker archive exec stream")
                        break
                    wire_size += len(part); require(wire_size <= maximum + 65536 + 1024 * 1024)
                    buffer += part
            else:
                raise Denied("Archive command exceeded its deadline")
            while time.time() < deadline:
                connected()
                inspection = self.request("GET", "/exec/" + ident + "/json")
                require(inspection[0] == 200)
                info = json_object(inspection[2])
                if not info.get("Running"):
                    require(info.get("ExitCode") == 0, "Native archive command failed")
                    completed = True
                    return bytes(output)
                time.sleep(0.05)
            raise Denied("Archive command completion is unconfirmed")
        finally:
            if upstream is not None: upstream.close()
            if not completed: self.delete(record)

    def archive(self, record, action, path, raw, client=None):
        container_path(path)
        transfer = {"operation": action, "path": path, "status": "started"}
        with self.lock:
            require(self.records.get(record["record_id"]) is record and record["state"] != "removed")
            require(len(record["transfers"]) < 1024)
            record["transfers"].append(transfer); self.persist(record)
        try:
            if action == "archive_put":
                clean = sanitize_tar(raw)
                transfer.update(bytes=len(clean), sha256=hashlib.sha256(clean).hexdigest(),
                                wire_sha256=hashlib.sha256(raw).hexdigest())
                self.persist(record)
                self.fixed_exec(record, ["/bin/tar", "--no-same-owner", "-xf", "-", "-C", path],
                                input_bytes=clean, maximum=4096, client=client)
                response = 200, {"Content-Type": "application/json"}, b""
            else:
                stat_bytes = self.fixed_exec(record, ["/usr/bin/stat", "-c", "%s %f %Y", "--", path], seconds=30, client=client)
                values = stat_bytes.decode("ascii").strip().split()
                require(len(values) == 3 and values[0].isdigit() and re.fullmatch(r"[0-9a-fA-F]+", values[1])
                        and re.fullmatch(r"-?[0-9]+", values[2]))
                size, mode, modified = int(values[0]), int(values[1], 16), int(values[2])
                require(stat.S_ISREG(mode) or stat.S_ISDIR(mode), "Only native regular files/directories may be exported")
                require(size <= MAX_EXPANDED)
                root = PurePosixPath(path)
                exported = self.fixed_exec(record, ["/bin/tar", "--format=pax", "-cf", "-", "-C", str(root.parent), "--", root.name], maximum=MAX_TAR, client=client)
                clean = sanitize_tar(exported, root.name)
                item = {"name": root.name, "size": size, "mode": (mode & 0o777) | (1 << 31 if stat.S_ISDIR(mode) else 0),
                        "mtime": datetime.fromtimestamp(modified, timezone.utc).isoformat().replace("+00:00", "Z"), "linkTarget": ""}
                transfer.update(bytes=len(clean), sha256=hashlib.sha256(clean).hexdigest(),
                                wire_sha256=hashlib.sha256(exported).hexdigest())
                response = 200, {"Content-Type": "application/x-tar", "X-Docker-Container-Path-Stat": base64.b64encode(encoded(item)).decode()}, clean
            transfer["status"] = 200
            self.persist(record)
            return response
        except BaseException:
            transfer["status"] = "failed"
            try: self.delete(record)
            finally:
                # persist writes the journal only. A confirmed delete's removed
                # state/capability removal is retained alongside this failure.
                self.persist(record)
            raise

    def dispatch(self, method, target, raw, run_id, admitted, client=None):
        version, action, ident, query = route(method, target)
        require(action in {"create", "exec", "exec_start", "archive_put"} or not raw)
        if action in {"_ping", "version"}:
            return self.request(method, version + "/" + action)
        if action == "info":
            status, _, native = self.request("GET", "/info"); data = json_object(native)
            return result({k: data[k] for k in ("CgroupDriver", "CgroupVersion")}, status)
        if action == "image":
            native = self.image(ident)
            bindings = [b for b in self.config.images if b["image_id"] == native["Id"]]
            return result({**{k: native[k] for k in ("Id", "Created", "Os", "Architecture")},
                           "RepoTags": [b["alias"] for b in bindings],
                           "RepoDigests": [b["reference"] for b in bindings]})
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
            return self.archive(record, action, query["path"], raw, client)
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
