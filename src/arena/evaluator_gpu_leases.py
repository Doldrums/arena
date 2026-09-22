"""Persistent, host-global ownership of the single approved GPU device.

A flock serializes proxy processes. The fsynced root-owned ownership record
survives process exit and reboot: an unknown daemon outcome never means free.
The operator must provision STATE_ROOT; the proxy never creates it implicitly.
"""
from __future__ import annotations

from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import stat
import uuid

from .evaluator_gpu import (DEVICE_UUID, DRIVER_SHA, HASH, IMAGE, IMAGE_ID, IMAGE_LABELS,
                            MODEL_SHA, PROFILE, TASK_IDS, require)
from .evaluator_policy import GPUCapacityUnavailable, RUN, directory_fd, json_object, read_regular

STATE_ROOT = Path("/var/lib/arena/evaluator-gpu")
OWNER_UID = 0
LOCK_NAME = DEVICE_UUID + ".lock"
RECORD_NAME = DEVICE_UUID + ".json"


def state_directory():
    descriptor = directory_fd(STATE_ROOT)
    try:
        for path in (STATE_ROOT, *STATE_ROOT.parents):
            info = path.lstat()
            require(stat.S_ISDIR(info.st_mode) and info.st_uid in {0, OWNER_UID} and not info.st_mode & 0o022,
                    "GPU lease storage requires trusted ancestors")
        require(os.fstat(descriptor).st_uid == OWNER_UID
                and stat.S_IMODE(os.fstat(descriptor).st_mode) == 0o700,
                "GPU ownership storage must be root-owned mode0700")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def device_lock(directory):
    descriptor = os.open(LOCK_NAME, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=directory)
    try:
        info = os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == OWNER_UID and info.st_nlink == 1
                and stat.S_IMODE(info.st_mode) == 0o600 and info.st_size == 0, "Unsafe GPU lease lock")
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def validate_record(record, staging_root):
    require(type(record) is dict and set(record) == {"schema", "id", "run", "name", "stage", "gpu"}
            and record["schema"] == "arena.gpu-ownership/1" and type(record["run"]) is str
            and RUN.fullmatch(record["run"]) and type(record["name"]) is str
            and re.fullmatch(r"arena-eval-[a-f0-9]{32}", record["name"])
            and (record["id"] is None or type(record["id"]) is str and HASH.fullmatch(record["id"])))
    require(type(record["stage"]) is str)
    stage = Path(record["stage"])
    require(stage.parent == staging_root and RUN.fullmatch(stage.name))
    gpu = record["gpu"]
    require(type(gpu) is dict and set(gpu) == {"device_uuid", "image", "labels"}
            and gpu["device_uuid"] == DEVICE_UUID and gpu["image"] == IMAGE)
    labels = gpu["labels"]
    expected = {**IMAGE_LABELS, "arena.evaluator": "canonical-v1", "arena.control-run": record["run"],
                "arena.evaluation-profile": PROFILE, "arena.gpu-device": DEVICE_UUID,
                "arena.gpu-driver": DRIVER_SHA, "arena.model-assets": MODEL_SHA}
    require(type(labels) is dict and set(labels) == set(expected) | {
        "arena.gpu-capability", "arena.task-manifest", "arena.task-id"})
    require(all(labels.get(key) == value for key, value in expected.items())
            and labels["arena.task-id"] in TASK_IDS
            and all(type(labels[key]) is str and HASH.fullmatch(labels[key])
                    for key in ("arena.gpu-capability", "arena.task-manifest")))
    return record


def read_ownership(directory, staging_root):
    try:
        raw = read_regular(directory, RECORD_NAME, 8192, OWNER_UID)
    except FileNotFoundError:
        return None
    info = os.stat(RECORD_NAME, dir_fd=directory, follow_symlinks=False)
    require(stat.S_IMODE(info.st_mode) == 0o600)
    return validate_record(json_object(raw), staging_root)


