"""Real TLS and HTTP fixtures only; no external provider is contacted."""
from contextlib import contextmanager
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import shutil
import ssl
import subprocess
import threading
import time

import pytest

from arena import tls_gateway


@pytest.fixture(scope="module")
def certificate(tmp_path_factory):
    if not shutil.which("openssl"):
        pytest.skip("openssl is required for local certificate fixtures")
    directory = tmp_path_factory.mktemp("relay-tls")
    config = directory / "openssl.cnf"
    config.write_text("[req]\ndistinguished_name=dn\nx509_extensions=ext\nprompt=no\n"
                      "[dn]\nCN=localhost\n[ext]\nsubjectAltName=DNS:localhost,IP:127.0.0.1\n"
                      "basicConstraints=critical,CA:TRUE\nkeyUsage=critical,keyCertSign,digitalSignature,keyEncipherment\n")
    cert, key = directory / "cert.pem", directory / "key.pem"
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                    "-config", str(config), "-keyout", str(key), "-out", str(cert)],
                   check=True, capture_output=True)
    return cert, key


@contextmanager
def serving(server):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


@pytest.fixture
def relay(certificate):
    calls = []

    class Upstream(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            payload = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            calls.append((self.path, self.headers.get("Authorization"), payload))
            body = json.dumps({"choices": [{"message": {"content": "fixture"}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(*certificate)
    with serving(ThreadingHTTPServer(("127.0.0.1", 0), Upstream)) as backend:
        with serving(tls_gateway.RelayServer(("127.0.0.1", 0), context,
                                            upstream_port=backend.server_port)) as frontend:
            yield frontend.server_port, calls, certificate[0]


def test_real_verified_tls_preserves_native_payload_and_auth(relay, monkeypatch, capsys):
    port, calls, cert = relay
    monkeypatch.setenv("SSL_CERT_FILE", str(cert))
    # No custom SSL context: this is the exact native HTTPSConnection seam.
    client = http.client.HTTPSConnection("127.0.0.1", port, timeout=3)
    body = b'{"model":"fixture","messages":[{"role":"user","content":"inert"}]}'
    try:
        client.request("POST", "/v1/chat/completions", body,
                       {"Authorization": "Bearer fixture-local-key", "Content-Type": "application/json"})
        response = client.getresponse()
        assert response.status == 200
        assert json.loads(response.read())["choices"][0]["message"]["content"] == "fixture"
    finally:
        client.close()
    assert calls == [("/v1/chat/completions", "Bearer fixture-local-key", body)]
    assert "fixture-local-key" not in str(capsys.readouterr())


def test_untrusted_certificate_is_rejected(relay, monkeypatch):
    port, calls, _ = relay
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    client = http.client.HTTPSConnection("127.0.0.1", port, timeout=3)
    with pytest.raises(ssl.SSLCertVerificationError):
        client.request("GET", "/v1/models")
    client.close()
    assert not calls


@pytest.mark.parametrize("path,headers,status", [
    ("/admin", {}, 404), ("http://example.invalid/v1/chat/completions", {}, 404),
    ("/v1/chat/completions", {"Content-Length": str(tls_gateway.MAX_BODY + 1)}, 413),
    ("/v1/chat/completions", {"Transfer-Encoding": "chunked"}, 400),
    ("/v1/chat/completions", {"X-Long": "a" * (tls_gateway.MAX_HEADERS + 1)}, 400),
])
def test_disallowed_routes_and_bounded_requests_never_reach_gateway(relay, path, headers, status):
    port, calls, cert = relay
    client = http.client.HTTPSConnection("127.0.0.1", port, context=ssl.create_default_context(cafile=str(cert)), timeout=3)
    client.request("POST", path, b"", headers)
    response = client.getresponse()
    assert response.status == status
    response.read()
    client.close()
    assert not calls


def test_response_limit(relay, monkeypatch):
    port, _, cert = relay
    monkeypatch.setattr(tls_gateway, "MAX_RESPONSE", 8)
    client = http.client.HTTPSConnection("127.0.0.1", port, context=ssl.create_default_context(cafile=str(cert)), timeout=3)
    client.request("POST", "/v1/chat/completions", b"{}")
    response = client.getresponse()
    assert response.status == 502 and b"response_too_large" in response.read()
    client.close()


def test_absolute_deadline_interrupts_dripping_close_delimited_response(certificate):
    class Drip(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            self.send_response(200)
            self.end_headers()
            for _ in range(50):
                try:
                    self.wfile.write(b"a")
                    self.wfile.flush()
                except OSError:
                    break
                time.sleep(0.1)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(*certificate)
    with serving(ThreadingHTTPServer(("127.0.0.1", 0), Drip)) as backend:
        with serving(tls_gateway.RelayServer(("127.0.0.1", 0), context,
                                            upstream_port=backend.server_port, deadline=1)) as front:
            client = http.client.HTTPSConnection("127.0.0.1", front.server_port,
                       context=ssl.create_default_context(cafile=str(certificate[0])), timeout=3)
            started = time.monotonic()
            client.request("POST", "/v1/chat/completions", b"{}")
            with pytest.raises((http.client.RemoteDisconnected, OSError)):
                client.getresponse()
            assert time.monotonic() - started < 2.5
            client.close()


def test_non_loopback_bind_is_rejected():
    with pytest.raises(ValueError):
        tls_gateway.RelayServer(("0.0.0.0", 8790), ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER))


def test_explicit_ca_bundle_is_validated_before_setting_environment(certificate, monkeypatch, tmp_path):
    from arena.frameworks.drivers._tls import configure_ca
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    configure_ca(certificate[0])
    import os
    assert os.environ["SSL_CERT_FILE"] == str(certificate[0])
    bad = tmp_path / "invalid.pem"
    bad.write_text("not a certificate")
    with pytest.raises(ssl.SSLError):
        configure_ca(bad)
    link = tmp_path / "linked.pem"
    link.symlink_to(certificate[0])
    with pytest.raises(ValueError):
        configure_ca(link)
    assert os.environ["SSL_CERT_FILE"] == str(certificate[0])
