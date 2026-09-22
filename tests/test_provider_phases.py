"""Inert Responses fixtures verify phase projection without provider requests."""
import json

import pytest

from arena.provider_protocol import chat_completion
from arena.providers import ProviderError, parse_sse
from test_providers import MODEL, Transport, call, chat, completion, gateway


def message(text, phase="final_answer", **extra):
    return {"id": "msg-" + str(phase), "type": "message", "role": "assistant", "status": "completed",
            "phase": phase, "content": [{"type": "output_text", "text": text}], **extra}


def terminal(output):
    result = completion()
    result["response"]["output"] = output
    return result


def project(output):
    return chat_completion(terminal(output)["response"], MODEL, "fixture", {})["choices"][0]


def phased_events(*, empty_terminal=False, output=None):
    output = output or [message('{"action":"create"}', "commentary"), message('{"action":"finish"}')]
    rows = []
    for index, item in enumerate(output):
        rows.append({"type": "response.output_item.added", "output_index": index,
                     "item": {**item, "status": "in_progress"}})
        if item["type"] == "message":
            for part in item["content"]:
                if part["type"] == "output_text":
                    rows.append({"type": "response.output_text.delta", "output_index": index, "delta": part["text"]})
        rows.append({"type": "response.output_item.done", "output_index": index, "item": item})
    rows.append(terminal([] if empty_terminal else output))
    return rows


def streamed_message(raw):
    events = list(parse_sse([raw]))
    assert events[-1] is None
    message = {"role": "assistant", "content": None}
    content, refusal, calls = [], [], []
    for event in events[:-1]:
        for choice in event["choices"]:
            delta = choice["delta"]
            content.append(delta.get("content", ""))
            refusal.append(delta.get("refusal", ""))
            calls.extend({key: value for key, value in item.items() if key != "index"}
                         for item in delta.get("tool_calls", []))
    message["content"] = "".join(content) or None
    if any(refusal):
        message["refusal"] = "".join(refusal)
    if calls:
        message["tool_calls"] = calls
    return message, events[-2]["usage"], events[-3]["choices"][0]["finish_reason"]


@pytest.mark.parametrize("empty_terminal", [False, True])
def test_phased_json_chat_stream_and_nonstream_are_identical_without_commentary(empty_terminal):
    results = []
    for stream in (False, True):
        transport = Transport(phased_events(empty_terminal=empty_terminal))
        with gateway(transport) as (server, _, audits):
            status, _, raw = call(server, body=chat(stream=stream, stream_options={"include_usage": True}))
        assert status == 200 and b'\\"action\\":\\"create\\"' not in raw
        assert len(transport.seen) == 1
        assert audits[0]["usage"] == {"input_tokens": 9, "output_tokens": 2, "total_tokens": 11}
        if stream:
            projected, usage, finish = streamed_message(raw)
        else:
            data = json.loads(raw)
            projected, usage, finish = data["choices"][0]["message"], data["usage"], data["choices"][0]["finish_reason"]
        assert json.loads(projected["content"]) == {"action": "finish"}
        results.append((projected, usage, finish))
    assert results[0] == results[1]


@pytest.mark.parametrize("stream", [False, True])
def test_responses_output_phases_and_replayed_input_are_unchanged(stream):
    rows = phased_events(empty_terminal=True)
    inputs = [message("prior commentary", "commentary"), message("prior final"),
              {"role": "user", "content": "inert next request"}]
    transport = Transport(rows)
    with gateway(transport) as (server, _, _):
        status, _, raw = call(server, "/v1/responses", {"model": MODEL, "input": inputs, "stream": stream})
    assert status == 200
    result = list(parse_sse([raw]))[-1]["response"] if stream else json.loads(raw)
    assert result["output"] == [row["item"] for row in rows if row["type"] == "response.output_item.done"]
    assert transport.seen[0]["input"] == inputs


@pytest.mark.parametrize("phase", [None, "final_answer"])
def test_selected_refusal_preserved(phase):
    item = message("", phase, content=[{"type": "refusal", "refusal": "Inert refusal."}])
    result = project([item])
    assert result["message"] == {"role": "assistant", "content": None, "refusal": "Inert refusal."}
    assert result["finish_reason"] == "stop"


def test_legacy_single_message_without_role_or_status_supported():
    result = project([{"type": "message", "content": [{"type": "output_text", "text": "legacy"}]}])
    assert result["message"]["content"] == "legacy"


