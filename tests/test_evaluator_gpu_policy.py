"""An exact root grant supplies GPU authority; callers cannot extend it."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from arena import evaluation_resources as resources, evaluator_gpu as gpu
from arena import evaluator_policy as policy
from evaluator_gpu_helpers import NAME, RUN, prepared, root_configuration, setup


def test_exact_gpu_request_rebuilds_only_proven_devices_mounts_and_environment(prepared):
    config, body, candidate, output = prepared
    original = deepcopy(body)
    checked, cpath, opath = policy.canonical_config(body, NAME, RUN, config)
    assert body == original and (cpath, opath) == (candidate, output)
    host = checked["HostConfig"]
    assert host["Runtime"] == "runc" and host["NetworkMode"] == "none" and host["ReadonlyRootfs"]
    assert host["NanoCpus"] == 2000000000 and host["Memory"] == host["MemorySwap"] == 16 * 1024 ** 3
    assert host["PidsLimit"] == 256 and host["CapDrop"] == ["ALL"]
    assert host["Devices"] == [{"PathOnHost": node, "PathInContainer": node, "CgroupPermissions": "rw"}
                               for node, _, _ in gpu.DEVICE_NODES]
    assert [mount["Target"] for mount in host["Mounts"]] == ["/tasks", "/model", "/private-nvidia"]
    assert all(mount["ReadOnly"] for mount in host["Mounts"])
    assert "CUDA_VISIBLE_DEVICES=" + gpu.DEVICE_UUID in checked["Env"]
    assert "NVIDIA_VISIBLE_DEVICES=void" in checked["Env"]
    assert "LD_LIBRARY_PATH=/private-nvidia" in checked["Env"]
    assert all(checked["Labels"][key] == value for key, value in gpu.IMAGE_LABELS.items())
    assert checked["Labels"]["arena.task-manifest"] == config.lmx_gpu.task_manifest_sha256
    assert checked["Labels"]["arena.gpu-driver"] == gpu.DRIVER_SHA
    assert checked["Labels"]["arena.model-assets"] == gpu.MODEL_SHA


@pytest.mark.parametrize("change", ["no-config", "no-profile", "other-image", "other-task", "other-root",
    "timeout", "gpu-env", "driver-env", "extra-mount", "device", "all-gpus", "nvidia-runtime",
    "device-rule", "fake-binding", "memory", "cpus", "pids", "swap"])
def test_gpu_authority_cannot_be_selected_or_expanded_by_the_caller(prepared, change, tmp_path):
    config, body, *_ = prepared
    if change == "no-config": config = replace(config, lmx_gpu=None)
    elif change == "no-profile": del body["Labels"]["arena.evaluation-profile"]
    elif change == "other-image":
        body["Image"] = "sha256:" + "a" * 64
        config = replace(config, images=(body["Image"],))
    elif change == "other-task": body["Cmd"][5] = "some-other-gpu-task"
    elif change == "other-root":
        other = tmp_path.resolve() / "other"; other.mkdir()
        config = replace(config, additional_tasks_roots=(other,))
        body["HostConfig"]["Mounts"][0]["Source"] = str(other)
    elif change == "timeout": body["Cmd"][11] = "601"
    elif change == "gpu-env": body["Env"].append("CUDA_VISIBLE_DEVICES=all")
    elif change == "driver-env": body["Env"].append("LD_LIBRARY_PATH=/candidate")
    elif change == "extra-mount": body["HostConfig"]["Mounts"].append(
        {"Type": "bind", "Source": "/etc", "Target": "/model", "ReadOnly": True})
    elif change == "device": body["HostConfig"]["Devices"] = [{"PathOnHost": "/dev/nvidia1"}]
    elif change == "all-gpus": body["HostConfig"]["DeviceRequests"] = [{"Count": -1, "Capabilities": [["gpu"]]}]
    elif change == "nvidia-runtime": body["HostConfig"]["Runtime"] = "nvidia"
    elif change == "device-rule": body["HostConfig"]["DeviceCgroupRules"] = ["c *:* rwm"]
    elif change == "fake-binding": body["Labels"]["arena.gpu-capability"] = "f" * 64
    elif change == "memory": body["HostConfig"]["Memory"] *= 2
    elif change == "cpus": body["HostConfig"]["NanoCpus"] *= 2
    elif change == "pids": body["HostConfig"]["PidsLimit"] *= 2
    else: body["HostConfig"]["MemorySwap"] = -1
    with pytest.raises(policy.Denied):
        policy.canonical_config(body, NAME, RUN, config)


@pytest.mark.parametrize("key,value", [("memory.max", str(18 * 1024 ** 3 - 1)),
    ("pids.max", "319"), ("cpu.max", "300000 100000"), ("cpu.max", "max 100000")])
def test_gpu_needs_finite_parent_engine_headroom(prepared, key, value):
    config, body, *_ = prepared
    path = resources.CGROUP_MOUNT / "arena-workers" / ("arena-control-" + RUN) / key
    path.write_text(value)
    with pytest.raises(policy.Denied, match="envelope"):
        policy.canonical_config(body, NAME, RUN, config)


def test_gpu_is_not_a_generic_cpu_resource_grant(prepared):
    config, *_ = prepared
    assert gpu.PROFILE not in resources.PROFILES
    with pytest.raises(ValueError):
        resources.parse_grants([{"image": gpu.IMAGE, "profile": gpu.PROFILE, "task_ids": list(gpu.TASK_IDS)}], config.images)
    with pytest.raises(ValueError):
        resources.budget(gpu.PROFILE)


@pytest.mark.parametrize("change", [None, "extra", "image", "task", "missing-task", "duplicate-task", "device",
    "minor", "bool-minor", "manifest", "model", "driver", "relative", "overlap"])
def test_optional_root_configuration_has_no_unreviewed_extension_points(prepared, change):
    config, *_ = prepared
    value = root_configuration(config.lmx_gpu)
    if change == "extra": value["gpus"] = "all"
    elif change == "image": value["image"] = gpu.IMAGE.replace("706361", "aaaaaa")
    elif change == "task": value["task_ids"][0] = "other-task"
    elif change == "missing-task": value["task_ids"].pop()
    elif change == "duplicate-task": value["task_ids"][0] = value["task_ids"][1]
    elif change == "device": value["device_uuid"] = "GPU-other"
    elif change == "minor": value["device_minor"] = 1
    elif change == "bool-minor": value["device_minor"] = False
    elif change == "manifest": value["task_manifest_sha256"] = "latest"
    elif change == "model": value["model_manifest_sha256"] = "a" * 64
    elif change == "driver": value["driver_manifest_sha256"] = "a" * 64
    elif change == "relative": value["model_root"] = "../model"
    elif change == "overlap": value["driver_root"] = value["model_root"]
    if change:
        with pytest.raises(policy.Denied):
            gpu.LmxGpu.parse(value, config)
    else:
        assert gpu.LmxGpu.parse(value, config) == config.lmx_gpu


def test_configuration_reader_preserves_cpu_defaults_and_parses_explicit_gpu(prepared, tmp_path):
    config, *_ = prepared
    value = {"docker_socket": str(config.docker_socket), "socket_path": str(config.socket_path),
        "staging_root": str(config.staging_root), "tasks_root": str(config.tasks_root),
        "run_roots": [str(p) for p in config.run_roots], "images": [gpu.IMAGE],
        "worker_uid": 998, "worker_gid": 998}
    path = tmp_path / "config.json"; path.write_text(json.dumps(value))
    assert policy.Config.read(path).lmx_gpu is None
    value["lmx_gpu"] = root_configuration(config.lmx_gpu)
    path.write_text(json.dumps(value))
    assert policy.Config.read(path).lmx_gpu == config.lmx_gpu
