#!/usr/bin/env python3
"""Offline native AEL conformance with SDK MockTransport and packaged prices.

One model per fresh Python process. No network/backend credentials are needed.
Only the central SDK returns fixture text; search, parsers, tools and evaluator
are the real pinned source. This does not measure model or method performance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import socket
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from arena.frameworks.drivers.ael_portfolio_gateway import MODELS, run, preparation, sha
from arena.frameworks.drivers.ael_gateway_transport import write_json


def fixture_response(prompt):
    if prompt.startswith("# Portfolio Allocation"):
        return json.dumps({"AAPL": 0.6, "MSFT": 0.4, "cash": 0})
    if "CURRENT PLANNER CODE" in prompt:
        return '''class FixturePlanner(BasePlanner):
    name = "fixture_planner"
    description = "Offline protocol fixture only"
    def plan(self, task, available_tools, memory_context=None):
        return [PlanStep(step_id=1, action="synthesize", rationale="fixture")]
    def replan(self, task, completed_steps, remaining_steps, available_tools, memory_context=None):
        return self.plan(task, available_tools, memory_context)
'''
    if "Must inherit BaseTool" in prompt:
        return '''class FixtureTool(BaseTool):
    name = "fixture_tool"
    description = "Offline protocol fixture only"
    def execute(self, **kwargs):
        return {"fixture": True}
'''
    if "has_template" in prompt:
        return json.dumps({"has_template": False})
    if "has_strategy" in prompt:
        return json.dumps({"has_strategy": False})
    if "Generate a CAUSAL insight" in prompt:
        return json.dumps({"key_insight": "Offline fixture, not research evidence", "market_regime": "mixed",
            "pattern_confidence": 0.5, "tomorrow_outlook": "fixture",
            "planner_critique": {"failing_planner": "sequential", "successful_planner": None, "reason": "fixture"},
            "structural_problem": {"detected": True, "description": "fixture trigger"}})
    raise AssertionError("Unreviewed native fixture prompt kind")


def check(source, destination, freeze, model):
    import httpx
    from openai import OpenAI
    if destination.exists():
        raise ValueError("Conformance destination must be new")
    destination.mkdir(parents=True)
    workspace = destination / "workspace"
    shutil.copytree(source, workspace, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    write_json(destination / "preparation.json", preparation(workspace, freeze))
    calls = []
    def respond(request):
        body = json.loads(request.content)
        assert request.url.path == "/v1/chat/completions"
        assert body["model"] == model and body["stream"] is False
        prompt = body["messages"][0]["content"]
        calls.append({"model": body["model"], "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                      "allocation": prompt.startswith("# Portfolio Allocation")})
        return httpx.Response(200, json={"id": "inert-ael-fixture", "object": "chat.completion",
            "created": 0, "model": model, "choices": [{"index": 0, "finish_reason": "stop",
            "message": {"role": "assistant", "content": fixture_response(prompt)}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})
    client = OpenAI(api_key="offline-fixture", base_url="http://127.0.0.1:1/v1", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(respond)))
    def blocked_network(*args, **kwargs):
        raise AssertionError("Offline AEL conformance must not connect to any network")
    socket.socket.connect = blocked_network
    socket.create_connection = blocked_network
    receipt = run(workspace, model, destination / "output", destination / "preparation.json", freeze, client=client)
    assert receipt["status"] == "completed"
    assert len([c for c in calls if c["allocation"]]) == 16
    assert receipt["native_activity"]["nightly_cycles"] == 3
    assert receipt["native_activity"]["reflections"] == 3
    assert "fixture_planner" in receipt["native_activity"]["planner_names"]
    assert {k:v["n_bars"] for k,v in receipt["phase_metrics"].items()} == {"train":8,"val":4,"test":4}
    proof = {"schema": "arena.ael-offline-conformance/1", "model": model, "native_sdk_calls": len(calls),
             "allocation_calls": 16, "model_calls": 0, "network_connections": 0,
             "native_activity": receipt["native_activity"],
             "dependency_freeze_sha256": sha(freeze), "preparation_sha256": sha(destination / "preparation.json"),
             "native_result_sha256": sha(destination / "output/native-result.json"),
             "fixture_result_not_research": True}
    write_json(destination / "conformance.json", proof)
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--dependencies", type=Path, required=True)
    parser.add_argument("--model", choices=MODELS, required=True)
    args = parser.parse_args()
    print(json.dumps(check(args.source, args.destination, args.dependencies, args.model)))


if __name__ == "__main__":
    main()
