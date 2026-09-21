"""Private loopback bridge to the explicitly configured Codex account provider.

Importing this module does not read credentials, discover models or make calls.
Run ``python -m arena.providers --help`` for operator-controlled entrypoints.
"""
from __future__ import annotations

import argparse
import base64
from collections import deque
from contextlib import contextmanager
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import re
import secrets
import socket
import stat
import sys
import threading
import time
from urllib import error, request
import uuid

BASE_URL = "https://chatgpt.com/backend-api/codex"
CLIENT_VERSION = "0.155.1"
MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
MAX_BODY = 2 * 1024 * 1024
MAX_STREAM = 32 * 1024 * 1024
UNENFORCED = {"temperature", "top_p", "max_tokens", "max_completion_tokens", "max_output_tokens",
              "stop", "top_k", "frequency_penalty", "presence_penalty", "seed", "logit_bias"}


class ProviderError(Exception):
    """Only fixed, non-sensitive diagnostics cross the HTTP/log boundary."""
    def __init__(self, status, code, message, retry_after=None):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message
        self.retry_after = retry_after


def _bad(message):
    return ProviderError(400, "invalid_request", message)


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


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


def _content(value, role):
    kind = "output_text" if role == "assistant" else "input_text"
    if isinstance(value, str):
        return [{"type": kind, "text": value}]
    if not isinstance(value, list):
        raise _bad("Message content must be text or a supported content array.")
    result = []
    for item in value:
        if not isinstance(item, dict):
            raise _bad("Invalid message content item.")
        if item.get("type") == "text" and isinstance(item.get("text"), str):
            result.append({"type": kind, "text": item["text"]})
        elif item.get("type") == "image_url" and role == "user" and isinstance(item.get("image_url"), dict):
            image = item["image_url"]
            url = image.get("url")
            if not isinstance(url, str) or not url.startswith(("https://", "http://", "data:image/")):
                raise _bad("Unsupported image URL.")
            result.append({"type": "input_image", "image_url": url, "detail": image.get("detail", "auto")})
        else:
            raise _bad("Unsupported message content item.")
    return result


def _generation_controls(body, policy):
    present = sorted(key for key in UNENFORCED if body.get(key) is not None)
    if present and policy == "strict":
        raise ProviderError(400, "unsupported_generation_controls",
                            "Codex does not guarantee these controls: " + ", ".join(present) + ". Select the explicit codex-native compatibility policy to proceed without them.")
    for key in present:
        value = body[key]
        if key in {"max_tokens", "max_completion_tokens", "max_output_tokens"}:
            valid = type(value) is int and 1 <= value <= 1_000_000
        elif key == "stop":
            valid = isinstance(value, str) and len(value) <= 4096 or isinstance(value, list) and len(value) <= 16 and all(isinstance(x, str) and len(x) <= 4096 for x in value)
        elif key == "logit_bias":
            valid = isinstance(value, dict) and len(value) <= 256 and all(isinstance(k, str) and type(v) in (int, float) and math.isfinite(v) and -100 <= v <= 100 for k, v in value.items())
        else:
            valid = type(value) in (int, float) and math.isfinite(value) and abs(value) <= (2**53 if key == "seed" else 100)
        if not valid:
            raise _bad("Invalid generation control value.")
    return present


