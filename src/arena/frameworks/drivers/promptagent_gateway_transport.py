"""Bounded provider constructor for native PromptAgent's unchanged API loop."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import threading
from types import SimpleNamespace

from .base_gateway import MODELS

ENDPOINT = "http://127.0.0.1:8789/v1"
REQUEST_LIMIT = 96
REQUEST_TIMEOUT = 330
LOGICAL_ATTEMPTS = 2
_transport = None


class PromptAgentStopped(BaseException):
    """Terminal integration stop, outside the native infinite Exception retry."""


class RetryableProviderError(Exception):
    """Sanitized single retry through the native backoff loop."""


def write_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temp.replace(path)


class GatewayTransport:
    def __init__(self, model, output, *, client=None):
        if model not in MODELS:
            raise ValueError('PromptAgent requires an exact reviewed model')
        self.model, self.output = model, Path(output)
        self.records, self.failures = [], {'base': 0, 'optim': 0}
        self.lock = threading.RLock()
        self.questions, self.observer = {}, None
        if client is None:
            import httpx
            from openai import OpenAI as SDKOpenAI
            key = os.environ.get('OPENAI_API_KEY')
            if not key:
                raise ValueError('The worker scoped OPENAI_API_KEY is required')
            client = SDKOpenAI(api_key=key, base_url=ENDPOINT, max_retries=0, timeout=REQUEST_TIMEOUT,
                http_client=httpx.Client(follow_redirects=False, trust_env=False, timeout=REQUEST_TIMEOUT))
        self.client = client

    def bind_task(self, task, observer=None):
        self.questions = {split: [row['question'] for row in rows] for split, rows in task.dataset.items()}
        self.answer_format = task.answer_format_prompt
        self.observer = observer

    def phase(self, role, messages):
        if role == 'optim':
            return 'optimization'
        text = messages[0]['content']
        found = [split for split, questions in self.questions.items()
                 if any(text.endswith('\n' + question + '\n' + self.answer_format) for question in questions)]
        if len(found) != 1:
            raise PromptAgentStopped('Native forward prompt did not identify exactly one prepared split')
        return {'train': 'training', 'eval': 'reward', 'test': 'heldout'}[found[0]]

    def save(self):
        write_json(self.output / 'gateway-usage.json', {
            'schema': 'arena.promptagent-gateway-usage/1', 'model': self.model, 'endpoint': ENDPOINT,
            'records': self.records, 'requests_attempted': len(self.records), 'request_limit': REQUEST_LIMIT,
            'request_timeout_seconds': REQUEST_TIMEOUT, 'sdk_retries': 0, 'http_redirects': False,
            'max_attempts_per_native_call': LOGICAL_ATTEMPTS, 'max_concurrent_requests': 1,
            'provider_controls_unenforced': ['temperature'], 'cost_usd': None,
            'scope': 'Actual SDK admissions including the bounded native retry; not a monetary/token budget.'})

    def complete(self, role, *, messages, model, temperature, **kwargs):
        if role not in self.failures or model != self.model or kwargs or not isinstance(messages, list) or len(messages) != 1 or set(messages[0]) != {'role', 'content'} or messages[0]['role'] != 'user' or not isinstance(messages[0]['content'], str):
            raise PromptAgentStopped('Unreviewed PromptAgent provider request')
        if temperature != {'base': 0.0, 'optim': 1.0}[role]:
            raise PromptAgentStopped('Unreviewed native role configuration')
        with self.lock:
            if len(self.records) >= REQUEST_LIMIT:
                self.save()
                raise PromptAgentStopped('PromptAgent SDK attempt budget exhausted')
            phase = self.phase(role, messages)
            if self.observer:
                self.observer(phase)
            record = {'request': len(self.records) + 1, 'role': role, 'phase': phase, 'model': model,
                'messages_sha256': hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest(),
                'requested_temperature': temperature, 'status': 'dispatched'}
            self.records.append(record)
            self.save()
            try:
                response = self.client.chat.completions.create(model=model, messages=messages, stream=False)
            except Exception as error:
                self.failures[role] += 1
                record.update(status='error', error_type=type(error).__name__, outcome='unknown')
                self.save()
                if self.failures[role] >= LOGICAL_ATTEMPTS:
                    raise PromptAgentStopped('PromptAgent provider failed twice; native retry stopped') from None
                raise RetryableProviderError('PromptAgent provider request failed; one native retry remains') from None
            try:
                if response.model != model or len(response.choices) != 1 or not isinstance(response.choices[0].message.content, str):
                    raise ValueError('Response model or text cardinality mismatch')
                self.failures[role] = 0
                record.update(status='returned', usage=response.usage.model_dump() if response.usage else None)
                return response
            except Exception as error:
                record.update(status='error', error_type=type(error).__name__, outcome='unknown')
                raise PromptAgentStopped('PromptAgent response identity/protocol failed') from None
            finally:
                self.save()


def install_transport(transport):
    global _transport
    _transport = transport


def OpenAI(*, api_key):
    """Native constructor seam; config contains role markers, never credentials."""
    role = {'environment:base': 'base', 'environment:optim': 'optim'}.get(api_key)
    if _transport is None or role is None:
        raise PromptAgentStopped('PromptAgent provider constructor is not bound')
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kwargs: _transport.complete(role, **kwargs))))
