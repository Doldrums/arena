"""Recovery never turns ambiguous ownership into permission to kill another run."""
from copy import deepcopy
import json
import os

import pytest

from arena.evaluator_policy import Denied
from arena import research_tool_recovery as recovery
from arena.research_tool_policy import canonical
from research_tool_helpers import (IDENT, NAME, RUN, create, lifecycle, restart, remove_fixture_stage)


@pytest.mark.parametrize('known', [True, False])
@pytest.mark.parametrize('snapshot_present', [True, False])
def test_restart_recovers_exact_owned_container_even_after_tmpfs_loss(lifecycle, known, snapshot_present):
    old, daemon, *_ = lifecycle
    if not known: daemon.failure = 'create_timeout'
    if known: create(lifecycle)
    else:
        with pytest.raises(TimeoutError): create(lifecycle)
    daemon.failure = None
    if not snapshot_present: remove_fixture_stage(old.records[NAME]['stage'])
    proxy = restart(lifecycle)
    try:
        proxy.recover()
        assert not daemon.containers and not proxy.records
        assert not list(proxy.config.receipts_root.glob('*.ownership.json'))
        assert len(list(proxy.config.receipts_root.glob('*.receipt.json'))) == 1
        assert ('DELETE', '/containers/' + IDENT + '?force=1') in daemon.calls
    finally:
        proxy.close()


@pytest.mark.parametrize('failure', ['get_timeout', 'get500', 'delete_timeout', 'delete500', 'image_timeout'])
def test_recovery_retains_unknown_ownership_and_never_releases_stage(lifecycle, failure):
    old, daemon, *_ = lifecycle
    create(lifecycle)
    stage = old.records[NAME]['stage']
    proxy = restart(lifecycle)
    daemon.failure = failure
    try:
        with pytest.raises((TimeoutError, Denied)): proxy.recover()
        assert stage.exists() and NAME in proxy.records
        assert len(list(proxy.config.receipts_root.glob('*.ownership.json'))) == 1
        assert not list(proxy.config.receipts_root.glob('*.receipt.json'))
    finally:
        # Close must also retain uncertainty rather than deleting ownership.
        proxy.close()
        assert stage.exists()


@pytest.mark.parametrize('mutation', ['id', 'name', 'imageid', 'imageconfig', 'label', 'extra_label',
    'owner_label', 'engine_label', 'run_label', 'env', 'cpu', 'memory', 'pids', 'parent', 'capability',
    'privileged', 'devices', 'entrypoint', 'cmd', 'user', 'rw', 'foreign_mount', 'extra_mount'])
def test_recovery_never_deletes_foreign_or_modified_container(lifecycle, mutation):
    old, daemon, *_ = lifecycle
    create(lifecycle)
    native = daemon.containers[NAME]
    if mutation == 'id': native['Id'] = '9' * 64
    elif mutation == 'name': native['Name'] = '/foreign'
    elif mutation == 'imageid': native['Image'] = 'sha256:' + '9' * 64
    elif mutation == 'imageconfig': native['Config']['Image'] = 'mutable:tag'
    elif mutation == 'label': native['Config']['Labels']['io.arena.base'] = 'changed'
    elif mutation == 'extra_label': native['Config']['Labels']['extra'] = 'yes'
    elif mutation == 'owner_label': native['Config']['Labels']['sciel.invocation-owner'] = '9' * 32
    elif mutation == 'engine_label': native['Config']['Labels']['arena.engine-container'] = '9' * 64
    elif mutation == 'run_label': native['Config']['Labels']['arena.control-run'] = '9' * 32
    elif mutation == 'env': native['Config']['Env'].append('LD_PRELOAD=bad')
    elif mutation == 'cpu': native['HostConfig']['NanoCpus'] = 2_000_000_000
    elif mutation == 'memory': native['HostConfig']['Memory'] *= 2
    elif mutation == 'pids': native['HostConfig']['PidsLimit'] = 65
    elif mutation == 'parent': native['HostConfig']['CgroupParent'] = '/foreign'
    elif mutation == 'capability': native['HostConfig']['CapAdd'].append('SYS_ADMIN')
    elif mutation == 'privileged': native['HostConfig']['Privileged'] = True
    elif mutation == 'devices': native['HostConfig']['Devices'] = [{'PathOnHost': '/dev/nvidia0'}]
    elif mutation == 'entrypoint': native['Config']['Entrypoint'] = ['/bin/sh']
    elif mutation == 'cmd': native['Config']['Cmd'] = ['-c', 'execute']
    elif mutation == 'user': native['Config']['User'] = '10001'
    elif mutation == 'rw': native['Mounts'][0]['RW'] = True
    elif mutation == 'foreign_mount': native['Mounts'][0]['Source'] = '/foreign/bundle'
    else: native['Mounts'].append(deepcopy(native['Mounts'][0]))
    # A wrong-ID daemon response is still returned for our exact inspect handle.
    request = daemon.__call__
    def mutated_request(method, path, *args, **kwargs):
        if method == 'GET' and path.startswith('/containers/'):
            daemon.calls.append((method, path))
            return 200, {}, canonical(native)
        return request(method, path, *args, **kwargs)
    proxy = restart(lifecycle)
    proxy.request = mutated_request
    before = len(daemon.calls)
    try:
        with pytest.raises(Denied): proxy.recover()
        assert not any(m == 'DELETE' for m, _ in daemon.calls[before:])
        assert NAME in proxy.records and proxy.records[NAME]['stage'].exists()
    finally:
        proxy.close()