def normalize_request(body, *, chat, policy="strict"):
    if type(body) is not dict or not isinstance(body.get("model"), str) or not MODEL_ID.fullmatch(body["model"]):
        raise _bad("Provide an exact model identifier.")
    if type(body.get("stream", False)) is not bool:
        raise _bad("stream must be boolean.")
    if body.get("store") is not None and body.get("store") is not False:
        raise _bad("This private bridge requires store:false.")
    ignored = _generation_controls(body, policy)
    shared = {"model", "stream", "store", "tools", "tool_choice", "parallel_tool_calls", "reasoning", "reasoning_effort", "service_tier", "prompt_cache_key"}
    supported = shared | UNENFORCED | ({"messages", "response_format", "stream_options", "n"} if chat else {"input", "instructions", "text", "include", "truncation"})
    if set(body) - supported:
        raise _bad("The request includes unsupported API fields.")
    if type(body.get("n", 1)) is not int or body.get("n", 1) != 1:
        raise _bad("Only n=1 is supported; the bridge never launches hidden extra generations.")
    if chat and body.get("stream_options") is not None:
        options = body["stream_options"]
        if type(options) is not dict or set(options) - {"include_usage"} or type(options.get("include_usage", False)) is not bool:
            raise _bad("stream_options only supports boolean include_usage.")
    payload = {"model": body["model"], "instructions": "", "store": False, "stream": True}
    for key in ("parallel_tool_calls", "reasoning", "service_tier", "prompt_cache_key"):
        if body.get(key) is not None:
            payload[key] = body[key]
    if body.get("reasoning_effort") is not None:
        if "reasoning" in payload:
            raise _bad("Use either reasoning or reasoning_effort.")
        payload["reasoning"] = {"effort": body["reasoning_effort"]}
    if chat:
        messages = body.get("messages")
        if not isinstance(messages, list) or not messages or len(messages) > 10000:
            raise _bad("messages must be a nonempty bounded list.")
        inputs, instructions = [], []
        for message in messages:
            if not isinstance(message, dict):
                raise _bad("Invalid chat message.")
            role = message.get("role")
            if role in {"system", "developer"}:
                contents = _content(message.get("content"), "user")
                if any(item["type"] != "input_text" for item in contents):
                    raise _bad("System instructions must be text.")
                instructions.append("\n".join(item["text"] for item in contents))
            elif role in {"user", "assistant"}:
                if message.get("content") is not None:
                    inputs.append({"role": role, "content": _content(message["content"], role)})
                calls = message.get("tool_calls", [])
                if not isinstance(calls, list) or calls and role != "assistant":
                    raise _bad("Tool calls must belong to an assistant message.")
                for call in calls:
                    function = call.get("function", {}) if isinstance(call, dict) else {}
                    if not isinstance(call, dict) or not isinstance(function, dict) or set(function) - {"name", "arguments"} or call.get("type") != "function" or not all(isinstance(v, str) for v in [call.get("id"), function.get("name"), function.get("arguments")]):
                        raise _bad("Invalid assistant function call.")
                    inputs.append({"type": "function_call", "call_id": call["id"], **function})
            elif role == "tool":
                if not isinstance(message.get("tool_call_id"), str) or not isinstance(message.get("content"), str):
                    raise _bad("Tool results need tool_call_id and string content.")
                inputs.append({"type": "function_call_output", "call_id": message["tool_call_id"], "output": message["content"]})
            else:
                raise _bad("Unsupported message role.")
        if not inputs:
            raise _bad("At least one user or tool input is required.")
        payload.update(input=inputs, instructions="\n\n".join(instructions))
        if body.get("tools") is not None:
            if not isinstance(body["tools"], list):
                raise _bad("tools must be a list.")
            payload["tools"] = []
            for tool in body["tools"]:
                if not isinstance(tool, dict) or tool.get("type") != "function" or not isinstance(tool.get("function"), dict):
                    raise _bad("Chat compatibility currently supports function tools only.")
                function = tool["function"]
                if set(function) - {"name", "description", "parameters", "strict"} or not isinstance(function.get("name"), str):
                    raise _bad("Invalid function tool definition.")
                payload["tools"].append({"type": "function", **function})
        choice = body.get("tool_choice")
        if isinstance(choice, dict):
            if choice.get("type") != "function" or not isinstance(choice.get("function"), dict):
                raise _bad("Unsupported tool choice.")
            choice = {"type": "function", "name": choice["function"].get("name")}
        if choice is not None:
            payload["tool_choice"] = choice
        if body.get("response_format") is not None:
            fmt = body["response_format"]
            if not isinstance(fmt, dict) or fmt.get("type") not in {"text", "json_object", "json_schema"}:
                raise _bad("Unsupported response_format.")
            if fmt["type"] == "json_schema" and not isinstance(fmt.get("json_schema"), dict):
                raise _bad("json_schema must be a schema definition object.")
            payload["text"] = {"format": {"type": fmt["type"], **(fmt.get("json_schema", {}) if fmt["type"] == "json_schema" else {})}}
    else:
        if not isinstance(body.get("input"), (str, list)):
            raise _bad("Responses input must be text or an input-item list.")
        payload["input"] = ([{"role": "user", "content": [{"type": "input_text", "text": body["input"]}]}]
                            if isinstance(body["input"], str) else body["input"])
        for key in ("instructions", "tools", "tool_choice", "text", "include", "truncation"):
            if body.get(key) is not None:
                payload[key] = body[key]
        if not isinstance(payload["instructions"], str):
            raise _bad("instructions must be text.")
    compatibility = {"policy": policy, "unenforced_controls": ignored, "compute_cap_enforced": False}
    return payload, compatibility


