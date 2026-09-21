"""Private provider bridge tests use only inert fixture transports and local sockets."""
import base64
from contextlib import contextmanager
import http.client
import json
import os
from pathlib import Path
import threading
import time

import pytest

from arena.providers import (CodexTransport, GatewayServer, ProviderBridge, ProviderError,
                             TokenSource, create_gateway_key, normalize_request, parse_sse,
                             read_gateway_key)

KEY = "fixture-local-key-" + "x" * 40
MODEL = "fixture-model"


def completion(text="answer", calls=None):
    output = [{"type": "message", "content": [{"type": "output_text", "text": text}]}] if text else []
    output.extend(calls or [])
    return {"type": "response.completed", "response": {"id": "resp-fixture", "status": "completed", "model": MODEL,
            "output": output, "usage": {"input_tokens": 9, "output_tokens": 2, "total_tokens": 11}}}


class Transport:
    def __init__(self, events=None):
        self.seen = []
        self.rows = events if events is not None else [completion()]

    def models(self):
        return {"models": [{"slug": MODEL, "visibility": "list", "supported_in_api": True},
                           {"slug": "hidden-model", "visibility": "hide", "supported_in_api": True},
                           {"slug": "unavailable", "supported_in_api": False}]}

    def events(self, payload):
        self.seen.append(payload)
        for event in self.rows:
            if isinstance(event, Exception):
                raise event
            yield event


@contextmanager
def gateway(transport=None, **kwargs):
    audits = []
    audit_condition = threading.Condition()
    def audit(record):
        with audit_condition:
            audits.append(record)
            audit_condition.notify_all()
    bridge = ProviderBridge(transport or Transport(), audit=audit, **kwargs)
    server = GatewayServer(("127.0.0.1", 0), bridge, KEY)
    server.fixture_audits = audits
    server.fixture_audit_condition = audit_condition
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, bridge, audits
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def call(server, path="/v1/chat/completions", body=None, key=KEY, headers=None):
    conn = http.client.HTTPConnection(*server.server_address, timeout=3)
    kwargs = {"Authorization": "Bearer " + key, "Content-Type": "application/json", **(headers or {})}
    raw = None if body is None else json.dumps(body)
    with server.fixture_audit_condition:
        previous_audits = len(server.fixture_audits)
    conn.request("GET" if body is None else "POST", path, raw, kwargs)
    response = conn.getresponse()
    result = response.status, dict(response.headers), response.read()
    conn.close()
    if body is not None:
        # Response bytes can reach the client before the handler's finally
        # block appends its audit. Synchronize on that event, not scheduling.
        with server.fixture_audit_condition:
            assert server.fixture_audit_condition.wait_for(
                lambda: len(server.fixture_audits) > previous_audits, timeout=3
            ), "POST handler did not publish its final audit record"
    return result


def chat(**extra):
    return {"model": MODEL, "messages": [{"role": "user", "content": "private fixture prompt"}], **extra}


@pytest.mark.parametrize("route,stream", [("/v1/chat/completions",False),("/v1/chat/completions",True),("/v1/responses",False),("/v1/responses",True)])
def test_account_backend_empty_terminal_output_reconstructs_done_items_without_account_metadata(route, stream):
    item={"id":"msg-fixture","type":"message","role":"assistant","status":"completed",
          "content":[{"type":"output_text","text":"READY"}]}
    terminal=completion("")
    terminal["response"].update(safety_identifier="PRIVATE-ACCOUNT",prompt_cache_key="PRIVATE-CACHE",instructions="PRIVATE-INSTRUCTIONS")
    terminal["response"]["usage"]["attribution"]={"PRIVATE-ATTRIBUTION": {}}
    transport=Transport([{"type":"response.created","response":{**terminal["response"],"status":"in_progress"}},
                         {"type":"response.output_text.delta","output_index":0,"delta":"READY"},
                         {"type":"response.output_item.done","output_index":0,"item":item},terminal])
    body=chat(stream=stream) if route.endswith("completions") else {"model":MODEL,"input":"test","stream":stream}
    with gateway(transport) as (server,bridge,audits):
        status,headers,raw=call(server,route,body)
    assert status==200
    assert b"READY" in raw
    assert b"PRIVATE-" not in raw
    if not stream:
        value=json.loads(raw)
        if route.endswith("completions"):
            assert value["choices"][0]["message"]["content"]=="READY"
        else:
            assert value["output"]==[item]


