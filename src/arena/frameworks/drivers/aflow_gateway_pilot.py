"""Bounded provider/data configuration for the pinned native AFlow graph search."""
from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
from types import SimpleNamespace
import weakref

from ._gsm8k_pilot import DATASET_SHA256, ENDPOINT, MODELS, load_dataset, write_json

COMMIT = "3f457218fc716093fe53f6df8a5d5e6379d66346"
MAX_CALLS = 192
MAX_EVALUATIONS = 40
ROUNDS = 2
SDK_TIMEOUT_SECONDS = 330
EMPTY_HISTORY = ("results.json", "processed_experience.json", "round_1/log.json")
SOURCE_HASHES = {
    "scripts/async_llm.py": "4c8b40f13c84385ba7c20e26816436818fb5a143ed6543f501ccfa8d39b72184",
    "scripts/optimizer.py": "26cc9ac8f99177ed670c75fd6a265294c1dbaf1518e41f383eaf1d980b3968e5",
    "scripts/evaluator.py": "5d115ac921b69f9d5055300cf52969c5e0b4474ab2f5daad13b8af988218616e",
    "scripts/formatter.py": "b383f3bd209ac14d90d30b47e507918194000c920b161ec7f217176dcbcc16bf",
    "benchmarks/gsm8k.py": "c2f5ce790cf162fc987e88fd3a6a17a37358f3a63f153c3dbcaa20e41ca2568c",
    "benchmarks/benchmark.py": "f84ad22e452965ea15b0849ceffde436b619f6ade51abafa6725755fa2801de5",
}


class PilotBudgetExhausted(BaseException):
    """A non-result termination that escapes native retry/round Exception handlers."""