def test_confirmed_absence_releases_intent_without_delete(lifecycle):
    old, daemon, *_ = lifecycle
    create(lifecycle)
    daemon.containers.clear()
    proxy = restart(lifecycle)
    try:
        proxy.recover()
        assert not proxy.records
        assert not any(m == 'DELETE' for m, _ in daemon.calls)
        receipt = json.loads(next(proxy.config.receipts_root.glob('*.receipt.json')).read_bytes())
        assert receipt['deletion']['daemon_status'] == 404
    finally:
        proxy.close()


@pytest.mark.parametrize('mutation', ['content', 'symlink', 'hardlink', 'extra_file'])
def test_root_snapshot_tampering_preserves_container_instead_of_foreign_delete(lifecycle, mutation):
    old, daemon, *_ = lifecycle
    create(lifecycle)
    path = old.records[NAME]['stage'] / 'inputs/bundle/tool.py'
    path.parent.chmod(0o755)
    raw = path.read_bytes()
    if mutation == 'content':
        path.chmod(0o644);path.write_bytes(raw + b'# changed');path.chmod(0o444)
    elif mutation == 'symlink':
        path.unlink();path.symlink_to('/etc/passwd')
    elif mutation == 'hardlink': os.link(path, path.parent / 'extra.py')
    else: (path.parent / 'extra.py').write_bytes(b'extra')
    path.parent.chmod(0o555)
    proxy = restart(lifecycle)
    try:
        with pytest.raises((Denied, OSError)): proxy.recover()
        assert not any(m == 'DELETE' for m, _ in daemon.calls)
        assert NAME in proxy.records
    finally:
        proxy.close()


def test_changed_trusted_image_labels_cannot_inherit_saved_ownership(lifecycle):
    old, daemon, *_ = lifecycle
    create(lifecycle)
    daemon.image['Config']['Labels']['io.arena.base'] = 'different'
    proxy = restart(lifecycle)
    try:
        with pytest.raises(Denied): proxy.recover()
        assert not any(m == 'DELETE' for m, _ in daemon.calls)
    finally:
        proxy.close()


def test_durable_write_syncs_file_then_directory(lifecycle, monkeypatch):
    proxy, daemon, *_ = lifecycle
    synced = []
    original = recovery.os.fsync
    def fsync(fd):
        synced.append(os.fstat(fd).st_mode)
        return original(fd)
    monkeypatch.setattr(recovery.os, 'fsync', fsync)
    def inspect_intent(native):
        import stat
        assert len(synced) >= 2 and stat.S_ISREG(synced[-2]) and stat.S_ISDIR(synced[-1])
    daemon.on_create = inspect_intent
    create(lifecycle)
