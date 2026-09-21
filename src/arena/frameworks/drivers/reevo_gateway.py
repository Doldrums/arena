"""OpenAI transport seam for native ReEvo; imported by Hydra at run time only.

ReEvo's own client, reflection, selection, mutation and evaluator remain native.
A provider supporting only n=1 receives ordered, sequential independent draws.
"""
from __future__ import annotations

# This module is intentionally a native-runtime dependency, never imported by
# catalog validation or prepare(). `utils` belongs to the verified workspace.
from utils.llm_client.openai import OpenAIClient


class GatewayClient(OpenAIClient):
    def __init__(self, model, temperature=1.0, base_url=None, api_key=None):
        super().__init__(model, temperature, base_url, api_key)
        self.client = self.client.with_options(timeout=180.0, max_retries=0)

    def _chat_completion_api(self, messages, temperature, n=1):
        if type(n) is not int or not 1 <= n <= 8:
            raise ValueError("This pilot transport supports one to eight choices")
        choices = []
        for index in range(n):
            result = self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=temperature,
                n=1, stream=False,
            )
            if len(result.choices) != 1:
                raise ValueError("Provider must return exactly one choice per draw")
            choice = result.choices[0]
            choices.append(choice.model_copy(update={"index": index}))
        return choices
