"""Request and response translation for supported provider protocols."""
from __future__ import annotations

import json
import math
import time
from .provider_common import (
    MODEL_ID,
    ProviderError,
    UNENFORCED,
    _bad,
    _json,
)


def _content(value, role):
    kind = "output_text" if role == "assistant" else "input_text"
    if isinstance(value, str):
        return [{"type": kind, "text": value}]
    if not isinstance(value, list):
        raise _bad("Message content must be text or a supported content array.")
    result = []
    for item in value:
        if not isinstance(item, dict):
            raise _bad("Invalid message content item.")
        if item.get("type") == "text" and isinstance(item.get("text"), str):
            result.append({"type": kind, "text": item["text"]})
        elif item.get("type") == "image_url" and role == "user" and isinstance(item.get("image_url"), dict):
            image = item["image_url"]
            url = image.get("url")
            if not isinstance(url, str) or not url.startswith(("https://", "http://", "data:image/")):
                raise _bad("Unsupported image URL.")
            result.append({"type": "input_image", "image_url": url, "detail": image.get("detail", "auto")})
        else:
            raise _bad("Unsupported message content item.")
    return result


def _generation_controls(body, policy):
    present = sorted(key for key in UNENFORCED if body.get(key) is not None)
    if present and policy == "strict":
        raise ProviderError(400, "unsupported_generation_controls",
                            "Codex does not guarantee these controls: " + ", ".join(present) + ". Select the explicit codex-native compatibility policy to proceed without them.")
    for key in present:
        value = body[key]
        if key in {"max_tokens", "max_completion_tokens", "max_output_tokens"}:
            valid = type(value) is int and 1 <= value <= 1_000_000
        elif key == "stop":
            valid = isinstance(value, str) and len(value) <= 4096 or isinstance(value, list) and len(value) <= 16 and all(isinstance(x, str) and len(x) <= 4096 for x in value)
        elif key == "logit_bias":
            valid = isinstance(value, dict) and len(value) <= 256 and all(isinstance(k, str) and type(v) in (int, float) and math.isfinite(v) and -100 <= v <= 100 for k, v in value.items())
        else:
            valid = type(value) in (int, float) and math.isfinite(value) and abs(value) <= (2**53 if key == "seed" else 100)
        if not valid:
            raise _bad("Invalid generation control value.")
    return present


