"""Foreground lifecycle invariants without executing a tool or invoking Docker."""
from copy import deepcopy
import hashlib
import json
import os
import shutil
from types import SimpleNamespace

import pytest

from arena.evaluator_policy import Denied
from arena.research_tool_execution import ResearchProxy
from arena import research_tool_recovery as recovery
from research_tool_helpers import IMAGE, IDENT, NAME, RUN, create, lifecycle


def test_intent_snapshot_rebuilt_config_are_durable_before_post(lifecycle):
    proxy, daemon, body, binding = lifecycle
    def inspect_intent(native):
        files = list(proxy.config.receipts_root.glob('*.ownership.json'))
        assert len(files) == 1
        saved = recovery.load_record(files[0])
        assert saved['id'] is None
        assert saved['config']['Image'] == IMAGE
        assert saved['image']['environment'] == daemon.image['Config']['Env']
        stage = proxy.config.staging_root / files[0].name.split('.')[0]
        recovery.verify_snapshot(stage, saved)
        assert saved['config']['HostConfig']['CgroupParent'] == '/arena-workers/arena-control-' + RUN
        assert saved['config']['HostConfig']['Mounts'][0]['Source'].startswith(str(stage))
        assert saved['config']['HostConfig']['Mounts'] != body['HostConfig']['Mounts']
    daemon.on_create = inspect_intent
    assert create(lifecycle)[0] == 201
    assert proxy.owned(IDENT, RUN)[0] == NAME
    saved = recovery.load_record(next(proxy.config.receipts_root.glob('*.ownership.json')))
    assert saved['id'] == IDENT
    assert not [call for call in daemon.calls if call[0] == 'DELETE']


def test_second_process_cannot_own_same_global_capacity(lifecycle):
    proxy = lifecycle[0]
    with pytest.raises(BlockingIOError): ResearchProxy(proxy.config)


def test_unknown_and_other_run_are_distinct_and_one_per_run_includes_unknown_create(lifecycle):
    proxy, daemon, body, binding = lifecycle
    with pytest.raises(KeyError): proxy.owned(IDENT, RUN)
    daemon.failure = 'create_timeout'
    with pytest.raises(TimeoutError): create(lifecycle)
    with pytest.raises(Denied, match='another run'): proxy.owned(NAME, '9' * 32)
    with pytest.raises(Denied, match='capacity'): proxy.create(body, 'sciel-method-' + '9' * 32, RUN, '', binding)
    assert sum(method == 'POST' for method, _ in daemon.calls) == 1
    daemon.failure = None
    assert proxy.owned(NAME, RUN)[1]['id'] == IDENT


@pytest.mark.parametrize('failure', ['create_timeout', 'create500', 'bad_id'])
def test_ambiguous_create_retains_durable_ownership_and_stage(lifecycle, failure):
    proxy, daemon, *_ = lifecycle
    daemon.failure = failure
    if failure == 'create500': assert create(lifecycle)[0] == 500
    else:
        with pytest.raises((TimeoutError, Denied)): create(lifecycle)
    assert list(proxy.records) == [NAME]
    assert proxy.records[NAME]['stage'].is_dir()
    assert len(list(proxy.config.receipts_root.glob('*.ownership.json'))) == 1
    assert not list(proxy.config.receipts_root.glob('*.receipt.json'))


