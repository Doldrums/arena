"""Private, non-replaceable Docker attach bytes for independent tool auditing."""
from __future__ import annotations

import os
import stat

from .evaluator_policy import RUN, directory_fd, require

STREAM_LIMIT = 256 * 1024


def _identity(info):
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
            and info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o600
            and info.st_size <= STREAM_LIMIT, 'Unsafe research output stream file')
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def retain_stream(receipts_root, stage_id, raw):
    """Persist before the output proof; never replace even a partial prior file.

    The root-only reader derives this path from the lifecycle receipt basename:
    <stage_id>.receipt.json refers to <stage_id>.stream. Bytes are the unmodified
    Docker multiplex stream, not a parsed or semantically verified tool result.
    """
    require(type(stage_id) is str and RUN.fullmatch(stage_id))
    require(type(raw) is bytes and len(raw) <= STREAM_LIMIT)
    name = stage_id + '.stream'
    directory = directory_fd(receipts_root)
    descriptor = None
    try:
        info = os.fstat(directory)
        require(info.st_uid == os.geteuid() and not stat.S_IMODE(info.st_mode) & 0o077,
                'Research output streams require a private root receipt directory')
        try:
            descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o600, dir_fd=directory)
        except FileExistsError:
            descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            before = _identity(os.fstat(descriptor))
            require(before[2] == len(raw), 'Research output stream changed')
            chunks, remaining = [], len(raw)
            while remaining:
                chunk = os.read(descriptor, min(65536, remaining))
                require(chunk, 'Research output stream changed')
                chunks.append(chunk)
                remaining -= len(chunk)
            require(b''.join(chunks) == raw and not os.read(descriptor, 1)
                    and _identity(os.fstat(descriptor)) == before, 'Research output stream changed')
        else:
            os.fchmod(descriptor, 0o600)
            _identity(os.fstat(descriptor))
            offset = 0
            while offset < len(raw):
                written = os.write(descriptor, raw[offset:])
                require(written > 0, 'Research output stream write failed')
                offset += written
        # Sync also after an identical read-only retry: a previous fsync may
        # have failed after the complete bytes reached the file.
        os.fsync(descriptor)
        final = _identity(os.fstat(descriptor))
        require(final[2] == len(raw)
                and _identity(os.stat(name, dir_fd=directory, follow_symlinks=False)) == final,
                'Research output stream path changed')
        os.fsync(directory)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(directory)
