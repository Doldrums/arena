"""Retained root bytes must exist durably before an attach proof can be saved."""
import hashlib
import json
import os
import stat

import pytest

from arena.evaluator_policy import Denied
from arena import research_tool_stream as streams
from arena.research_tool_recovery import load_record
from research_tool_helpers import NAME, create, lifecycle, restart


def paths(proxy, record):
    return (proxy.config.receipts_root / (record['stage'].name + '.stream'),
            proxy.config.receipts_root / (record['stage'].name + '.ownership.json'))


@pytest.mark.parametrize('raw', [b'', b'\x01\0\0\0\0\0\0\x02{}', b'x' * streams.STREAM_LIMIT])
def test_real_private_bytes_precede_proof_and_survive_confirmed_cleanup(lifecycle, monkeypatch, raw):
    proxy = lifecycle[0]
    create(lifecycle)
    record = proxy.records[NAME]
    stream, ownership = paths(proxy, record)
    original, synced = proxy._save, []
    fsync = streams.os.fsync
    def observe_fsync(fd):
        synced.append(os.fstat(fd).st_mode)
        fsync(fd)
    def save(record):
        assert stream.read_bytes() == raw
        assert stat.S_ISREG(synced[-2]) and stat.S_ISDIR(synced[-1])
        assert 'output' not in load_record(ownership)
        original(record)
    monkeypatch.setattr(streams.os, 'fsync', observe_fsync)
    monkeypatch.setattr(proxy, '_save', save)
    proxy.record_output(record, raw)
    assert stat.S_IMODE(stream.stat().st_mode) == 0o600
    assert stream.stat().st_nlink == 1 and stream.stat().st_uid == os.geteuid()
    proof = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    assert load_record(ownership)['output'] == proof
    proxy._terminate(NAME, record)
    assert stream.read_bytes() == raw and not ownership.exists() and not record['stage'].exists()
    receipt = json.loads(stream.with_suffix('.receipt.json').read_bytes())
    assert receipt['ownership']['output'] == proof
    assert receipt['output_verified'] is False


def test_identical_duplicate_is_read_only_without_replacing_bytes(lifecycle, monkeypatch):
    proxy = lifecycle[0]
    create(lifecycle)
    record = proxy.records[NAME]
    raw = b'original multiplex stream'
    proxy.record_output(record, raw)
    stream, _ = paths(proxy, record)
    before = stream.stat()
    opened, original = [], streams.os.open
    def observe_open(name, flags, *args, **kwargs):
        if name == stream.name:
            opened.append(flags)
        return original(name, flags, *args, **kwargs)
    monkeypatch.setattr(streams.os, 'open', observe_open)
    proxy.record_output(record, raw)
    after = stream.stat()
    assert (before.st_ino, before.st_mtime_ns, before.st_ctime_ns) == (
        after.st_ino, after.st_mtime_ns, after.st_ctime_ns)
    assert len(opened) == 2 and opened[0] & os.O_EXCL
    assert opened[1] & os.O_ACCMODE == os.O_RDONLY and opened[1] & os.O_NOFOLLOW


@pytest.mark.parametrize('mutation', ['different_bytes', 'symlink', 'hardlink', 'mode', 'directory', 'fifo'])
def test_existing_unsafe_or_different_file_is_never_overwritten_or_given_proof(lifecycle, mutation):
    proxy = lifecycle[0]
    create(lifecycle)
    record = proxy.records[NAME]
    stream, ownership = paths(proxy, record)
    raw = b'original bytes'
    target = stream.parent / 'other-private-file'
    if mutation == 'directory': stream.mkdir()
    elif mutation == 'fifo': os.mkfifo(stream, 0o600)
    elif mutation == 'symlink':
        target.write_bytes(raw); target.chmod(0o600); stream.symlink_to(target)
    else:
        stream.write_bytes(b'changed! bytes' if mutation == 'different_bytes' else raw)
        stream.chmod(0o644 if mutation == 'mode' else 0o600)
        if mutation == 'hardlink': os.link(stream, target)
    before = stream.lstat()
    with pytest.raises((Denied, OSError)):
        proxy.record_output(record, raw)
    after = stream.lstat()
    assert (before.st_ino, before.st_mtime_ns, before.st_size) == (
        after.st_ino, after.st_mtime_ns, after.st_size)
    assert 'output' not in record['saved'] and 'output' not in load_record(ownership)
    assert record['stage'].exists() and NAME in proxy.records


