"""Complete fixture trees verify host identity without a model or GPU."""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace

import pytest

from arena import evaluator_gpu as gpu, evaluator_gpu_integrity as integrity
from arena.evaluator_policy import Denied


def write(path, raw, mode=0o444):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    path.chmod(mode)
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw)}


def lock(path, value):
    raw = json.dumps(value).encode()
    write(path, raw, 0o600)
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def trees(monkeypatch):
    monkeypatch.setattr(integrity, "OWNER_UID", os.getuid())
    with tempfile.TemporaryDirectory(prefix=".arena-gpu-tree-", dir=Path.home().resolve()) as directory:
        root = Path(directory)
        tasks, model, driver = [root / name for name in ("tasks", "model", "driver")]
        for path in (tasks, model, driver): path.mkdir()
        task_files = {}
        for task in gpu.TASK_IDS:
            for filename in ("task.json", "evaluator.py"):
                name = f"suite/{task}/{filename}"
                task_files[name] = write(tasks / name, b"trusted task")["sha256"]
        task_files["suite/other-science/evaluator.py"] = write(tasks / "suite/other-science/evaluator.py", b"other science")["sha256"]
        task_sha = lock(root / "tasks.json", {"schema": "arena.task-library/1", "files": task_files})
        model_files = {f"component/file-{index}.bin": write(model / f"component/file-{index}.bin", str(index).encode())
                       for index in range(17)}
        model_sha = lock(root / "model.json", {"schema": "arena.lmx-sd-assets/1",
            "model_id": "CompVis/stable-diffusion-v1-4", "revision": "2880f2ca379f41b0226444936bb7a6766a227587",
            "files": model_files})
        rows = []
        for index in range(8):
            name = f"library{index}.so.580.95.05"
            soname = f"library{index}.so.1" if index < 4 else name
            rows.append({"file": name, "soname": soname, **write(driver / name, b"ELF" + bytes([index]))})
            if soname != name: (driver / soname).symlink_to(name)
        driver_sha = lock(root / "driver.json", {"schema": "arena.private-nvidia-userland/1", "files": rows})
        monkeypatch.setattr(integrity, "MODEL_SHA", model_sha)
        monkeypatch.setattr(integrity, "DRIVER_SHA", driver_sha)
        for path in (model, model / "component", driver): path.chmod(0o555)
        yield gpu.LmxGpu(tasks, root / "tasks.json", task_sha, model, root / "model.json", driver, root / "driver.json")


def test_complete_task_model_and_driver_inventories_are_verified(trees):
    integrity.task_tree(trees)
    integrity.model_tree(trees)
    integrity.driver_tree(trees)


@pytest.mark.parametrize("mutation", ["other-task", "missing-task", "extra-source", "source-link",
                                   "writable-parent", "manifest-bytes", "missing-lmx-definition"])
def test_full_library_identity_includes_non_lmx_tasks(trees, mutation):
    other = trees.tasks_root / "suite/other-science/evaluator.py"
    if mutation == "other-task":
        other.chmod(0o644); other.write_bytes(b"changed evaluator"); other.chmod(0o444)
    elif mutation == "missing-task": other.unlink()
    elif mutation == "extra-source": write(trees.tasks_root / "unreviewed.py", b"source")
    elif mutation == "source-link":
        other.unlink(); other.symlink_to(trees.task_manifest)
    elif mutation == "writable-parent": other.parent.chmod(0o777)
    elif mutation == "manifest-bytes": trees.task_manifest.write_text("{}")
    elif mutation == "missing-lmx-definition":
        value = json.loads(trees.task_manifest.read_text())
        key = f"suite/{gpu.TASK_IDS[0]}/evaluator.py"
        del value["files"][key]
        (trees.tasks_root / key).unlink()
        sha = lock(trees.task_manifest, value)
        trees = replace(trees, task_manifest_sha256=sha)
    with pytest.raises((Denied, OSError)):
        integrity.task_tree(trees)