def normalize_request(body, *, chat, policy="strict"):
    if type(body) is not dict or not isinstance(body.get("model"), str) or not MODEL_ID.fullmatch(body["model"]):
        raise _bad("Provide an exact model identifier.")
    if type(body.get("stream", False)) is not bool:
        raise _bad("stream must be boolean.")
    if body.get("store") is not None and body.get("store") is not False:
        raise _bad("This private bridge requires store:false.")
    ignored = _generation_controls(body, policy)
    shared = {"model", "stream", "store", "tools", "tool_choice", "parallel_tool_calls", "reasoning", "reasoning_effort", "service_tier", "prompt_cache_key"}
    supported = shared | UNENFORCED | ({"messages", "response_format", "stream_options", "n"} if chat else {"input", "instructions", "text", "include", "truncation"})
    if set(body) - supported:
        raise _bad("The request includes unsupported API fields.")
    if type(body.get("n", 1)) is not int or body.get("n", 1) != 1:
        raise _bad("Only n=1 is supported; the bridge never launches hidden extra generations.")
    if chat and body.get("stream_options") is not None:
        options = body["stream_options"]
        if type(options) is not dict or set(options) - {"include_usage"} or type(options.get("include_usage", False)) is not bool:
            raise _bad("stream_options only supports boolean include_usage.")
    payload = {"model": body["model"], "instructions": "", "store": False, "stream": True}
    for key in ("parallel_tool_calls", "reasoning", "service_tier", "prompt_cache_key"):
        if body.get(key) is not None:
            payload[key] = body[key]
    if body.get("reasoning_effort") is not None:
        if "reasoning" in payload:
            raise _bad("Use either reasoning or reasoning_effort.")
        payload["reasoning"] = {"effort": body["reasoning_effort"]}
    if chat:
        messages = body.get("messages")
        if not isinstance(messages, list) or not messages or len(messages) > 10000:
            raise _bad("messages must be a nonempty bounded list.")
        inputs, instructions = [], []
        for message in messages:
            if not isinstance(message, dict):
                raise _bad("Invalid chat message.")
            role = message.get("role")
            if role in {"system", "developer"}:
                contents = _content(message.get("content"), "user")
                if any(item["type"] != "input_text" for item in contents):
                    raise _bad("System instructions must be text.")
                instructions.append("\n".join(item["text"] for item in contents))
            elif role in {"user", "assistant"}:
                if message.get("content") is not None:
                    inputs.append({"role": role, "content": _content(message["content"], role)})
                calls = message.get("tool_calls", [])
                if not isinstance(calls, list) or calls and role != "assistant":
                    raise _bad("Tool calls must belong to an assistant message.")
                for call in calls:
                    function = call.get("function", {}) if isinstance(call, dict) else {}
                    if not isinstance(call, dict) or not isinstance(function, dict) or set(function) - {"name", "arguments"} or call.get("type") != "function" or not all(isinstance(v, str) for v in [call.get("id"), function.get("name"), function.get("arguments")]):
                        raise _bad("Invalid assistant function call.")
                    inputs.append({"type": "function_call", "call_id": call["id"], **function})
            elif role == "tool":
                if not isinstance(message.get("tool_call_id"), str) or not isinstance(message.get("content"), str):
                    raise _bad("Tool results need tool_call_id and string content.")
                inputs.append({"type": "function_call_output", "call_id": message["tool_call_id"], "output": message["content"]})
            else:
                raise _bad("Unsupported message role.")
        if not inputs:
            raise _bad("At least one user or tool input is required.")
        payload.update(input=inputs, instructions="\n\n".join(instructions))
        if body.get("tools") is not None:
            if not isinstance(body["tools"], list):
                raise _bad("tools must be a list.")
            payload["tools"] = []
            for tool in body["tools"]:
                if not isinstance(tool, dict) or tool.get("type") != "function" or not isinstance(tool.get("function"), dict):
                    raise _bad("Chat compatibility currently supports function tools only.")
                function = tool["function"]
                if set(function) - {"name", "description", "parameters", "strict"} or not isinstance(function.get("name"), str):
                    raise _bad("Invalid function tool definition.")
                payload["tools"].append({"type": "function", **function})
        choice = body.get("tool_choice")
        if isinstance(choice, dict):
            if choice.get("type") != "function" or not isinstance(choice.get("function"), dict):
                raise _bad("Unsupported tool choice.")
            choice = {"type": "function", "name": choice["function"].get("name")}
        if choice is not None:
            payload["tool_choice"] = choice
        if body.get("response_format") is not None:
            fmt = body["response_format"]
            if not isinstance(fmt, dict) or fmt.get("type") not in {"text", "json_object", "json_schema"}:
                raise _bad("Unsupported response_format.")
            if fmt["type"] == "json_schema" and not isinstance(fmt.get("json_schema"), dict):
                raise _bad("json_schema must be a schema definition object.")
            payload["text"] = {"format": {"type": fmt["type"], **(fmt.get("json_schema", {}) if fmt["type"] == "json_schema" else {})}}
    else:
        if not isinstance(body.get("input"), (str, list)):
            raise _bad("Responses input must be text or an input-item list.")
        payload["input"] = ([{"role": "user", "content": [{"type": "input_text", "text": body["input"]}]}]
                            if isinstance(body["input"], str) else body["input"])
        for key in ("instructions", "tools", "tool_choice", "text", "include", "truncation"):
            if body.get(key) is not None:
                payload[key] = body[key]
        if not isinstance(payload["instructions"], str):
            raise _bad("instructions must be text.")
    compatibility = {"policy": policy, "unenforced_controls": ignored, "compute_cap_enforced": False}
    return payload, compatibility


def anthropic_to_chat(body):
    """Narrow Messages compatibility for native nonstreaming Anthropic SDKs."""
    if type(body) is not dict:
        raise _bad("Messages requests must be objects.")
    allowed = {"model", "messages", "system", "max_tokens", "temperature", "top_p", "top_k",
               "stop_sequences", "stream", "tools", "tool_choice"}
    if set(body) - allowed:
        raise _bad("This Messages bridge does not support these request fields.")
    if body.get("stream") not in (None, False):
        raise ProviderError(400, "anthropic_streaming_not_supported", "Messages compatibility currently supports stream:false only.")
    result = {key: body[key] for key in ("model", "max_tokens", "temperature", "top_p", "top_k") if key in body}
    result["messages"] = []
    def text_blocks(content):
        if isinstance(content, str):
            return content
        if not isinstance(content, list) or any(not isinstance(x, dict) or x.get("type") != "text" or not isinstance(x.get("text"), str) or set(x) - {"type", "text"} for x in content):
            raise _bad("Messages compatibility supports plain text and function tool content only.")
        return "\n".join(x["text"] for x in content)
    if "system" in body:
        result["messages"].append({"role": "system", "content": text_blocks(body["system"])})
    if not isinstance(body.get("messages"), list) or not body["messages"]:
        raise _bad("Messages requires a nonempty messages list.")
    for message in body["messages"]:
        if not isinstance(message, dict) or message.get("role") not in {"user", "assistant"}:
            raise _bad("Unsupported Messages role.")
        content, role = message.get("content"), message["role"]
        if isinstance(content, str):
            result["messages"].append({"role": role, "content": content})
            continue
        if not isinstance(content, list):
            raise _bad("Messages content must be text or content blocks.")
        texts, calls = [], []
        for block in content:
            if not isinstance(block, dict):
                raise _bad("Invalid Messages content block.")
            if block.get("type") == "text":
                texts.append(text_blocks([block]))
            elif block.get("type") == "tool_use" and role == "assistant":
                if not all(isinstance(block.get(k), str) for k in ("id", "name")) or not isinstance(block.get("input"), dict):
                    raise _bad("Invalid Messages tool use.")
                calls.append({"id": block["id"], "type": "function", "function": {"name": block["name"], "arguments": json.dumps(block["input"], allow_nan=False)}})
            elif block.get("type") == "tool_result" and role == "user":
                if not isinstance(block.get("tool_use_id"), str):
                    raise _bad("A tool result must identify its tool use.")
                value = text_blocks(block.get("content", ""))
                if block.get("is_error"):
                    value = "Tool returned an error:\n" + value
                result["messages"].append({"role": "tool", "tool_call_id": block["tool_use_id"], "content": value})
            else:
                raise _bad("Unsupported Messages content block.")
        if texts or calls:
            converted = {"role": role, "content": "\n".join(texts) if texts else None}
            if calls:
                converted["tool_calls"] = calls
            result["messages"].append(converted)
    if "stop_sequences" in body:
        result["stop"] = body["stop_sequences"]
    if "tools" in body:
        if not isinstance(body["tools"], list):
            raise _bad("Messages tools must be a list.")
        result["tools"] = []
        for tool in body["tools"]:
            if not isinstance(tool, dict) or not isinstance(tool.get("name"), str) or not isinstance(tool.get("input_schema"), dict) or set(tool) - {"name", "description", "input_schema"}:
                raise _bad("Only ordinary Messages function tools are supported.")
            result["tools"].append({"type": "function", "function": {"name": tool["name"], "description": tool.get("description", ""), "parameters": tool["input_schema"]}})
    if "tool_choice" in body:
        choice = body["tool_choice"]
        if not isinstance(choice, dict) or choice.get("type") not in {"auto", "any", "none", "tool"}:
            raise _bad("Unsupported Messages tool choice.")
        if choice["type"] == "tool":
            if not isinstance(choice.get("name"), str):
                raise _bad("Named tool choice needs a name.")
            result["tool_choice"] = {"type": "function", "function": {"name": choice["name"]}}
        else:
            result["tool_choice"] = {"auto": "auto", "any": "required", "none": "none"}[choice["type"]]
        if "disable_parallel_tool_use" in choice:
            result["parallel_tool_calls"] = not choice["disable_parallel_tool_use"]
    return result