def test_tool_calls_are_reconstructed_from_done_events_with_empty_terminal_output():
    item={"type":"function_call","id":"fc-fixture","call_id":"call-fixture","name":"evaluate","arguments":'{"x":1}'}
    transport=Transport([{"type":"response.output_item.done","output_index":0,"item":item},completion("")])
    with gateway(transport) as (server,bridge,audits):
        status,headers,raw=call(server,body=chat())
    message=json.loads(raw)["choices"][0]["message"]
    assert status==200 and message["tool_calls"][0]["function"]["arguments"]=='{"x":1}'


def test_uncommitted_deltas_are_not_reported_as_successful_empty_response():
    transport=Transport([{"type":"response.output_text.delta","delta":"partial"},completion("")])
    with gateway(transport) as (server,bridge,audits):
        status,headers,raw=call(server,body=chat())
    assert status==502 and json.loads(raw)["error"]["code"]=="missing_output_items"


def test_token_file_is_private_expiry_is_checked_without_exposing_claims(tmp_path):
    claims = {"exp": time.time() + 3600, "https://api.openai.com/auth": {"chatgpt_account_id": "private-account-fixture"}}
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    token = "eyJhbGciOiJmaXh0dXJlIn0." + payload + ".fixtureSignature"
    file = tmp_path / "credential"
    file.write_text(token)
    file.chmod(0o600)
    headers, expiry = TokenSource(file).read()
    assert headers["Authorization"] == "Bearer " + token and expiry == claims["exp"]
    assert headers["ChatGPT-Account-Id"] == "private-account-fixture"
    file.chmod(0o644)
    with pytest.raises(ProviderError) as exc:
        TokenSource(file).read()
    assert token not in str(exc.value) and "private-account-fixture" not in str(exc.value)
    file.chmod(0o600)
    claims["exp"] = 1
    file.write_text("eyJhbGciOiJmaXh0dXJlIn0." + base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=") + ".sig")
    with pytest.raises(ProviderError, match="expired"):
        TokenSource(file).read()


def test_gateway_key_creation_does_not_overwrite_or_accept_jwt(tmp_path, capsys):
    file = tmp_path / "gateway-key"
    create_gateway_key(file)
    assert len(read_gateway_key(file)) >= 32
    assert file.stat().st_mode & 0o777 == 0o600
    assert capsys.readouterr().out == ""
    with pytest.raises(FileExistsError):
        create_gateway_key(file)
    file.write_text("eyJfixture.claims.signature")
    with pytest.raises(ProviderError):
        read_gateway_key(file)


def test_sse_fragments_crlf_multiline_unicode_and_comments():
    raw = ': ping\r\nevent: response.output_text.delta\r\ndata: {"type":"response.output_text.delta",\r\ndata: "delta":"é"}\r\n\r\ndata: [DONE]\n\n'.encode()
    assert list(parse_sse([raw[i:i + 1] for i in range(len(raw))])) == [{"type": "response.output_text.delta", "delta": "é"}, None]


@pytest.mark.parametrize("raw", [b'data: {"x":1,"x":2}\n\n', b'data: {"x":NaN}\n\n', b'data: {"x":1}', b'data: \xff\n\n'])
def test_invalid_or_truncated_sse_fails(raw):
    with pytest.raises(ProviderError):
        list(parse_sse([raw]))


def test_sse_limits_bound_both_events_and_whole_response():
    with pytest.raises(ProviderError):
        list(parse_sse([b"data:" + b"x" * 40], event_limit=20))
    with pytest.raises(ProviderError):
        list(parse_sse([b":1234\n\n"] * 10, event_limit=100, total_limit=20))


def test_chat_roles_tools_and_json_schema_translate_without_model_rewrite():
    body = chat(messages=[{"role": "system", "content": "system instruction"},
        {"role": "user", "content": [{"type": "text", "text": "question"}]},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "call-1", "type": "function", "function": {"name": "measure", "arguments": '{"x":1}'}}]},
        {"role": "tool", "tool_call_id": "call-1", "content": '{"result":2}'}],
        tools=[{"type": "function", "function": {"name": "measure", "parameters": {"type": "object"}}}],
        tool_choice={"type": "function", "function": {"name": "measure"}},
        reasoning_effort="low", response_format={"type": "json_schema", "json_schema": {"name": "test", "schema": {"type": "object"}, "strict": True}})
    payload, compatibility = normalize_request(body, chat=True)
    assert payload["model"] == MODEL and payload["stream"] is True and payload["store"] is False
    assert payload["instructions"] == "system instruction"
    assert payload["input"][-2] == {"type": "function_call", "call_id": "call-1", "name": "measure", "arguments": '{"x":1}'}
    assert payload["input"][-1]["type"] == "function_call_output"
    assert payload["tools"][0]["name"] == "measure" and payload["reasoning"] == {"effort": "low"}
    assert payload["text"]["format"]["strict"] is True
    assert compatibility["unenforced_controls"] == []


