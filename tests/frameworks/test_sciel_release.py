import copy
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import sys

import pytest

from arena.frameworks import get_adapter
from arena.frameworks.sciel import COMMIT
from arena.frameworks.sciel_release import SCiELReleaseAdapter
from arena.frameworks.drivers import sciel_release as driver
from arena import release_deployment as deployment



@pytest.fixture
def native_request(release_fixture, tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("fixture: true\n")
    tasks = tmp_path / "tasks"
    tasks.mkdir()
    return {"python": sys.executable, "release": release_fixture["reference"], "deployment": str(release_fixture["path"]),
            "config": str(config), "tasks_root": str(tasks), "seed": 1, "budget": 2}


def test_factory_resolves_new_private_pin_before_runtime_source_verification(release_fixture, native_request, tmp_path):
    adapter = get_adapter("sciel-release", request=native_request)
    assert adapter.commit == release_fixture["binding"]["repository"]["commit"]
    assert adapter.commit != COMMIT
    plan = adapter.prepare(release_fixture["source"], native_request, tmp_path / "output")
    assert plan["argv"][:4] == [sys.executable, "-P", "-m", "arena.frameworks.drivers.sciel_release"]
    assert "sciel.cli.main" not in plan["argv"]
    assert plan["execution_backend"] == "private_sciel_image_broker"
    assert plan["private_image"]["image"] == release_fixture["binding"]["image"]
    assert native_request["deployment"] in plan["input_paths"]
    assert not (tmp_path / "output").exists()


def test_adapter_refuses_changed_manifest_and_host_fallback(release_fixture, native_request, tmp_path):
    adapter = SCiELReleaseAdapter(request=native_request)
    value = copy.deepcopy(release_fixture["manifest"])
    value["review"]["reference"] = "changed-review"
    release_fixture["path"].write_bytes(deployment.canonical_bytes(value))
    with pytest.raises(ValueError, match="changed"):
        adapter.prepare(release_fixture["source"], native_request, tmp_path / "output")
    with pytest.raises(ValueError, match="Resolve"):
        SCiELReleaseAdapter().prepare(release_fixture["source"], native_request, tmp_path / "output")


@pytest.mark.parametrize("field,value", [("image", "other-image"), ("api_key", "secret"), ("command", ["sh"]), ("budget", 0), ("seed", -1)])
def test_adapter_has_no_image_credential_or_command_override(release_fixture, native_request, tmp_path, field, value):
    changed = {**native_request, field: value}
    with pytest.raises(ValueError):
        SCiELReleaseAdapter(request=native_request).prepare(release_fixture["source"], changed, tmp_path / "output")


@pytest.fixture
def transport(release_fixture, tmp_path, monkeypatch):
    run_id = "d" * 32
    output = tmp_path / "output"
    (output / ".arena").mkdir(parents=True)
    monkeypatch.setenv("ARENA_CONTROL_RUN_ID", run_id)
    monkeypatch.setenv("ARENA_EVALUATION_RECEIPTS_DIR", str(output / "canonical-evaluations"))
    manifest = release_fixture["manifest"]
    result = {"type": "result", "run_id": run_id, "status": "completed", "returncode": 0,
              "deployment_sha256": release_fixture["digest"], "image": manifest["image"]["reference"],
              "image_id": manifest["image"]["image_id"], "source_commit": manifest["binding"]["repository"]["commit"]}
    state = {"frames": [{"type": "started", "run_id": run_id}, {"type": "stdout", "text": "inert image diagnostic\n"}, result],
             "requests": [], "status": 200, "output": output, "result": result}
    class Response(io.BytesIO):
        @property
        def status(self):
            return state["status"]
    class Connection:
        sock = None
        def __init__(self, path, timeout=30):
            state["socket"] = str(path)
        def request(self, method, path, body=None, headers=None):
            state["requests"].append((method, path, None if body is None else json.loads(body)))
        def getresponse(self):
            return Response(b"".join(json.dumps(frame).encode() + b"\n" for frame in state["frames"]))
        def close(self):
            state["closed"] = True
    monkeypatch.setattr(driver, "UnixHTTPConnection", Connection)
    return state


def invoke(release_fixture, transport):
    return driver.run(release_fixture["path"], release_fixture["digest"], transport["output"])


def test_driver_sends_only_admitted_identity_and_records_actual_image_result(release_fixture, transport, capsys):
    assert invoke(release_fixture, transport) == 0
    method, path, body = transport["requests"][0]
    assert (method, path) == ("POST", "/v1/run")
    assert set(body) == {"run_id", "deployment_sha256"}
    assert "image" not in body and "command" not in body and "config" not in body
    assert "inert image diagnostic" in capsys.readouterr().out
    recorded = json.loads((transport["output"] / ".arena/private-image-result.json").read_text())
    assert recorded == transport["result"]
    assert transport["closed"]


@pytest.mark.parametrize("change", [
    lambda state: state.update(frames=state["frames"][:-1]),
    lambda state: state["result"].update(image="wrong-image"),
    lambda state: state["result"].update(image_id="sha256:" + "f" * 64),
    lambda state: state["result"].update(source_commit="f" * 40),
    lambda state: state["result"].update(deployment_sha256="f" * 64),
    lambda state: state["result"].update(run_id="f" * 32),
    lambda state: state.update(frames=state["frames"][1:]),
    lambda state: state.update(status=403),
])
def test_driver_missing_or_inconsistent_provenance_never_reports_success(release_fixture, transport, change):
    change(transport)
    with pytest.raises(ValueError):
        invoke(release_fixture, transport)
    assert not (transport["output"] / ".arena/private-image-result.json").exists()
    assert transport["closed"]


@pytest.mark.parametrize("status,returncode", [("failed", 1), ("cancelled", 137), ("timed_out", 124), ("completed", 1)])
def test_driver_nonzero_or_noncompleted_result_is_failure(release_fixture, transport, status, returncode):
    transport["result"].update(status=status, returncode=returncode)
    assert invoke(release_fixture, transport) == 1


def test_driver_requires_control_metadata_before_connecting(release_fixture, transport, monkeypatch):
    monkeypatch.delenv("ARENA_CONTROL_RUN_ID")
    with pytest.raises(ValueError, match="admitted"):
        invoke(release_fixture, transport)
    assert not transport["requests"]


def test_shared_runtime_plans_the_resolved_private_pin_without_broker_execution(release_fixture, native_request, tmp_path, monkeypatch):
    from arena.frameworks.runtime import prepare_plan
    monkeypatch.setattr(driver, "UnixHTTPConnection", lambda *args, **kwargs: pytest.fail("Planning must not contact a broker"))
    plan = prepare_plan({"schema": "arena.native-run/1", "framework": "sciel-release",
                         "source_dir": str(release_fixture["source"]), "output_dir": str(tmp_path / "planned-output"),
                         "timeout_seconds": 60, "request": native_request})
    assert plan["source"]["commit"] == release_fixture["binding"]["repository"]["commit"]
    assert plan["source"]["commit"] != COMMIT
    assert plan["command"]["execution_backend"] == "private_sciel_image_broker"
    assert not (tmp_path / "planned-output").exists()


def test_protocol_failure_explicitly_cancels_its_owned_container(release_fixture, transport):
    transport["frames"] = transport["frames"][:-1]
    with pytest.raises(ValueError, match="without an execution result"):
        invoke(release_fixture, transport)
    assert any(method == "DELETE" and path == "/v1/run/" + "d" * 32 for method, path, _ in transport["requests"])
