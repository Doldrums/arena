"""Run-scoped Docker SDK capability for the pinned, prebuilt DGM experiment.

This service is deliberately separate from the canonical evaluator and SCiEL
brokers. It never builds/pulls images or mounts host paths into a container.
Native commands execute only inside approved, offline, resource-bound images."""
from __future__ import annotations
import argparse
import hmac
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import select
import signal
import socket
import socketserver
import sqlite3
import stat
import threading
import time
from urllib.parse import urlsplit
from .evaluator_policy import Denied, json_object, require
from .dgm_policy import Config, MAX_JSON, MAX_STREAM, MAX_TAR, REQUEST_TIMEOUT, admission, peer_run, result, route
from .dgm_execution import Proxy


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args): pass

    def setup(self):
        super().setup(); self.connection.settimeout(30)

    def reply(self, status, headers, raw):
        self.send_response(status)
        for key, value in headers.items():
            if key.lower() in {"content-type", "api-version", "ostype", "docker-experimental", "x-docker-container-path-stat"}:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(raw))); self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD": self.wfile.write(raw)

    def handle_request(self):
        self.close_connection = True; self.upgraded = False
        archive_slot = False; archive_record = None
        try:
            proxy = self.server.proxy
            require(not self.headers.get_all("Transfer-Encoding") and not self.headers.get_all("Expect"))
            lengths = self.headers.get_all("Content-Length", []); require(len(lengths) <= 1)
            length = int(lengths[0]) if lengths else 0
            _, action, ident, _ = route(self.command, self.path)
            if action.startswith("archive_"):
                archive_slot = self.server.archive_slots.acquire(blocking=False)
                require(archive_slot, "Archive I/O capacity reached")
            require(0 <= length <= (MAX_TAR if action == "archive_put" else MAX_JSON))
            run_id = peer_run(self.connection, proxy.config)
            admitted = admission(proxy.config, run_id)
            if action.startswith("archive_"): archive_record = proxy.owned(ident, run_id)
            raw = self.rfile.read(length); require(len(raw) == length)
            response = proxy.dispatch(self.command, self.path, raw, run_id, admitted, self.connection)
            if type(response) is dict: self.stream_exec(response["stream"], response["record"])
            else: self.reply(*response)
        except (ValueError, KeyError, TypeError, OSError, http.client.HTTPException, sqlite3.Error):
            if archive_record is not None:
                try: proxy.delete(archive_record)
                except (ValueError, OSError, http.client.HTTPException): pass
            if not self.upgraded:
                try: self.reply(*result({"message": "DGM proxy denied or could not safely complete the request"}, 403))
                except OSError: pass
        finally:
            if archive_slot: self.server.archive_slots.release()

    def stream_exec(self, path, record):
        """Real Docker hijack, stdout/stderr direction only, no interactive stdin."""
        proxy = self.server.proxy
        upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        upstream.settimeout(30); complete = False
        try:
            upstream.connect(str(proxy.config.docker_socket))
            body = b'{"Detach":false,"Tty":false}'
            request = ("POST " + path + " HTTP/1.1\r\nHost: localhost\r\nConnection: Upgrade\r\nUpgrade: tcp\r\n"
                       "Content-Type: application/json\r\nContent-Length: " + str(len(body)) + "\r\n\r\n").encode() + body
            upstream.sendall(request)
            header = b""
            while b"\r\n\r\n" not in header:
                chunk = upstream.recv(4096); require(chunk and len(header) + len(chunk) <= 32768)
                header += chunk
            first, rest = header.split(b"\r\n\r\n", 1)
            require(first.startswith((b"HTTP/1.1 101 ", b"HTTP/1.1 200 ")))
            upstream.settimeout(1)
            # The upstream raw stream is Docker's native multiplex format.
            self.upgraded = True
            self.connection.sendall(b"HTTP/1.1 101 UPGRADED\r\nContent-Type: application/vnd.docker.raw-stream\r\nConnection: Upgrade\r\nUpgrade: tcp\r\n\r\n" + rest)
            size = len(rest)
            while time.time() < record["expires"] and not proxy.stop_event.is_set():
                if select.select([self.connection], [], [], 0)[0]:
                    # Neither EOF nor caller input is valid during one-way exec.
                    raise Denied("Exec client disconnected or attempted stdin")
                try: chunk = upstream.recv(65536)
                except socket.timeout: continue
                if not chunk: complete = True; return
                size += len(chunk); require(size <= MAX_STREAM, "Native exec output exceeded bound")
                self.connection.sendall(chunk)
        finally:
            upstream.close()
            if not complete:
                # A lost exec transport must not leave an unobserved paid process.
                proxy.delete(record)

    do_GET = do_HEAD = do_POST = do_PUT = do_DELETE = do_PATCH = handle_request


class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    request_queue_size = 32

    def __init__(self, config):
        self.proxy = Proxy(config); self.slots = threading.BoundedSemaphore(32)
        self.archive_slots = threading.BoundedSemaphore(2)
        super().__init__(str(config.socket_path), Handler)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False): request.close(); return
        try: super().process_request(request, address)
        except BaseException: self.slots.release(); raise

    def process_request_thread(self, request, address):
        try: super().process_request_thread(request, address)
        finally: self.slots.release()


