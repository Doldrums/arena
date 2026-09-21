#!/usr/bin/env python3
"""Offline actual-SDK / pinned-native ADAS fixture. Never use a real provider."""
from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from arena.frameworks.drivers import adas_mgsm_gateway as pilot


def check(source, output, dataset_path):
    import httpx
    import openai
    from arena.frameworks.runtime import verify_source

    revision = verify_source(source.resolve(), pilot.SOURCE_COMMIT)

    if output.exists():
        raise ValueError("Choose a new fixture output")
    output.mkdir(parents=True)
    # This process has no real credential; all SDK calls use MockTransport.
    os.environ["OPENAI_API_KEY"] = "inert-adas-sdk-fixture"
    blocked = {"network": 0, "subprocess": 0}
    def deny_external(event, args):
        if event in {"socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system"}:
            blocked["subprocess" if event in {"subprocess.Popen", "os.system"} else "network"] += 1
            raise RuntimeError("Offline ADAS fixture forbids external operations")
    sys.addaudithook(deny_external)
    data = pilot.load_dataset(dataset_path)
    calls = []
    pair = pilot.load_native(source)
    native, utils = pair
    code = native.get_init_archive()[0]["code"] + "\n# inert SDK fixture candidate\n"
    active_model = pilot.MODELS[0]

    def handle(request):
        body = json.loads(request.content)
        assert body["model"] == active_model
        assert str(request.url) == pilot.GATEWAY + "/chat/completions"
        assert body["response_format"] == {"type": "json_object"}
        assert request.extensions["timeout"] == {key: 330 for key in ("connect", "read", "write", "pool")}
        system = body["messages"][0]["content"]
        if "Reply EXACTLY with the following JSON format." in system:
            role = "inner"
            fields = ast.literal_eval(re.search(r"JSON format\.\n(.*?)\nDO NOT", system, re.S).group(1))
            question_context = body["messages"][-1]["content"]
            matching = [row for rows in data["splits"].values() for row in rows if row["question"] in question_context]
            answer = matching[0]["answer"] if matching else "0"
            payload = {key: ({"answer": answer, "correct": "True", "choice": "Math Professor"}.get(key, "inert fixture")) for key in fields}
        else:
            role = "meta"
            payload = {"thought": "inert fixture, not a research result", "name": "Fixture candidate", "code": code}
        calls.append({"sequence": len(calls) + 1, "model": body["model"], "role": role,
                      "json_mode": body["response_format"]["type"],
                      "prompt_sha256": pilot.digest(json.dumps(body["messages"], ensure_ascii=False))})
        return httpx.Response(200, json={"id": "fixture-response", "object": "chat.completion", "created": 1,
                "model": body["model"], "choices": [{"index": 0, "finish_reason": "stop",
                "message": {"role": "assistant", "content": json.dumps(payload)}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})

    with openai.OpenAI(base_url=pilot.GATEWAY, api_key="inert-adas-sdk-fixture", timeout=330,
                       max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client:
        assert client.max_retries == 0
        args = SimpleNamespace(model=active_model, output=output / "native-full-cycle", dataset=dataset_path)
        assert pilot.run(args, native_pair=pair, client=client) == 0
        full_calls = len(calls)
        assert full_calls == 55
        events = [json.loads(line) for line in (args.output / "events.jsonl").read_text().splitlines()]
        completed = [event for event in events if event["type"] == "evaluation" and event["status"] == "completed"]
        assert len(completed) == 9
        assert [event["phase"] for event in completed] == ["optimization"] * 8 + ["heldout"]
        assert all(event["scores"] == [1, 1] for event in completed)
        archive = json.loads((args.output / "mgsm_run_archive.json").read_text())
        assert len(archive) == 8 and sum(item["generation"] == "initial" for item in archive) == 7
        freeze_index = next(index for index, event in enumerate(events) if event["type"] == "selection_frozen")
        assert all(event.get("phase") != "heldout" for event in events[:freeze_index])
        # All remaining IDs traverse actual native JSON functions and SDK
        # transport in both roles, without repeating the full bootstrap loop.
        for active_model in pilot.MODELS[1:]:
            native, utils = pilot.load_native(source)
            directory = output / active_model
            directory.mkdir()
            session = pilot.Session(directory, active_model, client.chat.completions.create)
            pilot.bind_native(native, utils, session, data)
            native.get_json_response_from_gpt_reflect([{"role": "system", "content": "inert meta fixture"}], active_model)
            row = data["splits"]["optimization"][0]
            info = native.Info("task", "User", utils.LANG_TO_INSTRUCTIONS[row["language"]].format(input=row["question"]), -1)
            response = native.LLMAgentBase(["thinking", "answer"], "Fixture agent")([info], "inert fixture")
            assert response[1].content == row["answer"]
    for model in pilot.MODELS:
        assert {call["role"] for call in calls if call["model"] == model} == {"meta", "inner"}
    failed_requests = []
    def fail_transport(request):
        failed_requests.append(1)
        return httpx.Response(503, json={"error": {"message": "inert provider failure", "type": "server_error"}})
    with openai.OpenAI(base_url=pilot.GATEWAY, api_key="inert-adas-sdk-fixture", timeout=330,
                       max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(fail_transport))) as client:
        failed_output = output / "provider-failure"
        args = SimpleNamespace(model=pilot.MODELS[0], output=failed_output, dataset=dataset_path)
        assert pilot.run(args, native_pair=pilot.load_native(source), client=client) == 1
        failure = json.loads((failed_output / "pilot-status.json").read_text())
        assert failure["reason"] == "provider_request_failed" and failure["completed_requests"] == 0
        assert len(failed_requests) == 1  # SDK and native backoff cannot retry.
        assert not (failed_output / "heldout.json").exists()
        assert not (failed_output / "selection.json").exists()
        failure_events = [json.loads(line) for line in (failed_output / "events.jsonl").read_text().splitlines()]
        assert not any(event.get("status") == "completed" and event["type"] == "evaluation" for event in failure_events)
    assert utils.score_mgsm("1,800", "1800.00") is True
    assert utils.score_mgsm("18", "answer: 18") is False
    proof = {"schema": "arena.adas-mgsm-offline-conformance/1", "source_commit": pilot.SOURCE_COMMIT,
             "source": revision, "uid": os.getuid(), "python_version": sys.version.split()[0],
             "source_hashes": pilot.SOURCE_HASHES, "dataset_sha256": pilot.DATASET_SHA256,
             "driver_sha256": pilot.digest(Path(pilot.__file__).read_bytes()),
             "openai_version": openai.__version__, "httpx_version": httpx.__version__,
             "models": list(pilot.MODELS), "mock_requests": len(calls), "full_cycle_mock_requests": full_calls,
             "mock_failure_requests": len(failed_requests), "provider_failure_aborts_without_retry_or_zero_fitness": True,
             "native_initial_strategies": 7, "native_meta_generations": 1,
             "native_evaluator_invocations": 9, "native_question_scores": 18,
             "native_bootstrap_samples_default": 100000, "selection_before_heldout": True,
             "sdk_timeout_seconds": 330, "sdk_max_retries": 0,
             "real_provider_requests": 0, "research_executed": False,
             "blocked_external_operations": blocked, "calls": calls,
             "note": "Known inert fixture code only; mock scores are not research evidence."}
    pilot.write_json(output / "proof.json", proof)
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=ROOT / "registry/datasets/mgsm-adas-pilot-v1.json")
    args = parser.parse_args()
    proof = check(args.source, args.output, args.dataset)
    print(json.dumps({"mock_requests": proof["mock_requests"], "real_provider_requests": 0,
                      "proof": str(args.output / "proof.json")}))


if __name__ == "__main__":
    main()
