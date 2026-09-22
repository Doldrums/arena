"""A distinct Docker capability for SCiEL's pinned foreground tool supervisor."""
import argparse
import http.client
import json
import os
from pathlib import Path
import re
import signal
import socket
import socketserver
import stat
import threading
import time
from urllib.parse import parse_qs, urlsplit

from .evaluator_http import Handler as StreamHandler, Server as LimitedServer
from .evaluator_policy import Denied, MAX_BODY, json_object, require
from .research_tool_policy import peer_binding
from .research_tool_server_config import Config

MAX_STREAM = 256 * 1024


def route(method, target, image_id):
    parsed = urlsplit(target)
    require(not parsed.scheme and not parsed.netloc and not parsed.fragment)
    match = re.fullmatch(r'(/v1\.[0-9]{1,3})?(/.*)', parsed.path)
    require(match is not None)
    version, path = match[1] or '', match[2]
    query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
    require(all(len(values) == 1 for values in query.values()))
    query = {key: values[0] for key, values in query.items()}
    if path in ('/_ping', '/version'):
        require(method in ('GET', 'HEAD') and not query)
        return version, 'ping' if path == '/_ping' else 'version', None, ''
    if path in ('/images/' + image_id + '/json', '/images/' + image_id.replace(':', '%3A') + '/json'):
        require(method == 'GET' and not query)
        return version, 'image', image_id, ''
    require('%' not in path)
    if path == '/containers/create':
        require(method == 'POST' and set(query) == {'name'}
                and re.fullmatch(r'sciel-method-[a-f0-9]{32}', query['name']))
        return version, 'create', query['name'], ''
    match = re.fullmatch(r'/containers/(sciel-method-[a-f0-9]{32}|[a-f0-9]{64})(?:/(json|start|wait|attach))?', path)
    require(match is not None)
    ident, action = match.groups()
    if action == 'json':
        require(method == 'GET' and not query)
    elif action == 'start':
        require(method == 'POST' and not query)
    elif action == 'wait':
        require(method == 'POST' and set(query) <= {'condition'}
                and query.get('condition', 'not-running') in ('not-running', 'next-exit', 'removed'))
    elif action == 'attach':
        require(method == 'POST' and set(query) <= {'stream', 'stdout', 'stderr', 'logs', 'stdin'})
        require(all(value in ('0', '1', 'false', 'true') for value in query.values()))
        require(query.get('stdin', '0') in ('0', 'false'))
    else:
        require(method == 'DELETE' and set(query) <= {'force', 'v', 'link'})
        require(query.get('force') in ('1', 'true') and all(
            query.get(key, '0') in ('0', 'false') for key in ('v', 'link')))
        action = 'delete'
    return version, action, ident, parsed.query


