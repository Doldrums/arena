"""Private operator barrier for new claims; never interrupts admitted work."""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import stat
import threading
import time
import uuid

from .control_types import ControlError

_ROOT_UID = 0
_LOCK = "claims.lock"
_MARKER = "paused"
_PAUSED = b"arena.worker-claims-paused/1\n"


def _path(value):
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or path == Path(path.anchor):
        raise ControlError("Claim gate needs an exact absolute directory")
    return path


def _directory(info, *, leaf=False):
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in {0, _ROOT_UID}
            or stat.S_IMODE(info.st_mode) & 0o022):
        raise ControlError("Claim gate ancestors must be trusted nonwritable directories")
    if leaf and (info.st_uid != _ROOT_UID or stat.S_IMODE(info.st_mode) != 0o755):
        raise ControlError("Claim gate must be root-owned with mode 0755")


def _open_directory(path, *, leaf=True):
    descriptor = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        _directory(os.fstat(descriptor))
        for index, part in enumerate(path.parts[1:]):
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
            _directory(os.fstat(descriptor), leaf=leaf and index == len(path.parts) - 2)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _regular(info, *, size):
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != _ROOT_UID
            or stat.S_IMODE(info.st_mode) != 0o444 or info.st_nlink != 1
            or info.st_size != size):
        raise ControlError("Claim gate files must be root-owned, single-link and mode 0444")


def _open_lock(directory):
    descriptor = os.open(_LOCK, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        _regular(os.fstat(descriptor), size=0)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _identity(directory, lock):
    return tuple((info.st_dev, info.st_ino) for info in (os.fstat(directory), os.fstat(lock)))


def _recheck(path, directory, lock):
    current = _open_directory(path)
    try:
        current_lock = _open_lock(current)
        try:
            if _identity(current, current_lock) != _identity(directory, lock):
                raise ControlError("Claim gate directory or lock inode changed")
        finally:
            os.close(current_lock)
    finally:
        os.close(current)


def _paused(directory):
    try:
        descriptor = os.open(_MARKER, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    except FileNotFoundError:
        return False
    try:
        before = os.fstat(descriptor)
        _regular(before, size=len(_PAUSED))
        if os.read(descriptor, len(_PAUSED) + 1) != _PAUSED:
            raise ControlError("Claim gate marker has invalid contents")
        after = os.fstat(descriptor)
        if (before.st_mtime_ns, before.st_ctime_ns, before.st_size) != (
                after.st_mtime_ns, after.st_ctime_ns, after.st_size):
            raise ControlError("Claim gate marker changed during inspection")
        return True
    finally:
        os.close(descriptor)


class ClaimGate:
    """A missing or unsafe configured gate blocks new claims, including --once."""

    def __init__(self, path):
        self.path = _path(path)
        self.identity = None
        self._identity_lock = threading.Lock()

    @contextmanager
    def claim_window(self):
        # Each acquisition needs its own open file description: sharing one FD
        # across worker threads would let one thread unlock another's barrier.
        directory = lock = None
        allowed = False
        try:
            try:
                directory = _open_directory(self.path)
                lock = _open_lock(directory)
                fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
                _recheck(self.path, directory, lock)
                identity = _identity(directory, lock)
                with self._identity_lock:
                    if self.identity is not None and self.identity != identity:
                        raise ControlError("Configured claim gate identity changed")
                    self.identity = identity
                allowed = not _paused(directory)
            except (OSError, ControlError):
                # This path affects only idle workers. Active execute/heartbeat
                # and cleanup paths never consult or wait on the claim gate.
                allowed = False
            yield allowed
        finally:
            if lock is not None:
                os.close(lock)
            if directory is not None:
                os.close(directory)


def _write_marker(directory):
    temporary = ".paused-" + uuid.uuid4().hex
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o400, dir_fd=directory)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(_PAUSED)
            stream.flush()
            os.fchmod(descriptor, 0o444)
            os.fsync(descriptor)
        os.replace(temporary, _MARKER, src_dir_fd=directory, dst_dir_fd=directory)
        os.fsync(directory)
    finally:
        os.close(descriptor)
        try:
            os.unlink(temporary, dir_fd=directory)
        except FileNotFoundError:
            pass


def _initialize(path):
    parent = _open_directory(path.parent, leaf=False)
    try:
        # Refuse existing directories: never replace a lock used by a worker.
        os.mkdir(path.name, 0o700, dir_fd=parent)
        directory = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            os.fchmod(directory, 0o755)
            _write_marker(directory)  # Initial state is paused, even on a crash.
            lock = os.open(_LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                           0o400, dir_fd=directory)
            try:
                os.fchmod(lock, 0o444)
                os.fsync(lock)
            finally:
                os.close(lock)
            os.fsync(directory)
            os.fsync(parent)
        finally:
            os.close(directory)
    finally:
        os.close(parent)


def operate(path, action, *, timeout=30):
    """Root-only administration, independent of queue bytes and config revision.

    Pause acknowledges only after all in-progress claim windows have closed.
    Already claimed preparing/running work is deliberately allowed to finish.
    """
    if os.geteuid() != _ROOT_UID:
        raise ControlError("Claim gate administration requires root")
    if action not in {"initialize", "pause", "resume", "status"}:
        raise ControlError("Unknown claim gate action")
    if type(timeout) not in (int, float) or not 0 < timeout <= 120:
        raise ControlError("Claim gate lock timeout must be between 0 and 120 seconds")
    path = _path(path)
    if action == "initialize":
        _initialize(path)
    directory = _open_directory(path)
    lock = None
    try:
        lock = _open_lock(directory)
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise ControlError("Claim gate barrier did not become available") from None
                time.sleep(0.025)
        _recheck(path, directory, lock)
        paused = _paused(directory)
        if action == "pause" and not paused:
            _write_marker(directory)
        elif action == "resume" and paused:
            os.unlink(_MARKER, dir_fd=directory)
            os.fsync(directory)
        return {"schema": "arena.worker-claim-gate/1", "paused": _paused(directory),
                "gate_identity": _identity(directory, lock), "active_runs_interrupted": False}
    finally:
        if lock is not None:
            os.close(lock)
        os.close(directory)
