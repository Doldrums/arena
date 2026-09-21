"""Bounded loopback TLS transport for native HTTPS-only provider clients.

This relay preserves request bytes and Authorization, forwards only to the
operator's local gateway, and never reads a provider credential file. It is not
an authentication service: the upstream gateway authenticates every request.
"""
from __future__ import annotations

import argparse
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import ssl
import threading

MAX_BODY = 8 * 1024 * 1024
MAX_RESPONSE = 16 * 1024 * 1024
MAX_HEADERS = 16 * 1024
DEADLINE = 180


class RelayServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, context, *, upstream_port=8789, deadline=DEADLINE, concurrency=32):
        if address[0] != "127.0.0.1" or not 1 <= upstream_port <= 65535:
            raise ValueError("Relay and upstream must use fixed IPv4 loopback")
        if not 1 <= deadline <= 300 or not 1 <= concurrency <= 64:
            raise ValueError("Invalid relay limits")
        self.context = context
        self.upstream_port = upstream_port
        self.deadline = deadline
        self.slots = threading.BoundedSemaphore(concurrency)
        super().__init__(address, RelayHandler)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()

    def handle_error(self, request, client_address):
        # A traceback may include sensitive input. Clients receive fixed errors.
        pass


class RelayHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "ArenaLocalTLS"

    def setup(self):
        self.request.settimeout(10)
        self.request = self.server.context.wrap_socket(self.request, server_side=True)
        self.upstream = None
        self.deadline_timer = threading.Timer(self.server.deadline, self._expire)
        self.deadline_timer.daemon = True
        self.deadline_timer.start()
        super().setup()

    def _expire(self):
        # Closing both sockets also bounds a peer that sends bytes indefinitely.
        for connection in (self.connection, getattr(self.upstream, "sock", None),
                           getattr(self, "response_socket", None)):
            if connection is not None:
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                try:
                    connection.close()
                except OSError:
                    pass

    def finish(self):
        self.deadline_timer.cancel()
        if self.upstream is not None:
            self.upstream.close()
        super().finish()

    def log_message(self, format, *args):
        pass

    def handle_expect_100(self):
        self._reply(417, b'{"error":"expectation_not_supported"}')
        return False

    def _reply(self, status, data, content_type="application/json"):
        self.close_connection = True
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)

    def _relay(self):
        self.close_connection = True
        allowed = (self.command == "POST" and self.path == "/v1/chat/completions") or (
            self.command == "GET" and self.path == "/v1/models")
        if not allowed:
            self._reply(404, b'{"error":"route_not_allowed"}')
            return
        if (sum(len(k) + len(v) + 4 for k, v in self.headers.items()) > MAX_HEADERS
                or self.headers.get_all("Transfer-Encoding")
                or len(self.headers.get_all("Content-Length", [])) > 1
                or len(self.headers.get_all("Authorization", [])) > 1):
            self._reply(400, b'{"error":"invalid_headers"}')
            return
        length = self.headers.get("Content-Length", "0")
        if not length.isascii() or not length.isdecimal() or len(length) > 9:
            self._reply(400, b'{"error":"invalid_length"}')
            return
        length = int(length)
        if length > MAX_BODY or (self.command == "GET" and length):
            self._reply(413, b'{"error":"request_too_large"}')
            return
        try:
            body = self.rfile.read(length)
            if len(body) != length:
                self._reply(400, b'{"error":"incomplete_body"}')
                return
            headers = {"Content-Type": "application/json", "Connection": "close"}
            if "Authorization" in self.headers:
                headers["Authorization"] = self.headers["Authorization"]
            self.upstream = http.client.HTTPConnection("127.0.0.1", self.server.upstream_port,
                                                       timeout=self.server.deadline)
            self.upstream.request(self.command, self.path, body=body, headers=headers)
            response = self.upstream.getresponse()
            # Hold a reference after HTTPConnection detaches a close-delimited
            # response socket, so the absolute deadline still interrupts it.
            self.response_socket = response.fp.raw._sock
            data = response.read(MAX_RESPONSE + 1)
            if len(data) > MAX_RESPONSE:
                self._reply(502, b'{"error":"response_too_large"}')
                return
            if not 200 <= response.status <= 599:
                self._reply(502, b'{"error":"invalid_upstream_status"}')
                return
            self._reply(response.status, data)
        except (OSError, ValueError, http.client.HTTPException):
            try:
                self._reply(502, b'{"error":"local_gateway_unavailable"}')
            except OSError:
                pass
        finally:
            if self.upstream is not None:
                self.upstream.close()

    do_POST = _relay
    do_GET = _relay


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certificate", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8790)
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("port must be an unprivileged local port")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(args.certificate, args.private_key)
    with RelayServer(("127.0.0.1", args.port), context) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
