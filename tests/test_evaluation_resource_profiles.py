"""Larger canonical budgets require explicit grants and an adequate run envelope."""
from copy import deepcopy
from dataclasses import replace
import importlib.util
import json
from pathlib import Path

import pytest

from arena import evaluation_resources as resources
from arena import evaluator_proxy as proxy
from arena.frameworks import evaluation

spec = importlib.util.spec_from_file_location("resource_proxy_fixture",
    Path(__file__).with_name("test_evaluator_proxy.py"))
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
setup = fixture.setup
RUN, NAME, IMAGE = fixture.RUN, fixture.NAME, fixture.IMAGE
spec = importlib.util.spec_from_file_location("resource_evaluation_fixture",
    Path(__file__).parent / "frameworks/test_evaluation.py")
execution_fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(execution_fixture)
evaluation_inputs = execution_fixture.evaluation_inputs


def grant(profile="cpu-4g-p128-v1", task="fixture-task", image=IMAGE):
    return {"image": image, "profile": profile, "task_ids": [task]}


def parent(tmp_path, monkeypatch, *, memory=8192, pids=512):
    root = tmp_path.resolve() / "cgroup"
    directory = root / "arena-workers" / ("arena-control-" + RUN)
    directory.mkdir(parents=True)
    (directory / "memory.max").write_text(str(memory * 1024 ** 2))
    (directory / "pids.max").write_text(str(pids))
    monkeypatch.setattr(resources, "CGROUP_MOUNT", root)
    return directory


def extended(setup, profile):
    config, original, candidate, output = setup
    body = deepcopy(original)
    selected = resources.budget(profile)
    task = body["Cmd"][5]
    config = replace(config, resource_grants=resources.parse_grants([grant(profile, task)], config.images))
    body["Labels"]["arena.evaluation-profile"] = profile
    body["HostConfig"].update(Memory=selected["memory_mb"] * 1024 ** 2,
                              MemorySwap=selected["memory_mb"] * 1024 ** 2, PidsLimit=selected["pids"])
    return config, body, candidate, output


@pytest.mark.parametrize("profile", list(resources.PROFILES))
def test_exact_profile_is_rebuilt_and_remains_contained(setup, tmp_path, monkeypatch, profile):
    parent(tmp_path, monkeypatch, memory=16384)
    config, body, candidate, output = extended(setup, profile)
    checked, actual_candidate, actual_output = proxy.canonical_config(body, NAME, RUN, config)
    selected = resources.budget(profile)
    assert actual_candidate == candidate and actual_output == output
    host = checked["HostConfig"]
    assert host["Memory"] == host["MemorySwap"] == selected["memory_mb"] * 1024 ** 2
    assert host["PidsLimit"] == selected["pids"]
    assert host["NetworkMode"] == "none" and host["ReadonlyRootfs"] is True
    assert host["NanoCpus"] == 1_000_000_000 and host["CapDrop"] == ["ALL"]
    assert checked["Labels"]["arena.evaluation-profile"] == profile
    envelope = resources.worker_resources(profile)
    assert envelope["memory_mb"] >= selected["memory_mb"] + 2048
    assert envelope["pids"] >= selected["pids"] + 64


@pytest.mark.parametrize("change", ["no_grant", "wrong_task", "wrong_image", "wrong_profile", "memory", "pids", "swap", "missing_label", "null_label"])
def test_expanded_resource_request_cannot_escape_its_exact_grant(setup, tmp_path, monkeypatch, change):
    parent(tmp_path, monkeypatch)
    config, body, *_ = extended(setup, "cpu-4g-p128-v1")
    if change == "no_grant": config = replace(config, resource_grants=())
    elif change == "wrong_task": body["Cmd"][5] = "unapproved-task"
    elif change == "wrong_image": body["Image"] = "sha256:" + "e" * 64
    elif change == "wrong_profile": body["Labels"]["arena.evaluation-profile"] = "cpu-8g-p256-v1"
    elif change == "memory": body["HostConfig"]["Memory"] *= 2
    elif change == "pids": body["HostConfig"]["PidsLimit"] *= 2
    elif change == "swap": body["HostConfig"]["MemorySwap"] = -1
    elif change == "missing_label": del body["Labels"]["arena.evaluation-profile"]
    else: body["Labels"]["arena.evaluation-profile"] = None
    with pytest.raises(proxy.Denied): proxy.canonical_config(body, NAME, RUN, config)


@pytest.mark.parametrize("memory,pids", [(4096, 512), (6143, 512), (8192, 128), (8192, 191)])
def test_outer_run_must_reserve_engine_headroom(setup, tmp_path, monkeypatch, memory, pids):
    parent(tmp_path, monkeypatch, memory=memory, pids=pids)
    config, body, *_ = extended(setup, "cpu-4g-p128-v1")
    with pytest.raises(proxy.Denied, match="envelope"):
        proxy.canonical_config(body, NAME, RUN, config)


