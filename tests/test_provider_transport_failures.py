"""Transport failure receipts use fixture upstream bytes, never real accounts."""
from http.client import IncompleteRead
import json
import time
from types import SimpleNamespace

import pytest

from arena.provider_transport import CodexTransport
from test_providers import KEY, MODEL, Transport, call, chat, gateway


@pytest.mark.parametrize("route", ["/v1/chat/completions", "/v1/responses"])
@pytest.mark.parametrize("stream", [False, True])
def test_incomplete_http_read_is_sanitized_without_retry_or_invented_usage(monkeypatch, route, stream):
    class Response:
        fp = None
        reads = 0
        closed = False

        def read1(self, size):
            self.reads += 1
            if self.reads == 1:
                return (b'data: {"type":"response.created","response":'
                        b'{"id":"fixture","status":"in_progress"}}\n\n')
            raise IncompleteRead(b"PRIVATE-PARTIAL-UPSTREAM-BODY", 100)

        def close(self):
            self.closed = True

    response = Response()
    attempts = []

    def open_once(req, timeout):
        attempts.append(req)
        return response

    monkeypatch.setattr("arena.provider_transport.request.build_opener",
                        lambda *args: SimpleNamespace(open=open_once))
    tokens = SimpleNamespace(read=lambda: ({"Authorization": "Bearer PRIVATE-FIXTURE-TOKEN"}, time.time() + 600))
    transport = CodexTransport(tokens, timeout=5)
    monkeypatch.setattr(transport, "models", Transport().models)
    body = chat(stream=stream) if route.endswith("completions") else {
        "model": MODEL, "input": "private fixture prompt", "stream": stream,
    }
    with gateway(transport) as (server, bridge, audits):
        status, headers, raw = call(server, route, body)

    assert status == (200 if stream else 502)
    assert b"truncated_upstream_stream" in raw
    assert b"[DONE]" not in raw and b"response.completed" not in raw
    assert len(attempts) == 1 and response.reads == 2 and response.closed
    assert len(audits) == 1
    assert audits[0]["status"] == 502
    assert audits[0]["error_code"] == "truncated_upstream_stream"
    assert audits[0]["exception_type"] == "ProviderError"
    assert audits[0]["usage"] == {}  # Unknown, never a fabricated zero-cost receipt.
    public = raw.decode() + json.dumps(audits)
    for private in ("PRIVATE-PARTIAL-UPSTREAM-BODY", "PRIVATE-FIXTURE-TOKEN", "private fixture prompt", KEY):
        assert private not in public
    assert '"usage"' not in raw.decode() and "cost" not in public
    assert "Retry-After" not in headers
