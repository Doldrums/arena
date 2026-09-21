#!/usr/bin/env python3
"""Check native imports/configs/provider transport against inert local fixtures.

No optimizers or task evaluators are run. Network audit permits only temporary
fixed-response fixture endpoints, never the gateway or an external provider.
"""
from __future__ import annotations
import argparse
import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile
import threading

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from arena.tls_gateway import RelayServer
from arena.frameworks.drivers._tls import configure_ca
from arena.frameworks.drivers.cpu_program_gateway import configure_codeevolve_transport, verify_embedding_cache
from arena.providers import normalize_request


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--engine", choices=("codeevolve", "loongflow", "coevo"), required=True)
    parser.add_argument("--root", type=Path, default=Path("/srv/arena"))
    args = parser.parse_args()
    report_stream = sys.stdout
    sys.stdout = sys.stderr  # Native import/config diagnostics must not corrupt the JSON receipt.
    source = args.root / "sources" / args.engine
    configs = args.root / "configs" / ("program-pilots-20260921-" + args.engine)
    templates = json.loads((configs / "templates.json").read_text())
    sys.path[:0] = [str(source), str(source / "src"), str(source / "CoEvo/src")]
    sys.dont_write_bytecode = True
    os.environ.update(OPENAI_API_KEY="fixture-transport-only", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                      LITELLM_LOCAL_MODEL_COST_MAP="True", LITELLM_TELEMETRY="False", DO_NOT_TRACK="1",
                      HF_HOME=str(args.root / "caches/coevo-hf"))
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    calls, errors = [], []

    class Backend(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            try:
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                assert self.path == "/v1/chat/completions"
                assert self.headers["Authorization"] == "Bearer fixture-transport-only"
                normalized, compatibility = normalize_request(payload, chat=True, policy="codex-native")
                assert normalized["model"] in {t["model"] for t in templates}
                assert "user" not in payload
                calls.append(payload)
                body = json.dumps({"id": "fixture", "object": "chat.completion", "created": 1,
                    "model": payload["model"], "choices": [{"index": 0, "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "fixture-native-transport"}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}).encode()
                self.send_response(200)
            except Exception as exc:
                errors.append(type(exc).__name__ + ": " + str(exc))
                body = b'{"error":{"message":"fixture rejected request","type":"invalid_request_error"}}'
                self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    with tempfile.TemporaryDirectory(prefix="arena-additional-native-fixture-") as temporary:
        directory = Path(temporary)
        os.environ["MPLCONFIGDIR"] = str(directory / "matplotlib")
        cert, key, config = directory / "cert.pem", directory / "key.pem", directory / "openssl.cnf"
        config.write_text("[req]\ndistinguished_name=dn\nx509_extensions=ext\nprompt=no\n[dn]\nCN=localhost\n"
                          "[ext]\nsubjectAltName=DNS:localhost,IP:127.0.0.1\nbasicConstraints=critical,CA:TRUE\n")
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                        "-config", str(config), "-keyout", str(key), "-out", str(cert)], check=True, capture_output=True)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        backend = ThreadingHTTPServer(("127.0.0.1", 0), Backend)
        relay = RelayServer(("127.0.0.1", 0), context, upstream_port=backend.server_port, deadline=10)
        for server in (backend, relay):
            threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            permitted = {backend.server_port, relay.server_port}
            def no_external_network(event, event_args):
                if event == "socket.connect":
                    address = event_args[1]
                    if not isinstance(address, tuple) or address[0] != "127.0.0.1" or address[1] not in permitted:
                        raise RuntimeError("Only temporary fixture endpoints may be contacted")
                elif event == "socket.sendto":
                    raise RuntimeError("UDP is disabled during the transport fixture")
            sys.addaudithook(no_external_network)
            base = "http://127.0.0.1:" + str(backend.server_port) + "/v1"
            configure_ca(cert)
            if args.engine == "codeevolve":
                import yaml
                configure_codeevolve_transport()
                from codeevolve.lm.openai import OpenAILM
                from codeevolve.utils.cli_setup import validate_paths
                for item in templates:
                    model = item["model"]
                    config_path = configs / (model + ".yaml")
                    data = yaml.safe_load(config_path.read_text())
                    validate_paths(source / "problems/alphaevolve_math_problems/packing_problems/circle_packing_square/26/input", config_path, False)
                    assert data["EVOLVE_CONFIG"]["num_islands"] == 1
                    async def check():
                        provider = OpenAILM(**data["EXPLORATION_ENSEMBLE"][0], api_base=base, api_key="fixture-transport-only")
                        try:
                            result = await provider.generate([{"role": "user", "content": "inert fixture"}])
                            assert result == ("fixture-native-transport", 1, 1)
                        finally:
                            await provider.client.close()
                    asyncio.run(check())
            elif args.engine == "loongflow":
                import yaml
                from agents.math_agent.math_evolve_agent import MathPESAgent
                from loongflow.framework.pes.context import EvolveChainConfig
                from loongflow.agentsdk.models import LiteLLMModel, CompletionRequest
                from loongflow.agentsdk.message import Message, Role
                runner = MathPESAgent()  # Constructor creates only its argument parser.
                for item in templates:
                    native_args = runner.parser.parse_args(["--config", str(configs / (item["model"] + ".yaml")),
                        "--eval-file", str(source / "agents/math_agent/examples/packing_circle_in_unit_square/eval_program.py"),
                        "--initial-file", str(source / "agents/math_agent/examples/packing_circle_in_unit_square/initial_program.py"),
                        "--workspace-path", str(directory / "evaluator")])
                    raw = runner._merge_configs(native_args, runner._load_yaml_config(native_args.config))
                    validated = EvolveChainConfig.model_validate(raw)
                    assert validated.llm_config.api_key is None and validated.evolve.concurrency == 1
                    settings = validated.llm_config.model_dump()
                    settings["url"] = base
                    provider = LiteLLMModel.from_config(settings)
                    async def check():
                        responses = [r async for r in provider.generate(CompletionRequest(messages=[Message.from_text(data="inert fixture", role=Role.USER)]))]
                        assert len(responses) == 1 and not responses[0].error_code, repr(responses)
                    asyncio.run(check())
            else:
                from evotoolkit.tools import HttpsApi
                from coevo.core.coevo_method import CoEvoMethod
                from coevo.core.summarizer import CoEvoSummarizer
                from transformers import AutoTokenizer, AutoModelForCausalLM
                cache = args.root / "caches/coevo-hf"
                verify_embedding_cache(cache, cache / "manifest.json")
                # Loading the native embedding dependencies is not a forward pass.
                tokenizer = AutoTokenizer.from_pretrained("openai-community/gpt2", local_files_only=True)
                embedding = AutoModelForCausalLM.from_pretrained("openai-community/gpt2", local_files_only=True)
                del tokenizer, embedding
                for item in templates:
                    provider = HttpsApi("https://127.0.0.1:" + str(relay.server_port) + "/v1/chat/completions",
                                        "fixture-transport-only", item["model"], timeout=5)
                    result, usage = provider.get_response("inert fixture")
                    assert result == "fixture-native-transport" and usage["total_tokens"] == 2
            assert not errors, errors
            assert len(calls) == 7 and [c["model"] for c in calls] == [t["model"] for t in templates]
            print(json.dumps({"engine": args.engine, "native_provider_fixture": "passed", "native_config_checks": "passed",
                "native_requests_to_fake_backend": len(calls), "gateway_request_normalization": "passed",
                "verified_tls": args.engine == "coevo", "embedding_forward_passes": 0,
                "discarded_metadata": ["user"] if args.engine == "codeevolve" else [],
                "model_calls": 0, "optimizer_instantiated": False, "evaluation_run": False}), file=report_stream)
        finally:
            for server in (relay, backend):
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    main()
