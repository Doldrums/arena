"""Exact-model transport for the pinned AEL centralized llm_call interface.

No native imports or model calls occur on import. Provider failure/budget stop
escapes upstream Exception fallbacks; neither is an equal-weight experiment.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import threading

from .base_gateway import MODELS

ENDPOINT = "http://127.0.0.1:8789/v1"
REQUEST_LIMIT = 64
REQUEST_TIMEOUT = 330
_transport = None


class AELGatewayStopped(BaseException):
    """Terminal integration failure, not a native fallback or search result."""


def write_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temp.replace(path)


class GatewayTransport:
    def __init__(self, model, output, *, client=None):
        if model not in MODELS:
            raise ValueError("AEL requires an exact reviewed gateway model")
        self.model, self.output = model, Path(output)
        self.records = []
        self.lock = threading.RLock()
        if client is None:
            key = os.environ.get("OPENAI_API_KEY")
            if not key:
                raise ValueError("The scoped OPENAI_API_KEY must be supplied by the worker")
            from openai import OpenAI
            client = OpenAI(api_key=key, base_url=ENDPOINT, max_retries=0, timeout=REQUEST_TIMEOUT)
        self.client = client

    def save(self):
        write_json(self.output / "gateway-usage.json", {
            "schema": "arena.ael-gateway-usage/1", "model": self.model,
            "endpoint": ENDPOINT, "records": self.records,
            "requests_attempted": len(self.records), "request_limit": REQUEST_LIMIT,
            "request_timeout_seconds": REQUEST_TIMEOUT, "sdk_retries": 0,
            "max_concurrent_requests": 1, "cost_usd": None,
            "provider_controls_unenforced": ["temperature", "max_tokens"],
            "scope": "Central native llm_call requests, not a monetary budget or billing receipt."})

    def complete(self, model, messages, temperature=0.3, max_tokens=1024,
                 response_format=None, **kwargs):
        if model != self.model or kwargs or response_format not in (None, {"type": "json_object"}):
            raise AELGatewayStopped("Unreviewed AEL model or request controls")
        with self.lock:
            if len(self.records) >= REQUEST_LIMIT:
                self.save()
                raise AELGatewayStopped("AEL centralized request budget exhausted")
            record = {"request": len(self.records) + 1, "model": model, "status": "dispatched",
                      "messages_sha256": hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest(),
                      "requested_controls": {"temperature": temperature, "max_tokens": max_tokens},
                      "response_format": response_format}
            self.records.append(record)
            self.save()
            try:
                arguments = {"model": model, "messages": messages, "stream": False}
                if response_format is not None:
                    arguments["response_format"] = response_format
                response = self.client.chat.completions.create(**arguments)
                if response.model != self.model or len(response.choices) != 1 or not isinstance(response.choices[0].message.content, str):
                    raise ValueError("AEL requires a native text completion")
                record.update(status="returned", usage=response.usage.model_dump() if response.usage else None)
                return response
            except Exception as error:
                record.update(status="error", error_type=type(error).__name__, outcome="unknown")
                raise AELGatewayStopped("AEL provider request failed; no automatic retry or fallback") from None
            finally:
                self.save()


def install_transport(transport):
    global _transport
    _transport = transport


def normalize_model(model):
    if _transport is None or model != _transport.model:
        raise AELGatewayStopped("AEL transport is unbound or model identity changed")
    return model


def llm_call(model, messages, **kwargs):
    normalize_model(model)
    return _transport.complete(model, messages, **kwargs)