@pytest.mark.parametrize("change", ["unlimited_memory", "unlimited_pids", "linked_file", "linked_parent", "missing"])
def test_resource_parent_requires_real_finite_limits(setup, tmp_path, monkeypatch, change):
    directory = parent(tmp_path, monkeypatch)
    if change.startswith("unlimited"):
        (directory / ("memory.max" if change.endswith("memory") else "pids.max")).write_text("max")
    elif change == "linked_file":
        target = directory / "real-memory.max"
        (directory / "memory.max").rename(target)
        (directory / "memory.max").symlink_to(target)
    elif change == "linked_parent":
        target = directory.with_name("actual")
        directory.rename(target)
        directory.symlink_to(target, target_is_directory=True)
    else: (directory / "memory.max").unlink()
    config, body, *_ = extended(setup, "cpu-4g-p128-v1")
    with pytest.raises(proxy.Denied, match="envelope"):
        proxy.canonical_config(body, NAME, RUN, config)


@pytest.mark.parametrize("value", [None, {}, [grant(image="sha256:" + "e" * 64)],
    [grant(profile="arbitrary")], [grant(task="*")], [{**grant(), "task_ids": []}],
    [{**grant(), "task_ids": ["fixture-task", "fixture-task"]}], [grant(), grant()],
    [grant(), grant(profile="cpu-8g-p256-v1")], [{**grant(), "memory_mb": 8192}]])
def test_config_grants_refuse_implicit_or_ambiguous_authority(value):
    with pytest.raises(ValueError): resources.parse_grants(value, (IMAGE,))


@pytest.mark.parametrize("value", [True, 4096, "4g", "cpu-32g-p256-v1", {}, []])
def test_only_finite_named_profiles_exist(value):
    with pytest.raises(ValueError): resources.budget(value)


def test_config_reader_preserves_default_and_validates_explicit_grants(tmp_path):
    value = {"docker_socket": "/run/docker.sock", "socket_path": "/run/evaluator.sock",
        "staging_root": "/run/stage", "tasks_root": "/srv/arena/tasks", "run_roots": ["/srv/arena/runs"],
        "images": [IMAGE], "worker_uid": 998, "worker_gid": 998}
    path = tmp_path / "proxy.json"
    path.write_text(json.dumps(value))
    assert proxy.Config.read(path).resource_grants == ()
    value["resource_grants"] = [grant()]
    path.write_text(json.dumps(value))
    assert proxy.Config.read(path).resource_grants == ((IMAGE, "cpu-4g-p128-v1", ("fixture-task",)),)
    value["resource_grants"][0]["task_ids"] = ["*"]
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError): proxy.Config.read(path)


def test_legacy_profile_does_not_require_new_files_or_grants(setup, monkeypatch):
    def forbidden(*args): raise AssertionError("Legacy profile does not read a new resource grant")
    monkeypatch.setattr(resources, "require_parent_budget", forbidden)
    config, body, *_ = setup
    checked, _, _ = proxy.canonical_config(body, NAME, RUN, config)
    assert checked["HostConfig"]["Memory"] == 2 * 1024 ** 3
    assert checked["HostConfig"]["PidsLimit"] == 128


@pytest.mark.parametrize("profile", list(resources.PROFILES))
def test_execution_records_exact_profile_and_forbids_swap(evaluation_inputs, monkeypatch, tmp_path, profile):
    config, candidate, _, _ = evaluation_inputs
    _, _, receipts, hierarchy, ident = execution_fixture.controlled_context(tmp_path, monkeypatch)
    config["execution"] = {"kind": "docker", "image": IMAGE, "python": "python",
        "require_control_cgroup": True, "resource_profile": profile}
    output = receipts / ("e" * 32)
    calls, _ = execution_fixture.fake_docker(monkeypatch, config, candidate, output)
    result = evaluation.evaluate(config, candidate, output)
    assert result["status"] == "completed"
    assert result["execution"] == config["execution"]
    assert json.loads((output / "receipt.json").read_text())["execution"] == config["execution"]
    argv = next(args for args, _ in calls if args[:2] == ["docker", "run"])
    limits = resources.budget(profile)
    assert argv[argv.index("--memory") + 1] == f"{limits['memory_mb']}m"
    assert argv[argv.index("--memory-swap") + 1] == f"{limits['memory_mb']}m"
    assert argv[argv.index("--pids-limit") + 1] == str(limits["pids"])
    assert argv[argv.index("--cgroup-parent") + 1] == hierarchy
    labels = [argv[index + 1] for index, arg in enumerate(argv) if arg == "--label"]
    assert set(labels) == {"arena.evaluator=canonical-v1", "arena.control-run=" + ident,
                           "arena.evaluation-profile=" + profile}


@pytest.mark.parametrize("profile", [None, True, "arbitrary", "cpu-32g-p256-v1", {}, 4096])
def test_bad_explicit_execution_budget_is_rejected_before_execution(evaluation_inputs, profile):
    config, candidate, output, _ = evaluation_inputs
    config["execution"] = {"kind": "docker", "image": IMAGE, "python": "python", "resource_profile": profile}
    with pytest.raises(ValueError): evaluation.prepare_evaluation(config, candidate, output)
    assert not output.exists()