def verify_source(root):
    for name, expected in SOURCE_HASHES.items():
        if hashlib.sha256((Path(root) / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Unexpected AFlow source: " + name)


def fresh_workspace():
    root = Path("workspace/GSM8K/workflows")
    if sorted(p.name for p in root.glob("round_*")) != ["round_1"]:
        raise ValueError("AFlow pilot requires a fresh seed-only workspace")
    for name in EMPTY_HISTORY:
        path = root / name
        if path.read_bytes() != b"":
            raise ValueError("Refusing to mix historical native results into this run")
    # These three tracked upstream files are empty placeholders at this pin.
    # Removing them only in the isolated run workspace avoids JSON decode noise.
    for name in EMPTY_HISTORY:
        (root / name).unlink()
    return {name: hashlib.sha256(b"").hexdigest() for name in EMPTY_HISTORY}


class GatewayBudget:
    def __init__(self, model, path=None, sdk_factory=None, limit=MAX_CALLS):
        if model not in MODELS or type(limit) is not int or not 1 <= limit <= MAX_CALLS:
            raise ValueError("Use an exact reviewed model and bounded request limit")
        if sdk_factory is None:
            from openai import AsyncOpenAI
            sdk_factory = AsyncOpenAI
        self.model, self.path, self.sdk_factory, self.limit = model, path, sdk_factory, limit
        self.records, self.phase, self.evaluations = [], "optimization", 0
        self.locks = weakref.WeakKeyDictionary()

    def save(self):
        if self.path:
            write_json(self.path, {"schema": "arena.aflow-gateway-usage/1", "model": self.model,
                "endpoint": ENDPOINT, "phase": self.phase, "request_limit": self.limit,
                "requests_attempted": len(self.records), "problem_evaluations_admitted": self.evaluations,
                "problem_evaluation_limit": MAX_EVALUATIONS, "sdk_timeout_seconds": SDK_TIMEOUT_SECONDS, "records": self.records,
                "cost_usd": None, "native_price_estimates_are_billing": False,
                "scope": "SDK admissions, including failed attempts; SDK retries disabled. Not billing records.",
                "provider_controls_unenforced": ["temperature", "top_p"]})

    def client(self, *, api_key, base_url):
        if base_url != ENDPOINT or not isinstance(api_key, str) or not api_key:
            raise ValueError("AFlow must use the scoped local gateway endpoint and credential")
        # Native creates one client per graph/optimizer. Avoid keeping its HTTP
        # pool across the separate event loops created by Optimizer.optimize.
        async def create(**kwargs):
            if kwargs.get("model") != self.model or set(kwargs) - {"model", "messages", "temperature", "top_p"}:
                raise ValueError("Unreviewed model or native SDK request fields")
            loop = asyncio.get_running_loop()
            lock = self.locks.setdefault(loop, asyncio.Lock())
            async with lock:
                if len(self.records) >= self.limit:
                    raise PilotBudgetExhausted("Gateway request admission limit exhausted")
                record = {"request": len(self.records) + 1, "phase": self.phase, "status": "started",
                    "messages_sha256": hashlib.sha256(json.dumps(kwargs["messages"], sort_keys=True).encode()).hexdigest()}
                self.records.append(record)
                self.save()
                try:
                    async with self.sdk_factory(api_key=api_key, base_url=base_url, max_retries=0, timeout=SDK_TIMEOUT_SECONDS) as sdk:
                        response = await sdk.chat.completions.create(**kwargs)
                    if response.model != self.model or len(response.choices) != 1:
                        raise ValueError("Gateway changed model identity or completion count")
                    if not isinstance(response.choices[0].message.content, str) or response.usage is None:
                        raise ValueError("Native AFlow requires textual output and reported token usage")
                    record.update(status="completed", response_id=response.id, usage=response.usage.model_dump())
                    return response
                except BaseException as error:
                    record.update(status="error", error_type=type(error).__name__)
                    raise
                finally:
                    self.save()
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


@contextmanager
def configure_native(budget):
    import scripts.async_llm as llm
    from benchmarks.benchmark import BaseBenchmark
    original_sdk = llm.AsyncOpenAI
    original_evaluate = BaseBenchmark.evaluate_all_problems

    async def serial_evaluate(self, data, agent, max_concurrent_tasks=50):
        if budget.evaluations + len(data) > MAX_EVALUATIONS:
            raise PilotBudgetExhausted("Problem evaluation admission limit exhausted")
        budget.evaluations += len(data)
        budget.save()
        return await original_evaluate(self, data, agent, max_concurrent_tasks=1)

    llm.AsyncOpenAI = budget.client
    BaseBenchmark.evaluate_all_problems = serial_evaluate
    try:
        yield
    finally:
        llm.AsyncOpenAI = original_sdk
        BaseBenchmark.evaluate_all_problems = original_evaluate


def materialize_data(dataset, split):
    # The native evaluator consumes only question/answer fields. The immutable
    # bundle preserves exact source rows/indices/hashes and the unused train split.
    if split not in {"validation", "heldout"}:
        raise ValueError("AFlow uses optimization validation and post-search heldout only")
    name = "validate" if split == "validation" else "test"
    path = Path("data/datasets") / ("gsm8k_" + name + ".jsonl")
    if path.exists():
        raise ValueError("Refusing to replace a native dataset")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps({k: row[k] for k in ("question", "answer")}, ensure_ascii=False) + "\n"
                            for row in dataset["selected_records"][split]))
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "count": 8}


def build_native(model, key):
    from scripts.async_llm import LLMConfig
    from scripts.optimizer import Optimizer
    if model not in MODELS or not key:
        raise ValueError("Exact gateway model and scoped credential required")
    config = LLMConfig({"model": model, "key": key, "base_url": ENDPOINT, "temperature": 1, "top_p": 1})
    # Keep the native workspace package name: generated graph imports refer to
    # workspace.GSM8K and GraphUtils converts the relative path to a module name.
    return Optimizer(dataset="GSM8K", question_type="math", opt_llm_config=config,
        exec_llm_config=config, operators=["Custom", "ScEnsemble", "Programmer"],
        sample=4, check_convergence=False, optimized_path="workspace", initial_round=1,
        max_rounds=ROUNDS, validation_rounds=1)


