"""Route the pinned native Docker command families to two restricted brokers.

This is routing, not authorization: each broker must validate the authenticated
engine peer, every request, owned container lifecycle and its resource grant.
The immutable outer wrapper supplies socket constants; callers cannot select one.
"""
from __future__ import annotations

import http.client
import json
import os
from pathlib import PurePosixPath
import re
import socket
import sys

DOCKER = "/usr/bin/docker"
CANONICAL_SOCKET = "/run/arena-evaluator/docker.sock"
RESEARCH_SOCKET = "/run/arena-research-tools/docker.sock"
IMAGE_FORMAT = "{{.Id}} {{.Os}} {{.Architecture}}"
OWNER_FORMAT = '{"id":{{json .Id}},"owner":{{json (index .Config.Labels "sciel.invocation-owner")}}}'
HASH = re.compile(r"[a-f0-9]{64}")
RESEARCH_NAME = re.compile(r"sciel-method-[a-f0-9]{32}")
CANONICAL_NAME = re.compile(r"arena-eval-[a-f0-9]{32}")
MAX_PROBE_BYTES = 1024 * 1024


class RoutingError(ValueError):
    """No command was dispatched; uncertainty cannot choose a fallback broker."""


def _require(condition, message):
    if not condition:
        raise RoutingError(message)


def _socket_path(value):
    _require(type(value) is str and 0 < len(value.encode()) < 104
             and value.startswith("/") and str(PurePosixPath(value)) == value
             and not any(part in (".", "..") for part in value.split("/"))
             and not any(ord(c) < 33 for c in value), "Invalid fixed broker socket")
    return value


def _arguments(argv):
    _require(type(argv) in (list, tuple) and 0 < len(argv) <= 256, "Invalid Docker command")
    _require(all(type(v) is str and v and len(v) <= 16384
                 and not any(ord(c) < 32 for c in v) for v in argv), "Invalid Docker argument")
    _require(sum(map(len, argv)) <= 65536, "Docker command exceeds routing bound")
    # Reject global endpoint/config flags even if placed after the subcommand.
    forbidden = ("--host", "--context", "--config", "--tls", "--tlsverify",
                 "--tlscacert", "--tlscert", "--tlskey")
    for value in argv:
        _require(not value.startswith("-H") and not value.startswith("-c")
                 and not any(value == flag or value.startswith(flag + "=") for flag in forbidden),
                 "Docker endpoint/context overrides are forbidden")
    return list(argv)


def _named_command(args, prefix, expression):
    # Names must occur in the exact CLI option position used by the two clients.
    # Other command options are still enforced by the selected privileged broker.
    if args[:len(prefix)] != prefix:
        return False
    position = len(prefix)
    return (len(args) > position and expression.fullmatch(args[position]) is not None
            and sum(v == "--name" or v.startswith("--name=") for v in args) == 1)


def route(argv, *, probe):
    """Classify exact native families; probe is a read-only owned-ID predicate."""
    args = _arguments(argv)
    if (len(args) == 5 and args[:3] == ["image", "inspect", "--format"]
            and args[3] == IMAGE_FORMAT and re.fullmatch(r"sha256:[a-f0-9]{64}", args[4])):
        return "research"
    if args == ["version", "--format", "{{.Server.Version}}"]:
        return "research"
    if _named_command(args, ["create", "--pull=never", "--name"], RESEARCH_NAME):
        return "research"
    if (len(args) == 5 and args[:4] == ["inspect", "--type=container", "--format", OWNER_FORMAT]
            and RESEARCH_NAME.fullmatch(args[4])):
        return "research"
    if args == ["info", "--format", "{{.CgroupDriver}} {{.CgroupVersion}}"]:
        return "canonical"
    if _named_command(args, ["run", "--rm", "--pull=never", "--name"], CANONICAL_NAME):
        return "canonical"
    if len(args) == 3 and args[:2] == ["rm", "--force"] and CANONICAL_NAME.fullmatch(args[2]):
        return "canonical"
    if len(args) == 3 and args[:2] in (["start", "--attach"], ["rm", "--force"]) and HASH.fullmatch(args[2]):
        # The only permitted fallback is an explicit authenticated-broker404.
        # No mutable routing map and no retry of a mutating command.
        owned = probe(args[2])
        _require(type(owned) is bool, "Ownership probe did not resolve container")
        return "research" if owned else "canonical"
    raise RoutingError("Unsupported Docker command family")


class _UnixConnection(http.client.HTTPConnection):
    def __init__(self, path, timeout):
        super().__init__("localhost", timeout=timeout)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.path)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "Ambiguous ownership response")
        result[key] = value
    return result


def probe_research_owner(container_id, *, research_socket=RESEARCH_SOCKET, timeout=3.0):
    """One bounded GET; never redirects, retries, starts or deletes anything."""
    _require(type(container_id) is str and HASH.fullmatch(container_id), "Expected complete container ID")
    path = _socket_path(research_socket)
    _require(type(timeout) in (int, float) and 0 < timeout <= 10, "Invalid ownership probe timeout")
    connection = _UnixConnection(path, timeout)
    try:
        connection.request("GET", f"/containers/{container_id}/json", headers={"Accept": "application/json"})
        response = connection.getresponse()
        _require(response.status in (200, 404), "Research broker did not resolve container ownership")
        data = response.read(MAX_PROBE_BYTES + 1)
        _require(len(data) <= MAX_PROBE_BYTES, "Ownership response exceeds routing bound")
        if response.status == 404:
            return False
        result = json.loads(data, object_pairs_hook=_unique,
            parse_constant=lambda _: (_ for _ in ()).throw(RoutingError("Nonfinite ownership response")))
        _require(type(result) is dict and result.get("Id") == container_id,
                 "Research broker returned a different container identity")
        return True
    except (OSError, http.client.HTTPException, ValueError) as exc:
        # Do not print response bytes, socket paths, environment or arbitrary
        # transport exception strings. Importantly, never interpret as404.
        raise RoutingError("Research container ownership is unavailable or invalid") from exc
    finally:
        connection.close()


def execution_plan(argv, *, canonical_socket=CANONICAL_SOCKET, research_socket=RESEARCH_SOCKET, probe=None):
    canonical_socket, research_socket = _socket_path(canonical_socket), _socket_path(research_socket)
    _require(canonical_socket != research_socket, "Two distinct restricted brokers required")
    args = _arguments(argv)
    if probe is None:
        probe = lambda ident: probe_research_owner(ident, research_socket=research_socket)
    selected = route(args, probe=probe)
    path = research_socket if selected == "research" else canonical_socket
    # No inherited endpoint, context, TLS setting, credential, plugin/config or
    # dynamic linker environment. A missing fixed config directory is deliberate.
    environment = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/nonexistent",
                   "DOCKER_CONFIG": "/nonexistent/.docker", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
                   "DOCKER_HOST": "unix://" + path}
    return {"broker": selected, "argv": [DOCKER, *args], "environment": environment}


def main(argv=None, *, canonical_socket=CANONICAL_SOCKET, research_socket=RESEARCH_SOCKET):
    try:
        plan = execution_plan(list(sys.argv[1:] if argv is None else argv),
                              canonical_socket=canonical_socket, research_socket=research_socket)
        os.execve(DOCKER, plan["argv"], plan["environment"])
    except RoutingError as exc:
        print(f"Arena Docker routing refused: {exc}", file=sys.stderr)
        return 125
    return 125


if __name__ == "__main__":
    raise SystemExit(main())