def write_ownership(directory, record):
    temporary = ".ownership-" + uuid.uuid4().hex
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(json.dumps(record, sort_keys=True).encode())
            stream.flush()
            os.fsync(descriptor)
        os.replace(temporary, RECORD_NAME, src_dir_fd=directory, dst_dir_fd=directory)
        os.fsync(directory)
    finally:
        os.close(descriptor)
        try:
            os.unlink(temporary, dir_fd=directory)
        except FileNotFoundError:
            pass


@dataclass
class Lease:
    directory: int
    lock: int
    record: dict

    def close_descriptors(self):
        for name in ("lock", "directory"):
            descriptor = getattr(self, name)
            if descriptor is not None:
                os.close(descriptor)
                setattr(self, name, None)


class GpuLeases:
    def __init__(self, staging_root):
        self.staging_root = staging_root
        self.current = None

    def owns_stage(self, stage):
        return self.current is not None and self.current.record["stage"] == str(stage)

    def reserve(self, recovery, stage):
        if self.current is not None and self.current.record["id"] is not None:
            raise GPUCapacityUnavailable("The reviewed GPU has a known container lease")
        require(self.current is None, "GPU already has active or uncertain ownership")
        directory, lock = state_directory(), None
        try:
            try:
                lock = device_lock(directory)
            except BlockingIOError:
                # A pending/unsafe record is not a retryable capacity signal.
                # Only a held lock with a verified known container owner is.
                owner = read_ownership(directory, self.staging_root)
                if owner is not None and owner["id"] is not None:
                    raise GPUCapacityUnavailable("The reviewed GPU is leased by another proxy") from None
                raise
            require(read_ownership(directory, self.staging_root) is None,
                    "Pending GPU ownership must be recovered before admission")
            record = validate_record({"schema": "arena.gpu-ownership/1", "id": None,
                "run": recovery["run"], "name": recovery["name"], "stage": str(stage),
                "gpu": recovery["gpu"]}, self.staging_root)
            self.current = Lease(directory, lock, record)
            directory = lock = None
            write_ownership(self.current.directory, record)
            return self.current
        finally:
            for descriptor in (lock, directory):
                if descriptor is not None:
                    os.close(descriptor)

    def identify(self, lease, ident):
        require(lease is self.current and type(ident) is str and HASH.fullmatch(ident))
        require(lease.record["id"] in (None, ident))
        lease.record = {**lease.record, "id": ident}
        write_ownership(lease.directory, lease.record)

    def release(self, lease, daemon_status):
        require(lease is self.current and daemon_status in (204, 404),
                "GPU ownership needs confirmed daemon deletion")
        os.unlink(RECORD_NAME, dir_fd=lease.directory)
        os.fsync(lease.directory)
        lease.close_descriptors()
        self.current = None

    def recover(self, request):
        """Before serving: remove only the exactly recorded, label-bound owner."""
        require(self.current is None, "Recovery cannot replace a live proxy lease")
        directory, lock = state_directory(), None
        try:
            lock = device_lock(directory)
            record = read_ownership(directory, self.staging_root)
            if record is None:
                return
            lease = Lease(directory, lock, record)
            self.current = lease
            directory = lock = None
            ident = record["id"] or record["name"]
            status, _, raw = request("GET", "/containers/" + ident + "/json")
            if status == 404:
                deleted = 404
            else:
                require(status == 200)
                native = json_object(raw)
                ident = native.get("Id")
                require(type(ident) is str and HASH.fullmatch(ident)
                        and (record["id"] is None or record["id"] == ident)
                        and native.get("Image") == IMAGE_ID
                        and native.get("Config", {}).get("Image") == IMAGE
                        and native.get("Config", {}).get("Labels") == record["gpu"]["labels"],
                        "GPU recovery container does not match its trusted ownership record")
                deleted, _, _ = request("DELETE", "/containers/" + ident + "?force=1")
                require(deleted in (204, 404), "GPU recovery deletion remains uncertain")
            stage = Path(record["stage"])
            if stage.exists() or stage.is_symlink():
                descriptor = directory_fd(stage)
                try:
                    require(os.fstat(descriptor).st_uid == OWNER_UID)
                finally:
                    os.close(descriptor)
                shutil.rmtree(stage)
            self.release(lease, deleted)
        finally:
            for descriptor in (lock, directory):
                if descriptor is not None:
                    os.close(descriptor)
