#!/usr/bin/env python3
"""Check actual DGM SDK requests against an inert localhost fixture only.

No native optimizer, evaluator, executable tool, Docker or external model is run.
Run in the prepared DGM environment. Network is restricted by a Python audit
hook to the fixture listener; its key and responses are invented test data.
"""
from __future__ import annotations

import argparse
import copy
import contextlib
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib
import io
import json
import os
from pathlib import Path
import shutil
import runpy
import sys
import tempfile
import threading

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from arena.frameworks.drivers.dgm_gateway import MODELS, provider_overlays
from arena.providers import normalize_request


def check(source: Path):
    requests, errors, tool_results, compatibility = [], [], [], []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            try:
                size = int(self.headers.get("Content-Length", "0"))
                assert 0 < size < 65536
                assert self.headers.get("Authorization") == "Bearer inert-dgm-fixture-key"
                body = json.loads(self.rfile.read(size))
                assert body["model"] == os.environ["ARENA_DGM_MODEL"]
                chat = self.path == "/v1/chat/completions"
                assert chat or self.path == "/v1/responses"
                normalized, policy = normalize_request(body, chat=chat, policy="codex-native")
                assert normalized["model"] == body["model"]
                compatibility.append(policy)
                requests.append({"route": self.path, "body": body})
                if chat:
                    assert body["messages"] == [{"role": "user", "content": "fixture-systemfixture-diagnosis"}]
                    result = {"id": "chatcmpl-fixture", "object": "chat.completion", "created": 1,
                        "model": body["model"], "choices": [{"index": 0, "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "fixture-diagnosis-result"}}]}
                else:
                    assert body["parallel_tool_calls"] is False and body["tool_choice"] == "auto"
                    assert body["tools"][0]["name"] == "inert_tool"
                    assert body["tools"][0]["strict"] is True
                    output_items = [item for item in body["input"] if item.get("type") == "function_call_output"]
                    if output_items:
                        assert output_items == [{"type": "function_call_output", "call_id": "call-fixture", "output": "inert-result:fixture-input"}]
                        calls = [item for item in body["input"] if item.get("type") == "function_call"]
                        assert len(calls) == 1 and calls[0]["call_id"] == "call-fixture"
                        output = [{"type": "message", "id": "msg-fixture", "status": "completed", "role": "assistant",
                                   "content": [{"type": "output_text", "text": "fixture-complete", "annotations": []}]}]
                    else:
                        output = [{"type": "function_call", "id": "fc-fixture", "status": "completed",
                                   "call_id": "call-fixture", "name": "inert_tool", "arguments": '{"value":"fixture-input"}'}]
                    result = {"id": "resp-fixture", "object": "response", "created_at": 1,
                        "status": "completed", "model": body["model"], "output": output,
                        "parallel_tool_calls": False, "tool_choice": "auto", "tools": body["tools"]}
                raw = json.dumps(result).encode()
                self.send_response(200)
            except Exception as exc:
                errors.append(type(exc).__name__ + ": " + str(exc))
                raw = b'{"error":{"message":"inert fixture validation failed","type":"invalid_request_error"}}'
                self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    endpoint = server.server_address

    def audit(event, args):
        if event == "socket.connect" and args[1] != endpoint:
            raise RuntimeError("DGM fixture forbids network outside its inert localhost listener")

    sys.addaudithook(audit)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    os.environ.update(OPENAI_API_KEY="inert-dgm-fixture-key", ARENA_DGM_GATEWAY_URL=f"http://127.0.0.1:{endpoint[1]}/v1",
                      PYTHONDONTWRITEBYTECODE="1", HF_HUB_OFFLINE="1", HF_DATASETS_OFFLINE="1")
    # Avoid accidental inherited HTTP proxies even for this fixture request.
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(name, None)
    sys.dont_write_bytecode = True
    overlays = provider_overlays(source)
    try:
        with tempfile.TemporaryDirectory(prefix="arena-dgm-provider-fixture-") as temporary:
            workspace = Path(temporary) / "source"
            shutil.copytree(source, workspace, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            for name, content in overlays.items():
                (workspace / name).write_text(content)
            sys.path.insert(0, str(workspace))
            old_cwd = Path.cwd()
            os.chdir(workspace)
            try:
                for model in MODELS:
                    os.environ["ARENA_DGM_MODEL"] = model
                    for name in ("llm", "llm_withtools", "coding_agent_polyglot", "self_improve_step", "DGM_outer"):
                        sys.modules.pop(name, None)
                    llm = importlib.import_module("llm")
                    native = importlib.import_module("llm_withtools")
                    coding = importlib.import_module("coding_agent_polyglot")
                    diagnosis = importlib.import_module("self_improve_step")
                    importlib.import_module("DGM_outer")
                    assert diagnosis.diagnose_model == native.CLAUDE_MODEL == native.OPENAI_MODEL == model
                    client, actual_model = llm.create_client(model)
                    assert actual_model == model
                    text, history = llm.get_response_from_llm("fixture-diagnosis", client, model, "fixture-system")
                    assert text == "fixture-diagnosis-result" and history[-1]["content"] == text
                    client.close()

                    def inert_tool(value):
                        tool_results.append((model, value))
                        return "inert-result:" + value

                    definition = {"name": "inert_tool", "description": "Returns inert fixture text; no execution",
                        "input_schema": {"type": "object", "properties": {"value": {"type": "string"}}, "required": ["value"]}}
                    native.load_all_tools = lambda **kwargs: [{"info": copy.deepcopy(definition), "function": inert_tool}]
                    for role, improve in (("coding", False), ("self_improvement", True)):
                        agent = coding.AgenticSystem("fixture only", str(workspace), "0" * 40,
                            chat_history_file=str(Path(temporary) / (role + ".log")), self_improve=improve)
                        assert agent.code_model == model
                        result = native.chat_with_agent("fixture-tool-protocol", model=agent.code_model, logging=lambda *args: None)
                        assert len(result) == 4 and result[-1].output_text == "fixture-complete"
                        assert native.check_for_tool_use(result[-1], model=model) is None
                    try:
                        native.chat_with_agent("must not call provider", model="o3-mini-2025-01-31")
                    except ValueError:
                        pass
                    else:
                        raise AssertionError("Wrong model was not rejected before native retries")
                cli_checks = []
                for script in ("DGM_outer.py", "self_improve_step.py", "coding_agent_polyglot.py"):
                    old_argv = sys.argv
                    help_text = io.StringIO()
                    try:
                        sys.argv = [script, "--help"]
                        with contextlib.redirect_stdout(help_text):
                            try:
                                runpy.run_path(str(workspace / script), run_name="__main__")
                            except SystemExit as exc:
                                assert exc.code == 0
                        assert "usage:" in help_text.getvalue().lower()
                        cli_checks.append(script)
                    finally:
                        sys.argv = old_argv
            finally:
                os.chdir(old_cwd)
                sys.path.remove(str(workspace))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
    assert not errors, errors
    assert len(requests) == 35 and len(tool_results) == 14
    return {"schema": "arena.dgm-provider-fixture/1", "models": list(MODELS), "fixture_requests": len(requests),
        "native_tool_round_trips": len(tool_results), "roles": ["diagnosis", "coding", "self_improvement"],
        "native_cli_help": cli_checks,
        "overlay_sha256": {name: hashlib.sha256(content.encode()).hexdigest() for name, content in overlays.items()},
        "gateway_compatibility": {"policy": "codex-native", "unenforced_controls": sorted({key for record in compatibility for key in record["unenforced_controls"]}), "compute_cap_enforced": False},
        "model_calls": 0, "task_evaluations": 0, "optimizer_runs": 0, "container_runs": 0, "status": "passed"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--source", type=Path, required=True)
    arguments = parser.parse_args()
    print(json.dumps(check(arguments.source), indent=2))
