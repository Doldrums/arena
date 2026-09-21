"""Bounded, hash-checked native evidence readers."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import PurePosixPath
import re


HASH = re.compile(r'[a-f0-9]{64}')


INTEGER = re.compile(r'0|[1-9][0-9]{0,8}')


NUMBER = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'


def _number(value):
    try:
        return value if type(value) in (int, float) and math.isfinite(value) else None
    except OverflowError:
        return None


def _count(value):
    return value if type(value) is int and 0 <= value <= 10**9 else None


def _pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            raise ValueError('Duplicate native evidence key')
        result[key] = value
    return result


class _Artifacts:
    def __init__(self, evidence, native):
        self.evidence, self.files, self.used = evidence, {}, []
        rows = native.get('artifacts')
        if type(rows) is not list or len(rows) > 256:
            raise ValueError('Invalid native artifact inventory')
        for row in rows:
            if type(row) is not dict:
                raise ValueError('Invalid native artifact record')
            name, digest = row.get('path'), row.get('sha256')
            if (type(name) is not str or len(name) > 1024 or '\\' in name or '\x00' in name
                    or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts
                    or str(PurePosixPath(name)) != name or name in self.files
                    or type(digest) is not str or not HASH.fullmatch(digest)):
                raise ValueError('Invalid or duplicate native artifact path/hash')
            self.files[name] = digest

    def matching(self, pattern):
        return sorted(name for name in self.files if re.fullmatch(pattern, name))

    def one(self, pattern):
        paths = self.matching(pattern)
        if len(paths) != 1:
            raise ValueError('Expected one published native result')
        return paths[0]

    def raw(self, name, limit=2 * 1024**2):
        if name not in self.files:
            raise ValueError('Unlisted native evidence')
        raw = self.evidence.raw(name, limit)
        if hashlib.sha256(raw).hexdigest() != self.files[name]:
            raise ValueError('Native evidence hash mismatch')
        self.used.append(self.files[name])
        return raw

    def json(self, name, limit=2 * 1024**2):
        # Upstream may encode invalid scores as NaN/-Infinity. Keep them in
        # decoded input; _number excludes them instead of converting to zero.
        return json.loads(self.raw(name, limit), object_pairs_hook=_pairs)
