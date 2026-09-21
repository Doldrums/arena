"""Pinned GSM8K pilot data, official scoring, and a bounded local transport."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import threading

from .base_gateway import MODELS

DATASET_SHA256 = "98abad8a6fc5b24172c329f257815fe0c4c3b6756716a9de980d4ed1be96a974"
DATASET_COMMIT = "3101c7d5072418e28b9008a6636bde82a006892c"
ENDPOINT = "http://127.0.0.1:8789/v1"
SEED = "Solve the math word problem. End your answer with #### followed by a space and the numeric answer."

# Official OpenAI GSM8K dataset.py extraction/equality semantics, MIT license.
# Source c22b81bccaaebfd1123be296e8b3c3dca3ddc704c46b70bf4a50603bb627e197.
# License and original source URL are retained in the pinned dataset bundle.
ANS_RE = re.compile(r"#### (\-?[0-9\.\,]+)")
INVALID_ANS = "[invalid]"


def extract_answer(completion):
    match = ANS_RE.search(completion)
    if match:
        match_str = match.group(1).strip()
        match_str = match_str.replace(",", "")
        return match_str
    else:
        return INVALID_ANS


def is_correct(model_completion, gt_example):
    gt_answer = extract_answer(gt_example["answer"])
    assert gt_answer != INVALID_ANS
    return extract_answer(model_completion) == gt_answer


def load_dataset(path):
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != DATASET_SHA256:
        raise ValueError("The immutable GSM8K pilot dataset hash does not match")
    value = json.loads(data)
    if value["commit"] != DATASET_COMMIT or value["schema"] != "arena.prompt-pilot-dataset/1":
        raise ValueError("Unexpected dataset identity")
    splits = value["selected_records"]
    questions = []
    for name in ("train", "validation", "heldout"):
        if len(splits[name]) != 8:
            raise ValueError("Each pilot split must contain eight genuine examples")
        for row in splits[name]:
            questions.append(row["question"])
            if extract_answer(row["answer"]) == INVALID_ANS:
                raise ValueError("Invalid official gold answer")
    if len(set(questions)) != 24:
        raise ValueError("Pilot splits must be question-disjoint")
    return value


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    temporary.replace(path)


class GatewayCallBudgetExhausted(BaseException):
    """Escapes native retry loops; exhaustion is not an optimization result."""


class GatewayTransport:
    def __init__(self, model, ledger_path=None, limit=128, client=None):
        if model not in MODELS:
            raise ValueError("Choose an exact reviewed gateway model")
        if type(limit) is not int or not 1 <= limit <= 128:
            raise ValueError("Gateway request limit must be in 1..128")
        self.model, self.limit = model, limit
        self.ledger_path = Path(ledger_path) if ledger_path else None
        self.phase, self.records = "optimization", []
        self.lock = threading.RLock()
        if client is None:
            key = os.environ.get("OPENAI_API_KEY")
            if not key:
                raise ValueError("OPENAI_API_KEY must contain the scoped local gateway credential")
            from openai import OpenAI
            client = OpenAI(api_key=key, base_url=ENDPOINT, timeout=180, max_retries=0)
        self.client = client

    def __deepcopy__(self, memo):
        # Native program copies must share one transport/request budget.
        return self

    def save(self):
        if self.ledger_path:
            write_json(self.ledger_path, {"schema": "arena.prompt-gateway-usage/1", "model": self.model,
                       "endpoint": ENDPOINT, "gateway_requests_attempted": len(self.records),
                       "request_limit": self.limit, "records": self.records, "cost_usd": None,
                       "scope": "SDK calls admitted by this driver; SDK retries disabled. These are not billing records.",
                       "provider_controls_unenforced": ["temperature", "max_tokens", "top_p"]})

    def complete(self, messages, **kwargs):
        n = kwargs.pop("n", 1)
        if type(n) is not int or not 1 <= n <= 8:
            raise ValueError("Native multi-completion request must have n in 1..8")
        if set(kwargs) - {"temperature", "max_tokens", "top_p"}:
            raise ValueError("Unreviewed gateway generation fields: " + ", ".join(sorted(set(kwargs) - {"temperature", "max_tokens", "top_p"})))
        responses = []
        # Ordered n=1 draws preserve native choice count without concurrent bursts.
        with self.lock:
            for _ in range(n):
                if len(self.records) >= self.limit:
                    self.save()
                    raise GatewayCallBudgetExhausted("Explicit gateway request limit exhausted")
                record = {"request": len(self.records) + 1, "phase": self.phase,
                          "status": "started", "usage": None,
                          "messages_sha256": hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()}
                self.records.append(record)
                self.save()
                try:
                    response = self.client.chat.completions.create(model=self.model, messages=messages,
                        n=1, stream=False, **{k: v for k, v in kwargs.items() if v is not None})
                    if response.model != self.model or len(response.choices) != 1:
                        raise ValueError("Gateway response changed model identity or choice count")
                    content = response.choices[0].message.content
                    if not isinstance(content, str):
                        raise ValueError("Expected a textual gateway completion")
                    usage = getattr(response, "usage", None)
                    record.update(status="completed", response_id=response.id,
                                  usage=usage.model_dump() if usage is not None else None)
                    responses.append(response)
                except BaseException as error:
                    record.update(status="error", error_type=type(error).__name__)
                    raise
                finally:
                    self.save()
        if len(responses) == 1:
            return responses[0]
        choices = [r.choices[0].model_copy(update={"index": i}) for i, r in enumerate(responses)]
        usages = [r.usage for r in responses]
        if all(u is not None for u in usages):
            from openai.types import CompletionUsage
            usage = CompletionUsage(**{key: sum(getattr(u, key) for u in usages)
                                       for key in ("prompt_tokens", "completion_tokens", "total_tokens")})
        else:
            usage = None
        return responses[0].model_copy(update={"choices": choices, "usage": usage})

    def text(self, prompt):
        messages = [{"role": "user", "content": prompt}] if isinstance(prompt, str) else prompt
        return self.complete(messages, temperature=1.0, max_tokens=8192).choices[0].message.content


def heldout_report(rows, predict, output_path=None):
    records = []
    for row in rows:
        response = predict(row["question"])
        records.append({"source_split": row["source_split"], "source_index_zero_based": row["source_index_zero_based"],
                        "question_sha256": row["question_sha256"], "prediction": response,
                        "extracted_prediction": extract_answer(response), "gold": extract_answer(row["answer"]),
                        "correct": bool(is_correct(response, row))})
        if output_path:
            write_json(output_path, {"status": "partial", "expected_total": len(rows),
                                    "completed_count": len(records), "accuracy": None, "records": records})
    correct = sum(r["correct"] for r in records)
    result = {"correct": correct, "total": len(records), "accuracy": correct / len(records), "records": records}
    if output_path:
        write_json(output_path, {"status": "completed", **result})
    return result


def protocol(dataset, framework, model, budget):
    return {"schema": "arena.prompt-pilot-protocol/1", "framework": framework, "model": model,
            "dataset_id": dataset["id"], "dataset_sha256": DATASET_SHA256, "dataset_commit": DATASET_COMMIT,
            "split_sizes": {k: len(v) for k, v in dataset["selected_records"].items()},
            "metric": dataset["metric"], "native_budget": budget,
            "heldout_policy": "Seed and validation-selected program evaluated only after optimization; heldout never passed to the optimizer or selection.",
            "canonical_evaluation": False, "paper_replication": False, "gateway_request_limit": 128,
            "sdk_timeout_seconds": 180, "sdk_retries": 0, "gateway_parallel_requests": 1,
            "provider_controls_unenforced": ["temperature", "max_tokens", "top_p"],
            "limits": "Eight examples per split is an integration pilot. No absence of model pretraining contamination or cross-framework scientific comparability is established."}
