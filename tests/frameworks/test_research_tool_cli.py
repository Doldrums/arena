"""Routing cannot grant runtime, leak client environment or replay mutations."""
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
from unittest.mock import Mock

import pytest

from arena import research_tool_cli as cli

IDENT = "a" * 64
RESEARCH = "sciel-method-" + "b" * 32
CANONICAL = "arena-eval-" + "c" * 32


def native_create():
    return ["create", "--pull=never", "--name", RESEARCH, "--network=none", "--read-only", "--cpus=1",
            "--label=sciel.invocation-owner=" + "d" * 32, "--user=0:0", "--cgroupns=private",
            "--pids-limit=64", "--memory=536870912", "--memory-swap=536870912", "--cap-drop=ALL",
            "--cap-add=SETUID", "--cap-add=SETGID", "--security-opt=no-new-privileges", "--log-driver=none",
            "--workdir=/tmp", "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=33554432,mode=1777",
            "--entrypoint=/usr/local/bin/python", "--mount", "type=bind,src=/a/bundle,dst=/bundle,readonly",
            "--mount", "type=bind,src=/a/dependencies,dst=/dependencies,readonly",
            "--mount", "type=bind,src=/a/runtime,dst=/runtime,readonly",
            "--mount", "type=bind,src=/a/request.json,dst=/request.json,readonly",
            "sha256:" + IDENT, "-I", "-B", "/runtime/_runner.py", "--supervise", "/request.json"]


@pytest.mark.parametrize("args,expected", [
    (["image", "inspect", "--format", cli.IMAGE_FORMAT, "sha256:" + IDENT], "research"),
    (["version", "--format", "{{.Server.Version}}"], "research"),
    (native_create(), "research"),
    (["inspect", "--type=container", "--format", cli.OWNER_FORMAT, RESEARCH], "research"),
    (["info", "--format", "{{.CgroupDriver}} {{.CgroupVersion}}"], "canonical"),
    (["run", "--rm", "--pull=never", "--name", CANONICAL, "--cpus", "1", "pinned-image", "python3"], "canonical"),
    (["rm", "--force", CANONICAL], "canonical"),
])
def test_known_native_and_canonical_commands_preserve_every_argument(args, expected):
    probe = Mock(side_effect=AssertionError("Named commands need no ownership lookup"))
    plan = cli.execution_plan(args, canonical_socket="/run/c.sock", research_socket="/run/r.sock", probe=probe)
    assert plan["broker"] == expected
    assert plan["argv"] == ["/usr/local/bin/docker", *args]
    assert plan["environment"]["DOCKER_HOST"] == "unix:///run/" + ("r" if expected == "research" else "c") + ".sock"
    probe.assert_not_called()


@pytest.mark.parametrize("command", [["start", "--attach"], ["rm", "--force"]])
@pytest.mark.parametrize("owned", [True, False])
def test_exact_id_probe_routes_one_mutation_without_dispatch_or_retry(command, owned):
    probe = Mock(return_value=owned)
    plan = cli.execution_plan([*command, IDENT], probe=probe)
    assert plan["broker"] == ("research" if owned else "canonical")
    probe.assert_called_once_with(IDENT)


@pytest.mark.parametrize("args", [
    [], ["ps"], ["pull", "alpine"], ["exec", IDENT, "bash"], ["context", "use", "other"],
    ["-H", "unix:///host.sock", "version"], ["version", "--context=other"],
    ["version", "-cother"], ["version", "--tlsverify"], ["version", "--config=/tmp/attacker"],
    ["rm", "--force", IDENT, "b" * 64], ["rm", "-f", IDENT], ["start", "--attach", IDENT[:12]],
    ["image", "inspect", "--format", cli.IMAGE_FORMAT, "latest"],
    ["run", "--rm", "--pull=never", "--name", RESEARCH, "image"],
    ["create", "--pull=never", "--name", CANONICAL, "image"],
    ["create", "--pull=never", "--name", RESEARCH, "--name=another", "image"],
    ["inspect", "--type=container", "--format", "{{json .}}", RESEARCH],
    ["rm", "--force", CANONICAL + "\n"],
])
def test_unknown_alias_ambiguous_or_endpoint_override_commands_fail_before_probe(args):
    probe = Mock()
    with pytest.raises(cli.RoutingError): cli.execution_plan(args, probe=probe)
    probe.assert_not_called()


