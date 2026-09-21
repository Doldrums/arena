"""Exact-model text transport for the pinned QDAIF poetry callable interface."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import threading
from types import SimpleNamespace

from .base_gateway import MODELS

ENDPOINT = "http://127.0.0.1:8789/v1"
REQUEST_LIMIT = 24
REQUEST_TIMEOUT = 330
_transport = None


class QDAIFGatewayStopped(BaseException):
    """Provider/budget failure, never a native quality judgment."""


def write_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temp.replace(path)


class GatewayTransport:
    def __init__(self, model, output, *, session=None, sdk=None):
        if model not in MODELS:
            raise ValueError("QDAIF requires an exact reviewed model")
        self.model, self.output = model, Path(output)
        self.records, self.lock = [], threading.RLock()
        if sdk is None:
            import openai as sdk
        if session is None:
            import requests
            session = requests.Session()
            session.trust_env = False
            for scheme in ("http://", "https://"):
                session.mount(scheme, requests.adapters.HTTPAdapter(max_retries=0))
        context = getattr(getattr(sdk, "api_requestor", None), "_thread_context", None)
        if context is not None and hasattr(context, "session"):
            raise ValueError("QDAIF transport requires a fresh SDK process")
        self.sdk, self.session = sdk, session
        self.key = os.environ.get("OPENAI_API_KEY")
        if not self.key:
            raise ValueError("Worker OPENAI_API_KEY is required")
        # The pinned SDK explicitly supports a requestssession factory. Count at
        # this seam: ChatCompletion.create itself retries TryAgain responses.
        sdk.requestssession = lambda: SimpleNamespace(request=self.dispatch, close=session.close, proxies={})

    def save(self):
        write_json(self.output / "gateway-usage.json", {
            "schema": "arena.qdaif-gateway-usage/1", "model": self.model,
            "endpoint": ENDPOINT, "records": self.records,
            "http_attempts": len(self.records), "http_attempt_limit": REQUEST_LIMIT,
            "request_timeout_seconds": REQUEST_TIMEOUT,
            "http_adapter_retries": 0, "sdk_warmup_retries": "included in HTTP attempt limit",
            "max_concurrent_requests": 1, "cost_usd": None,
            "provider_controls_unenforced": ["temperature", "top_p", "max_tokens"],
            "scope": "Physical HTTP admissions, including legacy SDK warmup retries; not a monetary budget."})

    def dispatch(self, method, url, **kwargs):
        with self.lock:
            if method.lower() != "post" or url != ENDPOINT + "/chat/completions":
                raise QDAIFGatewayStopped("Unreviewed QDAIF endpoint")
            body = json.loads(kwargs.get("data", "{}"))
            if set(body) != {"model", "messages", "stream"} or body["model"] != self.model or body["stream"] is not False:
                raise QDAIFGatewayStopped("Unreviewed QDAIF wire request")
            if len(self.records) >= REQUEST_LIMIT:
                self.save()
                raise QDAIFGatewayStopped("QDAIF HTTP attempt budget exhausted")
            record = {"attempt": len(self.records) + 1, "model": self.model, "status": "dispatched",
                "messages_sha256": hashlib.sha256(json.dumps(body["messages"], sort_keys=True).encode()).hexdigest()}
            self.records.append(record)
            self.save()
            kwargs.update(allow_redirects=False, timeout=REQUEST_TIMEOUT)
            try:
                response = self.session.request(method, url, **kwargs)
                record.update(status="http_returned", http_status=response.status_code)
                return response
            except Exception as error:
                record.update(status="error", error_type=type(error).__name__, outcome="unknown")
                raise QDAIFGatewayStopped("QDAIF HTTP request failed") from None
            finally:
                self.save()

    def complete(self, value):
        is_text = isinstance(value, str)
        if is_text:
            messages = [{"role": "user", "content": value}]
        elif isinstance(value, list) and value and all(getattr(v, "type", None) == "human" and isinstance(v.content, str) for v in value):
            messages = [{"role": "user", "content": v.content} for v in value]
        else:
            raise QDAIFGatewayStopped("Unsupported native poetry message interface")
        with self.lock:
            before = len(self.records)
            try:
                response = self.sdk.ChatCompletion.create(api_key=self.key, api_base=ENDPOINT,
                    api_type="open_ai", api_version=None, organization=None,
                    model=self.model, messages=messages, stream=False,
                    request_timeout=REQUEST_TIMEOUT, timeout=REQUEST_TIMEOUT)
                if response.model != self.model or len(response.choices) != 1 or not isinstance(response.choices[0].message.content, str):
                    raise ValueError("QDAIF response model/text cardinality mismatch")
                if len(self.records) == before:
                    raise ValueError("SDK bypassed the bounded HTTP session")
                self.records[-1].update(status="returned", usage=dict(response.usage) if response.get("usage") else None)
                text = response.choices[0].message.content
                return text if is_text else SimpleNamespace(content=text)
            except Exception as error:
                if len(self.records) > before:
                    self.records[-1].update(status="error", error_type=type(error).__name__, outcome="unknown")
                raise QDAIFGatewayStopped("QDAIF provider response failed; no model fallback") from None
            finally:
                self.save()


def install_transport(transport):
    global _transport
    _transport = transport


def make_model(config):
    if _transport is None or config.model_type != "openai" or config.model_path != _transport.model or config.logits_only:
        raise QDAIFGatewayStopped("QDAIF poetry transport requires the bound exact text model")
    return _transport.complete