def anthropic_completion(completion):
    message = completion["choices"][0]["message"]
    content = []
    if message.get("content"):
        content.append({"type": "text", "text": message["content"]})
    if message.get("refusal"):
        content.append({"type": "text", "text": message["refusal"]})
    for call in message.get("tool_calls", []):
        try:
            arguments = _json(call["function"]["arguments"])
            if not isinstance(arguments, dict):
                raise ValueError()
        except ValueError:
            raise ProviderError(502, "invalid_function_arguments", "The provider returned invalid function arguments.") from None
        content.append({"type": "tool_use", "id": call["id"], "name": call["function"]["name"], "input": arguments})
    return {"id": "msg-" + completion["id"].removeprefix("chatcmpl-"), "type": "message", "role": "assistant",
            "model": completion["model"], "content": content, "stop_reason": "tool_use" if message.get("tool_calls") else "end_turn",
            "stop_sequence": None, "usage": {"input_tokens": completion["usage"]["prompt_tokens"], "output_tokens": completion["usage"]["completion_tokens"]},
            "arena_compatibility": completion["arena_compatibility"]}


def usage_counts(value):
    value = value if isinstance(value, dict) else {}
    result = {}
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        number = value.get(key)
        if type(number) is int and number >= 0:
            result[key] = number
    return result


def public_response(value):
    """Forward response content without account IDs or provider cache identifiers."""
    result = {key: value[key] for key in
              ("id", "object", "created_at", "completed_at", "status", "error", "incomplete_details", "model", "output")
              if key in value}
    if isinstance(value.get("usage"), dict):
        usage = usage_counts(value["usage"])
        for key in ("input_tokens_details", "output_tokens_details"):
            if isinstance(value["usage"].get(key), dict):
                usage[key] = {name: count for name, count in value["usage"][key].items()
                              if name in {"cached_tokens", "cache_write_tokens", "reasoning_tokens"}
                              and type(count) is int and count >= 0}
        result["usage"] = usage
    return result


def chat_completion(response, requested_model, request_id, compatibility):
    content, refusals, calls = [], [], []
    for item in response.get("output", []):
        if item.get("type") == "message":
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    content.append(part.get("text", ""))
                elif part.get("type") == "refusal":
                    refusals.append(part.get("refusal", ""))
        elif item.get("type") == "function_call":
            calls.append({"id": item["call_id"], "type": "function", "function": {"name": item["name"], "arguments": item["arguments"]}})
    message = {"role": "assistant", "content": "".join(content) or None}
    if calls:
        message["tool_calls"] = calls
    if refusals:
        message["refusal"] = "".join(refusals)
    observed = usage_counts(response.get("usage"))
    usage = {"prompt_tokens": observed.get("input_tokens"), "completion_tokens": observed.get("output_tokens"), "total_tokens": observed.get("total_tokens")}
    return {"id": "chatcmpl-" + request_id, "object": "chat.completion", "created": int(time.time()),
            "model": requested_model, "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls" if calls else "stop"}],
            "usage": usage, "arena_compatibility": compatibility}
