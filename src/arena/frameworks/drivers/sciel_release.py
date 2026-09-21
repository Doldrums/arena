"""Run one admitted SCiEL private image through the root-owned Unix broker."""
from __future__ import annotations

import argparse
import http.client
import json
import os
from pathlib import Path
import re
import signal
import socket
import struct
import sys

from arena.release_deployment import _decode, load_manifest

MAX_FRAME = 64 * 1024
MAX_STREAM = 8 * 1024 * 1024


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, path, *, timeout=30):
        super().__init__("localhost", timeout=timeout)
        self.socket_path = str(path)

    def connect(self):
        if sys.platform != "linux" or not hasattr(socket, "SO_PEERCRED"):
            raise ValueError("Private image broker execution requires Linux peer credentials")
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.socket_path)
        _, uid, _ = struct.unpack("3i", self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")))
        if uid != 0:
            self.sock.close()
            raise ValueError("Private image broker must be the root-owned operator service")
        self.stream_socket = self.sock


def _request(connection, method, path, value=None):
    body = None if value is None else json.dumps(value, separators=(",", ":")).encode()
    connection.request(method, path, body=body, headers={"Content-Type": "application/json"})
    return connection.getresponse()


def _cancel(socket_path, run_id):
    connection = UnixHTTPConnection(socket_path, timeout=2)
    try:
        response = _request(connection, "DELETE", "/v1/run/" + run_id)
        response.read(MAX_FRAME)
    except (OSError, ValueError, http.client.HTTPException):
        pass
    finally:
        connection.close()


def _result_matches(value, run_id, digest, manifest):
    return (value.get("run_id") == run_id and value.get("deployment_sha256") == digest
            and value.get("image") == manifest["image"]["reference"]
            and value.get("image_id") == manifest["image"]["image_id"]
            and value.get("source_commit") == manifest["binding"]["repository"]["commit"]
            and value.get("status") in {"completed", "failed", "cancelled", "timed_out"}
            and type(value.get("returncode")) is int and -255 <= value["returncode"] <= 255)


def run(deployment, expected_digest, output):
    manifest, digest = load_manifest(deployment)
    if digest != expected_digest:
        raise ValueError("Deployment changed after native planning")
    run_id = os.environ.get("ARENA_CONTROL_RUN_ID", "")
    if re.fullmatch(r"[0-9a-f]{32}", run_id) is None:
        raise ValueError("Private image execution requires an admitted control run")
    output = Path(output)
    if not output.is_absolute() or output.is_symlink() or not output.is_dir():
        raise ValueError("An existing admitted runtime output directory is required")
    if os.environ.get("ARENA_EVALUATION_RECEIPTS_DIR") != str(output / "canonical-evaluations"):
        raise ValueError("Private image output must match the control run's trusted artifact directory")
    socket_path = Path(manifest["broker"]["socket"])
    if socket_path.is_symlink() or any(parent.is_symlink() for parent in socket_path.parents):
        raise ValueError("The private broker socket must not traverse symlinks")
    connection = UnixHTTPConnection(socket_path)
    interrupted, prior = [], {}
    response, terminal = None, False

    def interrupt(number, _frame):
        interrupted.append(number)
        _cancel(socket_path, run_id)
        connection.close()

    try:
        for number in (signal.SIGTERM, signal.SIGINT):
            prior[number] = signal.signal(number, interrupt)
        response = _request(connection, "POST", "/v1/run", {"run_id": run_id, "deployment_sha256": digest})
        if response.status != 200:
            response.read(MAX_FRAME)
            raise ValueError("Private image broker refused execution")
        # Admission is bounded above. Streaming may remain quiet between model
        # calls; the enclosing native runtime and cgroup enforce the wall limit.
        stream_socket = connection.sock or getattr(connection, "stream_socket", None)
        if stream_socket is not None:
            stream_socket.settimeout(None)
        started, result = False, None
        written = {"stdout": 0, "stderr": 0}
        while not interrupted:
            raw = response.readline(MAX_FRAME + 1)
            if not raw:
                break
            if len(raw) > MAX_FRAME or not raw.endswith(b"\n"):
                raise ValueError("Private broker returned an oversized or incomplete frame")
            value = _decode(raw)
            if type(value) is not dict:
                raise ValueError("Private broker returned an invalid frame")
            kind = value.get("type")
            if kind == "started":
                if started or result is not None or value.get("run_id") != run_id:
                    raise ValueError("Private broker run identity is inconsistent")
                started = True
            elif kind in {"stdout", "stderr"}:
                if not started or result is not None or not isinstance(value.get("text"), str):
                    raise ValueError("Private broker diagnostic ordering is invalid")
                encoded = value["text"].encode("utf-8")
                keep = encoded[:max(0, MAX_STREAM - written[kind])]
                stream = sys.stdout if kind == "stdout" else sys.stderr
                stream.write(keep.decode("utf-8", errors="replace"))
                stream.flush()
                written[kind] += len(keep)
            elif kind == "result":
                if not started or result is not None or not _result_matches(value, run_id, digest, manifest):
                    raise ValueError("Private image execution provenance is missing or inconsistent")
                result = value
                terminal = True
                break
            else:
                raise ValueError("Private broker returned an unknown frame")
        if interrupted:
            return 128 + interrupted[0]
        if result is None:
            raise ValueError("Private broker ended without an execution result")
        metadata = output / ".arena"
        if metadata.is_symlink() or not metadata.is_dir():
            raise ValueError("Runtime metadata directory is missing or unsafe")
        path = metadata / "private-image-result.json"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "w", closefd=False) as stream:
                json.dump(result, stream, sort_keys=True, allow_nan=False)
                stream.write("\n")
        finally:
            os.close(fd)
        return 0 if result["status"] == "completed" and result["returncode"] == 0 else 1
    finally:
        if not terminal:
            _cancel(socket_path, run_id)
        if response is not None:
            response.close()
        connection.close()  # Broker disconnect is also an owned-container cancellation signal.
        for number, handler in prior.items():
            signal.signal(number, handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deployment", type=Path, required=True)
    parser.add_argument("--deployment-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        return run(args.deployment, args.deployment_sha256, args.output)
    except (OSError, ValueError, http.client.HTTPException):
        print("Private SCiEL image execution failed; consult scoped broker diagnostics.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