@pytest.mark.parametrize("stream", [False, True])
def test_real_function_calls_and_final_refusal_survive_phase_projection(stream):
    function = {"type": "function_call", "id": "fc-1", "call_id": "call-1", "name": "measure",
                "arguments": '{"inert": 1}', "status": "completed"}
    output = [message("PRIVATE-COMMENTARY", "commentary"), function,
              message("", content=[{"type": "refusal", "refusal": "Inert refusal."}])]
    transport = Transport(phased_events(output=output, empty_terminal=True))
    with gateway(transport) as (server, _, _):
        status, _, raw = call(server, body=chat(stream=stream, stream_options={"include_usage": True}))
    assert status == 200 and b"PRIVATE-COMMENTARY" not in raw
    if stream:
        projected, usage, finish = streamed_message(raw)
    else:
        result = json.loads(raw)
        projected, finish = result["choices"][0]["message"], result["choices"][0]["finish_reason"]
    assert finish == "tool_calls" and projected["refusal"] == "Inert refusal."
    assert projected["content"] is None
    assert projected["tool_calls"] == [{"id": "call-1", "type": "function",
                                      "function": {"name": "measure", "arguments": '{"inert": 1}'}}]


def test_commentary_with_real_function_call_is_valid_tool_only_turn():
    result = project([message("tool preamble", "commentary"), {"type": "function_call", "call_id": "call-1",
                      "name": "measure", "arguments": "{}"}])
    assert result["message"]["content"] is None
    assert result["finish_reason"] == "tool_calls"


def test_duplicate_function_identity_fails_instead_of_replaying_a_call():
    function = {"type": "function_call", "call_id": "call-1", "name": "measure", "arguments": "{}"}
    with pytest.raises(ProviderError) as error:
        project([function, dict(function)])
    assert error.value.code == "ambiguous_chat_output" and error.value.status == 502


AMBIGUOUS = [
    [message("one"), message("two")],
    [message("one", None), message("two", None)],
    [message("one"), message("two", None)],
    [message("preamble", "commentary"), message("unknown role", None)],
    [message("unknown phase", "analysis")],
    [message("", "commentary", content=[{"type": "refusal", "refusal": "PRIVATE-REFUSAL"}]), message("answer")],
]


@pytest.mark.parametrize("output", AMBIGUOUS)
@pytest.mark.parametrize("stream", [False, True])
def test_ambiguous_phase_projection_is_typed_failure_and_never_leaks_text(output, stream):
    transport = Transport(phased_events(output=output))
    with gateway(transport) as (server, _, audits):
        status, _, raw = call(server, body=chat(stream=stream))
    assert status == (200 if stream else 502)
    assert b'"code": "ambiguous_chat_output"' in raw
    assert b"PRIVATE-REFUSAL" not in raw and b"[DONE]" not in raw
    if stream:
        events = list(parse_sse([raw]))
        assert not any(choice["delta"].get("content") for event in events if "choices" in event for choice in event["choices"])
    assert audits[0]["status"] == 502 and audits[0]["error_code"] == "ambiguous_chat_output"
    assert audits[0]["usage"]["total_tokens"] == 11
    assert len(transport.seen) == 1


@pytest.mark.parametrize("output,code", [
    ([message("only commentary", "commentary")], "missing_final_message"),
    ([message("incomplete", status="in_progress")], "invalid_chat_output"),
    ([message("missing status", status=None)], "invalid_chat_output"),
    ([message("wrong role", role="user")], "invalid_chat_output"),
    ([message("legacy incomplete", None, status="incomplete")], "invalid_chat_output"),
    ([{"type": "function_call", "call_id": "call-1", "name": "measure"}], "invalid_chat_output"),
])
def test_missing_final_or_invalid_item_is_sanitized(output, code):
    with pytest.raises(ProviderError) as error:
        project(output)
    assert error.value.status == 502 and error.value.code == code
    assert "only commentary" not in str(error.value)


def test_uncommitted_commentary_and_function_arguments_are_never_streamed():
    rows = [
        {"type": "response.output_text.delta", "delta": "PRIVATE-COMMENTARY"},
        {"type": "response.output_item.added", "output_index": 1,
         "item": {"type": "function_call", "call_id": "call-1", "name": "measure", "arguments": ""}},
        {"type": "response.function_call_arguments.delta", "output_index": 1, "delta": "PRIVATE-ARGUMENTS"},
        {"type": "error", "message": "private fixture error"},
    ]
    with gateway(Transport(rows)) as (server, _, audits):
        status, _, raw = call(server, body=chat(stream=True))
    assert status == 200 and audits[0]["status"] == 502
    assert b"PRIVATE-" not in raw and b'"tool_calls"' not in raw and b"[DONE]" not in raw
