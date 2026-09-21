#!/usr/bin/env python3
"""Actual native SDK/parser and fixed geometry fixtures, with all network denied."""
from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from arena.frameworks.drivers import darwinian_gateway as driver
from arena.providers import anthropic_to_chat, normalize_request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("/srv/arena/sources/darwinian-evolver"))
    args = parser.parse_args()
    driver.verify_source(args.source)
    def deny_network(event, arguments):
        if event in {"socket.connect", "socket.sendto"}:
            raise RuntimeError("Network is disabled in this inert fixture")
    sys.addaudithook(deny_network)
    sys.path.insert(0, str(args.source))
    os.environ["OPENAI_API_KEY"] = "inert-darwinian-fixture"
    import anthropic
    import httpx2 as httpx  # Transport package used by the frozen native Anthropic SDK.
    import numpy as np
    from darwinian_evolver.problems import circle_packing as problem
    cli = importlib.import_module("darwinian_evolver.__main__")
    original = anthropic.Anthropic
    calls = []

    def response(request):
        assert str(request.url) == driver.ENDPOINT + "/v1/messages"
        assert request.headers["x-api-key"] == "inert-darwinian-fixture"
        body = json.loads(request.content)
        normalized, compatibility = normalize_request(anthropic_to_chat(body), chat=True, policy="codex-native")
        assert normalized["model"] in driver.MODELS
        assert body["system"] == "fixture-system" and body["messages"][0]["content"] == "fixture-user"
        calls.append(body["model"])
        return httpx.Response(200, json={"id": "msg_fixture", "type": "message", "role": "assistant",
            "content": [{"type": "text", "text": "fixture-text"}], "model": body["model"],
            "stop_reason": "end_turn", "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1}})

    clients = []
    def constructor(**kwargs):
        client = original(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(response)))
        clients.append(client)
        return client
    anthropic.Anthropic = constructor
    try:
        for model in driver.MODELS:
            driver.bind_provider(problem, model)
            assert problem._prompt_llm("fixture-system", "fixture-user") == "fixture-text"
            sys.argv = ["darwinian_evolver", *driver.native_arguments(4, Path("/unused-fixture-output"))]
            parsed = cli.parse_args()
            assert parsed.problem == "circle_packing" and parsed.evaluator_concurrency == parsed.mutator_concurrency == 1
            config = cli.build_hyperparameter_config_from_args(parsed)
            assert config.learning_log_view_type == "ancestors" and config.num_parents_per_iteration == 1
            native = problem.make_circle_packing_problem()
            assert type(native.evaluator) is problem.CirclePackingEvaluator and len(native.mutators) == 1
        # Geometry-only fixtures; no candidate Python execution or optimizer loop.
        centers = np.array([(.1 + .16 * (i % 6), .1 + .18 * (i // 6)) for i in range(26)])
        radii = np.full(26, .04)
        assert native.evaluator._validate_packing((centers, radii, float(radii.sum())))[0]
        centers[1] = centers[0]
        assert not native.evaluator._validate_packing((centers, radii, float(radii.sum())))[0]
        assert calls == list(driver.MODELS)
        print(json.dumps({"native_sdk_fixture_requests": len(calls), "models": calls,
            "native_cli_and_problem_constructors": "passed", "native_geometry_fixtures": 2,
            "native_problem_sha256": driver.PROBLEM_SHA256, "network": "denied",
            "model_calls": 0, "generated_candidate_execution": False, "research_executed": False}))
    finally:
        anthropic.Anthropic = original
        for client in clients: client.close()


if __name__ == "__main__":
    main()
