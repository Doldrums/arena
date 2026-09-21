#!/usr/bin/env python3
"""Inert native-provider/TLS fixture. Never contacts the model gateway.

Run with the prepared EoH or MEoH Python interpreter and explicit source path.
The only endpoint is a temporary local fixed-response HTTP fixture behind the
real Arena TLS relay. It does not instantiate an optimizer or evaluate code.
"""
import argparse
import http.client
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
from arena.frameworks.drivers.meoh import environment_key_provider
from arena.providers import normalize_request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=("eoh", "meoh"), required=True)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    # Fixture credentials are invented, never copied from the worker/gateway.
    os.environ["OPENAI_API_KEY"] = "fixture-transport-only"
    calls = []

    class Backend(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert self.path == "/v1/chat/completions"
            assert self.headers["Authorization"] == "Bearer fixture-transport-only"
            assert payload["model"] == "fixture-no-model"
            normalized, compatibility = normalize_request(payload, chat=True, policy="codex-native")
            assert normalized["model"] == "fixture-no-model"
            calls.append(payload)
            body = b'{"choices":[{"message":{"content":"fixture-native-transport"}}]}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    with tempfile.TemporaryDirectory(prefix="arena-transport-fixture-") as temporary:
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
        threads = []
        for server in (backend, relay):
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            threads.append(thread)
        try:
            permitted = {backend.server_port, relay.server_port}

            def no_external_network(event, args):
                if event == "socket.connect":
                    address = args[1]
                    if not isinstance(address, tuple) or address[0] != "127.0.0.1" or address[1] not in permitted:
                        raise RuntimeError("Only temporary fixture endpoints may be contacted")
                elif event == "socket.sendto":
                    raise RuntimeError("UDP is disabled during the transport fixture")

            sys.addaudithook(no_external_network)
            configure_ca(cert)
            host = "127.0.0.1:" + str(relay.server_port)
            if args.engine == "eoh":
                sys.path.insert(0, str(args.source / "eoh/src"))
                from eoh.llm.api_general import InterfaceAPI
                provider = InterfaceAPI(host, "fixture-transport-only", "fixture-no-model", timeout=5)
                result = provider.get_response("inert fixture", max_retries=1)
            else:
                sys.path.insert(0, str(args.source))
                from llm4ad.tools.llm.llm_api_https import HttpsApi
                provider = environment_key_provider(HttpsApi)(host=host, key="fixture-transport-only",
                                                               model="fixture-no-model", timeout=5)
                assert "fixture-transport-only" not in str(provider.__dict__)
                result = provider.draw_sample("inert fixture")
            assert result == "fixture-native-transport" and len(calls) == 1
            print(json.dumps({"engine": args.engine, "native_provider_fixture": "passed",
                              "native_requests_to_fake_backend": len(calls), "verified_tls": True,
                              "gateway_request_normalization": "passed",
                              "model_calls": 0, "optimizer_instantiated": False, "evaluation_run": False}))
        finally:
            for server in (relay, backend):
                server.shutdown()
                server.server_close()
            for thread in threads:
                thread.join(timeout=3)


if __name__ == "__main__":
    main()
