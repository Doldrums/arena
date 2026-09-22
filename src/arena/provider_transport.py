"""Private credential files and bounded provider transport."""
from __future__ import annotations

import base64
from contextlib import contextmanager
from http.client import IncompleteRead
import json
import math
import os
from pathlib import Path
import re
import secrets
import socket
import stat
import threading
import time
from urllib import error
from urllib import request
from .provider_common import (
    BASE_URL,
    CLIENT_VERSION,
    MAX_BODY,
    MAX_STREAM,
    ProviderError,
    _json,
)


def _private_read(path, limit=65536):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as file:
            info = os.fstat(file.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077
                    or hasattr(os, "getuid") and info.st_uid != os.getuid() or info.st_size > limit):
                raise ValueError()
            raw = file.read(limit + 1)
            if len(raw) > limit:
                raise ValueError()
            return raw.decode("utf-8").strip()
    except (OSError, ValueError, UnicodeError):
        raise ProviderError(503, "private_credential_unavailable",
                            "Credential files must be private regular files owned by this process user (mode 0600).") from None


class TokenSource:
    def __init__(self, path):
        self.path = Path(path)

    def read(self):
        raw = _private_read(self.path)
        tokens = re.findall(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", raw)
        if len(tokens) != 1:
            raise ProviderError(503, "invalid_upstream_credential", "The private file must contain exactly one JWT.")
        token = tokens[0]
        try:
            claims = _json(base64.urlsafe_b64decode(token.split(".")[1] + "==="))
            expiry = claims["exp"]
            if type(expiry) not in (int, float) or not math.isfinite(expiry):
                raise ValueError()
            account = claims.get("https://api.openai.com/auth", {}).get("chatgpt_account_id")
            if account is not None and (not isinstance(account, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", account)):
                raise ValueError()
        except (ValueError, KeyError, TypeError, AttributeError):
            raise ProviderError(503, "invalid_upstream_credential", "Cannot read credential expiry metadata.") from None
        # Local claims are scheduling hints, never authentication proof; upstream validates JWT.
        if expiry <= time.time() + 5:
            raise ProviderError(503, "upstream_credential_expired", "The upstream credential has expired; rotate its private file.")
        headers = {"Authorization": "Bearer " + token, "User-Agent": "codex_cli_rs/" + CLIENT_VERSION,
                   "originator": "codex_cli_rs"}
        if account:
            headers["ChatGPT-Account-Id"] = account
        return headers, expiry


def create_gateway_key(path):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as file:
        file.write(secrets.token_urlsafe(48) + "\n")


def read_gateway_key(path):
    value = _private_read(path, 1024)
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,200}", value) or value.count("."):
        raise ProviderError(503, "invalid_gateway_key", "Use a separate generated gateway key.")
    return value


def _upstream_error(status, retry_after=None):
    if status == 429:
        return ProviderError(429, "upstream_rate_limit", "The account provider rate limit was reached.", retry_after or 30)
    if status in (401, 403):
        return ProviderError(503, "upstream_authentication_failed", "The upstream credential or account access was rejected.")
    if status in (400, 404, 422):
        return ProviderError(400, "upstream_request_rejected", "The account endpoint rejected this model or request configuration.")
    return ProviderError(502, "upstream_unavailable", "The account provider did not complete the request.")


def parse_sse(chunks, *, event_limit=MAX_BODY, total_limit=MAX_STREAM):
    """Parse UTF-8 SSE, including fragmented CRLF, comments and multiline data."""
    buffer = b""
    data = []
    event_size = total = 0
    for chunk in chunks:
        total += len(chunk)
        if total > total_limit:
            raise ProviderError(502, "upstream_stream_limit", "The upstream response exceeded the configured byte limit.")
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            line = line.removesuffix(b"\r")
            event_size += len(line)
            if event_size > event_limit:
                raise ProviderError(502, "upstream_event_limit", "An upstream event exceeded the configured byte limit.")
            if line == b"":
                if data:
                    raw = b"\n".join(data)
                    if raw == b"[DONE]":
                        yield None
                    else:
                        try:
                            item = _json(raw.decode("utf-8"))
                            if not isinstance(item, dict):
                                raise ValueError()
                        except (ValueError, UnicodeError):
                            raise ProviderError(502, "invalid_upstream_event", "The provider returned an invalid streaming event.") from None
                        yield item
                data, event_size = [], 0
            elif line.startswith(b"data:"):
                data.append(line[5:].removeprefix(b" "))
        if len(buffer) + event_size > event_limit:
            raise ProviderError(502, "upstream_event_limit", "An upstream event exceeded the configured byte limit.")
    if buffer.strip() or data:
        raise ProviderError(502, "truncated_upstream_stream", "The provider stream ended inside an event.")


class CodexTransport:
    def __init__(self, token_source, timeout=180):
        self.token_source, self.timeout = token_source, timeout

    @contextmanager
    def _open(self, path, payload=None):
        headers, _ = self.token_source.read()
        headers["Accept"] = "application/json" if payload is None else "text/event-stream"
        if payload is not None:
            headers["Content-Type"] = "application/json"
        started = time.monotonic()
        body = None if payload is None else json.dumps(payload, allow_nan=False).encode()
        req = request.Request(BASE_URL + path, data=body, headers=headers)
        response = None
        timer = None
        timed_out = threading.Event()
        try:
            # No redirects: an Authorization header must never reach another host.
            class NoRedirect(request.HTTPRedirectHandler):
                def redirect_request(self, *args, **kwargs):
                    return None
            response = request.build_opener(NoRedirect).open(req, timeout=min(self.timeout, 30))
            remaining = self.timeout - (time.monotonic() - started)
            if remaining <= 0:
                raise TimeoutError()
            sock = getattr(getattr(getattr(response, "fp", None), "raw", None), "_sock", None)
            if sock is not None:
                sock.settimeout(remaining)
            def abort():
                timed_out.set()
                try:
                    if sock is not None:
                        sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            timer = threading.Timer(remaining, abort)
            timer.daemon = True
            timer.start()
            yield response
            if timed_out.is_set():
                raise ProviderError(504, "upstream_timeout", "The account provider request timed out.")
        except error.HTTPError as exc:
            retry = exc.headers.get("Retry-After", "")
            retry = min(3600, max(1, int(retry))) if retry.isdigit() else None
            exc.close()  # Never copy upstream bodies, which can echo sensitive input.
            raise _upstream_error(exc.code, retry) from None
        except ProviderError:
            raise
        except IncompleteRead:
            # The request was dispatched: partial bytes are not a completion or
            # usage receipt, and retrying here could duplicate a charged call.
            raise ProviderError(502, "truncated_upstream_stream",
                                "The account provider stream ended before a completed response.") from None
        except (TimeoutError, socket.timeout):
            raise ProviderError(504, "upstream_timeout", "The account provider request timed out.") from None
        except (error.URLError, OSError):
            if timed_out.is_set():
                raise ProviderError(504, "upstream_timeout", "The account provider request timed out.") from None
            raise ProviderError(502, "upstream_connection_failed", "Could not complete the account provider connection.") from None
        finally:
            if timer is not None:
                timer.cancel()
            if response is not None:
                response.close()

    def models(self):
        with self._open("/models?client_version=" + CLIENT_VERSION) as response:
            raw = response.read(MAX_BODY + 1)
        if len(raw) > MAX_BODY:
            raise ProviderError(502, "model_inventory_limit", "The provider model inventory is too large.")
        try:
            return _json(raw)
        except ValueError:
            raise ProviderError(502, "invalid_model_inventory", "The provider model inventory is invalid.") from None

    def events(self, payload):
        with self._open("/responses", payload) as response:
            def chunks():
                while True:
                    chunk = response.read1(16384)
                    if not chunk:
                        break
                    yield chunk
            yield from parse_sse(chunks())
