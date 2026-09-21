"""Worker-only native log redaction and publication."""
from __future__ import annotations

import hashlib
import os
import re

from .control_io import (_private_dir, _read_regular, _regular_signature,
                         _replace_private_bytes)
from .control_types import ControlError, MAX_NATIVE_LOG, _json


def _secret_values():
    """Worker credentials stay in memory; only redacted snapshots leave here."""
    return tuple(sorted({value for name, value in os.environ.items()
                         if value and re.search(r"(?:KEY|TOKEN|PASSWORD|SECRET|CREDENTIAL|AUTH)", name, re.I)},
                        key=len, reverse=True))


def _partial_secret_suffix(text, secret):
    # Linear-time prefix-function search; credential values can be long JWTs.
    if len(secret) < 2 or not text:
        return 0
    pattern = secret + "\x00" + text[-(len(secret) - 1):]
    prefix = [0] * len(pattern)
    for index in range(1, len(pattern)):
        matched = prefix[index - 1]
        while matched and pattern[index] != pattern[matched]:
            matched = prefix[matched - 1]
        if pattern[index] == pattern[matched]:
            matched += 1
        prefix[index] = matched
    return prefix[-1]


def _redact_native(data, values):
    text = data.decode("utf-8", errors="replace")
    for secret in values:
        text = text.replace(secret, "[REDACTED]")
        # A still-growing log may end halfway through a credential. Do not
        # publish that prefix and reveal its remaining suffix on the next poll.
        size = _partial_secret_suffix(text, secret)
        if size:
            text = text[:-size] + "[REDACTED]"
    text = re.sub(r"(?i)Bearer\s+[^\s\"'<>]+", "Bearer [REDACTED]", text)
    text = re.sub(r"\beyJ[A-Za-z0-9_-]{4,}(?:\.[A-Za-z0-9_-]+){0,2}", "[REDACTED JWT]", text)
    text = re.sub(r"\b(?:sk-[A-Za-z0-9_-]{4,}|arena_[A-Za-z0-9_-]{8,}|gh[pousr]_[A-Za-z0-9_]{8,}|AKIA[A-Z0-9]{8,})", "[REDACTED KEY]", text)
    text = re.sub(r"(?im)((?:api[_-]?key|access[_-]?token|auth[_-]?token|password|secret)\s*[=:]\s*)[^\s,;]+", r"\1[REDACTED]", text)
    return text.encode("utf-8")[:MAX_NATIVE_LOG]


def _log_signature(path, maximum, *, private=False):
    try:
        return _regular_signature(path, maximum, private=private)
    except (OSError, ControlError):
        return None


def _publish_native_logs(directory, values, *, cache=None):
    """Publish redacted snapshots; a worker may retain only unchanged-file keys.

    Cache entries contain file metadata and a digest of the redaction policy,
    never log contents or credentials. Sources and published output must still
    pass the descriptor-based file boundary before an unchanged poll is skipped.
    A changing read is published but never cached, so the next poll retries it.
    """
    _private_dir(directory)
    values = tuple(values)
    policy = hashlib.sha256(_json(["native-log-redaction/1", MAX_NATIVE_LOG, values]).encode()).digest()
    for stream in ("stdout", "stderr"):
        raw_path = directory / "artifacts" / ".arena" / f"{stream}.log"
        diagnostic_path = directory / "preparation.stderr"
        output_path = directory / f"native_{stream}.log"

        def sources():
            return (_log_signature(raw_path, MAX_NATIVE_LOG),
                    _log_signature(diagnostic_path, 16384, private=True) if stream == "stderr" else None)

        before = sources() if cache is not None else None
        if cache is not None:
            published = _log_signature(output_path, MAX_NATIVE_LOG, private=True)
            key = (str(directory), stream)
            if published is not None and any(before) and cache.get(key) == (before, policy, published):
                continue
            cache.pop(key, None)
        chunks = []
        try:
            raw = _read_regular(raw_path, maximum=MAX_NATIVE_LOG)
            chunks.append(raw)
        except (OSError, ControlError):
            # Missing, oversized, nonregular or symlinked artifacts are never
            # copied. The API cannot use the raw file as a fallback.
            pass
        if stream == "stderr":
            try:
                diagnostic = _read_regular(diagnostic_path, maximum=16384, private=True)
                chunks.insert(0, diagnostic)
            except (OSError, ControlError):
                pass
        if chunks:
            _replace_private_bytes(output_path, _redact_native(b"\n".join(chunks)[:MAX_NATIVE_LOG], values))
            if cache is not None and before == sources():
                published = _log_signature(output_path, MAX_NATIVE_LOG, private=True)
                if published is not None:
                    cache[key] = (before, policy, published)


def _diagnostic(directory, stage, error, values):
    """Bounded scoped diagnostic, never a traceback or a public lifecycle event."""
    try:
        message = f"Stage: {stage}\n{type(error).__name__}: {str(error)[:4096]}\n"
        _replace_private_bytes(directory / "preparation.stderr", _redact_native(message.encode("utf-8", errors="replace"), values))
    except (OSError, ControlError):
        pass