def anthropic_to_chat(body):
    """Narrow Messages compatibility for native nonstreaming Anthropic SDKs."""
    if type(body) is not dict:
        raise _bad("Messages requests must be objects.")
    allowed = {"model", "messages", "system", "max_tokens", "temperature", "top_p", "top_k",
               "stop_sequences", "stream", "tools", "tool_choice"}
    if set(body) - allowed:
        raise _bad("This Messages bridge does not support these request fields.")
    if body.get("stream") not in (None, False):
        raise ProviderError(400, "anthropic_streaming_not_supported", "Messages compatibility currently supports stream:false only.")
    result = {key: body[key] for key in ("model", "max_tokens", "temperature", "top_p", "top_k") if key in body}
    result["messages"] = []
    def text_blocks(content):
        if isinstance(content, str):
            return content
        if not isinstance(content, list) or any(not isinstance(x, dict) or x.get("type") != "text" or not isinstance(x.get("text"), str) or set(x) - {"type", "text"} for x in content):
            raise _bad("Messages compatibility supports plain text and function tool content only.")
        return "\n".join(x["text"] for x in content)
    if "system" in body:
        result["messages"].append({"role": "system", "content": text_blocks(body["system"])})
    if not isinstance(body.get("messages"), list) or not body["messages"]:
        raise _bad("Messages requires a nonempty messages list.")
    for message in body["messages"]:
        if not isinstance(message, dict) or message.get("role") not in {"user", "assistant"}:
            raise _bad("Unsupported Messages role.")
        content, role = message.get("content"), message["role"]
        if isinstance(content, str):
            result["messages"].append({"role": role, "content": content})
            continue
        if not isinstance(content, list):
            raise _bad("Messages content must be text or content blocks.")
        texts, calls = [], []
        for block in content:
            if not isinstance(block, dict):
                raise _bad("Invalid Messages content block.")
            if block.get("type") == "text":
                texts.append(text_blocks([block]))
            elif block.get("type") == "tool_use" and role == "assistant":
                if not all(isinstance(block.get(k), str) for k in ("id", "name")) or not isinstance(block.get("input"), dict):
                    raise _bad("Invalid Messages tool use.")
                calls.append({"id": block["id"], "type": "function", "function": {"name": block["name"], "arguments": json.dumps(block["input"], allow_nan=False)}})
            elif block.get("type") == "tool_result" and role == "user":
                if not isinstance(block.get("tool_use_id"), str):
                    raise _bad("A tool result must identify its tool use.")
                value = text_blocks(block.get("content", ""))
                if block.get("is_error"):
                    value = "Tool returned an error:\n" + value
                result["messages"].append({"role": "tool", "tool_call_id": block["tool_use_id"], "content": value})
            else:
                raise _bad("Unsupported Messages content block.")
        if texts or calls:
            converted = {"role": role, "content": "\n".join(texts) if texts else None}
            if calls:
                converted["tool_calls"] = calls
            result["messages"].append(converted)
    if "stop_sequences" in body:
        result["stop"] = body["stop_sequences"]
    if "tools" in body:
        if not isinstance(body["tools"], list):
            raise _bad("Messages tools must be a list.")
        result["tools"] = []
        for tool in body["tools"]:
            if not isinstance(tool, dict) or not isinstance(tool.get("name"), str) or not isinstance(tool.get("input_schema"), dict) or set(tool) - {"name", "description", "input_schema"}:
                raise _bad("Only ordinary Messages function tools are supported.")
            result["tools"].append({"type": "function", "function": {"name": tool["name"], "description": tool.get("description", ""), "parameters": tool["input_schema"]}})
    if "tool_choice" in body:
        choice = body["tool_choice"]
        if not isinstance(choice, dict) or choice.get("type") not in {"auto", "any", "none", "tool"}:
            raise _bad("Unsupported Messages tool choice.")
        if choice["type"] == "tool":
            if not isinstance(choice.get("name"), str):
                raise _bad("Named tool choice needs a name.")
            result["tool_choice"] = {"type": "function", "function": {"name": choice["name"]}}
        else:
            result["tool_choice"] = {"auto": "auto", "any": "required", "none": "none"}[choice["type"]]
        if "disable_parallel_tool_use" in choice:
            result["parallel_tool_calls"] = not choice["disable_parallel_tool_use"]
    return result


def anthropic_completion(completion):
    message = completion["choices"][0]["message"]
    content = []
    if message.get("content"):
        content.append({"type": "text", "text": message["content"]})
    if message.get("refusal"):
        content.append({"type": "text", "text": message["refusal"]})
    for call in message.get("tool_calls", []):
        try:
            arguments = _json(call["function"]["arguments"])
            if not isinstance(arguments, dict):
                raise ValueError()
        except ValueError:
            raise ProviderError(502, "invalid_function_arguments", "The provider returned invalid function arguments.") from None
        content.append({"type": "tool_use", "id": call["id"], "name": call["function"]["name"], "input": arguments})
    return {"id": "msg-" + completion["id"].removeprefix("chatcmpl-"), "type": "message", "role": "assistant",
            "model": completion["model"], "content": content, "stop_reason": "tool_use" if message.get("tool_calls") else "end_turn",
            "stop_sequence": None, "usage": {"input_tokens": completion["usage"]["prompt_tokens"], "output_tokens": completion["usage"]["completion_tokens"]},
            "arena_compatibility": completion["arena_compatibility"]}


