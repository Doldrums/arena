"""Shared control contracts, validation primitives and error identity."""
from __future__ import annotations

import json
import re

SCHEMA = "arena.control/1"
ACTIVE = ("preparing", "running")
TERMINAL = ("completed", "failed", "cancelled", "blocked")
SCOPES = {"read", "submit", "cancel", "logs:native", "admin"}
MAX_CONFIG = 8 * 1024 * 1024
MAX_LOG = 64 * 1024
MAX_NATIVE_LOG = 8 * 1024 * 1024
LEASE_SECONDS = 30
ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}\Z")
MODEL = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,199}\Z")
SECRET_KEY = re.compile(r"(?:password|secret|api[_-]?key|access[_-]?token|auth[_-]?token|credential)", re.I)
SECRET_VALUE = re.compile(r"(?:sk-[A-Za-z0-9_-]{12,}|arena_[A-Za-z0-9_-]{20,}|Bearer\s+\S+|-----BEGIN .*PRIVATE KEY)", re.I)


class ControlError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ControlError("Duplicate JSON fields are not allowed")
        result[key] = value
    return result


def _decode(data):
    try:
        return json.loads(data, object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (UnicodeError, ValueError) as exc:
        if isinstance(exc, ControlError):
            raise
        raise ControlError("Invalid JSON") from None


def _int(value, name, low=1, high=10**9):
    if type(value) is not int or not low <= value <= high:
        raise ControlError(f"Invalid {name}")
    return value


def _id(value, name="identifier"):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ControlError(f"Invalid {name}")
    return value


def _plain(value, name, maximum=240):
    if not isinstance(value, str) or not 1 <= len(value) <= maximum or any(ord(c) < 32 for c in value):
        raise ControlError(f"Invalid {name}")
    if SECRET_VALUE.search(value):
        raise ControlError(f"Credentials are not permitted in {name}")
    return value
