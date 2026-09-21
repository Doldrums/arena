"""Provider errors, wire limits and strict JSON decoding."""
from __future__ import annotations

import json
import re


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
