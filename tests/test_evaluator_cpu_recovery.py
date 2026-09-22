"""Exact inherited-image restart identity; no real Docker or candidate execution."""
from copy import deepcopy
from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import stat
from urllib.parse import unquote

import pytest

from arena import evaluator_cpu_recovery as recovery
from arena import evaluator_execution
from arena.evaluator_policy import Denied
from evaluator_cpu_helpers import cpu_binding, native_container

spec = importlib.util.spec_from_file_location("cpu_recovery_fixture",
    Path(__file__).with_name("test_evaluator_proxy.py"))
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
setup = fixture.setup
RUN, NAME, IDENT, EVAL = fixture.RUN, fixture.NAME, fixture.IDENT, fixture.EVAL
EVIDENCE = json.loads((Path(__file__).parent / "fixtures/evaluator_proxy/science5-image-identity.json").read_text())


@pytest.fixture
def cpu(setup):
    config, body, candidate, output = setup
    config = replace(config, images=(EVIDENCE["reference"],))
    body = deepcopy(body)
    body["Image"] = EVIDENCE["reference"]
    return config, body, candidate, output


def persisted(cpu, *, legacy=False, known=True):
    config, body, *_ = cpu
    stage = config.staging_root / EVAL
    stage.mkdir()
    record = {"id": IDENT if known else None, "run": RUN, "name": NAME}
    if not legacy:
        record["cpu"] = cpu_binding(config, body, EVIDENCE["image"])
    recovery.write_record(stage, record)
    return stage, record, native_container(config, stage, record, EVIDENCE["image"])


def daemon(native, calls, *, image=None, failure=None):
    inspected = deepcopy(EVIDENCE["image"] if image is None else image)
    def request(method, path, body=None, **kwargs):
        calls.append((method, path))
        if path.startswith("/images/"):
            if failure == "image_timeout": raise TimeoutError("image lookup unknown")
            if failure in ("image404", "image500"): return int(failure[-3:]), {}, b"{}"
            assert unquote(path) == "/images/" + EVIDENCE["reference"] + "/json"
            return 200, {}, json.dumps(inspected).encode()
        if method == "GET":
            if failure == "get_timeout": raise TimeoutError("container lookup unknown")
            if failure == "get500": return 500, {}, b"{}"
            if failure == "absent": return 404, {}, b"{}"
            return 200, {}, json.dumps(native).encode()
        assert method == "DELETE"
        if failure == "delete_timeout": raise TimeoutError("deletion unknown")
        return (500 if failure == "delete500" else 204), {}, b""
    return request


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("known", [False, True])
def test_exact_real_eight_inherited_labels_recover_own_cpu(cpu, legacy, known):
    stage, record, native = persisted(cpu, legacy=legacy, known=known)
    assert len(EVIDENCE["image"]["Config"]["Labels"]) == 8
    assert len(native["Config"]["Labels"]) == 10
    instance, calls = evaluator_execution.Proxy(cpu[0]), []
    instance.request = daemon(native, calls)
    instance.recover()
    assert not stage.exists()
    assert calls[0] == ("GET", "/containers/" + (IDENT if known else NAME) + "/json")
    assert calls[-1] == ("DELETE", "/containers/" + IDENT + "?force=1")
    assert len(calls) == 3


@pytest.mark.parametrize("change", ["image_ref", "image_id", "inherited_label", "extra_label", "run",
    "profile", "name", "id", "cgroup", "candidate_source", "results_mode", "tasks_source", "extra_mount"])
