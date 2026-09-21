"""Private, authenticated native-run queue and explicit isolated worker commands."""
from __future__ import annotations

import argparse
from pathlib import Path
import signal
import sqlite3
import sys
import threading

from .control_service import ControlService
from .control_types import ControlError, SCHEMA, SCOPES, _int, _json
from .control_worker import Worker, _execute


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("serve", "worker", "create-key", "revoke-key", "check", "_execute"):
        child = sub.add_parser(command)
        child.add_argument("--config", required=True, type=Path)
        if command == "serve":
            child.add_argument("--port", type=int, default=8080)
            child.add_argument("--observe", action="append", default=[], type=Path)
        elif command == "worker":
            child.add_argument("--once", action="store_true")
            child.add_argument("--concurrency", type=int, default=1)
        elif command == "create-key":
            child.add_argument("--owner", required=True)
            child.add_argument("--scope", required=True, action="append", choices=sorted(SCOPES))
            child.add_argument("--max-runs", type=int)
            child.add_argument("--max-seconds", type=int)
        elif command == "revoke-key":
            child.add_argument("--key-id", required=True)
        elif command == "_execute":
            child.add_argument("--run-id", required=True)
            child.add_argument("--snapshot-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "_execute":
            return _execute(args.config, args.run_id, args.snapshot_sha256)
        service = ControlService(args.config)
        if args.command == "check":
            print(_json({"schema": SCHEMA, "revision": service.revision, "templates": len(service.config["templates"])}))
        elif args.command == "create-key":
            print(_json(service.create_key(args.owner, args.scope, max_runs=args.max_runs, max_seconds=args.max_seconds)))
        elif args.command == "revoke-key":
            service.revoke_key(args.key_id)
            print(_json({"revoked": True}))
        elif args.command == "serve":
            from .server import DashboardServer
            server = DashboardServer(("127.0.0.1", args.port), args.observe, control=service)
            try:
                server.serve_forever(poll_interval=0.25)
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
        elif args.command == "worker":
            _int(args.concurrency, "worker concurrency", high=64)
            workers = [Worker(service) for _ in range(args.concurrency)]
            for number in (signal.SIGTERM, signal.SIGINT):
                signal.signal(number, lambda *_: [worker.stopping.set() for worker in workers])
            if args.once:
                if args.concurrency != 1:
                    raise ControlError("--once requires concurrency 1")
                workers[0].once()
            else:
                threads = [threading.Thread(target=worker.loop, name=worker.id) for worker in workers]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
        return 0
    except (ControlError, OSError, sqlite3.Error):
        # Configuration exceptions can include private paths; do not echo them.
        print("Control operation failed; verify private configuration and permissions.", file=sys.stderr)
        return 2