@pytest.mark.parametrize("extra", [{"n":2}, {"n":True}, {"store":True}, {"stream":"true"}, {"stream_options":True},
    {"messages":[{"role":"assistant","tool_calls":[None]}]}, {"response_format":{"type":"json_schema","json_schema":7}},
    {"previous_response_id":"unknown"}])
def test_invalid_client_shapes_fail_before_any_provider_call(extra):
    with pytest.raises(ProviderError) as exc:
        normalize_request(chat(**extra), chat=True)
    assert exc.value.status == 400


def test_compatibility_controls_require_explicit_opt_in_and_report_unenforced_cap():
    body = chat(max_tokens=8192, temperature=1, top_p=.9, stop=["END"])
    with pytest.raises(ProviderError) as exc:
        normalize_request(body, chat=True)
    assert exc.value.code == "unsupported_generation_controls"
    payload, compatibility = normalize_request(body, chat=True, policy="codex-native")
    assert not {"temperature", "max_tokens", "top_p", "stop"} & payload.keys()
    assert compatibility == {"policy": "codex-native", "unenforced_controls": ["max_tokens", "stop", "temperature", "top_p"], "compute_cap_enforced": False}


def test_models_require_local_key_and_never_leak_account_data():
    with gateway() as (server, bridge, audits):
        assert call(server, "/v1/models", key="wrong")[0] == 401
        status, headers, body = call(server, "/v1/models")
        data = json.loads(body)
        assert status == 200 and headers["Cache-Control"] == "no-store"
        assert [item["id"] for item in data["data"]] == [MODEL, "hidden-model"]
        assert all(item["generation_verified"] is False for item in data["data"])
        assert call(server, "/v1/models", headers={"Origin":"https://untrusted.example"})[0] == 403
        assert not audits
    with pytest.raises(ValueError, match="loopback"):
        GatewayServer(("0.0.0.0", 1), ProviderBridge(Transport()), KEY)


def test_http_chat_response_usage_and_metadata_only_audit():
    transport = Transport()
    with gateway(transport, policy="codex-native") as (server, bridge, audits):
        status, headers, raw = call(server, body=chat(max_tokens=8192))
        data = json.loads(raw)
        assert status == 200 and headers["X-Arena-Unenforced-Controls"] == "max_tokens"
        assert data["choices"][0]["message"]["content"] == "answer"
        assert data["usage"] == {"prompt_tokens": 9, "completion_tokens": 2, "total_tokens": 11}
        assert transport.seen[0]["model"] == MODEL and "max_tokens" not in transport.seen[0]
        assert audits and set(audits[0]) == {"request_id", "model", "usage", "status"}
        assert "private fixture prompt" not in json.dumps(audits) and "answer" not in json.dumps(audits) and KEY not in json.dumps(audits)


def test_unavailable_model_is_not_substituted_and_invalid_requests_never_generate():
    transport = Transport()
    with gateway(transport) as (server, bridge, audits):
        assert call(server, body=chat(model="not-available"))[0] == 400
        assert call(server, body=chat(temperature=1))[0] == 400
        assert transport.seen == []
        assert audits[0]["model"] is None


