"""Read-only journal compatibility extracted from sciel.methods.models.

SCiEL source commit: 0d67f813dd4ac21dee304f2b0de0b0ce59bf4157.
Only dependency-reachable validators/readers/constants are retained.
"""
from __future__ import annotations

import hashlib


import json


import math


import re


from typing import Any


HASH_RE = re.compile(r"[0-9a-f]{64}\Z")


def _json(value: Any, path: str = "$") -> None:
    if value is None or type(value) in (bool, str, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for i, item in enumerate(value):
            _json(item, f"{path}[{i}]")
        return
    if type(value) is dict and all(type(k) is str for k in value):
        for key, item in value.items():
            _json(item, f"{path}.{key}")
        return
    raise ValueError(f"{path}: expected finite JSON value")


def canonical_bytes(value: Any) -> bytes:
    _json(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def detached(value: Any) -> Any:
    return json.loads(canonical_bytes(value))


def require_hash(value: Any, label: str = "hash") -> str:
    if not isinstance(value, str) or not HASH_RE.fullmatch(value):
        raise ValueError(f"{label}: expected lowercase SHA256")
    return value
