"""One reviewed LMX GPU capability; never a generic GPU Docker grant."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

PROFILE = "lmx-sd14-gpu-v1"
IMAGE = "127.0.0.1:5000/empira/canonical-lmx-gpu@sha256:706361285badbab78bd6099e70135786f1ed6a6c28ea95fef97932915fc6e92d"
IMAGE_ID = "sha256:8220bcde62653228d91e3e018ff47ffac8c09f697f07966dcc5b8f40c2067f00"
MODEL_SHA = "d0317d08be943f5105f7bd148c9bad6f5dba6e07bed85ed63007bdae3418c9c5"
DRIVER_SHA = "d9a17949e4e571befde575cc48a6333fdaee20c16873c9190f934551051b938b"
DRIVER_VERSION = "580.95.05"
DEVICE_UUID = "GPU-3e124a34-572b-f732-33cb-d3a162919611"
TASK_IDS = tuple(sorted("lmx-stable-diffusion-excess-" + color for color in ("red", "green", "blue")))
GPU_BUDGET = {"cpus": 2, "memory_mb": 16384, "pids": 256}
DEVICE_NODES = (("/dev/nvidia0", 195, 0), ("/dev/nvidiactl", 195, 255), ("/dev/nvidia-uvm", 236, 0))
HASH = re.compile(r"[0-9a-f]{64}")
IMAGE_LABELS = {
    "io.arena.base": "127.0.0.1:5000/empira/canonical-small-cpu@sha256:5483308aca52e347ea81e4739d9789e76765d63a91ce2b62f41cb314af4446cc",
    "io.arena.entrypoint-fix": "canonical-python-command", "io.arena.profile": "lmx-sd14-gpu",
    "io.arena.requirements.sha256": "45a653b606713396946ba5166e9bd9452dd492cf93b23c26b6b395f0deeb316c",
    "io.arena.model-assets.sha256": MODEL_SHA,
}


def require(condition, message="Outside the reviewed LMX GPU capability"):
    from .evaluator_policy import require as check
    check(condition, message)


def absolute(value):
    require(type(value) is str and value.startswith("/") and "\x00" not in value)
    path = Path(value)
    require(str(path) == value and ".." not in path.parts and len(path.parts) >= 3)
    return path


@dataclass(frozen=True)
class LmxGpu:
    tasks_root: Path
    task_manifest: Path
    task_manifest_sha256: str
    model_root: Path
    model_manifest: Path
    driver_root: Path
    driver_manifest: Path

    @classmethod
    def parse(cls, value, config):
        fields = {"profile", "image", "task_ids", "tasks_root", "task_manifest", "task_manifest_sha256",
                  "model_root", "model_manifest", "model_manifest_sha256", "driver_root",
                  "driver_manifest", "driver_manifest_sha256", "device_uuid", "device_minor"}
        require(type(value) is dict and set(value) == fields)
        require(value["profile"] == PROFILE and value["image"] == IMAGE and IMAGE in config.images)
        require(type(value["task_ids"]) is list and len(value["task_ids"]) == 3
                and all(type(item) is str for item in value["task_ids"])
                and tuple(sorted(value["task_ids"])) == TASK_IDS)
        require(value["model_manifest_sha256"] == MODEL_SHA and value["driver_manifest_sha256"] == DRIVER_SHA)
        require(value["device_uuid"] == DEVICE_UUID and type(value["device_minor"]) is int
                and value["device_minor"] == 0)
        require(type(value["task_manifest_sha256"]) is str and HASH.fullmatch(value["task_manifest_sha256"]))
        paths = {key: absolute(value[key]) for key in (
            "tasks_root", "task_manifest", "model_root", "model_manifest", "driver_root", "driver_manifest")}
        require(paths["tasks_root"] in config.library_roots)
        roots = [paths[key] for key in ("tasks_root", "model_root", "driver_root")]
        require(all(not a.is_relative_to(b) and not b.is_relative_to(a)
                    for index, a in enumerate(roots) for b in roots[index + 1:]))
        return cls(**paths, task_manifest_sha256=value["task_manifest_sha256"])

    def identity(self):
        return {"profile": PROFILE, "image": IMAGE, "image_id": IMAGE_ID, "task_ids": list(TASK_IDS),
                "tasks_root": str(self.tasks_root), "task_manifest": str(self.task_manifest),
                "task_manifest_sha256": self.task_manifest_sha256,
                "model_root": str(self.model_root), "model_manifest": str(self.model_manifest),
                "model_manifest_sha256": MODEL_SHA, "driver_root": str(self.driver_root),
                "driver_manifest": str(self.driver_manifest), "driver_manifest_sha256": DRIVER_SHA,
                "driver_version": DRIVER_VERSION, "device_uuid": DEVICE_UUID, "device_minor": 0,
                "resources": GPU_BUDGET, "timeout_seconds": 600}

    def labels(self, task_id):
        require(task_id in TASK_IDS)
        digest = hashlib.sha256(json.dumps(self.identity(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return {"arena.gpu-capability": digest, "arena.gpu-device": DEVICE_UUID,
                "arena.gpu-driver": DRIVER_SHA, "arena.model-assets": MODEL_SHA,
                "arena.task-manifest": self.task_manifest_sha256, "arena.task-id": task_id}

    def validate_host(self):
        from .evaluator_gpu_integrity import validate_host
        validate_host(self)

    def authorize(self, image, task, source, timeout):
        require(image == IMAGE and task in TASK_IDS and source == str(self.tasks_root) and timeout <= 600)
        self.validate_host()

    def rebuild(self, result):
        result["Labels"] = {**IMAGE_LABELS, **result["Labels"], **self.labels(result["Cmd"][5])}
        result["Env"] += ["CUDA_VISIBLE_DEVICES=" + DEVICE_UUID, "NVIDIA_VISIBLE_DEVICES=void",
            "LD_LIBRARY_PATH=/private-nvidia", "LMX_SD_ASSETS_DIR=/model", "HF_HUB_OFFLINE=1",
            "TRANSFORMERS_OFFLINE=1", "HF_HUB_DISABLE_TELEMETRY=1", "HF_HOME=/tmp/hf",
            "OMP_NUM_THREADS=1", "MKL_NUM_THREADS=1", "OPENBLAS_NUM_THREADS=1", "NUMEXPR_NUM_THREADS=1"]
        host = result["HostConfig"]
        host["Runtime"] = "runc"
        host["Devices"] = [{"PathOnHost": path, "PathInContainer": path, "CgroupPermissions": "rw"}
                           for path, _, _ in DEVICE_NODES]
        host["Mounts"] += [
            {"Type": "bind", "Source": str(self.model_root), "Target": "/model", "ReadOnly": True},
            {"Type": "bind", "Source": str(self.driver_root), "Target": "/private-nvidia", "ReadOnly": True}]


def selected(config, profile):
    if profile == PROFILE:
        require(config.lmx_gpu is not None, "LMX GPU profile is not configured")
        return config.lmx_gpu
    return None
