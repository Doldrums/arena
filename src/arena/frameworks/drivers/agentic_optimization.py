"""Drive a bounded native AgenticOptimization assignment through its real API.

The native control plane owns worker continuation, candidate generation and
evaluation. This module imports it only after an explicit launch, never to plan.
"""
import argparse
import json
from pathlib import Path
import signal
import threading
import time


def _native_components():
    from agentic_opt.web.app import create_app
    from werkzeug.serving import make_server
    return create_app, make_server


def _bounded(value):
    value = int(value)
    if not 1 <= value <= 86400:
        raise argparse.ArgumentTypeError("Value must be an integer from 1 to 86400")
    return value


def _post(client, path, payload):
    response = client.post(path, json=payload)
    if response.status_code not in (200, 201, 202):
        raise RuntimeError(f"Native control API rejected {path} (HTTP {response.status_code})")
    value = response.get_json()
    if not isinstance(value, dict):
        raise RuntimeError("Native control API returned a non-object response")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--max-evaluator-runs", type=_bounded, required=True)
    parser.add_argument("--worker-seconds", type=_bounded, required=True)
    parser.add_argument("--wall-seconds", type=_bounded, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--codex-binary", type=Path)
    args = parser.parse_args(argv)
    if not args.state_root.is_absolute():
        raise ValueError("state-root must be absolute")
    if args.codex_binary is not None and not args.codex_binary.is_absolute():
        raise ValueError("codex-binary must be absolute when supplied")
    if args.state_root.exists():
        raise ValueError("state-root must be new; this driver does not resume an old experiment")
    args.state_root.mkdir(parents=True, mode=0o700)
    create_app, make_server = _native_components()
    app = create_app(state_root=args.state_root, database_path=args.state_root / "control.sqlite3")
    ctx = app.config["AO_CONTEXT"]
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = app.test_client()
    experiment_id = assignment_id = None
    previous = {}
    termination = "error"
    returncode = 1

    def interrupted(signum, _frame):
        raise SystemExit(128 + signum)

    try:
        for signum in (signal.SIGTERM, signal.SIGINT):
            previous[signum] = signal.signal(signum, interrupted)
        created = _post(client, "/api/v1/experiments", {
            "task_id": args.task_id, "mode": "local", "assignment_count": 1,
            "worker_backend": "codex-local",
            "budget": {"total_evaluator_runs": args.max_evaluator_runs},
        })
        experiment_id = created["experiment"]["experiment_id"]
        assignments = created.get("assignments")
        if not isinstance(assignments, list) or len(assignments) != 1:
            raise RuntimeError("Native control plane did not create exactly one assignment")
        assignment_id = assignments[0]["assignment_id"]
        payload = {"api_url": f"http://127.0.0.1:{server.server_port}",
                   "max_turn_wall_time_s": args.worker_seconds}
        if args.codex_binary is not None:
            payload["codex_binary"] = str(args.codex_binary)
        _post(client, f"/api/v1/assignments/{assignment_id}/start-local", payload)
        deadline = time.monotonic() + args.wall_seconds
        while time.monotonic() < deadline:
            status = ctx.workers.worker_status(assignment_id)
            if status is None:
                # The native reaper may have consumed a terminal status first.
                termination = "native_worker_terminal"
                sessions = ctx.control.list_sessions(experiment_id=experiment_id)
                terminal = [s for s in sessions if s.get("assignment_id") == assignment_id]
                returncode = 0 if terminal and all(s.get("status") == "completed" for s in terminal) else 1
                break
            if status.get("status") == "finished" and not status.get("continuation"):
                termination = "native_worker_terminal"
                returncode = 0 if status.get("returncode") == 0 else 1
                break
            if status.get("status") == "stopped":
                termination = "native_worker_stopped"
                break
            time.sleep(0.2)
        else:
            termination = "wall_timeout"
            returncode = 124
    finally:
        try:
            if experiment_id is not None:
                ctx.control.update_experiment_status(experiment_id, "stopped")
            if assignment_id is not None:
                # Native stop handling terminates its independently started
                # process group plus relay/proxy children, unlike close() alone.
                ctx.workers.worker_status(assignment_id)
        finally:
            ctx.workers.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            for signum, handler in previous.items():
                signal.signal(signum, handler)
            (args.state_root / "arena-native.json").write_text(json.dumps({
                "framework": "agentic-optimization", "experiment_id": experiment_id,
                "assignment_id": assignment_id, "termination": termination,
                "canonical_evaluation": False,
            }, indent=2) + "\n", encoding="utf-8")
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
