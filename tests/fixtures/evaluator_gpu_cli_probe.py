"""Standalone stdlib probe: real CLI, inert Unix daemon, no GPU or model calls."""
from contextlib import ExitStack
import http.server
import json
import os
from pathlib import Path
import platform
import socketserver
import subprocess
import tempfile
import threading
import time
from unittest.mock import patch

from arena import evaluation_resources as resources, evaluator_gpu as gpu
from arena import evaluator_gpu_leases as leases, evaluator_http as proxy_http, evaluator_policy as policy
from arena.frameworks import evaluation_gpu_client as client

RUN, NAME, IDENT = "b" * 32, "arena-eval-" + "a" * 32, "d" * 64


def configuration():
    return {"task_id": client.TASK_IDS[0], "timeout_seconds": 600,
            "execution": {"kind": "docker", "python": "python", "image": client.IMAGE,
                          "resource_profile": client.PROFILE, "require_control_cgroup": True}}


def run(config, candidate, output):
    finished = threading.Event()
    created, calls = {}, []
    class Daemon(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
        daemon_threads = True
    class Native(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        def log_message(self, *args): pass
        def reply(self, status, value=None):
            raw = json.dumps(value).encode() if value is not None else b""
            self.send_response(status)
            self.send_header("Api-Version", "1.48")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            if raw: self.wfile.write(raw)
        def do_HEAD(self): self.reply(200)
        def do_GET(self):
            self.reply(200, {"Id": IDENT, "Image": client.IMAGE,
                "Config": {"Tty": False, "OpenStdin": False}, "HostConfig": {"AutoRemove": True},
                "State": {"Running": not finished.is_set(), "Paused": False, "ExitCode": 0}})
        def do_POST(self):
            calls.append(self.path)
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if "/create?" in self.path:
                created.update(json.loads(raw)); self.reply(201, {"Id": IDENT, "Warnings": []})
            elif "/attach?" in self.path:
                self.send_response(101); self.send_header("Connection", "Upgrade")
                self.send_header("Upgrade", "tcp"); self.end_headers(); self.wfile.flush()
                assert finished.wait(5)
                self.connection.sendall(b"\x01\0\0\0\0\0\0\x03OK\n")
                self.close_connection = True
            elif "/wait?" in self.path:
                raw = b'{"StatusCode":0}'
                self.send_response(200); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.flush()
                assert finished.wait(5)
                self.wfile.write(raw)
            elif self.path.endswith("/start"):
                target = next(row["Source"] for row in created["HostConfig"]["Mounts"] if row["Target"] == "/results")
                Path(target, "native.json").write_text('{"fixture":"no candidate executed"}')
                finished.set(); self.reply(204)
            else:
                self.reply(404, {})
        def do_DELETE(self): self.reply(204)
    daemon = Daemon(str(config.docker_socket), Native)
    daemon_thread = threading.Thread(target=daemon.serve_forever, daemon=True); daemon_thread.start()
    server = proxy_http.Server(config)
    proxy_thread = threading.Thread(target=server.serve_forever, daemon=True); proxy_thread.start()
    body = client.create_body(configuration(), config.tasks_root, candidate, output,
        {"run_id": RUN, "cgroup_parent": "/arena-workers/arena-control-" + RUN})
    environment = {"PATH": os.environ.get("PATH", ""), "HOME": str(output), "DOCKER_HOST": client.DOCKER_HOST}
    try:
        stats = {}
        ident = client.create_when_available(body, NAME, environment, time.monotonic() + 15, stats)
        assert ident == IDENT and stats["create_requests"] == 1 and not finished.is_set()
        process = subprocess.run(["docker", "start", "--attach", ident], env=environment,
                                 capture_output=True, timeout=15)
        assert process.returncode == 0, process.stderr.decode()
        assert process.stdout == b"OK\n"
        assert len([path for path in calls if "/create?" in path]) == 1
        assert len([path for path in calls if path.endswith("/start")]) == 1
        assert json.loads((output / "native.json").read_text()) == {"fixture": "no candidate executed"}
        assert created["HostConfig"]["Runtime"] == "runc" and len(created["HostConfig"]["Devices"]) == 3
        return {"schema": "arena.inert-gpu-cli-probe/1", "platform": platform.system(),
                "create_requests": stats["create_requests"], "container_starts": 1,
                "cli_returncode": process.returncode, "stdout": process.stdout.decode(),
                "real_daemon_calls": 0, "model_calls": 0, "candidate_executions": 0}
    finally:
        server.proxy.close(); server.shutdown(); server.server_close(); proxy_thread.join()
        daemon.shutdown(); daemon.server_close(); daemon_thread.join()


def main():
    # Everything under these private fixture roots is synthetic and discarded.
    with tempfile.TemporaryDirectory(prefix=".arena-cli-probe-", dir=Path.home().resolve()) as directory, \
            tempfile.TemporaryDirectory(prefix="gpu-cli-", dir="/tmp") as sockets, ExitStack() as stack:
        root = Path(directory)
        tasks, runs, stage, state = (root / name for name in ("tasks", "runs", "staging", "state"))
        for path in (tasks, runs, stage, state): path.mkdir(mode=0o700)
        output = runs / RUN / "artifacts/canonical-evaluations" / ("a" * 32) / "native-output"
        candidate = output.with_name("input")
        candidate.mkdir(parents=True); output.mkdir()
        (candidate / "program.py").write_text("raise AssertionError('inert fixture must never execute')\n")
        cgroup = root / "cgroup"
        parent = cgroup / "arena-workers" / ("arena-control-" + RUN)
        parent.mkdir(parents=True)
        for name, value in (("memory.max", str(20 * 1024 ** 3)), ("pids.max", "512"), ("cpu.max", "400000 100000")):
            (parent / name).write_text(value)
        capability = gpu.LmxGpu(tasks, root / "manifest.json", "e" * 64,
            root / "model", root / "model.json", root / "driver", root / "driver.json")
        config = policy.Config(Path(sockets) / "daemon.sock", Path(sockets) / "proxy.sock", stage, tasks,
            (runs,), (client.IMAGE,), os.getuid(), os.getgid(), lmx_gpu=capability)
        for target, name, value in ((resources, "CGROUP_MOUNT", cgroup), (leases, "STATE_ROOT", state),
                (leases, "OWNER_UID", os.getuid()), (gpu.LmxGpu, "validate_host", lambda self: None),
                (proxy_http, "peer_run", lambda *args: RUN),
                (client, "DOCKER_HOST", "unix://" + str(config.socket_path))):
            stack.enter_context(patch.object(target, name, value))
        return run(config, candidate, output)


if __name__ == "__main__":
    print(json.dumps(main(), sort_keys=True))
