"""Detached bounded tool snapshots; fixtures are text and are never executed."""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path

import pytest

from arena import research_tool_policy as p, research_tool_snapshot as s


@pytest.fixture
def files(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    incoming, runtime, staging = (root / name for name in ('incoming', 'runtime', 'staging'))
    for path in (incoming, runtime, staging): path.mkdir(mode=0o700)
    trusted = {'_runner.py': b'# inert supervisor fixture\n', '_loader.py': b'# inert loader fixture\n'}
    pins = {k: hashlib.sha256(v).hexdigest() for k, v in trusted.items()}
    monkeypatch.setattr(s, 'RUNTIME_PINS', pins)
    for name, raw in trusted.items(): (runtime / name).write_bytes(raw)
    config = p.ResearchToolPolicy('sha256:' + 'a' * 64, runtime, (root / 'runs',), root / 'registry',
                                 root / 'engines', 'b' * 64, os.getuid(), os.getgid())
    for name in ('bundle', 'dependencies', 'runtime'): (incoming / name).mkdir()
    code = 'def run(payload):\n    return payload\n'
    dep = 'c' * 64
    d = incoming / 'dependencies' / ('m_' + dep)
    (d / 'files').mkdir(parents=True)
    (d / 'files/tool.py').write_text(code)
    (d / '__init__.py').write_bytes(s.dependency_wrapper(dep))
    (incoming / 'bundle/tool.py').write_text(code)
    for name, raw in trusted.items(): (incoming / 'runtime' / name).write_bytes(raw)
    main = 'd' * 64
    value = {'schema': 'sciel-method-request/1', 'method_id': main, 'invocation_id': 'i1',
        'plan_id': 'plan1', 'reservation_id': 'reservation1', 'input': {'observations': []},
        'input_sha256': p.digest({'observations': []}), 'source_sha256': p.digest({'tool.py': code}),
        'runtime_sha256': config.runtime_sha256, 'limits': dict(p.LIMITS), 'dependency_ids': [dep],
        'methods': {main: {'root': '/bundle', 'entrypoint': 'tool.py:run'},
                    dep: {'root': '/dependencies/m_' + dep + '/files', 'entrypoint': 'tool.py:run'}}}
    write_request(incoming, value)
    return incoming, staging / 'snapshot', config, value


def write_request(directory, value):
    value['request_sha256'] = p.digest({k: v for k, v in value.items() if k != 'request_sha256'})
    (directory / 'request.json').write_bytes(p.canonical(value))


def test_snapshot_is_exact_readonly_detached_and_source_bound(files):
    source, stage, config, request = files
    proof = s.snapshot_inputs(source, stage, config)
    assert proof['request_sha256'] == request['request_sha256']
    assert proof['method_manifest_verified'] is False
    assert len(proof['files']) == 6
    assert {m['Target'] for m in proof['mounts']} == {'/bundle', '/dependencies', '/runtime', '/request.json'}
    assert all(m['ReadOnly'] is True and m['Source'].startswith(str(stage)) for m in proof['mounts'])
    for path in stage.rglob('*'):
        assert not path.stat().st_mode & 0o222
        if path.is_file(): assert path.stat().st_nlink == 1
    (source / 'bundle/tool.py').write_text('changed after detached snapshot')
    assert p.digest({'tool.py': (stage / 'bundle/tool.py').read_text()}) == proof['source_sha256']


@pytest.mark.parametrize('target', ['bundle/tool.py', 'runtime/_runner.py', 'request.json'])
def test_symlink_and_hardlink_sources_rejected(files, target, tmp_path):
    source, stage, config, _ = files
    path = source / target
    original = path.read_bytes();path.unlink()
    foreign = tmp_path / 'foreign';foreign.write_bytes(original);path.symlink_to(foreign)
    with pytest.raises((p.Denied, OSError)): s.snapshot_inputs(source, stage, config)
    assert not stage.exists()
    path.unlink();os.link(foreign, path)
    with pytest.raises(p.Denied): s.snapshot_inputs(source, stage, config)
    assert not stage.exists()


@pytest.mark.parametrize('target', ['bundle', 'dependencies', 'runtime'])
def test_directory_symlink_sources_rejected(files, target):
    source, stage, config, _ = files
    old = source / target;new = source / (target + '-moved');old.rename(new);old.symlink_to(new, target_is_directory=True)
    with pytest.raises((p.Denied, OSError)): s.snapshot_inputs(source, stage, config)
    assert not stage.exists()


@pytest.mark.parametrize('mutation', ['runner', 'loader', 'source', 'shim', 'extra', 'extra_runtime', 'extra_dependency'])
def test_runtime_or_bundle_tampering_publishes_no_stage(files, mutation):
    source, stage, config, request = files
    targets = {'runner': 'runtime/_runner.py', 'loader': 'runtime/_loader.py', 'source': 'bundle/tool.py',
        'shim': 'dependencies/m_' + request['dependency_ids'][0] + '/__init__.py',
        'extra': 'bundle/hidden.py', 'extra_runtime': 'runtime/sitecustomize.py',
        'extra_dependency': 'dependencies/secret.py'}
    (source / targets[mutation]).write_text('# changed\n')
    with pytest.raises(p.Denied): s.snapshot_inputs(source, stage, config)
    assert not stage.exists()


@pytest.mark.parametrize('mutation', ['source_hash', 'input_hash', 'runtime_hash', 'methodroot', 'entrypoint',
    'duplicate_dep', 'bool_limit', 'over_wall', 'extra_key', 'wrong_schema', 'nonobject_input'])
def test_rehashed_request_still_must_obey_semantic_contract(files, mutation):
    source, stage, config, request = files
    if mutation.endswith('_hash'):
        request[mutation.replace('_hash', '_sha256')] = 'e' * 64
    elif mutation == 'methodroot': request['methods'][request['method_id']]['root'] = '/runtime'
    elif mutation == 'entrypoint': request['methods'][request['method_id']]['entrypoint'] = '_runner.py:_supervise'
    elif mutation == 'duplicate_dep': request['dependency_ids'] *= 2
    elif mutation == 'bool_limit': request['limits']['cpu_seconds'] = True
    elif mutation == 'over_wall': request['limits']['wall_seconds'] = 31
    elif mutation == 'extra_key': request['privileged'] = True
    elif mutation == 'wrong_schema': request['schema'] = 'other'
    else: request['input'] = []
    write_request(source, request)
    with pytest.raises(p.Denied): s.snapshot_inputs(source, stage, config)
    assert not stage.exists()


def test_duplicate_json_key_is_not_normalized_away(files):
    source, stage, config, _ = files
    path = source / 'request.json';raw = path.read_bytes();path.write_bytes(b'{"schema":"other",' + raw[1:])
    with pytest.raises(p.Denied, match='Duplicate'): s.snapshot_inputs(source, stage, config)


def test_request_cannot_change_between_initial_read_and_tree_snapshot(files, monkeypatch):
    source, stage, config, _ = files
    original = s._read_tree
    def changed(*args, **kwargs):
        values = original(*args, **kwargs)
        if len(args) == 3:
            values['request.json'] += b' '
        return values
    monkeypatch.setattr(s, '_read_tree', changed)
    with pytest.raises(p.Denied, match='Request changed'): s.snapshot_inputs(source, stage, config)
    assert not stage.exists()


def test_wrong_worker_owner_and_oversized_code_rejected(files, monkeypatch):
    source, stage, config, _ = files
    with pytest.raises(p.Denied): s.snapshot_inputs(source, stage, replace(config, worker_uid=98765))
    monkeypatch.setattr(s, 'MAX_SOURCE', 4)
    with pytest.raises(p.Denied): s.snapshot_inputs(source, stage, config)


def test_no_untrusted_runtime_accepted_even_if_worker_copy_matches(files):
    source, stage, config, _ = files
    (config.runtime_dir / '_runner.py').write_bytes(b'bad trusted copy')
    (source / 'runtime/_runner.py').write_bytes(b'bad trusted copy')
    with pytest.raises(p.Denied, match='Trusted supervisor'): s.snapshot_inputs(source, stage, config)
    assert not stage.exists()


def test_stage_collision_and_source_overlap_are_denied(files):
    source, stage, config, _ = files
    stage.mkdir()
    with pytest.raises(p.Denied): s.snapshot_inputs(source, stage, config)
    with pytest.raises(p.Denied): s.snapshot_inputs(source, source / 'nested', config)