def test_successful_deletion_publishes_hash_only_unverified_output_receipt(lifecycle):
    proxy, daemon, *_ = lifecycle
    create(lifecycle)
    record = proxy.records[NAME]
    raw = b'\x01\0\0\0\0\0\0\x02{}'
    proxy.record_output(record, raw)
    proxy.record_output(record, raw)
    with pytest.raises(Denied): proxy.record_output(record, raw + b'tamper')
    with pytest.raises(Denied): proxy.record_output(record, b'x' * (256 * 1024 + 1))
    proxy._terminate(NAME, record)
    assert not proxy.records and not record['stage'].exists()
    assert not list(proxy.config.receipts_root.glob('*.ownership.json'))
    receipt = json.loads(next(proxy.config.receipts_root.glob('*.receipt.json')).read_bytes())
    assert receipt['deletion']['daemon_status'] == 204
    assert receipt['ownership']['output'] == {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    assert receipt['output_verified'] is receipt['method_manifest_verified'] is False
    assert 'tamper' not in json.dumps(receipt)


@pytest.mark.parametrize('status', [None, 200, 400, 500])
def test_direct_remove_requires_confirmed_deletion(lifecycle, status):
    proxy = lifecycle[0]
    create(lifecycle)
    record = proxy.records[NAME]
    with pytest.raises(Denied): proxy.remove(NAME, record, status)
    assert record['stage'].exists() and NAME in proxy.records


@pytest.mark.parametrize('key,value', [('Volumes', {}), ('Healthcheck', {'Test': ['CMD', 'false']}),
                                    ('OnBuild', ['RUN arbitrary'])])
def test_implicit_image_execution_is_denied_before_post(lifecycle, key, value):
    proxy, daemon, *_ = lifecycle
    daemon.image['Config'][key] = value
    with pytest.raises(Denied): create(lifecycle)
    assert not any(m == 'POST' for m, _ in daemon.calls)
    assert not list(proxy.config.staging_root.iterdir())


@pytest.mark.parametrize('mutation', ['foreign_image', 'architecture', 'os', 'LD_PRELOAD', 'secret_env',
                                    'duplicate_env', 'version', 'daemon_arch'])
def test_runtime_cannot_be_spoofed_by_client_or_changed_daemon(lifecycle, mutation):
    proxy, daemon, body, _ = lifecycle
    if mutation == 'foreign_image': daemon.image['Id'] = 'sha256:' + '0' * 64
    elif mutation == 'architecture': daemon.image['Architecture'] = 'arm64'
    elif mutation == 'os': daemon.image['Os'] = 'windows'
    elif mutation == 'version': daemon.version['Version'] = '28.1.2'
    elif mutation == 'daemon_arch': daemon.version['Arch'] = 'arm64'
    else: daemon.image['Config']['Env'].append('PATH=duplicate' if mutation == 'duplicate_env' else mutation + '=x')
    with pytest.raises(Denied): proxy.image_info()
    with pytest.raises(Denied): create(lifecycle)
    assert not any(m == 'POST' for m, _ in daemon.calls)


def test_image_and_version_views_use_only_verified_actual_daemon(lifecycle):
    proxy = lifecycle[0]
    assert proxy.image_info() == {'Id': IMAGE, 'Os': 'linux', 'Architecture': 'amd64'}
    assert proxy.version_info() == {'Version': '28.1.1', 'Os': 'linux', 'Arch': 'amd64'}


def test_metadata_overflow_fails_before_post(lifecycle, monkeypatch):
    proxy, daemon, *_ = lifecycle
    monkeypatch.setattr(recovery, 'RECORD_LIMIT', 2500)
    with pytest.raises(Denied): create(lifecycle)
    assert not any(m == 'POST' for m, _ in daemon.calls)
    assert not proxy.records and not list(proxy.config.staging_root.iterdir())


def test_output_proof_survives_failed_cleanup_without_releasing_capacity(lifecycle):
    proxy, daemon, *_ = lifecycle
    create(lifecycle)
    proxy.record_output(proxy.records[NAME], b'bounded mux bytes')
    daemon.failure = 'delete500'
    with pytest.raises(Denied): proxy._terminate(NAME, proxy.records[NAME])
    saved = recovery.load_record(next(proxy.config.receipts_root.glob('*.ownership.json')))
    assert saved['output']['bytes'] == len(b'bounded mux bytes')
    assert NAME in proxy.records and not list(proxy.config.receipts_root.glob('*.receipt.json'))


def test_four_actual_owned_creates_exhaust_global_capacity(lifecycle):
    proxy, daemon, original, original_binding = lifecycle
    source = proxy.config.policy.engine_staging_root / RUN / 'artifacts'
    for number in range(1, 6):
        run = str(number) * 32
        body = deepcopy(original)
        for mount in body['HostConfig']['Mounts']:
            mount['Source'] = mount['Source'].replace(RUN, run)
        artifact_root = proxy.config.policy.engine_staging_root / run / 'artifacts'
        shutil.copytree(source, artifact_root)
        binding = original_binding | {'run_id': run, 'artifact_root': str(artifact_root)}
        name = 'sciel-method-' + run
        if number <= 4:
            assert proxy.create(body, name, run, '', binding)[0] == 201
        else:
            with pytest.raises(Denied, match='four globally'): proxy.create(body, name, run, '', binding)
    assert len(proxy.records) == 4 and sum(m == 'POST' for m, _ in daemon.calls) == 4


@pytest.mark.parametrize('failure', ['delete500', 'delete_timeout'])
def test_reaper_preserves_uncertainty_then_releases_only_after_confirmed_deletion(lifecycle, failure):
    proxy, daemon, *_ = lifecycle
    create(lifecycle)
    record = proxy.records[NAME]
    record['expires'] = 0
    daemon.failure = failure
    for fail in (True, False):
        waits = iter((False, True))
        proxy.stopping = SimpleNamespace(wait=lambda _: next(waits), set=lambda: None)
        if not fail: daemon.failure = None
        proxy.reap()
        assert (NAME in proxy.records) is fail
        assert record['stage'].exists() is fail


def test_failed_receipt_publication_keeps_ownership_after_daemon_absence(lifecycle, monkeypatch):
    from arena import research_tool_execution as execution
    proxy = lifecycle[0]
    create(lifecycle)
    record = proxy.records[NAME]
    original = execution.write_json
    def unavailable(*args): raise OSError('receipt disk unavailable')
    monkeypatch.setattr(execution, 'write_json', unavailable)
    with pytest.raises(OSError): proxy._terminate(NAME, record)
    assert NAME in proxy.records and record['stage'].exists()
    assert proxy._ownership_path(record).exists()
    monkeypatch.setattr(execution, 'write_json', original)
    proxy._terminate(NAME, record)
    receipt = json.loads(next(proxy.config.receipts_root.glob('*.receipt.json')).read_bytes())
    assert receipt['deletion']['daemon_status'] == 404
