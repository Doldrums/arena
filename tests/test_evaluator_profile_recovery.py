"""Restart cleanup binds the exact profile persisted before Docker creation."""
from copy import deepcopy
from dataclasses import replace
import importlib.util
import json
from pathlib import Path

import pytest

from arena import evaluation_resources as resources
from arena import evaluator_execution, evaluator_proxy as proxy

spec = importlib.util.spec_from_file_location("profile_recovery_fixture",
    Path(__file__).with_name("test_evaluator_proxy.py"))
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
setup = fixture.setup
RUN, NAME, IDENT, EVAL = fixture.RUN, fixture.NAME, fixture.IDENT, fixture.EVAL


def request_profile(setup, profile):
    config, original, *_ = setup
    body = deepcopy(original)
    if profile is not None:
        limits = resources.budget(profile)
        body["Labels"]["arena.evaluation-profile"] = profile
        body["HostConfig"].update(Memory=limits["memory_mb"] * 1024 ** 2,
                                  MemorySwap=limits["memory_mb"] * 1024 ** 2,
                                  PidsLimit=limits["pids"])
        grants = [{"image": body["Image"], "profile": profile, "task_ids": [body["Cmd"][5]]}]
        config = replace(config, resource_grants=resources.parse_grants(grants, config.images))
    return config, body


@pytest.mark.parametrize("profile", [None, *resources.PROFILES])
@pytest.mark.parametrize("transport_failure", [False, True])
def test_create_persists_profile_before_daemon_and_recovers_exact_labels(
        setup, monkeypatch, profile, transport_failure):
    config, body = request_profile(setup, profile)
    monkeypatch.setattr(resources, "require_parent_budget", lambda *args: None)
    monkeypatch.setattr(evaluator_execution.os, "chown", lambda *args: None)
    instance = proxy.Proxy(config)
    expected = {"id": None, "run": RUN, "name": NAME}
    if profile is not None:
        expected["resource_profile"] = profile
    def create(method, path, body=None, **kwargs):
        assert method == "POST"
        stages = list(config.staging_root.iterdir())
        assert len(stages) == 1
        assert json.loads((stages[0] / "record.json").read_text()) == expected
        if transport_failure:
            raise OSError("Daemon accepted create but transport ended")
        return 201, {}, json.dumps({"Id": IDENT}).encode()
    instance.request = create
    if transport_failure:
        with pytest.raises(OSError): instance.create(body, NAME, RUN, "")
    else:
        instance.create(body, NAME, RUN, "")
        expected["id"] = IDENT
    stage = next(config.staging_root.iterdir())
    assert json.loads((stage / "record.json").read_text()) == expected
    # Simulate process exit: recovery does not use the lost in-memory record.
    for record in instance.records.values():
        evaluator_execution.os.close(record["output_fd"])
    restarted = proxy.Proxy(config)
    calls = []
    def recover(method, path, **kwargs):
        calls.append((method, path))
        if method == "GET":
            return 200, {}, json.dumps({"Id": IDENT, "Config": {"Labels": body["Labels"]}}).encode()
        return 204, {}, b""
    restarted.request = recover
    restarted.recover()
    assert calls == [("GET", "/containers/" + (expected["id"] or NAME) + "/json"),
                     ("DELETE", "/containers/" + IDENT + "?force=1")]
    assert not stage.exists()


@pytest.mark.parametrize("record_profile,actual_profile", [
    (None, "cpu-4g-p128-v1"), ("cpu-4g-p128-v1", None),
    ("cpu-4g-p128-v1", "cpu-8g-p256-v1"), ("cpu-4g-p128-v1", "arbitrary")])
def test_recovery_cannot_accept_a_different_or_unrecorded_profile(setup, record_profile, actual_profile):
    config, *_ = setup
    stage = config.staging_root / EVAL
    stage.mkdir()
    record = {"id": IDENT, "run": RUN, "name": NAME}
    if record_profile is not None:
        record["resource_profile"] = record_profile
    (stage / "record.json").write_text(json.dumps(record))
    labels = {"arena.evaluator": "canonical-v1", "arena.control-run": RUN}
    if actual_profile is not None:
        labels["arena.evaluation-profile"] = actual_profile
    instance, calls = proxy.Proxy(config), []
    def request(method, path, **kwargs):
        calls.append(method)
        return 200, {}, json.dumps({"Id": IDENT, "Config": {"Labels": labels}}).encode()
    instance.request = request
    with pytest.raises(proxy.Denied): instance.recover()
    assert calls == ["GET"] and stage.exists()


@pytest.mark.parametrize("profile", [None, True, 4096, "arbitrary", {}, []])
def test_invalid_persisted_profile_fails_before_daemon_access(setup, profile):
    config, *_ = setup
    stage = config.staging_root / EVAL
    stage.mkdir()
    (stage / "record.json").write_text(json.dumps({
        "id": IDENT, "run": RUN, "name": NAME, "resource_profile": profile}))
    instance = proxy.Proxy(config)
    def forbidden(*args, **kwargs): raise AssertionError("Invalid metadata reached Docker")
    instance.request = forbidden
    with pytest.raises(proxy.Denied): instance.recover()
    assert stage.exists()
