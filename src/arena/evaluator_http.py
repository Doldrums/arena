"""Restricted, Linux-only Docker socket for canonical Arena evaluations.

This is a privileged boundary, not a general Docker proxy. Requests are rebuilt
from a fixed evaluator profile. No caller-provided Docker configuration is
forwarded, and mutable candidate/output paths are never passed to the daemon."""
from __future__ import annotations
import argparse
import http.client
from http.server import BaseHTTPRequestHandler
import os
from pathlib import Path
import signal
import socket
import socketserver
import stat
import threading
import time
from .evaluator_policy import Config, Denied, DockerConnection, MAX_BODY, MAX_RESPONSE, MAX_STREAM, engine_binding, json_object, peer_run, require, route
from .evaluator_execution import Proxy


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(20)

    def reply(self, status, headers, raw):
        self.send_response(status)
        for key, value in headers.items():
            if key.lower() in {"content-type", "api-version", "docker-experimental", "ostype", "builder-version"}:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(raw)

    def handle_request(self):
        self.close_connection = True
        self.upgraded = False
        try:
            require(not self.headers.get_all("Transfer-Encoding") and not self.headers.get_all("Expect"))
            lengths = self.headers.get_all("Content-Length", [])
            require(len(lengths) <= 1)
            length = int(lengths[0]) if lengths else 0
            require(0 <= length <= MAX_BODY)
            run_id = peer_run(self.connection, self.server.proxy.config)
            version, action, ident, query = route(self.command, self.path)
            raw = self.rfile.read(length)
            require(len(raw) == length and (action == "create" or not raw))
            proxy = self.server.proxy
            if action == "info":
                result = proxy.request(self.command, self.path)
            elif action == "cgroup_info":
                result = proxy.cgroup_info()
            elif action == "create":
                binding = (engine_binding(self.connection, proxy.config)
                           if proxy.config.engine_registry is not None else None)
                result = proxy.create(json_object(raw), ident, run_id, version, binding)
            else:
                name, record = proxy.owned(ident, run_id)
                suffix = "" if action == "delete" else "/" + action
                path = version + "/containers/" + record["id"] + suffix + ("?" + query if query else "")
                if action == "attach":
                    self.attach(path, record)
                    return
                if action == "wait":
                    self.wait(path, record)
                    return
                result = proxy.request(self.command, path, timeout=proxy.config.timeout_seconds + 30)
                if action in {"wait", "json", "delete"}:
                    proxy.publish(record)
                if action == "delete" and result[0] in {204, 404}:
                    proxy.remove(name, record)
            self.reply(*result)
        except (Denied, ValueError, KeyError, TypeError, UnicodeError, OSError, http.client.HTTPException):
            if not self.upgraded:
                try:
                    self.reply(403, {"Content-Type": "application/json"}, b'{"message":"Evaluator proxy denied or could not safely complete the request"}')
                except OSError:
                    pass

    def wait(self, path, record):
        # Docker CLI establishes /wait before /start and waits for its HTTP
        # headers. Buffering those headers until exit deadlocks that handshake.
        proxy = self.server.proxy
        connection = DockerConnection(proxy.config.docker_socket, proxy.config.timeout_seconds + 30)
        try:
            connection.request("POST", path, body=b"")
            response = connection.getresponse()
            self.send_response(response.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Transfer-Encoding", "chunked")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.flush()
            self.upgraded = True
            raw = response.read(MAX_RESPONSE + 1)
            require(len(raw) <= MAX_RESPONSE)
            proxy.publish(record)
            if raw:
                self.wfile.write(f"{len(raw):x}\r\n".encode() + raw + b"\r\n")
            self.wfile.write(b"0\r\n\r\n")
        finally:
            connection.close()

    def attach(self, path, record):
        # Docker uses an HTTP upgrade for multiplexed stdout/stderr. Only the
        # daemon-to-client direction is relayed: stdin/exec are never allowed.
        upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        upstream.settimeout(30)
        started = time.monotonic()
        try:
            upstream.connect(str(self.server.proxy.config.docker_socket))
            upstream.sendall(("POST " + path + " HTTP/1.1\r\nHost: localhost\r\nConnection: Upgrade\r\n"
                              "Upgrade: tcp\r\nContent-Length: 0\r\n\r\n").encode("ascii"))
            header = b""
            while b"\r\n\r\n" not in header:
                chunk = upstream.recv(4096)
                require(chunk and len(header) + len(chunk) <= 32768)
                header += chunk
            first, remainder = header.split(b"\r\n\r\n", 1)
            require(first.startswith((b"HTTP/1.1 101 ", b"HTTP/1.1 200 ")))
            self.upgraded = True
            self.connection.sendall(first + b"\r\n\r\n" + remainder)
            size = len(remainder)
            while time.monotonic() - started <= self.server.proxy.config.timeout_seconds + 30:
                try:
                    chunk = upstream.recv(65536)
                except socket.timeout:
                    continue
                if not chunk:
                    # Docker CLI can finish as soon as attach closes, before its
                    # concurrent wait handler finishes. Publish before that EOF.
                    self.server.proxy.publish(record)
                    return
                size += len(chunk)
                require(size <= MAX_STREAM, "Evaluator output exceeded its stream limit")
                self.connection.sendall(chunk)
        finally:
            upstream.close()

    do_GET = do_HEAD = do_POST = do_DELETE = do_PUT = do_PATCH = handle_request


class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    request_queue_size = 32

    def __init__(self, config):
        self.proxy = Proxy(config)
        self.slots = threading.BoundedSemaphore(64)
        super().__init__(str(config.socket_path), Handler)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    info = args.config.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
            "Proxy config must be a root-owned non-writable regular file")
    config = Config.read(args.config)
    config.validate_host()
    if config.socket_path.exists() or config.socket_path.is_symlink():
        info = config.socket_path.lstat()
        require(stat.S_ISSOCK(info.st_mode) and info.st_uid == 0, "Refusing to replace an unsafe socket path")
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            probe.connect(str(config.socket_path))
        except ConnectionRefusedError:
            config.socket_path.unlink()
        else:
            raise Denied("An evaluator proxy is already serving this socket")
        finally:
            probe.close()
    with Server(config) as server:
        server.proxy.cgroup_info()
        server.proxy.recover()
        os.chown(config.socket_path, 0, config.worker_gid)
        config.socket_path.chmod(0o660)
        threading.Thread(target=server.proxy.reap, daemon=True).start()
        def stop(signum, frame):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, stop)
        try:
            server.serve_forever(poll_interval=0.5)
        except KeyboardInterrupt:
            pass
        finally:
            server.proxy.close()
            config.socket_path.unlink(missing_ok=True)