@pytest.mark.parametrize("legacy", [False, True])
def test_container_identity_drift_never_deletes_and_keeps_record(cpu, change, legacy):
    stage, _, native = persisted(cpu, legacy=legacy)
    if change == "image_ref": native["Config"]["Image"] = "ubuntu:latest"
    elif change == "image_id": native["Image"] = "sha256:" + "f" * 64
    elif change == "inherited_label": native["Config"]["Labels"]["io.arena.base"] = "foreign"
    elif change == "extra_label": native["Config"]["Labels"]["caller-extra"] = "not allowed"
    elif change == "run": native["Config"]["Labels"]["arena.control-run"] = "e" * 32
    elif change == "profile": native["Config"]["Labels"]["arena.evaluation-profile"] = "cpu-8g-p256-v1"
    elif change == "name": native["Name"] = "/arena-eval-" + "f" * 32
    elif change == "id": native["Id"] = "f" * 64
    elif change == "cgroup": native["HostConfig"]["CgroupParent"] = "/foreign"
    elif change == "candidate_source": native["Mounts"][1]["Source"] = str(stage.parent / "other/candidate")
    elif change == "results_mode": native["Mounts"][2]["RW"] = False
    elif change == "tasks_source": native["Mounts"][0]["Source"] = "/unapproved/tasks"
    else: native["Mounts"].append(deepcopy(native["Mounts"][0]))
    instance, calls = evaluator_execution.Proxy(cpu[0]), []
    instance.request = daemon(native, calls)
    before = (stage / "record.json").read_bytes()
    with pytest.raises(Denied): instance.recover()
    assert (stage / "record.json").read_bytes() == before
    assert all(method != "DELETE" for method, _ in calls)


@pytest.mark.parametrize("change", ["digest", "id", "labels", "unapproved"])
def test_approved_image_binding_cannot_be_replaced_during_recovery(cpu, change):
    stage, _, native = persisted(cpu)
    inspected = deepcopy(EVIDENCE["image"])
    config = cpu[0]
    if change == "digest": inspected["RepoDigests"] = ["repo@sha256:" + "f" * 64]
    elif change == "id": inspected["Id"] = "sha256:" + "f" * 64
    elif change == "labels": inspected["Config"]["Labels"]["io.arena.profile"] = "other"
    else: config = replace(config, images=("sha256:" + "f" * 64,))
    instance, calls = evaluator_execution.Proxy(config), []
    instance.request = daemon(native, calls, image=inspected)
    with pytest.raises(Denied): instance.recover()
    assert stage.exists() and all(m != "DELETE" for m, _ in calls)


@pytest.mark.parametrize("failure", ["get_timeout", "get500", "image_timeout", "image404", "image500",
                                    "delete_timeout", "delete500"])
def test_recovery_transport_or_daemon_uncertainty_retains_stage(cpu, failure):
    stage, _, native = persisted(cpu, known=False)
    instance, calls = evaluator_execution.Proxy(cpu[0]), []
    instance.request = daemon(native, calls, failure=failure)
    with pytest.raises((Denied, TimeoutError)): instance.recover()
    assert stage.exists() and (stage / "record.json").exists()
    if not failure.startswith("delete"):
        assert all(method != "DELETE" for method, _ in calls)


def test_confirmed_container_404_clears_only_its_stage_without_image_lookup(cpu):
    stage, _, native = persisted(cpu, known=False)
    instance, calls = evaluator_execution.Proxy(cpu[0]), []
    instance.request = daemon(native, calls, failure="absent")
    instance.recover()
    assert not stage.exists() and len(calls) == 1


def test_unknown_create_persists_pinned_image_before_post_then_recovers(cpu, monkeypatch):
    config, body, *_ = cpu
    instance = evaluator_execution.Proxy(config)
    monkeypatch.setattr(evaluator_execution.os, "chown", lambda *args: None)
    calls = []
    def request(method, path, body=None, **kwargs):
        calls.append((method, path))
        if method == "GET": return 200, {}, json.dumps(EVIDENCE["image"]).encode()
        stage = next(config.staging_root.iterdir())
        record = json.loads((stage / "record.json").read_text())
        assert record["id"] is None and record["cpu"]["image_id"] == EVIDENCE["image"]["Id"]
        assert len(record["cpu"]["labels"]) == 10
        assert (stage / "record.json").stat().st_size <= 4096
        raise TimeoutError("POST may have created")
    instance.request = request
    with pytest.raises(TimeoutError): instance.create(body, NAME, RUN, "")
    assert [m for m, _ in calls] == ["GET", "POST"]
    stage = next(config.staging_root.iterdir())
    record = json.loads((stage / "record.json").read_text())
    restarted = evaluator_execution.Proxy(config)
    restarted.request = daemon(native_container(config, stage, record, EVIDENCE["image"]), [])
    restarted.recover()
    assert not stage.exists()