class Handler(StreamHandler):
    def handle_request(self):
        self.close_connection, self.upgraded = True, False
        try:
            require(not self.headers.get_all('Transfer-Encoding') and not self.headers.get_all('Expect'))
            lengths = self.headers.get_all('Content-Length', [])
            require(len(lengths) <= 1)
            length = int(lengths[0]) if lengths else 0
            require(0 <= length <= MAX_BODY)
            proxy = self.server.proxy
            binding = peer_binding(self.connection, proxy.config.policy)
            run_id = binding['run_id']
            version, action, ident, query = route(self.command, self.path, proxy.config.policy.image_id)
            raw = self.rfile.read(length)
            require(len(raw) == length and (action == 'create' or not raw))
            if action == 'ping':
                result = proxy.request(self.command, version + '/_ping')
            elif action == 'version':
                result = (200, {'Content-Type': 'application/json'}, json.dumps(proxy.version_info()).encode())
            elif action == 'image':
                result = (200, {'Content-Type': 'application/json'}, json.dumps(proxy.image_info()).encode())
            elif action == 'create':
                result = proxy.create(json_object(raw), ident, run_id, version, binding)
            else:
                try:
                    name, record = proxy.owned(ident, run_id)
                except KeyError:
                    # A read-only ownership probe lets the fixed CLI wrapper
                    # choose a socket BEFORE issuing a mutation. No fallback
                    # is permitted after a failed mutation or a transport error.
                    require(action == 'json')
                    self.reply(404, {'Content-Type': 'application/json'}, b'{"message":"Not owned by research capability"}')
                    return
                suffix = '' if action == 'delete' else '/' + action
                path = version + '/containers/' + record['id'] + suffix + ('?' + query if query else '')
                if action == 'attach':
                    self.attach(path, record)
                    return
                if action == 'wait':
                    self.wait(path, record)
                    return
                result = proxy.request(self.command, path, timeout=60)
                if action == 'delete' and result[0] in (204, 404):
                    proxy.remove(name, record, daemon_status=result[0])
            self.reply(*result)
        except (Denied, ValueError, KeyError, TypeError, UnicodeError, OSError, http.client.HTTPException):
            if not self.upgraded:
                try:
                    self.reply(403, {'Content-Type': 'application/json'},
                               b'{"message":"Research capability denied or could not safely complete the request"}')
                except OSError:
                    pass

    def attach(self, path, record):
        proxy = self.server.proxy
        upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        upstream.settimeout(10)
        started, captured = time.monotonic(), bytearray()
        try:
            upstream.connect(str(proxy.config.docker_socket))
            upstream.sendall(('POST ' + path + ' HTTP/1.1\r\nHost: localhost\r\nConnection: Upgrade\r\n'
                              'Upgrade: tcp\r\nContent-Length: 0\r\n\r\n').encode('ascii'))
            header = b''
            while b'\r\n\r\n' not in header:
                chunk = upstream.recv(4096)
                require(chunk and len(header) + len(chunk) <= 32768)
                header += chunk
            first, remainder = header.split(b'\r\n\r\n', 1)
            require(first.startswith((b'HTTP/1.1 101 ', b'HTTP/1.1 200 ')))
            captured.extend(remainder)
            self.upgraded = True
            self.connection.sendall(first + b'\r\n\r\n' + remainder)
            while time.monotonic() - started <= proxy.config.timeout_seconds + 30:
                try:
                    chunk = upstream.recv(65536)
                except socket.timeout:
                    continue
                if not chunk:
                    proxy.record_output(record, bytes(captured))
                    return
                require(len(captured) + len(chunk) <= MAX_STREAM)
                captured.extend(chunk)
                self.connection.sendall(chunk)
        finally:
            upstream.close()

    do_GET = do_HEAD = do_POST = do_DELETE = do_PUT = do_PATCH = handle_request


class Server(LimitedServer):
    def __init__(self, config):
        from .research_tool_execution import ResearchProxy
        self.proxy = ResearchProxy(config)
        self.slots = threading.BoundedSemaphore(32)
        socketserver.UnixStreamServer.__init__(self, str(config.socket_path), Handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    args = parser.parse_args(argv)
    info = args.config.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022 and info.st_size <= 65536)
    config = Config.read(args.config)
    config.validate_host()
    if config.socket_path.exists() or config.socket_path.is_symlink():
        info = config.socket_path.lstat()
        require(stat.S_ISSOCK(info.st_mode) and info.st_uid == 0)
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            probe.connect(str(config.socket_path))
        except ConnectionRefusedError:
            config.socket_path.unlink()
        else:
            raise Denied('Research capability socket is already in use')
        finally:
            probe.close()
    with Server(config) as server:
        server.proxy.verify_runtime()
        server.proxy.recover()
        os.chown(config.socket_path, 0, config.policy.worker_gid)
        config.socket_path.chmod(0o660)
        threading.Thread(target=server.proxy.reap, daemon=True).start()
        signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
        try:
            server.serve_forever(poll_interval=0.5)
        except KeyboardInterrupt:
            pass
        finally:
            server.proxy.close()
            config.socket_path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
