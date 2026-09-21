"""Reproducible provider-only overlay for the pinned DGM implementation.

Native diagnosis, tool-loop retry behavior, outer search and evaluators remain
in upstream source. Models are capability-selected without renaming wire IDs.
Preparing these files does not import DGM or create a model client.
"""
from __future__ import annotations

import ast
import hashlib
import ipaddress
import os
from pathlib import Path
from urllib.parse import urlsplit

DGM_COMMIT = "a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2"
MODELS = ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-6-astra", "gpt-5.5", "gpt-reserve", "codex-auto-review")
GATEWAY = "http://127.0.0.1:8789/v1"
SOURCE_HASHES = {
    "llm.py": "ca6ac22d7f128180de398cec48b9f5cc1f1f49f3bf1a8e935025588d8b09570d",
    "llm_withtools.py": "b6fa4ee18ad8b42767f7cad68bf8ed7f7937dcfaf32b85757182979bdb895836",
    "self_improve_step.py": "6f2ec364b11e7f6d35391ea66896fa2394cbca3bc59d68cf7352c2a77aa8cca7",
}
PREFIX = ("from arena.frameworks.drivers.dgm_gateway import (selected_model as _arena_model, "
          "require_model as _arena_require_model, is_selected_model as _arena_is_model, "
          "create_client as _arena_create_client)\n")


def selected_model() -> str:
    model = os.environ.get("ARENA_DGM_MODEL")
    if model not in MODELS:
        raise ValueError("ARENA_DGM_MODEL must select one exact reviewed gateway model")
    return model


def require_model(model: str) -> str:
    if model != selected_model():
        raise ValueError("DGM provider model differs from the explicitly selected run model")
    return model


def is_selected_model(model: str) -> bool:
    require_model(model)
    return True


def create_client(model: str):
    require_model(model)
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY must contain the scoped gateway credential")
    import openai
    return openai.OpenAI(api_key=key, base_url=gateway_url()), model


def gateway_url() -> str:
    """The operator/broker fixes this endpoint; it is never a model fallback."""
    value = os.environ.get("ARENA_DGM_GATEWAY_URL", GATEWAY)
    parsed = urlsplit(value)
    try:
        address = ipaddress.ip_address(parsed.hostname or "")
        valid = parsed.port is not None and (address.is_loopback or address.is_private)
    except ValueError:
        valid = False
    if (not valid or parsed.scheme != "http" or parsed.path != "/v1" or parsed.query or parsed.fragment
            or parsed.username is not None or parsed.password is not None):
        raise ValueError("DGM gateway must be an operator-pinned private HTTP /v1 endpoint without credentials")
    return value


def _replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError("Pinned DGM provider source structure differs from the reviewed seam")
    return text.replace(old, new, 1)


def _function_body_guard(text: str, name: str) -> str:
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == name)
    lines = text.splitlines(keepends=True)
    first = node.body[0]
    position = first.end_lineno if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str) else first.lineno - 1
    lines.insert(position, "    _arena_require_model(model)\n")
    return "".join(lines)


def provider_overlays(source: Path) -> dict[str, str]:
    """Return narrowly changed source texts after exact source-file hash checks."""
    original = {}
    for name, digest in SOURCE_HASHES.items():
        path = source / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Missing regular pinned DGM provider file")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("Pinned DGM provider file hash mismatch: " + name)
        original[name] = raw.decode()
    llm = original["llm.py"]
    node = next(n for n in ast.parse(llm).body if isinstance(n, ast.FunctionDef) and n.name == "create_client")
    lines = llm.splitlines(keepends=True)
    lines[node.lineno - 1:node.end_lineno] = ["def create_client(model: str):\n    return _arena_create_client(model)\n"]
    llm = "".join(lines)
    llm = _replace_once(llm, 'elif model.startswith("o1-") or model.startswith("o3-"):', 'elif _arena_is_model(model):')
    llm = _function_body_guard(llm, "get_response_from_llm")

    tools = original["llm_withtools.py"]
    tools = _replace_once(tools, "CLAUDE_MODEL = 'bedrock/us.anthropic.claude-3-5-sonnet-20241022-v2:0'", "CLAUDE_MODEL = _arena_model()")
    tools = _replace_once(tools, "OPENAI_MODEL = 'o3-mini-2025-01-31'", "OPENAI_MODEL = _arena_model()")
    if tools.count("model.startswith('o3-')") != 5:
        raise ValueError("Pinned native OpenAI tool-protocol dispatch sites changed")
    tools = tools.replace("model.startswith('o3-')", "_arena_is_model(model)")
    tools = _replace_once(tools,
        '        for tool_call in response.output:\n            if tool_call.type == "function_call":\n                break\n\n        if tool_call:',
        '        tool_call = next((item for item in response.output if item.type == "function_call"), None)\n\n        if tool_call is not None:')
    tools = _function_body_guard(tools, "get_response_withtools")
    tools = _function_body_guard(tools, "chat_with_agent")
    diagnose = _replace_once(original["self_improve_step.py"], "diagnose_model = 'o1-2024-12-17'", "diagnose_model = _arena_model()")
    diagnose = _replace_once(diagnose, '    image_name = "dgm"', '    image_name = "dgm:latest"')
    result = {"llm.py": PREFIX + llm, "llm_withtools.py": PREFIX + tools, "self_improve_step.py": PREFIX + diagnose}
    for name, text in result.items():
        compile(text, name, "exec")
    return result
