"""Inert fixtures for GPU policy and lifecycle tests; never require a GPU."""
from copy import deepcopy
from dataclasses import replace
import importlib.util
import os
from pathlib import Path
import tempfile

import pytest

from arena import evaluation_resources as resources, evaluator_gpu as gpu
from arena import evaluator_gpu_leases as leases

SPEC = importlib.util.spec_from_file_location("gpu_proxy_fixture", Path(__file__).with_name("test_evaluator_proxy.py"))
fixtures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixtures)
setup = fixtures.setup
RUN, NAME, IDENT = fixtures.RUN, fixtures.NAME, fixtures.IDENT


@pytest.fixture
def prepared(setup, tmp_path, monkeypatch):
    config, original, candidate, output = setup
    root = tmp_path.resolve()
    capability = gpu.LmxGpu(config.tasks_root, root / "manifest.json", "e" * 64,
                            root / "model", root / "model.json", root / "driver", root / "driver.json")
    config = replace(config, images=(gpu.IMAGE,), timeout_seconds=1200, lmx_gpu=capability)
    body = deepcopy(original)
    body["Image"] = gpu.IMAGE
    body["Cmd"][5], body["Cmd"][11] = gpu.TASK_IDS[0], "600"
    body["Labels"]["arena.evaluation-profile"] = gpu.PROFILE
    body["HostConfig"].update(NanoCpus=2000000000, Memory=16 * 1024 ** 3,
                              MemorySwap=16 * 1024 ** 3, PidsLimit=256)
    cgroup = root / "cgroup"
    parent = cgroup / "arena-workers" / ("arena-control-" + RUN)
    parent.mkdir(parents=True)
    for name, value in (("memory.max", str(20 * 1024 ** 3)), ("pids.max", "512"), ("cpu.max", "400000 100000")):
        (parent / name).write_text(value)
    monkeypatch.setattr(resources, "CGROUP_MOUNT", cgroup)
    monkeypatch.setattr(gpu.LmxGpu, "validate_host", lambda self: None)
    return config, body, candidate, output


@pytest.fixture
def lease_root(monkeypatch):
    with tempfile.TemporaryDirectory(prefix=".arena-gpu-leases-", dir=Path.home().resolve()) as directory:
        path = Path(directory) / "state"
        path.mkdir(mode=0o700)
        monkeypatch.setattr(leases, "STATE_ROOT", path)
        monkeypatch.setattr(leases, "OWNER_UID", os.getuid())
        yield path


def root_configuration(capability):
    return {"profile": gpu.PROFILE, "image": gpu.IMAGE, "task_ids": list(gpu.TASK_IDS),
            "tasks_root": str(capability.tasks_root), "task_manifest": str(capability.task_manifest),
            "task_manifest_sha256": capability.task_manifest_sha256,
            "model_root": str(capability.model_root), "model_manifest": str(capability.model_manifest),
            "model_manifest_sha256": gpu.MODEL_SHA, "driver_root": str(capability.driver_root),
            "driver_manifest": str(capability.driver_manifest), "driver_manifest_sha256": gpu.DRIVER_SHA,
            "device_uuid": gpu.DEVICE_UUID, "device_minor": 0}


def abandon(instance):
    """Simulate process exit without erasing the persisted recovery record."""
    for record in instance.records.values():
        if not record.get("closed"):
            os.close(record["output_fd"])
            record["closed"] = True
    if instance.gpu_leases.current:
        instance.gpu_leases.current.close_descriptors()