class RelayHandler(BaseHTTPRequestHandler):
    """Only an owned active container may reach the fixed loopback model API."""
    protocol_version = "HTTP/1.1"

    def setup(self):
        super().setup()
        self.connection.settimeout(REQUEST_TIMEOUT)

    def log_message(self, *args): pass

    def handle_request(self):
        self.close_connection = True; sent = False
        connection = None
        try:
            proxy = self.server.proxy
            require((self.command, self.path) in {("GET", "/v1/models"), ("POST", "/v1/responses"), ("POST", "/v1/chat/completions")})
            require(not self.headers.get_all("Transfer-Encoding") and not self.headers.get_all("Expect"))
            auth = self.headers.get_all("Authorization", [])
            require(len(auth) == 1 and hmac.compare_digest(auth[0], "Bearer " + proxy.gateway_key))
            with proxy.lock: records = list(proxy.records.values())
            found = []
            for record in records:
                if record["id"] is None: continue
                status, _, raw = proxy.request("GET", "/containers/" + record["id"] + "/json")
                if status != 200: continue
                info = json_object(raw)
                proxy.verify_owned_inspect(info, record)
                networks = info.get("NetworkSettings", {}).get("Networks", {}).values()
                if any(v.get("NetworkID") == proxy.config.network_id and v.get("IPAddress") == self.client_address[0] for v in networks):
                    found.append(record)
            require(len(found) == 1 and time.time() < found[0]["expires"])
            admitted = admission(proxy.config, found[0]["run"])
            lengths = self.headers.get_all("Content-Length", []); require(len(lengths) <= 1)
            length = int(lengths[0]) if lengths else 0
            require(0 <= length <= MAX_JSON and (self.command == "POST" or length == 0))
            self.connection.settimeout(30)
            body = self.rfile.read(length); require(len(body) == length)
            if self.command == "POST": require(json_object(body).get("model") == admitted["model"])
            connection = http.client.HTTPConnection("127.0.0.1", 8789, timeout=300)
            connection.request(self.command, self.path, body=body,
                               headers={"Content-Type": "application/json", "Authorization": "Bearer " + proxy.gateway_key})
            response = connection.getresponse()
            self.send_response(response.status)
            self.send_header("Content-Type", response.getheader("Content-Type", "application/json"))
            for key, value in response.getheaders():
                if key.lower().startswith("x-arena-") or key.lower() == "x-request-id":
                    self.send_header(key, value)
            self.send_header("Transfer-Encoding", "chunked"); self.send_header("Connection", "close")
            self.end_headers(); sent = True
            size = 0
            while time.time() < found[0]["expires"]:
                chunk = response.read1(65536)
                if not chunk:
                    self.wfile.write(b"0\r\n\r\n"); return
                size += len(chunk); require(size <= 16 * 1024**2)
                self.wfile.write(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n"); self.wfile.flush()
        except (ValueError, KeyError, TypeError, OSError, http.client.HTTPException, sqlite3.Error):
            if not sent:
                try:
                    raw = b'{"error":{"message":"DGM relay request denied"}}'
                    self.send_response(403); self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(raw))); self.send_header("Connection", "close")
                    self.end_headers(); self.wfile.write(raw)
                except OSError: pass
        finally:
            if connection: connection.close()

    do_GET = do_POST = do_PUT = do_DELETE = do_CONNECT = handle_request


class RelayServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, proxy):
        self.proxy = proxy; self.slots = threading.BoundedSemaphore(16)
        super().__init__((urlsplit(proxy.config.relay_url).hostname, 8789), RelayHandler)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False): request.close(); return
        try: super().process_request(request, address)
        except BaseException: self.slots.release(); raise

    def process_request_thread(self, request, address):
        try: super().process_request_thread(request, address)
        finally: self.slots.release()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    config = Config.read(args.config); config.host_check()
    if config.socket_path.exists() or config.socket_path.is_symlink():
        info = config.socket_path.lstat()
        require(stat.S_ISSOCK(info.st_mode) and info.st_uid == 0)
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            probe.connect(str(config.socket_path))
        except ConnectionRefusedError: config.socket_path.unlink()
        else: raise Denied("DGM proxy is already serving this socket")
        finally: probe.close()
    with Server(config) as server:
        server.proxy.preflight(); server.proxy.recover()
        os.chown(config.socket_path, 0, config.worker_gid); config.socket_path.chmod(0o660)
        threading.Thread(target=server.proxy.reap, daemon=True).start()
        relay = RelayServer(server.proxy)
        threading.Thread(target=relay.serve_forever, daemon=True).start()
        def stop(signum, frame): raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, stop)
        try: server.serve_forever(poll_interval=0.5)
        except KeyboardInterrupt: pass
        finally:
            server.proxy.close(); relay.shutdown(); relay.server_close(); config.socket_path.unlink(missing_ok=True)
