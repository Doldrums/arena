"""Model discovery, admission limits and completion integrity."""
from __future__ import annotations

from collections import deque
from contextlib import contextmanager
import json
import math
import threading
import time
from .provider_common import (
    MODEL_ID,
    ProviderError,
    UNENFORCED,
)
from .provider_protocol import (
    public_response,
)


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
        self.inventory, self.inventory_at = [], None
        self.audit = audit or (lambda record: print(json.dumps(record, separators=(",", ":")), flush=True))

    def models(self):
        with self.discovery_lock:
            if self.inventory_at is None or time.monotonic() - self.inventory_at >= 300:
                raw = self.transport.models()
                if not isinstance(raw, dict) or not isinstance(raw.get("models"), list):
                    raise ProviderError(502, "invalid_model_inventory", "Model discovery returned an invalid inventory.")
                models = []
                for item in raw["models"]:
                    if not isinstance(item, dict):
                        raise ProviderError(502, "invalid_model_inventory", "Model discovery returned an invalid entry.")
                    ident = item.get("slug")
                    if not isinstance(ident, str) or not MODEL_ID.fullmatch(ident) or item.get("supported_in_api") is not True:
                        continue
                    if self.allowed_models is not None and ident not in self.allowed_models:
                        continue
                    reasoning = item.get("supported_reasoning_levels", [])
                    if not isinstance(reasoning, list):
                        raise ProviderError(502, "invalid_model_inventory", "Model discovery returned invalid reasoning levels.")
                    levels = [x.get("effort") for x in reasoning if isinstance(x, dict) and isinstance(x.get("effort"), str)]
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