def test_all_inherited_credentials_config_and_loader_environment_are_discarded(monkeypatch):
    for key in ("OPENAI_API_KEY", "DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_CONFIG", "LD_PRELOAD", "HOME", "PATH"):
        monkeypatch.setenv(key, "untrusted-secret")
    plan = cli.execution_plan(["version", "--format", "{{.Server.Version}}"])
    assert "untrusted-secret" not in json.dumps(plan)
    assert set(plan["environment"]) == {"PATH", "HOME", "DOCKER_CONFIG", "LANG", "LC_ALL", "DOCKER_HOST"}


@pytest.mark.parametrize("value", [None, 1, "owned", {}, []])
def test_inconclusive_ownership_never_falls_back(value):
    with pytest.raises(cli.RoutingError):
        cli.execution_plan(["rm", "--force", IDENT], probe=lambda _: value)


@pytest.mark.parametrize("socket_path", ["tcp://host:2375", "/run/../other.sock", "/run//x.sock", "/run/x\n.sock"])
def test_endpoint_is_fixed_canonical_unix_path(socket_path):
    with pytest.raises(cli.RoutingError):
        cli.execution_plan(["version", "--format", "{{.Server.Version}}"], research_socket=socket_path)


class Response:
    def __init__(self, status, body): self.status, self.body = status, body
    def read(self, size): return self.body[:size]


@pytest.mark.parametrize("status,body,expected", [
    (200, json.dumps({"Id": IDENT}).encode(), True), (404, b'{"message":"not owned"}', False),
    (403, b"private denial", None), (500, b"private error", None), (302, b"redirect", None),
    (200, b'{"Id":"wrong"}', None), (200, b'[]', None), (200, b'invalid', None),
    (200, ('{"Id":"' + IDENT + '","Id":"' + IDENT + '"}').encode(), None),
    (200, b"x" * (cli.MAX_PROBE_BYTES + 1), None),
])
def test_probe_only_explicit404_means_canonical(monkeypatch, status, body, expected):
    connection = Mock(); connection.getresponse.return_value = Response(status, body)
    monkeypatch.setattr(cli, "_UnixConnection", Mock(return_value=connection))
    if expected is None:
        with pytest.raises(cli.RoutingError): cli.probe_research_owner(IDENT)
    else:
        assert cli.probe_research_owner(IDENT) is expected
    connection.request.assert_called_once_with("GET", f"/containers/{IDENT}/json", headers={"Accept": "application/json"})
    connection.close.assert_called_once()


def test_probe_transport_error_never_retries_mutation_or_prints_private_error(monkeypatch, capsys):
    connection = Mock(); connection.getresponse.side_effect = TimeoutError("secret transport detail")
    monkeypatch.setattr(cli, "_UnixConnection", Mock(return_value=connection))
    execute = Mock(); monkeypatch.setattr(cli.os, "execve", execute)
    assert cli.main(["start", "--attach", IDENT]) == 125
    execute.assert_not_called(); connection.request.assert_called_once()
    assert "secret transport detail" not in capsys.readouterr().err


def test_actual_unix_probe_is_one_get_without_redirect_or_mutation():
    with tempfile.TemporaryDirectory(dir="/tmp", prefix="rt-cli-") as directory:
        path = str(Path(directory) / "s")
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); server.bind(path); server.listen(1)
        observed = []
        def respond():
            connection, _ = server.accept()
            with connection:
                request = b""
                while b"\r\n\r\n" not in request: request += connection.recv(4096)
                observed.append(request)
                data = json.dumps({"Id": IDENT}).encode()
                connection.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(data)).encode() + b"\r\nConnection: close\r\n\r\n" + data)
        thread = threading.Thread(target=respond, daemon=True); thread.start()
        try:
            assert cli.probe_research_owner(IDENT, research_socket=path) is True
            thread.join(timeout=3); assert not thread.is_alive()
            assert len(observed) == 1
            assert observed[0].startswith(f"GET /containers/{IDENT}/json HTTP/1.1\r\n".encode())
        finally: server.close()


def test_main_executes_once_absolute_cli_with_no_shell(monkeypatch):
    execute = Mock(); monkeypatch.setattr(cli.os, "execve", execute)
    cli.main(["version", "--format", "{{.Server.Version}}"])
    execute.assert_called_once()
    binary, argv, environment = execute.call_args.args
    assert binary == argv[0] == "/usr/local/bin/docker"
    assert environment["DOCKER_HOST"] == "unix://" + cli.RESEARCH_SOCKET