@pytest.mark.parametrize("failure", ["oversized", "missing_image", "transport", "fsync"])
def test_new_create_cannot_post_without_bounded_persisted_identity(cpu, monkeypatch, failure):
    config, body, *_ = cpu
    instance, calls = evaluator_execution.Proxy(config), []
    monkeypatch.setattr(evaluator_execution.os, "chown", lambda *args: None)
    inspected = deepcopy(EVIDENCE["image"])
    if failure == "oversized": inspected["Config"]["Labels"]["large"] = "x" * 4096
    if failure == "fsync":
        monkeypatch.setattr(recovery.os, "fsync", lambda fd: (_ for _ in ()).throw(OSError("sync failed")))
    def request(method, path, body=None, **kwargs):
        calls.append(method)
        assert method == "GET"
        if failure == "transport": raise TimeoutError("unknown image")
        return (404 if failure == "missing_image" else 200), {}, json.dumps(inspected).encode()
    instance.request = request
    with pytest.raises((Denied, OSError)): instance.create(body, NAME, RUN, "")
    assert calls == ["GET"] and not list(config.staging_root.iterdir())


def test_record_is_file_fsynced_then_atomically_replaced_then_directory_fsynced(tmp_path, monkeypatch):
    calls = []
    real_fsync, real_replace = os.fsync, os.replace
    record = {"id": None, "run": RUN, "name": NAME}
    def sync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            assert json.loads((tmp_path / "record.json").read_text()) == record
            calls.append("directory_fsync")
        else:
            pending = list(tmp_path.glob(".record-*"))
            assert len(pending) == 1 and json.loads(pending[0].read_text()) == record
            calls.append("file_fsync")
        real_fsync(fd)
    def replace(source, target):
        assert calls == ["file_fsync"]
        calls.append("replace")
        return real_replace(source, target)
    monkeypatch.setattr(recovery.os, "fsync", sync)
    monkeypatch.setattr(recovery.os, "replace", replace)
    recovery.write_record(tmp_path, record)
    assert calls == ["file_fsync", "replace", "directory_fsync"]
    assert stat.S_IMODE((tmp_path / "record.json").stat().st_mode) == 0o600


def test_legacy_recorded_profile_keeps_exact_inherited_and_profile_labels(cpu):
    config, *_ = cpu
    stage, record, _ = persisted(cpu, legacy=True)
    record['resource_profile'] = 'cpu-4g-p128-v1'
    recovery.write_record(stage, record)
    native = native_container(config, stage, record, EVIDENCE['image'])
    assert len(native['Config']['Labels']) == 11
    instance = evaluator_execution.Proxy(config)
    instance.request = daemon(native, [])
    instance.recover()
    assert not stage.exists()


@pytest.mark.parametrize('change', ['null', 'extra', 'bad_id', 'bad_label', 'wrong_run', 'wrong_root', 'unapproved'])
def test_malformed_saved_cpu_identity_is_rejected_before_daemon_even_if_container_absent(cpu, change):
    stage, record, _ = persisted(cpu)
    if change == 'null': record['cpu'] = None
    elif change == 'extra': record['cpu']['anything'] = True
    elif change == 'bad_id': record['cpu']['image_id'] = 'latest'
    elif change == 'bad_label': record['cpu']['labels']['io.arena.base'] = 1
    elif change == 'wrong_run': record['cpu']['labels']['arena.control-run'] = 'f' * 32
    elif change == 'wrong_root': record['cpu']['task_root'] = '/unapproved'
    else: record['cpu']['image'] = 'sha256:' + 'f' * 64
    recovery.write_record(stage, record)
    instance = evaluator_execution.Proxy(cpu[0])
    def forbidden(*args, **kwargs): raise AssertionError('Invalid ownership reached daemon')
    instance.request = forbidden
    with pytest.raises(Denied): instance.recover()
    assert stage.exists()