def test_tampered_retained_bytes_cannot_satisfy_previously_saved_hash(lifecycle):
    proxy = lifecycle[0]
    create(lifecycle)
    record = proxy.records[NAME]
    proxy.record_output(record, b'original')
    stream, ownership = paths(proxy, record)
    proof = load_record(ownership)['output']
    stream.write_bytes(b'tampered')
    with pytest.raises(Denied): proxy.record_output(record, b'original')
    assert stream.read_bytes() == b'tampered' and load_record(ownership)['output'] == proof


@pytest.mark.parametrize('raw', [b'x' * (streams.STREAM_LIMIT + 1), bytearray(b'not bytes'), 'text'])
def test_invalid_output_has_no_file_or_proof(lifecycle, raw):
    proxy = lifecycle[0]
    create(lifecycle)
    record = proxy.records[NAME]
    stream, ownership = paths(proxy, record)
    with pytest.raises(Denied): proxy.record_output(record, raw)
    assert not stream.exists() and 'output' not in load_record(ownership)


def test_failed_fsync_keeps_bytes_and_ownership_but_no_output_proof(lifecycle, monkeypatch):
    proxy = lifecycle[0]
    create(lifecycle)
    record = proxy.records[NAME]
    stream, ownership = paths(proxy, record)
    fsync = streams.os.fsync
    def fail_sync(_): raise OSError('private stream sync failed')
    monkeypatch.setattr(streams.os, 'fsync', fail_sync)
    with pytest.raises(OSError): proxy.record_output(record, b'evidence')
    assert stream.read_bytes() == b'evidence' and 'output' not in record['saved']
    assert 'output' not in load_record(ownership) and NAME in proxy.records
    monkeypatch.setattr(streams.os, 'fsync', fsync)
    proxy.record_output(record, b'evidence')
    assert load_record(ownership)['output']['bytes'] == 8


def test_partial_write_is_preserved_and_not_repaired_by_overwrite(lifecycle, monkeypatch):
    proxy = lifecycle[0]
    create(lifecycle)
    record = proxy.records[NAME]
    stream, ownership = paths(proxy, record)
    write = streams.os.write
    def partial(fd, raw):
        write(fd, raw[:3])
        raise OSError('partial disk write')
    monkeypatch.setattr(streams.os, 'write', partial)
    with pytest.raises(OSError): proxy.record_output(record, b'evidence')
    monkeypatch.setattr(streams.os, 'write', write)
    with pytest.raises(Denied): proxy.record_output(record, b'evidence')
    assert stream.read_bytes() == b'evi' and 'output' not in load_record(ownership)


def test_failed_delete_and_recovery_preserve_retained_bytes(lifecycle):
    old, daemon, *_ = lifecycle
    create(lifecycle)
    record = old.records[NAME]
    old.record_output(record, b'evidence')
    stream, ownership = paths(old, record)
    daemon.failure = 'delete500'
    with pytest.raises(Denied): old._terminate(NAME, record)
    assert stream.read_bytes() == b'evidence' and ownership.exists()
    proxy = restart(lifecycle)
    try:
        with pytest.raises(Denied): proxy.recover()
        assert stream.read_bytes() == b'evidence' and ownership.exists()
        daemon.failure = None
        proxy._terminate(NAME, proxy.records[NAME])
        assert stream.read_bytes() == b'evidence' and not ownership.exists()
    finally:
        proxy.close()


@pytest.mark.parametrize('stage_id', ['../escape', 'f' * 31, 'f' * 33, 'F' * 32, None])
def test_stream_name_is_only_server_stage_uuid(tmp_path, stage_id):
    root = tmp_path.resolve()
    with pytest.raises(Denied): streams.retain_stream(root, stage_id, b'x')
    assert list(root.iterdir()) == []


@pytest.mark.parametrize('kind', ['public_directory', 'symlink_directory'])
def test_stream_directory_must_be_private_without_symlink_ancestors(tmp_path, kind):
    root = tmp_path.resolve() / 'private'
    root.mkdir(mode=0o700)
    if kind == 'public_directory': root.chmod(0o755)
    else:
        link = tmp_path.resolve() / 'link'
        link.symlink_to(root, target_is_directory=True)
        root = link
    with pytest.raises((Denied, OSError)):
        streams.retain_stream(root, 'f' * 32, b'x')
    assert list(root.iterdir()) == []


@pytest.mark.skipif(os.geteuid() != 0, reason='Changing a real file owner requires root')
def test_existing_wrong_owner_is_denied_without_repair(tmp_path):
    root = tmp_path.resolve()
    root.chmod(0o700)
    stream = root / ('f' * 32 + '.stream')
    stream.write_bytes(b'x'); stream.chmod(0o600); os.chown(stream, 998, 998)
    with pytest.raises(Denied): streams.retain_stream(root, 'f' * 32, b'x')
    assert stream.stat().st_uid == 998 and stream.read_bytes() == b'x'
