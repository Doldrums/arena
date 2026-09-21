"""Authenticated loopback HTTP endpoints for provider SDK clients."""
from __future__ import annotations

import hmac
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
import json
import re
import time
import uuid
from .provider_common import (
    MAX_BODY,
    ProviderError,
    _bad,
    _json,
)
from .provider_protocol import (
    anthropic_completion,
    anthropic_to_chat,
    chat_completion,
    normalize_request,
    usage_counts,
)


class GatewayServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, bridge, gateway_key):
        if address[0] not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("The provider gateway must bind to loopback")
        if not re.fullmatch(r"[A-Za-z0-9_-]{32,200}", gateway_key):
            raise ValueError("A separate private gateway key is required")
        self.bridge, self.gateway_key = bridge, gateway_key
        super().__init__(address, GatewayHandler)


class GatewayHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, *args):
        pass

    def _headers(self, status, mime, *, length=None, compatibility=None, retry=None):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.send_header("X-Content-Type-Options", "nosniff")
        if getattr(self, "request_id", None):
            self.send_header("X-Request-Id", self.request_id)
        if length is not None:
            self.send_header("Content-Length", str(length))
        if compatibility:
            self.send_header("X-Arena-Compatibility-Policy", compatibility["policy"])
            if compatibility["unenforced_controls"]:
                self.send_header("X-Arena-Unenforced-Controls", ",".join(compatibility["unenforced_controls"]))
        if retry:
            self.send_header("Retry-After", str(retry))
        self.end_headers()
        self.close_connection = True

    def _reply(self, payload, status=200, compatibility=None, retry=None):
        body = json.dumps(payload, allow_nan=False).encode()
        self._headers(status, "application/json", length=len(body), compatibility=compatibility, retry=retry)
        self.wfile.write(body)

    def _authenticate(self):
        values = self.headers.get_all("Authorization", [])
        key_values = self.headers.get_all("x-api-key", []) if self.path == "/v1/messages" else []
        valid = len(values) == 1 and not key_values and hmac.compare_digest(values[0].encode(), ("Bearer " + self.server.gateway_key).encode())
        valid = valid or not values and len(key_values) == 1 and hmac.compare_digest(key_values[0].encode(), self.server.gateway_key.encode())
        if not valid:
            raise ProviderError(401, "invalid_gateway_key", "A valid local gateway bearer key is required.")
        if self.headers.get("Origin"):
            raise ProviderError(403, "browser_origin_not_allowed", "This private gateway accepts worker SDK requests only.")

    def do_GET(self):
        try:
            self._authenticate()
            if self.path != "/v1/models":
                raise ProviderError(404, "not_found", "This gateway exposes /v1/models, /v1/responses and /v1/chat/completions.")
            self._reply(self.server.bridge.models())
        except ProviderError as exc:
            self._reply({"error": {"type": exc.code, "code": exc.code, "message": exc.message}}, exc.status, retry=exc.retry_after)
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass
        except Exception:
            self._reply({"error": {"code": "gateway_error", "message": "The private gateway could not complete this request."}}, 500)

    def _sse(self, item, *, event=None):
        line = ("event: " + event + "\n") if event else ""
        line += "data: " + ("[DONE]" if item is None else json.dumps(item, allow_nan=False)) + "\n\n"
        self.wfile.write(line.encode())
        self.wfile.flush()

    def do_POST(self):
        request_id = uuid.uuid4().hex
        self.request_id = request_id
        started_at, started_clock = time.time(), time.monotonic()
        model, observed, status, streaming = None, {}, 500, False
        compatibility = None
        error_code = exception_type = None
        try:
            self._authenticate()
            if self.path not in {"/v1/chat/completions", "/v1/responses", "/v1/messages"}:
                raise ProviderError(404, "not_found", "Unsupported private gateway route.")
            if self.headers.get("Transfer-Encoding") or len(self.headers.get_all("Content-Length", [])) != 1:
                raise _bad("A single Content-Length is required.")
            try:
                size = int(self.headers["Content-Length"])
            except ValueError:
                raise _bad("Invalid Content-Length.") from None
            if not 0 < size <= MAX_BODY:
                raise ProviderError(413, "request_too_large", "The request body must be at most 2 MiB.")
            raw = self.rfile.read(size)
            if len(raw) != size:
                raise _bad("The request body is incomplete.")
            try:
                body = _json(raw)
            except (ValueError, UnicodeError):
                raise _bad("The request body must be valid JSON.") from None
            anthropic = self.path == "/v1/messages"
            if anthropic:
                body = anthropic_to_chat(body)
            chat = self.path == "/v1/chat/completions" or anthropic
            payload, compatibility = normalize_request(body, chat=chat, policy=self.server.bridge.policy)
            available = {item["id"] for item in self.server.bridge.models()["data"]}
            if payload["model"] not in available:
                raise ProviderError(400, "model_not_available", "The exact requested model is not listed for this account or gateway policy; no substitution was made.")
            model = payload["model"]
            with self.server.bridge.admission():
                stream = body.get("stream", False)
                final, emitted_text, tool_indexes, emitted_arguments = None, "", {}, {}
                for event in self.server.bridge.events(payload):
                    kind = event.get("type")
                    if not streaming and stream:
                        self._headers(200, "text/event-stream", compatibility=compatibility)
                        streaming = True
                        if chat:
                            self._sse(self._chunk(request_id, model, {"role": "assistant"}, compatibility=compatibility))
                    if kind == "response.completed":
                        final = event["response"]
                        observed = usage_counts(final.get("usage"))
                    if not stream:
                        continue
                    if not chat:
                        if isinstance(event.get("response"), dict):
                            event = {**event, "response": {**event["response"], "arena_compatibility": compatibility}}
                        self._sse(event, event=kind if isinstance(kind, str) and re.fullmatch(r"[a-z_.]+", kind) else None)
                    elif kind == "response.output_text.delta":
                        delta = event.get("delta", "")
                        emitted_text += delta
                        self._sse(self._chunk(request_id, model, {"content": delta}))
                    elif kind == "response.output_item.added" and event.get("item", {}).get("type") == "function_call":
                        item = event["item"]
                        index = len(tool_indexes)
                        tool_indexes[event["output_index"]] = index
                        arguments = item.get("arguments", "")
                        emitted_arguments[index] = arguments
                        self._sse(self._chunk(request_id, model, {"tool_calls": [{"index": index, "id": item["call_id"], "type": "function", "function": {"name": item["name"], "arguments": arguments}}]}))
                    elif kind == "response.function_call_arguments.delta":
                        index = tool_indexes.get(event.get("output_index"))
                        if index is None:
                            raise ProviderError(502, "invalid_tool_stream", "Provider tool arguments arrived without a function call.")
                        delta = event.get("delta", "")
                        emitted_arguments[index] += delta
                        self._sse(self._chunk(request_id, model, {"tool_calls": [{"index": index, "function": {"arguments": delta}}]}))
                if final is None:
                    raise ProviderError(502, "missing_completion", "The provider did not return a complete response.")
                if chat:
                    completion = chat_completion(final, model, request_id, compatibility)
                    if stream:
                        message = completion["choices"][0]["message"]
                        final_text = message.get("content") or ""
                        if not final_text.startswith(emitted_text):
                            raise ProviderError(502, "inconsistent_text_stream", "Provider completion did not match its text stream.")
                        if final_text[len(emitted_text):]:
                            self._sse(self._chunk(request_id, model, {"content": final_text[len(emitted_text):]}))
                        for index, call in enumerate(message.get("tool_calls", [])):
                            args = call["function"]["arguments"]
                            previous = emitted_arguments.get(index)
                            if previous is None:
                                self._sse(self._chunk(request_id, model, {"tool_calls": [{"index": index, **call}]}))
                            elif args.startswith(previous):
                                if args[len(previous):]:
                                    self._sse(self._chunk(request_id, model, {"tool_calls": [{"index": index, "function": {"arguments": args[len(previous):]}}]}))
                            else:
                                raise ProviderError(502, "inconsistent_tool_stream", "Provider completion did not match its tool stream.")
                        if message.get("refusal"):
                            self._sse(self._chunk(request_id, model, {"refusal": message["refusal"]}))
                        self._sse(self._chunk(request_id, model, {}, finish=completion["choices"][0]["finish_reason"]))
                        if (body.get("stream_options") or {}).get("include_usage"):
                            chunk = self._chunk(request_id, model, {})
                            chunk["choices"], chunk["usage"] = [], completion["usage"]
                            self._sse(chunk)
                        self._sse(None)
                    else:
                        self._reply(anthropic_completion(completion) if anthropic else completion, compatibility=compatibility)
                elif not stream:
                    self._reply({**final, "arena_compatibility": compatibility}, compatibility=compatibility)
                status = 200
        except ProviderError as exc:
            status = exc.status
            error_code = exc.code
            exception_type = type(exc).__name__
            data = {"error": {"type": exc.code, "code": exc.code, "message": exc.message}}
            try:
                if streaming:
                    self._sse(data, event="error")
                else:
                    self._reply(data, status, compatibility, exc.retry_after)
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                pass
        except (BrokenPipeError, ConnectionResetError, TimeoutError) as exc:
            status = 499
            error_code = "client_disconnected"
            exception_type = type(exc).__name__
        except Exception as exc:
            status = 500
            error_code = "gateway_error"
            exception_type = type(exc).__name__
            data = {"error": {"code": "gateway_error", "message": "The private gateway could not complete this request."}}
            try:
                if streaming:
                    self._sse(data, event="error")
                else:
                    self._reply(data, 500)
            except OSError:
                pass
        finally:
            # No bodies, credentials, exception messages or input/output text.
            record = {"request_id": request_id, "model": model, "usage": observed, "status": status,
                      "started_at": started_at, "elapsed_seconds": max(0, time.monotonic() - started_clock)}
            if error_code is not None:
                record["error_code"] = error_code
                record["exception_type"] = exception_type
            self.server.bridge.audit(record)

    @staticmethod
    def _chunk(request_id, model, delta, *, finish=None, compatibility=None):
        item = {"id": "chatcmpl-" + request_id, "object": "chat.completion.chunk", "created": int(time.time()),
                "model": model, "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
        if compatibility:
            item["arena_compatibility"] = compatibility
        return item
