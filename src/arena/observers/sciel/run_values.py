"""Leaf helpers for finite, detached, redacted observer values."""
from datetime import datetime, timezone
import hashlib
import json
import math
import re

SCHEMA = "sciel-dashboard/1"
_SECRET_KEYS = {"api_key", "authorization", "access_token", "refresh_token", "password", "secret"}
_CODE_KEYS = {"code", "child_code", "parent_code", "code_fragment", "_failed_code"}


def _dict(value):
    return value if isinstance(value, dict) else {}


def _list(value):
    return value if isinstance(value, list) else []


def _number(value):
    if type(value) not in (int, float):
        return None
    try:
        return value if math.isfinite(value) else None
    except OverflowError:
        return None


def _sha(text):
    return hashlib.sha256(text.encode("utf-8", errors="surrogatepass")).hexdigest()


def _safe(value, *, compact=False, depth=0):
    """JSON-safe copies; never expose common credential fields from config."""
    if depth > 45:
        return "[nested data omitted]"
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if str(key).lower() in _SECRET_KEYS:
                result[str(key)] = "[redacted]"
            elif compact and (key in _CODE_KEYS | {"prompt", "response"}
                    or key == "source" and value.get("schema") == "sciel-initialization/1") and isinstance(item, str):
                result[str(key)] = {"omitted_chars": len(item), "sha256": _sha(item)}
            else:
                result[str(key)] = _safe(item, compact=compact, depth=depth + 1)
        return result
    if isinstance(value, list):
        return [_safe(item, compact=compact, depth=depth + 1) for item in value]
    if isinstance(value, float):
        return _number(value)
    if value is None or type(value) in (str, int, bool):
        return value
    return str(value)


def _signature(path):
    try:
        stat = path.stat()
        return stat.st_ino, stat.st_size, stat.st_mtime_ns
    except OSError:
        return None


def _time(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def _iteration(row):
    for value in (row.get("iteration_no"), row.get("iteration"),
                  _dict(row.get("evidence")).get("iteration"), row.get("iter_ref")):
        if type(value) is int:
            return value
    return None


def _seed_record(row):
    return (row.get("event") == "decision" and row.get("policy") == "initialization"
            and row.get("action") == "seed_program" and row.get("schema") == "sciel-initialization/1"
            and isinstance(row.get("program_id"), str))


def _bootstrap_admission(row, outcomes):
    """A portfolio/spawn decision commits admission after its evaluation."""
    if row.get("event") != "decision" or row.get("policy") != "portfolio_seed":
        return None, None
    if row.get("research") is not True:
        return (_number(row.get("score")), None) if row.get("ok", True) is True else (None, None)
    ident = _dict(row.get("meta")).get("research_id")
    record = outcomes.get(ident, {}) if isinstance(ident, str) else {}
    evaluation = _dict(record.get("evaluation"))
    score = _number(record.get("score"))
    if (row.get("ok") is not True or record.get("status") != "evaluated"
            or evaluation.get("ok") is not True or score is None
            or score != _number(evaluation.get("score"))
            or record.get("island") != row.get("island")):
        return None, None
    return score, ident


def _aux_key(row):
    return tuple(row.get(key) if type(row.get(key)) in (str, int) else None
                 for key in ("segment_id", "kind", "reference"))


def _stop_detail(checkpoint, rows):
    reason = _dict(checkpoint.get("research")).get("stopped_reason") or checkpoint.get("_accounting_stopped_reason")
    stopped = next((row for row in reversed(rows)
        if row.get("event") == "research" and row.get("phase") == "aux_stopped"), {})
    error_type = stopped.get("error_type")
    error_type = error_type if isinstance(error_type, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,79}", error_type) else None
    if isinstance(reason, str) and reason.strip():
        # Engine reasons contain exception classes, not provider bodies. Bound
        # historical free text and redact recognizable credentials defensively.
        reason = re.sub(r"(?i)\b(?:sk-[A-Za-z0-9_-]+|bearer\s+[^\s,;]+)", "[redacted]", reason)
        reason = re.sub(r"(?i)\b(?:api_key|token|password|secret)\s*[:=]\s*[^\s,;]+", "[redacted]", reason)
        reason = " ".join(reason.split())[:400]
        reason = reason[0].upper() + reason[1:]
    else:
        reason = "Research auxiliary response stopped" if stopped.get("stage") == "response" else "Research auxiliary request stopped" if stopped else None
    if error_type and reason and error_type not in reason:
        reason += ": " + error_type
    return reason


def _payload(text):
    """Decode only an explicit auxiliary JSON envelope, without repair."""
    if not isinstance(text, str):
        return {}
    text = text.strip()
    if text.startswith(("REFLECTION_JSON:", "CONCLUSION_JSON:")):
        text = text.split(":", 1)[1].strip()
    if text.startswith("```json\n") and text.endswith("\n```"):
        text = text[8:-4]
    try:
        return _dict(json.loads(text))
    except (ValueError, RecursionError):
        return {}


def cache_put(cache, key, value):
    cache[key] = value
    cache.move_to_end(key)
    while len(cache) > 8:
        cache.popitem(last=False)
