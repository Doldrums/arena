#!/usr/bin/env python3
"""Native constructor/parser/SDK fixtures for GEPA or MIPROv2, with no network."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from arena.frameworks.drivers import _gsm8k_pilot as common


def check(framework, source, dataset_path, output):
    from arena.frameworks.recipes import load_recipes
    from arena.frameworks.runtime import verify_source
    recipe_id = "gepa-gateway-gsm8k" if framework == "gepa" else "miprov2-gateway-gsm8k"
    revision = verify_source(source, load_recipes()[recipe_id]["repository"]["commit"])
    dataset = common.load_dataset(dataset_path)
    if not output.is_absolute() or output.exists():
        raise ValueError("Use a new absolute conformance output directory")
    output.mkdir(mode=0o750)
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
    os.environ["DSPY_CACHEDIR"] = str(output / "dspy-cache")
    def deny_network(event, arguments):
        if event in {"socket.connect", "socket.sendto"}:
            raise RuntimeError("Network is denied in this fixed-response fixture")
    sys.addaudithook(deny_network)
    sys.path[:0] = [str(source), str(source / "src")]
    os.environ["OPENAI_API_KEY"] = "inert-prompt-fixture-key"
    import openai
    from openai import _base_client
    # The two frozen environments resolve SDK versions using different HTTP
    # packages; attach the transport to the actual installed SDK dependency.
    httpx = getattr(_base_client, "httpx", None) or _base_client.httpx2
    calls, clients, records = [], [], []
    response_text = [""]
    def respond(request):
        assert str(request.url) == common.ENDPOINT + "/chat/completions"
        assert request.headers["authorization"] == "Bearer inert-prompt-fixture-key"
        body = json.loads(request.content)
        assert body["model"] in common.MODELS and body["n"] == 1 and body["stream"] is False
        calls.append(body)
        return httpx.Response(200, json={"id": "fixture-" + str(len(calls)), "object": "chat.completion",
            "created": 1, "model": body["model"],
            "choices": [{"index": 0, "message": {"role": "assistant", "content": response_text[0]}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5}})
    heldout_questions = {r["question"] for r in dataset["selected_records"]["heldout"]}
    for model in common.MODELS:
        client = openai.OpenAI(api_key="inert-prompt-fixture-key", base_url=common.ENDPOINT,
                              timeout=180, max_retries=0,
                              http_client=httpx.Client(transport=httpx.MockTransport(respond)))
        clients.append(client)
        transport = common.GatewayTransport(model, client=client)
        expected = common.extract_answer(dataset["selected_records"]["train"][0]["answer"])
        before = len(calls)
        if framework == "gepa":
            from arena.frameworks.drivers.gepa_gateway_pilot import build_native
            from gepa.strategies.instruction_proposal import InstructionProposalSignature
            kwargs = build_native(dataset, transport, output / model)
            assert kwargs["max_metric_calls"] == 24
            assert len(kwargs["trainset"]) == len(kwargs["valset"]) == 8
            assert not heldout_questions.intersection(x["input"] for x in kwargs["trainset"] + kwargs["valset"])
            row = kwargs["trainset"][0]
            response_text[0] = "Fixture answer.\n#### " + expected
            batch = kwargs["adapter"].evaluate([row], kwargs["seed_candidate"], capture_traces=True)
            assert batch.scores == [1.0] and batch.trajectories
            response_text[0] = "#### -987654321"
            assert kwargs["adapter"].evaluate([row], kwargs["seed_candidate"]).scores == [0.0]
            response_text[0] = "```\nA fixed fixture instruction.\n```"
            parsed = InstructionProposalSignature.run(kwargs["reflection_lm"], {
                "current_instruction_doc": common.SEED,
                "dataset_with_feedback": [{"Inputs": row["input"], "Feedback": "Fixture feedback"}],
                "prompt_template": None})
            assert parsed == {"new_instruction": "A fixed fixture instruction."}
        else:
            import dspy
            from arena.frameworks.drivers.mipro_gateway_pilot import build_native
            lm, optimizer, kwargs = build_native(dataset, transport, output / model)
            assert optimizer.num_threads == 1 and optimizer.num_candidates == 3
            assert kwargs["num_trials"] == 3 and kwargs["minibatch"] is False
            assert len(kwargs["trainset"]) == len(kwargs["valset"]) == 8
            assert not heldout_questions.intersection(x.question for x in kwargs["trainset"] + kwargs["valset"])
            response_text[0] = "[[ ## reasoning ## ]]\nFixed fixture reasoning.\n[[ ## answer ## ]]\n#### " + expected + "\n[[ ## completed ## ]]"
            with dspy.context(lm=lm):
                prediction = kwargs["student"](question=kwargs["trainset"][0].question)
            assert optimizer.metric(kwargs["trainset"][0], prediction) is True
            assert optimizer.metric(kwargs["trainset"][0], dspy.Prediction(answer="#### -987654321")) is False
            outputs = lm(messages=[{"role": "user", "content": "Fixed two-choice fixture"}], n=2)
            assert outputs == [response_text[0], response_text[0]]
            copy = kwargs["student"].deepcopy()
            assert copy.get_lm().transport is transport
            saved = output / (model + ".program.json")
            copy.save(str(saved), save_program=False)
            assert "inert-prompt-fixture-key" not in saved.read_text()
        records.append({"model": model, "native_fixture_requests": len(calls) - before})
    for client in clients:
        client.close()
    proof = {"schema": "arena.prompt-gateway-conformance/1", "framework": framework, "source": revision,
             "dataset_sha256": common.DATASET_SHA256, "records": records, "network": "denied",
             "native_optimizer_executed": False, "model_calls": 0, "research_executed": False,
             "scope": "Actual native SDK, parser, supplied official metric and optimizer constructors with fixed mock HTTP responses; not optimization or scientific results."}
    common.write_json(output / "conformance.json", proof)
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--framework", choices=["gepa", "mipro"], required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(check(args.framework, args.source, args.dataset, args.output), indent=2))


if __name__ == "__main__":
    main()