@pytest.mark.parametrize("mutation", ["missing", "extra-index", "bytes", "symlink", "writable-file", "writable-root"])
def test_model_cannot_load_unregistered_or_mutable_weights(trees, mutation):
    target = trees.model_root / "component/file-0.bin"
    trees.model_root.chmod(0o755); target.parent.chmod(0o755)
    if mutation == "missing": target.unlink()
    elif mutation == "extra-index": write(trees.model_root / "pytorch_model.bin.index.json", b"redirected weights")
    elif mutation == "bytes":
        target.chmod(0o644); target.write_bytes(b"wrong"); target.chmod(0o444)
    elif mutation == "symlink":
        target.unlink(); target.symlink_to(trees.model_manifest)
    elif mutation == "writable-file": target.chmod(0o644)
    target.parent.chmod(0o555)
    if mutation != "writable-root": trees.model_root.chmod(0o555)
    with pytest.raises((Denied, OSError)):
        integrity.model_tree(trees)


@pytest.mark.parametrize("mutation", ["bytes", "extra-library", "missing-link", "escape-link",
                                    "indirect-link", "regular-to-link", "writable-library", "manifest"])
def test_only_reviewed_driver_bytes_and_direct_soname_links_are_allowed(trees, mutation):
    target = trees.driver_root / "library0.so.580.95.05"
    alias = trees.driver_root / "library0.so.1"
    trees.driver_root.chmod(0o755)
    if mutation == "bytes":
        target.chmod(0o644); target.write_bytes(b"changed"); target.chmod(0o444)
    elif mutation == "extra-library": write(trees.driver_root / "inject.so", b"unreviewed")
    elif mutation == "missing-link": alias.unlink()
    elif mutation in ("escape-link", "indirect-link"):
        alias.unlink(); alias.symlink_to("../driver.json" if mutation == "escape-link" else "library1.so.1")
    elif mutation == "regular-to-link":
        target.unlink(); target.symlink_to(trees.driver_manifest)
    elif mutation == "writable-library": target.chmod(0o644)
    else: trees.driver_manifest.write_text("{}")
    trees.driver_root.chmod(0o555)
    with pytest.raises((Denied, OSError)):
        integrity.driver_tree(trees)


@pytest.mark.parametrize("mutation", [None, "version", "uuid", "minor", "duplicate-uuid",
                                    "device-minor", "device-major", "device-symlink", "device-owner"])
def test_kernel_identity_and_device_nodes_match_the_reviewed_uuid(tmp_path, monkeypatch, mutation):
    version = tmp_path / "version"
    version.write_text("NVRM version: NVIDIA UNIX Kernel Module  " +
                       ("550.54.14" if mutation == "version" else "580.95.05") + "\n")
    root = tmp_path / "gpus"; (root / "pci0").mkdir(parents=True)
    uuid = "GPU-other" if mutation == "uuid" else gpu.DEVICE_UUID
    raw = f"GPU UUID: {uuid}\nDevice Minor: " + ("1" if mutation == "minor" else "0") + "\n"
    (root / "pci0/information").write_text(raw)
    if mutation == "duplicate-uuid":
        (root / "pci1").mkdir(); (root / "pci1/information").write_text(raw)
    monkeypatch.setattr(integrity, "KERNEL_VERSION", version)
    monkeypatch.setattr(integrity, "GPU_INFORMATION", root)
    original = Path.lstat
    # Synthetic device IDs avoid Darwin's signed makedev representation.
    monkeypatch.setattr(integrity.os, "major", lambda value: value >> 16)
    monkeypatch.setattr(integrity.os, "minor", lambda value: value & 65535)
    nodes = {name: (major, minor) for name, major, minor in gpu.DEVICE_NODES}
    def lstat(path):
        if str(path) not in nodes: return original(path)
        major, minor = nodes[str(path)]
        if str(path) == "/dev/nvidia0":
            if mutation == "device-major": major += 1
            if mutation == "device-minor": minor += 1
        return SimpleNamespace(st_mode=(stat.S_IFLNK if mutation == "device-symlink" else stat.S_IFCHR) | 0o666,
                               st_uid=1 if mutation == "device-owner" else 0, st_rdev=(major << 16) | minor)
    monkeypatch.setattr(Path, "lstat", lstat)
    if mutation:
        with pytest.raises(Denied): integrity.device_identity()
    else:
        integrity.device_identity()
