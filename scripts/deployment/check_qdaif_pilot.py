#!/usr/bin/env python3
"""Offline real QDAIF loop + legacy OpenAI SDK; fixture transport, no network."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from arena.frameworks.drivers.qdaif_poetry_gateway import MODELS, run, preparation, sha
from arena.frameworks.drivers.qdaif_gateway_transport import ENDPOINT, GatewayTransport, QDAIFGatewayStopped, write_json


def check(source, destination, freeze, constraints, model):
    import requests
    if destination.exists():
        raise ValueError("Conformance destination must be new")
    destination.mkdir(parents=True)
    workspace = destination / "workspace"
    shutil.copytree(source, workspace, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    write_json(destination / "preparation.json", preparation(workspace, freeze, constraints))
    calls, poems = [], []
    quality = [6, 7, 8, 5, 9, 4, 7, 10]
    class FixtureSession(requests.Session):
        def request(self, method, url, **kwargs):
            body = json.loads(kwargs["data"])
            assert method.lower() == "post" and url == ENDPOINT + "/chat/completions"
            assert body["model"] == model and body["stream"] is False
            assert kwargs["allow_redirects"] is False and kwargs["timeout"] == 330
            prompt = body["messages"][0]["content"]
            if "Rate the quality of the above poem" in prompt:
                kind = "quality"
                index = int(re.search(r"Fixture poem (\d+)", prompt).group(1))
                content = json.dumps({"quality": quality[index]})
            elif "What genre is this poem closest to" in prompt:
                kind = "diversity"
                index = int(re.search(r"Fixture poem (\d+)", prompt).group(1))
                content = json.dumps({"genre": ["haiku", "sonnet"][index % 2],
                                      "tone": ["happy", "dark"][index % 2]})
            else:
                kind = "generation"
                if len(poems) < 2:
                    assert "Fields of green waves under" in prompt and "Write a " in prompt
                else:
                    assert "Translate this " in prompt and any(poem in prompt for poem in poems)
                content = f"Fixture poem {len(poems)}\nOffline protocol evidence only."
                poems.append(content)
            calls.append({"model": model, "kind": kind, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()})
            response = requests.Response()
            response.status_code = 200
            response._content = json.dumps({"id": "inert-qdaif-fixture", "object": "chat.completion",
                "created": 0, "model": model, "choices": [{"index": 0, "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}).encode()
            response.headers["content-type"] = "application/json"
            return response
    def blocked_network(*args, **kwargs):
        raise AssertionError("Offline QDAIF conformance must not connect")
    socket.socket.connect = blocked_network
    socket.create_connection = blocked_network
    os.environ["OPENAI_API_KEY"] = "offline-fixture"
    receipt = run(workspace, model, destination / "output", destination / "preparation.json", freeze, constraints, session=FixtureSession())
    assert receipt["status"] == "completed"
    assert [sum(c["kind"] == kind for c in calls) for kind in ("generation", "quality", "diversity")] == [8, 8, 8]
    state = json.loads((destination / "output/native-result.json").read_text())
    assert state["niches_filled"] == 2 and state["qd_score"] == 19 and state["max_fitness"] == 10
    assert sorted(a["fitness"] for a in state["archive"]) == [9, 10]
    assert sum(len(row["candidates"]) for row in state["history"]) == 8
    assert state["fitness_history"]["max"] == [7, 8, 9, 10]
    # Exercise upstream malformed/out-of-range judgment semantics without an
    # API call. These assertions do not repair or substitute native evaluation.
    from openelm.environments.poetry import PoetryGenotype
    from types import SimpleNamespace
    answers = iter(["not-json", '{"genre":"haiku","tone":"happy"}'])
    invalid = PoetryGenotype("inert malformed fixture")
    assert invalid.evaluate(lambda _: SimpleNamespace(content=next(answers))) == float("-inf")
    answers = iter(['{"quality":11}', '{"genre":"haiku","tone":"happy"}'])
    raw = PoetryGenotype("inert unclamped fixture")
    assert raw.evaluate(lambda _: SimpleNamespace(content=next(answers))) == 11
    proof = {"schema": "arena.qdaif-offline-conformance/1", "model": model,
        "native_sdk_http_attempts": len(calls), "generated_poems": 8, "native_judgments": 16,
        "native_archive_cells": 2, "native_mutation_iterations": 3,
        "native_malformed_json_preserved": True, "native_unclamped_quality_preserved": True,
        "model_calls": 0, "network_connections": 0, "fixture_result_not_research": True,
        "dependency_freeze_sha256": sha(freeze), "preparation_sha256": sha(destination / "preparation.json"),
        "native_result_sha256": sha(destination / "output/native-result.json")}
    write_json(destination / "conformance.json", proof)
    return proof


def check_sdk_budget(destination, model):
    import requests
    if destination.exists():
        raise ValueError("Conformance destination must be new")
    destination.mkdir(parents=True)
    calls = []
    class WarmingSession(requests.Session):
        def request(self, method, url, **kwargs):
            assert json.loads(kwargs["data"])["model"] == model
            calls.append(1)
            response = requests.Response()
            response.status_code = 409
            response._content = b'{"error":{"message":"offline warming fixture","type":"fixture","code":null}}'
            response.headers["content-type"] = "application/json"
            return response
    def blocked_network(*args, **kwargs):
        raise AssertionError("Offline SDK budget check must not connect")
    socket.socket.connect = blocked_network
    socket.create_connection = blocked_network
    os.environ["OPENAI_API_KEY"] = "offline-fixture"
    transport = GatewayTransport(model, destination, session=WarmingSession())
    try:
        transport.complete("offline warmup retry fixture")
    except QDAIFGatewayStopped:
        pass
    else:
        raise AssertionError("Legacy SDK retry loop did not stop")
    assert len(calls) == 24 and len(transport.records) == 24
    proof = {"schema":"arena.qdaif-sdk-budget-conformance/1", "model":model,
        "actual_legacy_sdk_http409_attempts":len(calls), "budget_stop_verified":True,
        "model_calls":0, "network_connections":0}
    write_json(destination / "budget-conformance.json", proof)
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--dependencies", type=Path, required=True)
    parser.add_argument("--constraints", type=Path, required=True)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--sdk-budget-only", action="store_true")
    args = parser.parse_args()
    result = check_sdk_budget(args.destination, args.model) if args.sdk_budget_only else check(
        args.source, args.destination, args.dependencies, args.constraints, args.model)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
