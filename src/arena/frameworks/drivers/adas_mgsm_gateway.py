"""Bounded MGSM pilot delegating pinned ADAS search and generated-agent scorer.

Importing this module is inert. Generated Python is native worker code, not a
security sandbox; admission must use the reviewed worker boundary.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import sys
import threading
import time
from types import SimpleNamespace

from .base_gateway import MODELS

IDENTITY = "adas-gateway-mgsm-v1"
DATASET_SHA256 = "67899701f97b7890ebd99bdb5b1098be4e86e3a846ed076ed9c675ce18588a96"
SOURCE_COMMIT = "2702bee8fefda42255efc5be9f60e3bd3db96ae4"
SOURCE_HASHES = {
    "search.py": "1d75318e452e1cdca455d9cd073749b9b43e3c49d2f00d85a1faa9d10585e920",
    "utils.py": "b294dc54f685fe14704154356da47b69bda7c254b8a1e06c4297d3169379ba2c",
    "mgsm_prompt.py": "6512b4a3d01ca80171f749981361c19edfbc6863b4de8ca70fa9aee6a6960f2b",
}
GATEWAY = "http://127.0.0.1:8789/v1"
REQUESTS = 128
EVALUATIONS = 32
WALL_SECONDS = 3600
SDK_TIMEOUT = 330


class PilotStop(BaseException):
    """Escape upstream broad Exception handlers without retry or zero fitness."""


def digest(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def load_dataset(path):
    raw = path.read_bytes()
    if len(raw) > 65536 or digest(raw) != DATASET_SHA256:
        raise ValueError("Expected the reviewed immutable MGSM pilot dataset")
    data = json.loads(raw)
    left = {x["problem_id"] for x in data["splits"]["optimization"]}
    right = {x["problem_id"] for x in data["splits"]["heldout"]}
    if left & right or len(left) != 2 or len(right) != 2:
        raise ValueError("MGSM split must separate underlying translated problems")
    return data


def load_native(source):
    root = source / "_mgsm"
    for name, expected in SOURCE_HASHES.items():
        if digest((root / name).read_bytes()) != expected:
            raise ValueError("ADAS source does not match the reviewed pin")
    previous = {name: sys.modules.get(name) for name in ("utils", "mgsm_prompt")}
    modules = {}
    try:
        for name in ("utils", "mgsm_prompt", "search"):
            spec = importlib.util.spec_from_file_location(name if name != "search" else "arena_adas_mgsm_native", root / (name + ".py"))
            module = importlib.util.module_from_spec(spec)
            if name != "search":
                sys.modules[name] = module
            spec.loader.exec_module(module)
            modules[name] = module
    finally:
        for name, value in previous.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value
    modules["search"].client.close()
    return modules["search"], modules["utils"]


def before_native_shuffle(examples, seed=0):
    """Invert native deterministic shuffle; leave upstream shuffle/slicing intact."""
    indices = list(range(len(examples)))
    random.Random(seed).shuffle(indices)
    result = [None] * len(examples)
    for index, item in zip(indices, examples):
        result[index] = dict(item)
    return result


class Session:
    def __init__(self, output, model, create):
        self.output, self.model, self.create = output, model, create
        self.started = time.monotonic()
        self.requests = self.completed_requests = self.evaluations = 0
        self.phase = "optimization"
        self.stop_reason = None
        self.role = threading.local()
        self.lock = threading.Lock()
        self.records = []

    def event(self, **record):
        with (self.output / "events.jsonl").open("a") as stream:
            stream.write(json.dumps(record, allow_nan=False) + "\n")

    def check_wall(self):
        if self.stop_reason is not None:
            raise PilotStop(self.stop_reason)
        if time.monotonic() - self.started >= WALL_SECONDS:
            self.stop("wall_budget_exhausted")

    def stop(self, reason):
        # Executor.map submits the entire native question slice in advance.
        # Latch failures so a queued second question cannot dispatch after the
        # first task has failed but before the main thread consumes its future.
        self.stop_reason = reason
        raise PilotStop(reason)

    def call(self, **kwargs):
        # All supplied SDK calls serialize. This accounting seam is not an
        # adversarial security boundary against arbitrary generated Python.
        with self.lock:
            self.check_wall()
            if kwargs.get("model") != self.model:
                self.stop("model_mismatch")
            if self.requests >= REQUESTS:
                self.stop("request_budget_exhausted")
            self.requests += 1
            sequence = self.requests
            start = time.monotonic()
            self.event(type="request_started", sequence=sequence, phase=self.phase,
                       role=getattr(self.role, "value", "inner"), model=self.model)
            try:
                response = self.create(**kwargs)
                if (getattr(response, "model", None) != self.model
                        or len(getattr(response, "choices", ())) != 1
                        or not isinstance(response.choices[0].message.content, str)):
                    raise ValueError("ADAS requires one text completion from the selected model")
            except Exception as error:
                self.event(type="request_failed", sequence=sequence, phase=self.phase,
                           error_class=type(error).__name__, outcome="unknown",
                           duration_seconds=time.monotonic() - start)
                self.stop_reason = "provider_request_failed"
                raise PilotStop(self.stop_reason) from None
            self.completed_requests += 1
            usage = getattr(response, "usage", None)
            safe_usage = {key: getattr(usage, key, None) for key in
                          ("prompt_tokens", "completion_tokens", "total_tokens")}
            safe_usage = {key: value for key, value in safe_usage.items()
                          if type(value) is int and value >= 0}
            self.event(type="request_completed", sequence=sequence, phase=self.phase,
                       duration_seconds=time.monotonic() - start, usage=safe_usage)
            return response


def bind_native(native, utils, session, data):
    native.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=session.call)))
    original_agent = native.LLMAgentBase

    class SelectedModelAgent(original_agent):
        def __init__(self, output_fields, agent_name, role="helpful assistant", model=None, temperature=0.5):
            if model is not None and model != session.model:
                session.stop("model_mismatch")
            super().__init__(output_fields, agent_name, role, session.model, temperature)

    native.LLMAgentBase = SelectedModelAgent
    for function_name, role in (("get_json_response_from_gpt", "inner"), ("get_json_response_from_gpt_reflect", "meta")):
        # Preserve the native request and JSON parser. Remove only the unbounded
        # RateLimitError decorator; transport errors terminate with unknown cost.
        function = getattr(native, function_name).__wrapped__

        def invoke(*args, _function=function, _role=role, **kwargs):
            session.role.value = _role
            return _function(*args, **kwargs)

        setattr(native, function_name, invoke)
    original_prompt = native.get_prompt

    def prompt(*args, **kwargs):
        system, text = original_prompt(*args, **kwargs)
        # The meta-prompt embeds a copy of the agent utility signature. Reflect
        # the explicitly bound model there, so generated code sees the contract.
        return system, text.replace("model='gpt-3.5-turbo-0125'", "model=" + repr(session.model))

    native.get_prompt = prompt

    def examples():
        records = list(data["splits"]["optimization"])
        if session.phase == "heldout":
            records += data["splits"]["heldout"]
        formatted = [{"inputs": utils.LANG_TO_INSTRUCTIONS[row["language"]].format(input=row["question"]),
                      "targets": row["answer"], "lang": row["language"]} for row in records]
        return before_native_shuffle(formatted)

    native.get_all_examples = examples
    original_evaluate = native.evaluate_forward_fn

    def evaluate(args, code):
        session.check_wall()
        if session.evaluations >= EVALUATIONS:
            session.stop("evaluation_budget_exhausted")
        session.evaluations += 1
        record = {"type": "evaluation", "sequence": session.evaluations, "phase": session.phase,
                  "code_sha256": digest(code), "example_ids": [row["id"] for row in data["splits"][session.phase]],
                  "status": "started"}
        session.event(**record)
        try:
            scores = original_evaluate(args, code)
        except BaseException as error:
            session.event(**{**record, "status": "failed", "error_class": type(error).__name__})
            raise
        if len(scores) != 2 or any(type(score) is not int or score not in (0, 1) for score in scores):
            raise PilotStop("invalid_native_scores")
        record.update(status="completed", scores=scores, mean=sum(scores) / len(scores))
        session.records.append(record)
        session.event(**record)
        return scores

    native.evaluate_forward_fn = evaluate


def select_observed(archive, records):
    """Select only archived code whose exact bytes have completed native scores."""
    evaluated = {item["code_sha256"]: item for item in records if item["phase"] == "optimization"}
    eligible = [(item, evaluated[digest(item["code"])]) for item in archive if digest(item["code"]) in evaluated]
    if not eligible:
        raise PilotStop("no_evaluated_archived_candidate")
    # Stable ties retain native archive order; rounded native CI strings are
    # never parsed as objective values. Debug proposals can otherwise carry a
    # previous code's fitness at this pin, so unobserved hashes are excluded.
    return max(eligible, key=lambda pair: pair[1]["mean"])


def run(args, *, native_pair=None, client=None):
    data = load_dataset(args.dataset)
    if args.model not in MODELS:
        raise ValueError("Use the exact selected gateway model")
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("A scoped local gateway key is required")
    args.output.mkdir(parents=True, exist_ok=True)
    if any(args.output.iterdir()):
        raise ValueError("ADAS pilot output must be empty")
    write_json(args.output / "provider-seam.json", {
        "schema": "arena.adas-mgsm-pilot/1", "framework": IDENTITY, "source_commit": SOURCE_COMMIT,
        "model": args.model, "model_roles": {"meta": args.model, "inner": args.model},
        "endpoint": GATEWAY, "provider_model_alias_substituted": False,
        "dataset_sha256": DATASET_SHA256, "dataset": {key: data[key] for key in ("repository", "commit", "license", "attribution", "selection", "metric")},
        "budgets": {"request_attempts": REQUESTS, "evaluator_invocations": EVALUATIONS,
                    "questions_per_evaluation": 2, "meta_generations": 1, "debug_max": 1,
                    "initial_strategies": 7, "native_workers": 1, "outer_wall_seconds": WALL_SECONDS,
                    "sdk_timeout_seconds": SDK_TIMEOUT, "sdk_max_retries": 0},
        "provider_controls_unenforced": ["temperature", "max_tokens", "stop"],
        "json_mode": "native json_object forwarded; native JSON parser retained",
        "heldout_policy": "One selected archived code hash, frozen by optimization mean before heldout; ties use archive order",
        "canonical_evaluation": False, "native_search_and_scorer": True,
        "generated_code_is_sandboxed": False,
        "limits_scope": "Cooperative native API/evaluator accounting plus external process-group deadline; arbitrary generated Python shares the worker and can bypass in-process hooks",
    })
    native, utils = native_pair or load_native(Path.cwd())
    own_client = client is None
    if own_client:
        import openai
        client = openai.OpenAI(base_url=GATEWAY, api_key=os.environ["OPENAI_API_KEY"],
                               timeout=SDK_TIMEOUT, max_retries=0)
    session = Session(args.output, args.model, client.chat.completions.create)
    bind_native(native, utils, session, data)
    native_args = SimpleNamespace(save_dir=str(args.output), expr_name="mgsm", model=args.model,
                                  valid_size=2, test_size=2, shuffle_seed=0, n_repreat=1,
                                  multiprocessing=False, max_workers=1, n_generation=1, debug_max=1)
    status, reason = "failed", "unexpected_exception"
    try:
        native.SEARCHING_MODE = True
        native.search(native_args)
        archive = json.loads((args.output / "mgsm_run_archive.json").read_text())
        selected, observed = select_observed(archive, session.records)
        selection = {"code_sha256": digest(selected["code"]), "native_generation": selected.get("generation"),
                     "optimization_scores": observed["scores"], "optimization_mean": observed["mean"],
                     "selection_rule": "highest completed native optimization mean; stable archive order ties"}
        write_json(args.output / "selection.json", selection)
        session.event(type="selection_frozen", **selection)
        session.phase = "heldout"
        native.SEARCHING_MODE = False
        scores = native.evaluate_forward_fn(native_args, selected["code"])
        write_json(args.output / "heldout.json", {"selection_sha256": digest((args.output / "selection.json").read_bytes()),
                    "code_sha256": selection["code_sha256"], "scores": scores, "mean": sum(scores) / len(scores),
                    "canonical_evaluation": False, "selection_uses_heldout": False})
        status, reason = "completed", None
    except PilotStop as error:
        reason = str(error)
    finally:
        write_json(args.output / "pilot-status.json", {"status": status, "reason": reason,
                   "request_attempts": session.requests, "completed_requests": session.completed_requests,
                   "evaluator_invocations": session.evaluations, "canonical_evaluation": False})
        if own_client:
            client.close()
    return 0 if status == "completed" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--dataset", type=Path, default=Path("arena-inputs/mgsm-adas-pilot-v1.json"))
    parser.add_argument("--output", type=Path, required=True)
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