def completed_rounds(optimizer):
    data = optimizer.data_utils.load_results("workspace/GSM8K/workflows")
    rounds = [row.get("round") for row in data]
    if sorted(rounds) != [1, 2, 3]:
        return False
    return all(type(row.get("score")) in (int, float) and math.isfinite(row["score"])
               and 0 <= row["score"] <= 1 for row in data) and all(
        Path(f"workspace/GSM8K/workflows/round_{r}/experience.json").is_file() for r in (2, 3))


def freeze_selection(optimizer, output):
    selected = optimizer.data_utils.get_top_rounds(1)[0]
    number = selected["round"]
    files = {name: hashlib.sha256(Path(f"workspace/GSM8K/workflows/round_{number}/{name}").read_bytes()).hexdigest()
             for name in ("graph.py", "prompt.py")}
    result = {"round": number, "validation_score": selected["score"], "files": files,
              "selection": "Native DataUtils mean validation score ranking; native stable tie order.",
              "heldout_seen": False}
    write_json(output / "selection.json", result)
    return number


def run(args):
    verify_source(Path.cwd())
    dataset = load_dataset(args.dataset)
    args.output.mkdir(parents=True, exist_ok=False)
    budget = GatewayBudget(args.model, args.output / "usage.json")
    report = {"schema": "arena.aflow-gsm8k-pilot/1", "model": args.model, "source_commit": COMMIT,
        "dataset_sha256": DATASET_SHA256, "optimization_examples": 8, "heldout_examples": 8, "unused_train_examples": 8,
        "status": "running", "native_completed": False, "heldout_completed": False,
        "canonical_evaluation": False, "paper_replication": False, "cost_usd": None,
        "native_cost_limitation": "Upstream unknown model prices default to zero; native zero is not a measured free run.",
        "metric": "Pinned native GSM8KBenchmark last-number float extraction; absolute tolerance1e-6.",
        "budgets": {"native_rounds": ROUNDS, "validation_repeats": 1, "requests": MAX_CALLS,
                    "problem_evaluations": MAX_EVALUATIONS, "evaluation_concurrency": 1,
                    "sdk_timeout_seconds": SDK_TIMEOUT_SECONDS, "outer_wall_seconds": 2400}}
    try:
        report["removed_empty_placeholders"] = fresh_workspace()
        report["validation_data"] = materialize_data(dataset, "validation")
        with configure_native(budget):
            optimizer = build_native(args.model, os.environ.get("OPENAI_API_KEY"))
            optimizer.optimize("Graph")
            report["native_returned"] = True
            if not completed_rounds(optimizer):
                report["status"] = "native_incomplete"
                return 76
            report["native_completed"] = True
            selected = freeze_selection(optimizer, args.output)
            report["selected_round"] = selected
            report["heldout_data"] = materialize_data(dataset, "heldout")
            budget.phase = "heldout"
            from scripts.evaluator import Evaluator
            report["heldout"] = {}
            for number in dict.fromkeys((1, selected)):
                directory = args.output / f"heldout-round-{number}"
                directory.mkdir()
                graph = optimizer.graph_utils.load_graph(number, "workspace/GSM8K/workflows")
                score, avg_cost, total_cost = asyncio.run(Evaluator(str(directory)).graph_evaluate(
                    "GSM8K", graph, {"dataset": "GSM8K", "llm_config": optimizer.execute_llm_config},
                    str(directory), is_test=True))
                report["heldout"][str(number)] = {"score": float(score), "native_avg_cost": float(avg_cost),
                                                "native_total_cost": float(total_cost), "cost_usd": None}
                write_json(args.output / "pilot.json", report)
            report.update(status="completed", heldout_completed=True)
            return 0
    except PilotBudgetExhausted as error:
        report.update(status="budget_exhausted", error_type=type(error).__name__)
        return 75
    except BaseException as error:
        report.update(status="error", error_type=type(error).__name__)
        raise
    finally:
        budget.save()
        write_json(args.output / "pilot.json", report)


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
