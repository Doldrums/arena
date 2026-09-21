"""Execution-only DSPy BaseLM plugin for the pinned 3.4 native contract.

Imported by the explicit MIPROv2 driver, never during recipe preparation.
"""
from __future__ import annotations

import dspy

from ._gsm8k_pilot import GatewayTransport


class GatewayLM(dspy.BaseLM):
    def __init__(self, model, *, transport=None, temperature=1.0, max_tokens=8192,
                 model_type="chat", cache=False, num_retries=0, **kwargs):
        if model_type != "chat" or cache is not False or num_retries != 0:
            raise ValueError("The pilot uses uncached chat completions without SDK retries")
        super().__init__(model=model, model_type=model_type, temperature=temperature,
                         max_tokens=max_tokens, cache=False, num_retries=0, **kwargs)
        self.transport = transport or GatewayTransport(model)
        if self.transport.model != model:
            raise ValueError("DSPy and gateway model identities must match")

    @property
    def supported_params(self):
        return {"temperature", "max_tokens", "top_p", "n"}

    def forward(self, prompt=None, messages=None, **kwargs):
        options = {**self.kwargs, **kwargs}
        # Native rollout_id affects response-cache identity, not provider sampling.
        # This pilot disables response caches; the identifier is not sent to API.
        options.pop("rollout_id", None)
        options.pop("cache", None)
        return self.transport.complete(messages or [{"role": "user", "content": prompt}], **options)

    def __deepcopy__(self, memo):
        copy = self.copy()
        memo[id(self)] = copy
        return copy