def usage_counts(value):
    value = value if isinstance(value, dict) else {}
    result = {}
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        number = value.get(key)
        if type(number) is int and number >= 0:
            result[key] = number
    return result


def public_response(value):
    """Forward response content without account IDs or provider cache identifiers."""
    result = {key: value[key] for key in
              ("id", "object", "created_at", "completed_at", "status", "error", "incomplete_details", "model", "output")
              if key in value}
    if isinstance(value.get("usage"), dict):
        usage = usage_counts(value["usage"])
        for key in ("input_tokens_details", "output_tokens_details"):
            if isinstance(value["usage"].get(key), dict):
                usage[key] = {name: count for name, count in value["usage"][key].items()
                              if name in {"cached_tokens", "cache_write_tokens", "reasoning_tokens"}
                              and type(count) is int and count >= 0}
        result["usage"] = usage
    return result


def chat_completion(response, requested_model, request_id, compatibility):
    content, refusals, calls = [], [], []
    for item in response.get("output", []):
        if item.get("type") == "message":
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    content.append(part.get("text", ""))
                elif part.get("type") == "refusal":
                    refusals.append(part.get("refusal", ""))
        elif item.get("type") == "function_call":
            calls.append({"id": item["call_id"], "type": "function", "function": {"name": item["name"], "arguments": item["arguments"]}})
    message = {"role": "assistant", "content": "".join(content) or None}
    if calls:
        message["tool_calls"] = calls
    if refusals:
        message["refusal"] = "".join(refusals)
    observed = usage_counts(response.get("usage"))
    usage = {"prompt_tokens": observed.get("input_tokens"), "completion_tokens": observed.get("output_tokens"), "total_tokens": observed.get("total_tokens")}
    return {"id": "chatcmpl-" + request_id, "object": "chat.completion", "created": int(time.time()),
            "model": requested_model, "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls" if calls else "stop"}],
            "usage": usage, "arena_compatibility": compatibility}


