"""Project committed Responses output into one unambiguous Chat answer."""
from __future__ import annotations

from .provider_common import ProviderError


def _invalid():
    return ProviderError(502, "invalid_chat_output", "The provider returned invalid Chat output items.")


def _ambiguous():
    return ProviderError(502, "ambiguous_chat_output", "The provider returned ambiguous assistant message phases.")


def _message_parts(item):
    content = item.get("content")
    if not isinstance(content, list):
        raise _invalid()
    texts, refusals = [], []
    for part in content:
        if not isinstance(part, dict):
            raise _invalid()
        kind = part.get("type")
        key = "text" if kind == "output_text" else "refusal" if kind == "refusal" else None
        if key is None or not isinstance(part.get(key), str):
            raise _invalid()
        (texts if key == "text" else refusals).append(part[key])
    return "".join(texts), "".join(refusals)


def chat_message(response):
    """Keep final text, real calls and refusals; never execute or repair text.

    A completed phased response needs exactly one completed final_answer. A
    single unphased message remains supported for older account responses.
    Commentary can accompany a tool-only turn but cannot become the answer.
    """
    if not isinstance(response, dict) or response.get("status") != "completed":
        raise _invalid()
    output = response.get("output")
    if not isinstance(output, list):
        raise _invalid()
    final, legacy, calls = [], [], []
    phased = False
    call_ids = set()
    for item in output:
        if not isinstance(item, dict):
            raise _invalid()
        kind = item.get("type")
        if kind == "message":
            if item.get("role") not in (None, "assistant") or item.get("status") not in (None, "completed"):
                raise _invalid()
            text, refusal = _message_parts(item)
            phase = item.get("phase")
            phased = phased or phase is not None
            if phase == "commentary":
                # Do not silently discard a refusal that another final message
                # or a tool call would otherwise hide.
                if refusal:
                    raise _ambiguous()
            elif phase == "final_answer":
                if item.get("status") != "completed":
                    raise _invalid()
                final.append((text, refusal))
            elif phase is None:
                legacy.append((text, refusal))
            else:
                raise _ambiguous()
        elif kind == "function_call":
            if item.get("status") not in (None, "completed") or any(
                not isinstance(item.get(key), str) for key in ("call_id", "name", "arguments")
            ):
                raise _invalid()
            if not item["call_id"] or not item["name"] or item["call_id"] in call_ids:
                raise _ambiguous()
            call_ids.add(item["call_id"])
            calls.append({"id": item["call_id"], "type": "function", "function": {
                "name": item["name"], "arguments": item["arguments"],
            }})
    if len(final) > 1 or len(legacy) > 1 or legacy and phased:
        raise _ambiguous()
    selected = final or legacy
    text, refusal = selected[0] if selected else ("", "")
    if not selected and not calls:
        raise ProviderError(502, "missing_final_message", "The provider completed without a final Chat answer or function call.")
    message = {"role": "assistant", "content": text or None}
    if refusal:
        message["refusal"] = refusal
    if calls:
        message["tool_calls"] = calls
    return message
