"""Read a same-run heartbeat without treating file presence as liveness."""
from datetime import datetime
import json
import math
import socket
import time

from .compat.runtime import process_matches
from .parallel import runtime_parallel
from .run_values import _number


def runtime_view(path, start):
    """Observe a same-run heartbeat; an extant file alone is not liveness."""
    result = dict(available=False, status="unknown", stage=None, active=None,
        heartbeat_at=None, heartbeat_age_seconds=None, pid=None, reason=None,
        verification="unavailable", stale_after_seconds=None)
    sidecar = path.parent / "runtime.json"
    try:
        if sidecar.is_symlink() or sidecar.resolve().parent != path.parent:
            return result
        if sidecar.stat().st_size > 65536:
            raise ValueError("oversized runtime sidecar")
        record = json.loads(sidecar.read_bytes())
        if not isinstance(record, dict) or record.get("schema") != "sciel-runtime/1":
            raise ValueError("unknown runtime schema")
    except FileNotFoundError:
        return result
    except (OSError, ValueError, UnicodeError, RecursionError):
        result.update(verification="unreadable", reason="Runtime telemetry is temporarily unreadable.")
        return result
    result["available"] = True
    if not start.get("run_id") or not start.get("segment_id") or any(
            record.get(key) != start.get(key) for key in ("run_id", "segment_id")):
        result.update(verification="different_run", reason="Runtime telemetry is not bound to this journal segment.")
        return result
    for key in ("stage", "heartbeat_at", "pid", "reason", "started_at", "finished_at",
                "runtime_id", "error_type", "stale_after_seconds"):
        result[key] = record.get(key)
    result['parallel'] = runtime_parallel(record.get('parallel'))
    status = record.get("status")
    if status in {"completed", "paused", "stopped", "failed", "interrupted"}:
        result.update(status=status, active=False, verification="terminal_recorded")
        return result
    if status != "running":
        result.update(verification="unknown_status", reason="Runtime status is not recognized.")
        return result
    try:
        heartbeat = datetime.fromisoformat(record["heartbeat_at"].replace("Z", "+00:00"))
        if heartbeat.tzinfo is None:
            raise ValueError("heartbeat needs timezone")
        age = time.time() - heartbeat.timestamp()
        if not math.isfinite(age):
            raise ValueError("invalid heartbeat age")
        result["heartbeat_age_seconds"] = max(0, age)
    except (KeyError, TypeError, AttributeError, ValueError, OverflowError):
        result.update(verification="invalid_timestamp", reason="Runtime heartbeat time is unavailable.")
        return result
    if record.get("hostname") != socket.gethostname():
        result.update(verification="different_host", reason="The writer belongs to another host; its process state is unknown.")
        return result
    same_process = process_matches(record)
    if same_process is False:
        result.update(status="interrupted", active=False, verification="process_not_running",
                      reason="The recorded writer process is no longer present; no terminal runtime record was written.")
    elif same_process is None:
        result.update(verification="process_unverified", reason="The writer process identity cannot be verified.")
    else:
        limit = _number(record.get("stale_after_seconds"))
        if limit is None or limit <= 0 or age < -2:
            result.update(verification="invalid_timestamp", reason="Runtime freshness cannot be established.")
        elif age > limit:
            result.update(status="stalled", verification="stale_heartbeat",
                          reason="The same writer process exists, but its heartbeat is stale.")
        else:
            result.update(status="running", active=True, verification="live_process", reason=None)
    return result
