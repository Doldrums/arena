"""Old and new immutable libraries share a bounded capability, not a prefix grant."""
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import socket

import pytest

from arena import evaluator_execution
from arena.evaluator_policy import Denied
from arena.evaluator_execution import Proxy
from test_engine_broker import engine, RUN as ENGINE_RUN
from test_evaluator_proxy import setup, fake_create, NAME, RUN


def second_library(primary):
    path = primary.with_name("tasks-next")
    path.mkdir(mode=0o755)
    (path / "run.py").write_text("# separately reviewed evaluator revision\n")
    return path


def write_config(path, config):
    value = {key: item for key, item in asdict(config).items() if item is not None}
    value.update(worker_uid=998, worker_gid=998)
    path.write_text(json.dumps(value, default=str))
    return json.loads(path.read_text())


@pytest.mark.parametrize("kind", ["engine", "evaluator"])
def test_config_preserves_legacy_root_and_accepts_explicit_revision(request, tmp_path, kind):
    original = request.getfixturevalue("engine")["config"] if kind == "engine" else request.getfixturevalue("setup")[0]
    config_path = tmp_path / "policy.json"
    value = write_config(config_path, original)
    value.pop("additional_tasks_roots")
    config_path.write_text(json.dumps(value))
    legacy = type(original).read(config_path)
    assert legacy.library_roots == (original.tasks_root,)
    extra = second_library(original.tasks_root)
    value["additional_tasks_roots"] = [str(extra)]
    config_path.write_text(json.dumps(value))
    upgraded = type(original).read(config_path)
    assert upgraded.tasks_root == original.tasks_root
    assert upgraded.additional_tasks_roots == (extra,)
    assert upgraded.library_roots == (original.tasks_root, extra)


@pytest.mark.parametrize("kind", ["engine", "evaluator"])
@pytest.mark.parametrize("bad", ["string", "relative", "traversal", "same", "child", "parent", "duplicate", "many", "nonstring"])
def test_additional_root_config_is_explicit_disjoint_and_bounded(request, tmp_path, kind, bad):
    config = request.getfixturevalue("engine")["config"] if kind == "engine" else request.getfixturevalue("setup")[0]
    root = config.tasks_root
    extra = root.with_name("tasks-next")
    choices = {
        "string": str(extra), "relative": ["tasks-next"],
        "traversal": [str(root / ".." / "tasks-next")], "same": [str(root)],
        "child": [str(root / "child")], "parent": [str(root.parent)],
        "duplicate": [str(extra), str(extra)], "nonstring": [None],
        "many": [str(root.with_name(f"tasks-{index}")) for index in range(17)],
    }
    path = tmp_path / "policy.json"
    value = write_config(path, config)
    value["additional_tasks_roots"] = choices[bad]
    path.write_text(json.dumps(value))
    with pytest.raises(Denied):
        type(config).read(path)


@pytest.mark.parametrize("selected", ["legacy", "next"])
def test_evaluation_roundtrip_uses_exact_selected_library(setup, monkeypatch, selected):
    config, body, candidate, output = setup
    extra = second_library(config.tasks_root)
    config = replace(config, additional_tasks_roots=(extra,))
    chosen = config.tasks_root if selected == "legacy" else extra
    mount = next(item for item in body["HostConfig"]["Mounts"] if item["Target"] == "/tasks")
    mount.update(Source=str(chosen), BindOptions={"Propagation": "rprivate"})
    proxy = Proxy(config); captures = []; fake_create(proxy, captures)
    monkeypatch.setattr(evaluator_execution.os, "chown", lambda *args: None)
    monkeypatch.setattr(evaluator_execution.os, "fchown", lambda *args: None)
    assert proxy.create(body, NAME, RUN, "")[0] == 201
    rebuilt = captures[0][2]
    mounts = rebuilt["HostConfig"]["Mounts"]
    assert mounts[0] == {"Type": "bind", "Source": str(chosen), "Target": "/tasks", "ReadOnly": True}
    assert Path(mounts[1]["Source"]) != candidate and Path(mounts[2]["Source"]) != output
    assert rebuilt["HostConfig"]["NetworkMode"] == "none"
    assert rebuilt["HostConfig"]["CgroupParent"].endswith(RUN)
    record = proxy.records[NAME]
    (record["stage"] / "results/native.json").write_text('{"valid":true,"score":0.25}')
    proxy.publish(record)
    assert json.loads((output / "native.json").read_text()) == {"valid": True, "score": 0.25}
    proxy.remove(NAME, record)
    assert not (chosen / "native.json").exists()


