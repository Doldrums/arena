"""Bounded, descriptor-based private file access for the control service."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import stat
import uuid

from .control_types import ControlError, MAX_CONFIG, _json


def _private_dir(path, *, create=False):
    path = Path(path)
    if not path.is_absolute() or path.is_symlink():
        raise ControlError("Private directories must be absolute and must not be symlinks")
    # Reject any symlink ancestor; resolving and then checking the leaf is insufficient.
    if any(parent.is_symlink() for parent in path.parents):
        raise ControlError("Private directory ancestors must not be symlinks")
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise ControlError("Private directories must be owned by this user with mode 0700")
    # Prevent accidental publication by the repository static server or a wheel.
    public_root = Path(__file__).resolve().parents[2]
    if any(path.is_relative_to(public_root / name) for name in ("web", "registry", "_assets")):
        raise ControlError("Control state must be outside public assets and registry")
    return path


@contextmanager
def _open_regular(path, maximum=MAX_CONFIG, *, private=False):
    """Open a bounded regular file without following any path component."""
    path = Path(path).absolute()
    if ".." in path.parts:
        raise ControlError("Parent traversal is not allowed")
    # Walk open directory descriptors rather than checking paths and following
    # them later. This also closes ancestor-symlink replacement races.
    parent = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = child
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            raise ControlError("File must be a bounded regular file")
        if private and (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077):
            raise ControlError("Private files must be owned by this user with mode 0600")
        yield fd, info
    finally:
        os.close(fd)


def _read_regular(path, maximum=MAX_CONFIG, *, private=False):
    with _open_regular(path, maximum, private=private) as (fd, _):
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(maximum + 1)
        if len(data) > maximum:
            raise ControlError("File exceeds size limit")
        return data


def _regular_signature(path, maximum=MAX_CONFIG, *, private=False):
    """Metadata cache key from the same bounded, nonsymlink file boundary."""
    with _open_regular(path, maximum, private=private) as (_, info):
        return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
                info.st_ctime_ns, info.st_mode, info.st_uid, info.st_nlink)


def _write_private(path, value):
    data = (_json(value) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)
    return hashlib.sha256(data).hexdigest()


def _replace_private_bytes(path, data):
    temporary = path.parent / (".log-" + uuid.uuid4().hex)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
        os.replace(temporary, path)
    finally:
        os.close(fd)
        temporary.unlink(missing_ok=True)