def test_chat_stream_text_function_argument_deltas_usage_and_terminal():
    fn={"type":"function_call","call_id":"call-1","name":"measure","arguments":'{"x":1}'}
    transport=Transport([
        {"type":"response.created","response":{"id":"resp-fixture","status":"in_progress"}},
        {"type":"response.output_text.delta","delta":"ans"},
        {"type":"response.output_item.added","output_index":1,"item":{**fn,"arguments":""}},
        {"type":"response.function_call_arguments.delta","output_index":1,"delta":'{"x":'},
        completion("answer",[fn]),
    ])
    with gateway(transport) as (server,bridge,audits):
        status,headers,raw=call(server,body=chat(stream=True,stream_options={"include_usage":True}))
        assert status==200 and headers["Content-Type"]=="text/event-stream"
        events=list(parse_sse([raw]))
        assert events[-1] is None
        assert ''.join(e["choices"][0]["delta"].get("content","") for e in events[:-1] if e["choices"])=="answer"
        deltas=[e["choices"][0]["delta"]["tool_calls"][0] for e in events[:-1] if e["choices"] and "tool_calls" in e["choices"][0]["delta"]]
        assert ''.join(d["function"].get("arguments","") for d in deltas)=='{"x":1}'
        assert events[-3]["choices"][0]["finish_reason"]=="tool_calls"
        assert events[-2]["usage"]["completion_tokens"]==2


@pytest.mark.parametrize("stream",[False,True])
def test_responses_endpoint_preserves_native_completed_structure(stream):
    with gateway() as (server,bridge,audits):
        status,headers,raw=call(server,"/v1/responses",{"model":MODEL,"input":"tiny input","stream":stream})
        assert status==200
        data=list(parse_sse([raw]))[-1]["response"] if stream else json.loads(raw)
        assert data["status"]=="completed" and data["id"]=="resp-fixture"
        assert data["arena_compatibility"]["policy"]=="strict"
        assert bridge.transport.seen[0]["input"][0]["content"][0]["type"]=="input_text"


@pytest.mark.parametrize("events",[[],[None],[{"type":"response.failed","response":{"error":{"message":"private upstream data"}}}],
    [ProviderError(504,"upstream_timeout","The account provider request timed out.")]])
def test_failed_or_truncated_provider_never_becomes_success(events):
    with gateway(Transport(events)) as (server,bridge,audits):
        status,headers,raw=call(server,body=chat())
        assert status in {502,504}
        assert "private upstream data" not in raw.decode()
        assert audits[0]["status"]==status


def test_error_after_stream_start_is_an_sse_error_without_done_marker():
    events=[{"type":"response.output_text.delta","delta":"partial"},{"type":"error","message":"private upstream error"}]
    with gateway(Transport(events)) as (server,bridge,audits):
        status,headers,raw=call(server,body=chat(stream=True))
        assert status==200
        parsed=list(parse_sse([raw]))
        assert parsed[-1]["error"]["code"]=="upstream_generation_failed"
        assert None not in parsed and "private upstream error" not in raw.decode()
        assert audits[0]["status"]==502


def test_concurrency_and_rate_limits_reject_without_hidden_retry():
    with gateway(requests_per_minute=1,max_concurrency=1) as (server,bridge,audits):
        with bridge.admission():
            assert call(server,body=chat())[0]==429
        status,headers,body=call(server,body=chat())
        assert status==429 and int(headers["Retry-After"])>0
        assert bridge.transport.seen==[]
        assert [row["error_code"] for row in audits] == ["gateway_busy", "gateway_rate_limit"]


def test_upstream_rate_limit_is_distinguished_without_logging_private_details():
    transport = Transport([ProviderError(429, "upstream_rate_limit", "private upstream diagnostic", 5)])
    with gateway(transport) as (server, bridge, audits):
        assert call(server, body=chat())[0] == 429
    assert audits[0]["error_code"] == "upstream_rate_limit"
    assert "private upstream diagnostic" not in json.dumps(audits)
    assert KEY not in json.dumps(audits)


