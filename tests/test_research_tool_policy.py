"""Exact native request policy, without Docker, model calls or root privileges."""
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path

import pytest

from arena import evaluation_resources
from arena import research_tool_policy as p

RUN = 'a' * 32
ENGINE = 'b' * 64
OWNER = 'c' * 32
IMAGE = 'sha256:' + 'd' * 64
NAME = 'sciel-method-' + 'e' * 32


@pytest.fixture
def setup(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    config = p.ResearchToolPolicy(IMAGE, root / 'runtime', (root / 'runs',),
        root / 'registry', root / 'engines', 'f' * 64)
    binding = {'schema': 'arena.engine-peer/1', 'run_id': RUN, 'container_id': ENGINE,
               'artifact_root': str(root / 'engines' / RUN / 'artifacts')}
    directory = root / 'runs' / RUN / 'artifacts/research-tool-tmp/sciel-method-abcd1234'
    body = {'Image': IMAGE, 'Cmd': list(p.COMMAND), 'Entrypoint': ['/usr/local/bin/python'],
        'User': '0:0', 'Env': None, 'WorkingDir': '/tmp', 'Labels': {'sciel.invocation-owner': OWNER},
        'HostConfig': {'NetworkMode': 'none', 'ReadonlyRootfs': True, 'NanoCpus': 1_000_000_000,
            'Memory': 512 * 1024 ** 2, 'MemorySwap': 512 * 1024 ** 2, 'PidsLimit': 64,
            'CapDrop': ['ALL'], 'CapAdd': ['SETUID', 'SETGID'], 'SecurityOpt': ['no-new-privileges'],
            'CgroupnsMode': 'private', 'Tmpfs': dict(p.TMPFS), 'LogConfig': {'Type': 'none', 'Config': {}},
            'Mounts': [{'Type': 'bind', 'Source': str(directory / name), 'Target': '/' + name,
                        'ReadOnly': True} for name in ('bundle', 'dependencies', 'runtime', 'request.json')]}}
    observed = []
    monkeypatch.setattr(evaluation_resources, 'require_parent_budget', lambda *a: observed.append(a))
    return config, binding, directory, body, observed


def validate(setup):
    config, binding, _, body, _ = setup
    return p.canonical_config(body, NAME, RUN, binding, config)


def test_exact_native_create_rebuilds_mounts_and_parent_identity(setup):
    config, binding, directory, body, observed = setup
    rebuilt, source = validate(setup)
    assert source == config.engine_staging_root / RUN / 'artifacts/research-tool-tmp' / directory.name
    assert rebuilt['HostConfig']['Mounts'] == []
    assert rebuilt['HostConfig']['CgroupParent'] == '/arena-workers/arena-control-' + RUN
    assert rebuilt['Labels'] == {'sciel.invocation-owner': OWNER, 'arena.control-run': RUN,
        'arena.research-tool': p.PROFILE, 'arena.engine-container': ENGINE}
    assert rebuilt['Env'] == [] and rebuilt['User'] == '0:0'
    assert rebuilt['HostConfig']['CapAdd'] == ['SETUID', 'SETGID']
    assert rebuilt['HostConfig']['AutoRemove'] is False
    assert observed == [('/arena-workers/arena-control-' + RUN, {'cpus': 1, 'memory_mb': 512, 'pids': 64})]
    body['HostConfig']['CapAdd'].reverse()
    assert validate(setup)[0] == rebuilt


@pytest.mark.parametrize('path,value', [
    (('Image',), 'sha256:' + '1' * 64), (('Cmd',), ['-c', 'arbitrary code']),
    (('Entrypoint',), ['/bin/sh']), (('User',), '998:998'), (('WorkingDir',), '/bundle'),
    (('Env',), ['OPENAI_API_KEY=not-a-real-key']), (('Tty',), True), (('OpenStdin',), True),
    (('HostConfig', 'Privileged'), True), (('HostConfig', 'CapAdd'), ['SETUID', 'SETGID', 'SYS_ADMIN']),
    (('HostConfig', 'CapAdd'), ['SETUID', 'SETUID']), (('HostConfig', 'Memory'), 512.0 * 1024 ** 2),
    (('HostConfig', 'PidsLimit'), 65), (('HostConfig', 'MemorySwap'), -1),
    (('HostConfig', 'NetworkMode'), 'host'), (('HostConfig', 'ReadonlyRootfs'), False),
    (('HostConfig', 'CgroupParent'), '/arena-workers/arena-control-' + RUN),
    (('HostConfig', 'PidMode'), 'host'), (('HostConfig', 'IpcMode'), 'host'),
    (('HostConfig', 'AutoRemove'), True), (('HostConfig', 'Binds'), ['/var/run/docker.sock:/x']),
    (('HostConfig', 'Devices'), [{'PathOnHost': '/dev/nvidia0'}]),
    (('HostConfig', 'SecurityOpt'), ['seccomp=unconfined']),
    (('HostConfig', 'Tmpfs'), {'/tmp': 'rw,exec,size=33554432'}),
    (('Labels',), {'sciel.invocation-owner': OWNER, 'arena.control-run': RUN}),
])
def test_denies_every_added_capability(setup, path, value):
    target = setup[3]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(p.Denied):
        validate(setup)


@pytest.mark.parametrize('mutation', ['wrongrun', 'outside', 'logicaldot', 'mixed', 'duplicate', 'rw', 'socket'])
def test_mounts_must_be_exact_same_owned_foreground_directory(setup, mutation):
    body = setup[3]
    mounts = body['HostConfig']['Mounts']
    if mutation == 'wrongrun':
        for m in mounts: m['Source'] = m['Source'].replace(RUN, 'f' * 32)
    elif mutation == 'outside':
        for m in mounts: m['Source'] = '/tmp/sciel-method-abcd1234/' + m['Target'][1:]
    elif mutation == 'logicaldot': mounts[0]['Source'] = mounts[0]['Source'].replace('/bundle', '/./bundle')
    elif mutation == 'mixed': mounts[0]['Source'] = mounts[0]['Source'].replace('abcd1234', 'ffff1111')
    elif mutation == 'duplicate': mounts[0] = deepcopy(mounts[1])
    elif mutation == 'rw': mounts[0]['ReadOnly'] = False
    else: mounts.append({'Type': 'bind', 'Source': '/var/run/docker.sock', 'Target': '/docker', 'ReadOnly': True})
    with pytest.raises(p.Denied): validate(setup)


@pytest.mark.parametrize('key,value', [('run_id', 'f' * 32), ('artifact_root', '/tmp/foreign'),
                                      ('container_id', 'short'), ('schema', 'other')])
def test_mapping_requires_exact_root_issued_binding(setup, key, value):
    setup[1][key] = value
    with pytest.raises(p.Denied): validate(setup)


def test_no_direct_main_worker_identity(setup, monkeypatch):
    monkeypatch.setattr(p, 'engine_binding', lambda *a: None)
    with pytest.raises(p.Denied): p.peer_binding(None, setup[0])
    monkeypatch.setattr(p, 'engine_binding', lambda *a: setup[1])
    assert p.peer_binding(None, setup[0]) == setup[1]


def test_parent_resource_denial_is_not_ignored(setup, monkeypatch):
    def reject(*a): raise ValueError('insufficient actual parent')
    monkeypatch.setattr(evaluation_resources, 'require_parent_budget', reject)
    with pytest.raises(p.Denied, match='parent envelope'): validate(setup)


def test_runtime_identity_pins_the_real_uid_drop_supervisor():
    identity = p.executor_identity(IMAGE, 'amd64', '28.3.3')
    assert identity['runner_sha256'] == 'a19034f5a17bb1a9b527fc8377058dfdc9edf7631c2e9f0e5055f796fb6d3f8e'
    assert identity['loader_sha256'] == '141e4224f72ff74bcd10916159d34ac55a4eb5e8ca04dc914fec1ed5d14f90f7'
    assert identity['policy']['candidate_uid'] == identity['policy']['candidate_gid'] == 10001
    assert identity['policy']['tmpfs_bytes'] == 33554432
    assert p.digest(identity) != p.digest(p.executor_identity(IMAGE, 'amd64', '28.3.4'))


@pytest.mark.parametrize('key,value', [('memory_bytes', 1024), ('pids', True), ('max_output_bytes', 65537),
    ('max_stderr_bytes', 8193), ('wall_seconds', 31), ('cpu_seconds', float('nan')), ('cpu_seconds', True)])
def test_limits_never_alias_boolean_or_exceed_fixed_envelope(key, value):
    with pytest.raises(p.Denied): p.validate_limits({**p.LIMITS, key: value})


def test_lower_cpu_and_wall_deadlines_keep_exact_static_resources():
    value = {**p.LIMITS, 'cpu_seconds': 1.25, 'wall_seconds': 2.5}
    assert p.validate_limits(value) == value


def test_malformed_json_members_fail_as_denials(setup):
    setup[3]['HostConfig']['CapAdd'] = [{}, []]
    with pytest.raises(p.Denied): validate(setup)
    setup[3]['HostConfig']['CapAdd'] = ['SETUID', 'SETGID']
    setup[3]['HostConfig']['Mounts'][0]['Target'] = []
    with pytest.raises(p.Denied): validate(setup)
    with pytest.raises(p.Denied): p.validate_limits({**p.LIMITS, 'cpu_seconds': 10 ** 1000})


@pytest.mark.parametrize('capabilities', [
    ['CAP_SETGID', 'CAP_SETUID'], ['CAP_SETUID', 'CAP_SETGID'],
    ['CAP_SETGID', 'SETUID'], ['SETGID', 'CAP_SETUID'],
])
def test_pinned_cli_capability_spellings_rebuild_same_fixed_profile(setup, capabilities):
    # Actual immutable CLI 0d7708f... (Docker28.1.1) wire capture body SHA:
    # 59b32656c29f610a801d0cd137d8983ee0c95781a3a5542851437a08b8f00503.
    # Wire CapAdd was [CAP_SETGID, CAP_SETUID], CapDrop ALL, Swappiness -1.
    expected, source = validate(setup)
    body = setup[3]
    body['HostConfig'].update(CapAdd=capabilities, MemorySwappiness=-1,
        MaskedPaths=None, ReadonlyPaths=None, ConsoleSize=[0, 0], ShmSize=0,
        RestartPolicy={'Name': 'no', 'MaximumRetryCount': 0})
    body['NetworkingConfig'] = {'EndpointsConfig': {}}
    assert validate(setup) == (expected, source)
    assert expected['HostConfig']['CapAdd'] == ['SETUID', 'SETGID']
    assert body['HostConfig']['CapAdd'] == capabilities  # No caller object mutation.


@pytest.mark.parametrize('capabilities', [
    ['SETUID', 'CAP_SETUID'], ['SETGID', 'CAP_SETGID'],
    ['CAP_SETUID', 'CAP_SETUID'], ['CAP_SETGID', 'CAP_SETGID'],
    ['CAP_SETUID', 'CAP_SYS_ADMIN'], ['SETUID', 'NET_ADMIN'],
    ['cap_setuid', 'CAP_SETGID'], ['CAP_CAP_SETUID', 'CAP_SETGID'],
    [' CAP_SETUID', 'CAP_SETGID'], ['CAP_SETUID', 'CAP_SETGID', 'SYS_ADMIN'],
    ['CAP_SETUID'], ['CAP_SETUID', True], ['CAP_SETUID', None],
])
def test_capability_aliases_cannot_duplicate_or_expand_privilege(setup, capabilities):
    setup[3]['HostConfig']['CapAdd'] = capabilities
    with pytest.raises(p.Denied): validate(setup)
