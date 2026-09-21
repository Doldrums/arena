"""Root-owned broker for an operator-approved private SCiEL image.

Only explicit admitted runs reach Docker. Clients supply an existing run ID and
deployment digest, never an image, mount, command, credential, or Docker option."""
from __future__ import annotations
import argparse
import http.client
from http.server import BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import re
import select
import signal
import socket
import socketserver
import sqlite3
import stat
import threading
from types import SimpleNamespace
from .evaluator_policy import Denied, json_object, peer_run, require
from .engine_policy import Config, root_file
from .engine_execution import Broker


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