def test_anthropic_messages_text_tools_and_local_api_key():
    from arena.providers import anthropic_to_chat
    native = {"model":MODEL,"system":"system","max_tokens":4096,"tools":[{"name":"measure","description":"measure a value","input_schema":{"type":"object"}}],
              "messages":[{"role":"user","content":"question"},
                  {"role":"assistant","content":[{"type":"tool_use","id":"call-0","name":"measure","input":{"x":1}}]},
                  {"role":"user","content":[{"type":"tool_result","tool_use_id":"call-0","content":"2"}]}]}
    body=anthropic_to_chat(native)
    assert body["messages"][-1]=={"role":"tool","tool_call_id":"call-0","content":"2"}
    fn={"type":"function_call","call_id":"call-1","name":"measure","arguments":'{"x":2}'}
    with gateway(Transport([completion("",[fn])]),policy="codex-native") as (server,bridge,audits):
        conn=http.client.HTTPConnection(*server.server_address,timeout=3)
        conn.request("POST","/v1/messages",json.dumps(native),{"Content-Type":"application/json","x-api-key":KEY,"anthropic-version":"2023-06-01"})
        response=conn.getresponse();result=json.loads(response.read());conn.close()
        assert response.status==200 and result["type"]=="message" and result["stop_reason"]=="tool_use"
        assert result["content"]==[{"type":"tool_use","id":"call-1","name":"measure","input":{"x":2}}]
        assert result["usage"]=={"input_tokens":9,"output_tokens":2}
        assert result["arena_compatibility"]["unenforced_controls"]==["max_tokens"]


def test_anthropic_unsupported_blocks_and_streaming_fail_before_upstream():
    with gateway(policy="codex-native") as (server,bridge,audits):
        body={"model":MODEL,"messages":[{"role":"user","content":"question"}],"max_tokens":1,"stream":True}
        assert call(server,"/v1/messages",body)[0]==400
        body.pop("stream");body["messages"][0]["content"]=[{"type":"thinking","thinking":"unsupported"}]
        assert call(server,"/v1/messages",body)[0]==400
        assert bridge.transport.seen==[]


def test_transport_deadline_interrupts_blocked_stream_without_logging_payload(monkeypatch):
    import socket
    from types import SimpleNamespace
    left,right=socket.socketpair()
    class Response:
        def __init__(self):
            self.fp=SimpleNamespace(raw=SimpleNamespace(_sock=left))
        def read1(self,size):
            return left.recv(size)
        def close(self):
            left.close()
    response=Response()
    monkeypatch.setattr("arena.providers.request.build_opener",lambda *args:SimpleNamespace(open=lambda *args,**kwargs:response))
    token=SimpleNamespace(read=lambda:({"Authorization":"Bearer PRIVATE-FIXTURE"},time.time()+100))
    started=time.monotonic()
    try:
        with pytest.raises(ProviderError) as exc:
            list(CodexTransport(token,timeout=.05).events({"model":MODEL}))
        assert exc.value.status==504 and time.monotonic()-started<1
        assert "PRIVATE-FIXTURE" not in str(exc.value)
    finally:
        right.close()


def test_transport_http_error_body_is_never_forwarded_and_no_redirects(monkeypatch):
    from io import BytesIO
    from types import SimpleNamespace
    from urllib.error import HTTPError
    captured=[]
    def opener(handler):
        assert handler.redirect_request(None,None,None,None,None,None) is None
        def fail(*args,**kwargs):
            captured.append(1)
            raise HTTPError("https://private.fixture/",429,"private failure",{"Retry-After":"7"},BytesIO(b'{"message":"SECRET-BODY"}'))
        return SimpleNamespace(open=fail)
    monkeypatch.setattr("arena.providers.request.build_opener",opener)
    token=SimpleNamespace(read=lambda:({"Authorization":"Bearer PRIVATE-FIXTURE"},time.time()+100))
    with pytest.raises(ProviderError) as exc:
        list(CodexTransport(token).events({"model":MODEL}))
    assert exc.value.status==429 and exc.value.retry_after==7
    assert "SECRET-BODY" not in str(exc.value) and len(captured)==1
