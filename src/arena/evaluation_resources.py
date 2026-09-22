"""Finite, explicitly granted CPU evaluation budgets; legacy defaults stay fixed."""
from __future__ import annotations

from pathlib import Path
import re


PROFILES = {
    "cpu-2g-p128-v1": (2048, 128),
    "cpu-4g-p128-v1": (4096, 128),
    "cpu-2g-p256-v1": (2048, 256),
    "cpu-4g-p256-v1": (4096, 256),
    "cpu-8g-p256-v1": (8192, 256),
}
CGROUP_MOUNT = Path("/sys/fs/cgroup")


def budget(profile=None):
    if profile is None:
        memory, pids = 2048, 128
    elif type(profile) is str and profile in PROFILES:
        memory, pids = PROFILES[profile]
    else:
        raise ValueError("Unknown explicit canonical resource profile")
    return {"cpus": 1, "memory_mb": memory, "pids": pids}


def parse_grants(value, images):
    """Exact image/task pairs only; no wildcard, numeric or host-wide budgets."""
    if type(value) is not list or len(value) > 64:
        raise ValueError("Expected at most 64 explicit evaluator resource grants")
    result, used = [], set()
    for row in value:
        if (type(row) is not dict or set(row) != {"image", "profile", "task_ids"}
                or type(row["image"]) is not str or row["image"] not in images
                or type(row["profile"]) is not str or row["profile"] not in PROFILES
                or type(row["task_ids"]) is not list or not 1 <= len(row["task_ids"]) <= 1024):
            raise ValueError("Resource grant must bind an approved image, profile and exact task IDs")
        ids = row["task_ids"]
        if (any(type(task) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,180}", task) for task in ids)
                or len(set(ids)) != len(ids)):
            raise ValueError("Resource grants need unique explicit task IDs")
        for task in ids:
            pair = (row["image"], task)
            if pair in used:
                raise ValueError("An image/task pair may have only one explicit resource profile")
            used.add(pair)
        result.append((row["image"], row["profile"], tuple(ids)))
    return tuple(result)


def granted_budget(profile, image, task_id, grants):
    if profile is not None and not any(
            image == approved_image and profile == approved_profile and task_id in task_ids
            for approved_image, approved_profile, task_ids in grants):
        raise ValueError("Evaluator resources are not explicitly granted to this image and task")
    return budget(profile)


def require_parent_budget(cgroup, resources):
    """A larger candidate cannot consume the engine's entire reserved envelope."""
    if type(cgroup) is not str or not re.fullmatch(r"/(?:[A-Za-z0-9_-]+/)*arena-control-[a-f0-9]{32}", cgroup):
        raise ValueError("Explicit resource profile requires an admitted run cgroup")
    parent = CGROUP_MOUNT / cgroup.lstrip("/")
    if parent.resolve() != parent or parent.is_symlink():
        raise ValueError("Admitted resource parent must not traverse symlinks")
    values = []
    for name in ("memory.max", "pids.max"):
        path = parent / name
        if path.is_symlink():
            raise ValueError("Admitted resource limit must not be a symlink")
        raw = path.read_text().strip()
        if not re.fullmatch(r"[1-9][0-9]{0,19}", raw):
            raise ValueError("Admitted resource parent needs finite numeric limits")
        values.append(int(raw))
    if values[0] < (resources["memory_mb"] + 2048) * 1024 ** 2 or values[1] < resources["pids"] + 64:
        raise ValueError("Worker reservation needs evaluator resources plus engine headroom")


def worker_resources(profile=None):
    selected = budget(profile)
    return {"cpus": 4, "memory_mb": max(8192, selected["memory_mb"] + 4096),
            "evaluation_slots": 1, "pids": 512}