@pytest.mark.parametrize("attack", ["unlisted", "prefix-child", "traversal", "symlink", "ancestor-symlink"])
def test_unapproved_or_linked_library_never_reaches_evaluator_daemon(setup, attack):
    config, body, *_ = setup
    extra = second_library(config.tasks_root)
    config = replace(config, additional_tasks_roots=(extra,))
    source = extra
    if attack == "unlisted":
        source = extra.with_name("unlisted"); source.mkdir()
    elif attack == "prefix-child":
        source = extra / "child"; source.mkdir()
    elif attack == "traversal":
        source = extra / ".." / config.tasks_root.name
    elif attack == "symlink":
        moved = extra.with_name("actual"); extra.rename(moved)
        extra.symlink_to(moved, target_is_directory=True)
    else:
        alias = extra.with_name("alias"); alias.symlink_to(extra, target_is_directory=True)
        (extra / "nested").mkdir()
        source = alias / "nested"
        config = replace(config, additional_tasks_roots=(source,))
    next(item for item in body["HostConfig"]["Mounts"] if item["Target"] == "/tasks")["Source"] = str(source)
    proxy = Proxy(config); captures = []; fake_create(proxy, captures)
    with pytest.raises((Denied, OSError)):
        proxy.create(body, NAME, RUN, "")
    assert not captures and not list(config.staging_root.iterdir())


@pytest.mark.parametrize("extra_enabled", [False, True])
def test_broker_mounts_only_approved_libraries_readonly(engine, extra_enabled):
    e = engine
    if extra_enabled:
        extra = second_library(e["config"].tasks_root)
        e["broker"].config = replace(e["config"], additional_tasks_roots=(extra,))
    expected = e["broker"].config.library_roots
    frames = []
    e["broker"].run(ENGINE_RUN, e["digest"], frames.append, lambda: False)
    assert frames[-1]["status"] == "completed"
    created = next(body for method, path, body in e["calls"] if "/create?" in path)
    mounts = created["HostConfig"]["Mounts"]
    assert [mount for mount in mounts if mount["Source"] in {str(path) for path in expected}] == [
        {"Type": "bind", "Source": str(path), "Target": str(path), "ReadOnly": True} for path in expected]
    assert len(mounts) == 4 + len(expected)


def test_broker_rechecks_library_links_before_staging_or_create(engine):
    e = engine
    extra = e["config"].tasks_root.with_name("tasks-next")
    extra.symlink_to(e["config"].tasks_root, target_is_directory=True)
    e["broker"].config = replace(e["config"], additional_tasks_roots=(extra,))
    plan = e["broker"].plan(ENGINE_RUN, e["digest"])
    with pytest.raises((Denied, OSError)):
        e["broker"].prepare(plan)
    assert not any(method == "POST" for method, *_ in e["calls"])
    assert not list(e["config"].staging_root.iterdir())


def mock_root_host(monkeypatch, anchor, stage, foreign_owner=None):
    """Mock Linux identity only; retain real path walking, links and tree modes."""
    original_stat, original_read = Path.stat, Path.read_text
    def stat_path(path, *args, **kwargs):
        fields = list(original_stat(path, *args, **kwargs))
        fields[4] = 123 if path == foreign_owner else 0
        if not path.is_relative_to(anchor):
            fields[0] &= ~0o022  # macOS temp ancestors are not a deployment host.
        return os.stat_result(fields)
    def read_path(path, *args, **kwargs):
        if str(path) == "/proc/self/mountinfo":
            return f"1 0 0:1 / {stage} rw - tmpfs tmpfs rw,size=256m\n"
        return original_read(path, *args, **kwargs)
    monkeypatch.setattr(Path, "stat", stat_path)
    monkeypatch.setattr(Path, "read_text", read_path)
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    monkeypatch.setattr(socket, "SO_PEERCRED", 17, raising=False)


@pytest.mark.parametrize("kind", ["engine", "evaluator"])
@pytest.mark.parametrize("attack", ["none", "writable-file", "foreign-owner", "nested-link", "root-link"])
def test_all_libraries_receive_host_ownership_and_link_checks(request, monkeypatch, kind, attack):
    config = request.getfixturevalue("engine")["config"] if kind == "engine" else request.getfixturevalue("setup")[0]
    config = replace(config, socket_path=config.socket_path.resolve())
    config.staging_root.chmod(0o700)
    extra = second_library(config.tasks_root)
    target = extra / "run.py"
    config = replace(config, additional_tasks_roots=(extra,))
    if attack == "writable-file":
        target.chmod(0o664)
    elif attack == "nested-link":
        (extra / "link").symlink_to(config.tasks_root, target_is_directory=True)
    elif attack == "root-link":
        moved = extra.with_name("actual"); extra.rename(moved)
        extra.symlink_to(moved, target_is_directory=True)
    mock_root_host(monkeypatch, config.tasks_root.parent, config.staging_root,
                   foreign_owner=target if attack == "foreign-owner" else None)
    check = config.host_check if kind == "engine" else config.validate_host
    if attack == "none":
        check()
    else:
        with pytest.raises((Denied, OSError)):
            check()