class ProviderBridge:
    def __init__(self, transport, *, max_concurrency=2, requests_per_minute=20, policy="strict", allowed_models=None, audit=None):
        if type(max_concurrency) is not int or not 1 <= max_concurrency <= 32 or type(requests_per_minute) is not int or not 1 <= requests_per_minute <= 10000:
            raise ValueError("Concurrency and rate limits must be bounded positive integers")
        if policy not in {"strict", "codex-native"}:
            raise ValueError("Unknown provider compatibility policy")
        self.transport, self.policy = transport, policy
        self.allowed_models = None if allowed_models is None else set(allowed_models)
        self.slots = threading.BoundedSemaphore(max_concurrency)
        self.rpm = requests_per_minute
        self.lock = threading.Lock()
        self.discovery_lock = threading.Lock()
        self.calls = deque()
        self.inventory, self.inventory_at = [], 0
        self.audit = audit or (lambda record: print(json.dumps(record, separators=(",", ":")), flush=True))

    def models(self):
        with self.discovery_lock:
            if not self.inventory or time.monotonic() - self.inventory_at > 300:
                raw = self.transport.models()
                if not isinstance(raw, dict) or not isinstance(raw.get("models"), list):
                    raise ProviderError(502, "invalid_model_inventory", "Model discovery returned an invalid inventory.")
                models = []
                for item in raw["models"]:
                    ident = item.get("slug")
                    if not isinstance(ident, str) or not MODEL_ID.fullmatch(ident) or item.get("supported_in_api") is not True:
                        continue
                    if self.allowed_models is not None and ident not in self.allowed_models:
                        continue
                    levels = [x.get("effort") for x in item.get("supported_reasoning_levels", []) if isinstance(x, dict) and isinstance(x.get("effort"), str)]
                    models.append({"id": ident, "object": "model", "created": 0, "owned_by": "openai",
                                   "visibility": item.get("visibility", "unknown"), "reasoning_efforts": levels,
                                   "availability": "listed_by_account_provider", "generation_verified": False})
                self.inventory, self.inventory_at = models, time.monotonic()
            return {"object": "list", "data": self.inventory,
                    "arena_capabilities": {"compatibility_policy": self.policy, "upstream_store": False,
                                           "chat_function_tools": True, "anthropic_messages": "nonstreaming-text-and-function-tools",
                                           "unsupported_generation_controls": sorted(UNENFORCED), "compute_cap_enforced": False}}

    @contextmanager
    def admission(self):
        if not self.slots.acquire(blocking=False):
            raise ProviderError(429, "gateway_busy", "The private gateway concurrency limit was reached.", 1)
        try:
            with self.lock:
                now = time.monotonic()
                while self.calls and self.calls[0] <= now - 60:
                    self.calls.popleft()
                if len(self.calls) >= self.rpm:
                    raise ProviderError(429, "gateway_rate_limit", "The private gateway request rate was reached.", max(1, math.ceil(60 - (now - self.calls[0]))))
                self.calls.append(now)
            yield
        finally:
            self.slots.release()

    def events(self, payload):
        complete = False
        completed_items = {}
        saw_output_delta = False
        for event in self.transport.events(payload):
            if event is None:
                break
            kind = event.get("type")
            if kind in {"response.output_text.delta", "response.function_call_arguments.delta"}:
                saw_output_delta = True
            if kind == "response.output_item.done":
                index, item = event.get("output_index"), event.get("item")
                if type(index) is not int or index < 0 or index > 10000 or not isinstance(item, dict):
                    raise ProviderError(502, "invalid_output_item", "The provider returned an invalid completed output item.")
                if index in completed_items and completed_items[index] != item:
                    raise ProviderError(502, "inconsistent_output_item", "The provider changed a completed output item.")
                completed_items[index] = item
            if kind in {"error", "response.failed", "response.incomplete"}:
                raise ProviderError(502, "upstream_generation_failed", "The provider did not complete the generation.")
            if kind == "response.completed":
                response = event.get("response")
                if not isinstance(response, dict) or response.get("status") != "completed" or response.get("error"):
                    raise ProviderError(502, "invalid_upstream_completion", "The provider returned an invalid completion.")
                # The account backend sends committed output items individually
                # and may leave response.completed.output empty (store=false).
                # Reconstruct from done events for both streaming and nonstreaming
                # SDK clients; never treat token usage alone as generated text.
                if not response.get("output"):
                    if completed_items:
                        response = {**response, "output": [completed_items[index] for index in sorted(completed_items)]}
                    elif saw_output_delta:
                        raise ProviderError(502, "missing_output_items", "The provider completed without committed output items.")
                event = {**event, "response": response}
                complete = True
            if isinstance(event.get("response"), dict):
                event = {**event, "response": public_response(event["response"])}
            yield event
            if complete:
                return
        if not complete:
            raise ProviderError(502, "truncated_upstream_stream", "The provider stream ended without a completed response.")


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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    key = commands.add_parser("key", help="Create a private gateway key without printing it")
    key.add_argument("--file", required=True)
    for name in ("models", "serve"):
        sub = commands.add_parser(name)
        sub.add_argument("--token-file", required=True)
        sub.add_argument("--timeout", type=int, default=180)
        if name == "serve":
            sub.add_argument("--gateway-key-file", required=True)
            sub.add_argument("--port", type=int, default=8789)
            sub.add_argument("--max-concurrency", type=int, default=2)
            sub.add_argument("--requests-per-minute", type=int, default=20)
            sub.add_argument("--compatibility-policy", choices=("strict", "codex-native"), default="strict")
            sub.add_argument("--allowed-model", action="append")
    args = parser.parse_args(argv)
    try:
        if args.command == "key":
            create_gateway_key(args.file)
            return 0
        if not 1 <= args.timeout <= 900:
            raise ValueError("Timeout must be between 1 and 900 seconds")
        token = TokenSource(args.token_file)
        _, expiry = token.read()
        transport = CodexTransport(token, args.timeout)
        bridge = ProviderBridge(transport, **({"max_concurrency": args.max_concurrency,
                                "requests_per_minute": args.requests_per_minute, "policy": args.compatibility_policy,
                                "allowed_models": args.allowed_model} if args.command == "serve" else {}))
        if args.command == "models":
            print(json.dumps({**bridge.models(), "credential_expires_at": expiry}, indent=2))
            return 0
        key_value = read_gateway_key(args.gateway_key_file)
        server = GatewayServer(("127.0.0.1", args.port), bridge, key_value)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0
    except (ProviderError, ValueError, OSError) as exc:
        # Do not print generic exception strings: filesystem paths and provider details are private.
        print(json.dumps({"error": exc.code if isinstance(exc, ProviderError) else "gateway_configuration_error"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