def test_raw_immutable_image_id_cannot_resolve_to_a_different_image(setup):
    config, *_ = setup
    def request(*args, **kwargs):
        return 200, {}, json.dumps({'Id': 'sha256:' + 'f' * 64, 'Config': {'Labels': {}}}).encode()
    with pytest.raises(Denied, match='different CPU image ID'):
        recovery.image_identity(request, config, config.images[0])


def padded_image(config, body, final_size):
    inspected = deepcopy(EVIDENCE["image"])
    inspected["Config"]["Labels"]["boundary"] = ""
    record = {"id": IDENT, "run": RUN, "name": NAME,
              "cpu": cpu_binding(config, body, inspected)}
    size = len(json.dumps(record, sort_keys=True, separators=(",", ":")).encode())
    assert size < final_size
    inspected["Config"]["Labels"]["boundary"] = "x" * (final_size - size)
    return inspected


def test_none_fits_but_future_container_id_exceeds_limit_so_create_never_posts(cpu, monkeypatch):
    config, body, *_ = cpu
    inspected = padded_image(config, body, recovery.RECORD_LIMIT + 31)
    pending = {"id": None, "run": RUN, "name": NAME,
               "cpu": cpu_binding(config, body, inspected)}
    encoded_size = lambda record: len(json.dumps(record, sort_keys=True, separators=(",", ":")).encode())
    assert encoded_size(pending) == recovery.RECORD_LIMIT - 31
    assert encoded_size(pending | {"id": IDENT}) == recovery.RECORD_LIMIT + 31
    monkeypatch.setattr(evaluator_execution.os, "chown", lambda *args: None)
    instance, calls = evaluator_execution.Proxy(config), []
    def request(method, path, body=None, **kwargs):
        calls.append(method)
        assert method == "GET", "Oversized future ownership must fail before POST"
        return 200, {}, json.dumps(inspected).encode()
    instance.request = request
    with pytest.raises(Denied, match="including container ID"):
        instance.create(body, NAME, RUN, "")
    assert calls == ["GET"] and not list(config.staging_root.iterdir())


@pytest.mark.parametrize("final_size", [recovery.RECORD_LIMIT - 1, recovery.RECORD_LIMIT])
def test_near_limit_record_roundtrips_null_and_acknowledged_id_then_recovers(cpu, monkeypatch, final_size):
    config, body, *_ = cpu
    inspected = padded_image(config, body, final_size)
    monkeypatch.setattr(evaluator_execution.os, "chown", lambda *args: None)
    instance = evaluator_execution.Proxy(config)
    def request(method, path, body=None, **kwargs):
        if method == "GET":
            return 200, {}, json.dumps(inspected).encode()
        stage = next(config.staging_root.iterdir())
        assert (stage / "record.json").stat().st_size == final_size - 62
        assert json.loads((stage / "record.json").read_text())["id"] is None
        return 201, {}, json.dumps({"Id": IDENT}).encode()
    instance.request = request
    instance.create(body, NAME, RUN, "")
    stage = next(config.staging_root.iterdir())
    assert (stage / "record.json").stat().st_size == final_size
    record = json.loads((stage / "record.json").read_text())
    assert record["id"] == IDENT
    os.close(instance.records[NAME]["output_fd"])  # Simulate restart without an open old proxy.
    restarted = evaluator_execution.Proxy(config)
    restarted.request = daemon(native_container(config, stage, record, inspected), [], image=inspected)
    restarted.recover()
    assert not stage.exists()
