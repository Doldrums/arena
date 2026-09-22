"""No-execution daemon fixture for exact research lifecycle tests."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
import shutil
from types import SimpleNamespace

import pytest

from arena import evaluation_resources, research_tool_policy as policy
from arena import research_tool_snapshot as snapshot
from arena.research_tool_execution import ResearchProxy
from arena import research_tool_execution
from arena.research_tool_recovery import ENV_KEYS

RUN = 'a' * 32
NAME = 'sciel-method-' + 'b' * 32
IDENT = 'c' * 64
IMAGE = 'sha256:891563137dc96cd99307df2eaa9a4592cfd0a26672d4df2aa2ba2503f3f30a9a'


class Daemon:
    def __init__(self, config):
        self.config, self.calls, self.containers = config, [], {}
        self.image = {'Id': IMAGE, 'Os': 'linux', 'Architecture': 'amd64', 'Config': {
            'Env': [key + '=fixture' for key in sorted(ENV_KEYS)],
            'Labels': {'io.arena.base': 'immutable-parent', 'io.arena.private-build': 'pinned'},
            'Volumes': None, 'Healthcheck': None, 'OnBuild': None}}
        self.version = {'Version': '28.1.1', 'Os': 'linux', 'Arch': 'amd64'}
        self.failure, self.on_create = None, None

    def __call__(self, method, path, body=None, **kwargs):
        self.calls.append((method, path))
        if path.startswith('/images/'):
            if self.failure == 'image_timeout': raise TimeoutError()
            return 200, {}, policy.canonical(self.image)
        if path == '/version': return 200, {}, policy.canonical(self.version)
        if method == 'POST':
            value = json.loads(body)
            name = path.split('name=')[1]
            ident = IDENT if name == NAME else hashlib.sha256(name.encode()).hexdigest()
            native = {'Id': ident, 'Image': IMAGE, 'Name': '/' + name,
                'Config': {k: v for k, v in value.items() if k != 'HostConfig'},
                'HostConfig': deepcopy(value['HostConfig']),
                'Mounts': [{'Type': 'bind', 'Source': m['Source'], 'Destination': m['Target'],
                            'RW': False, 'Propagation': 'rprivate'} for m in value['HostConfig']['Mounts']]}
            native['Config']['Env'] = self.image['Config']['Env'][:]
            native['Config']['Labels'] = self.image['Config']['Labels'] | value['Labels']
            if self.on_create: self.on_create(native)
            self.containers[name] = native
            if self.failure == 'create_timeout': raise TimeoutError()
            if self.failure == 'create500': return 500, {}, b'{}'
            if self.failure == 'bad_id': return 201, {}, b'{"Id":"wrong"}'
            return 201, {}, policy.canonical({'Id': ident})
        if method == 'GET':
            if self.failure == 'get_timeout': raise TimeoutError()
            if self.failure == 'get500': return 500, {}, b'{}'
            identity = path.removeprefix('/containers/').removesuffix('/json')
            native = next((n for name, n in self.containers.items() if identity in (name, n['Id'])), None)
            return (200, {}, policy.canonical(native)) if native is not None else (404, {}, b'{}')
        assert method == 'DELETE'
        if self.failure == 'delete_timeout': raise TimeoutError()
        if self.failure == 'delete500': return 500, {}, b'{}'
        identity = path.removeprefix('/containers/').split('?')[0]
        for name, native in list(self.containers.items()):
            if identity in (name, native['Id']):
                del self.containers[name]
                return 204, {}, b''
        return 404, {}, b'{}'


@pytest.fixture
def lifecycle(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    for name in ('runtime', 'staging', 'receipts'):
        (root / name).mkdir(mode=0o700)
    runtime_sha = policy.digest(policy.executor_identity(IMAGE, 'amd64', '28.1.1'))
    p = policy.ResearchToolPolicy(IMAGE, root / 'runtime', (root / 'runs',), root / 'registry',
        root / 'engines', runtime_sha, os.getuid(), os.getgid())
    config = SimpleNamespace(policy=p, staging_root=root / 'staging', receipts_root=root / 'receipts',
        docker_socket=root / 'docker.sock', max_containers=4, timeout_seconds=30)
    incoming = root / 'engines' / RUN / 'artifacts/research-tool-tmp/sciel-method-abcd1234'
    for name in ('bundle', 'runtime', 'dependencies'):
        (incoming / name).mkdir(parents=True)
    code = 'def run(value):\n    return value\n'
    (incoming / 'bundle/tool.py').write_text(code)
    inert = {'_runner.py': b'# inert runner\n', '_loader.py': b'# inert loader\n'}
    monkeypatch.setattr(snapshot, 'RUNTIME_PINS', {k: hashlib.sha256(v).hexdigest() for k, v in inert.items()})
    for name, raw in inert.items():
        (incoming / 'runtime' / name).write_bytes(raw)
        (p.runtime_dir / name).write_bytes(raw)
    method = 'd' * 64
    request = {'schema': 'sciel-method-request/1', 'method_id': method, 'invocation_id': 'i',
        'plan_id': 'p', 'reservation_id': 'r', 'input': {}, 'input_sha256': policy.digest({}),
        'source_sha256': policy.digest({'tool.py': code}), 'runtime_sha256': runtime_sha,
        'limits': dict(policy.LIMITS), 'dependency_ids': [],
        'methods': {method: {'root': '/bundle', 'entrypoint': 'tool.py:run'}}}
    request['request_sha256'] = policy.digest(request)
    (incoming / 'request.json').write_bytes(policy.canonical(request))
    logical = root / 'runs' / RUN / 'artifacts/research-tool-tmp/sciel-method-abcd1234'
    body = {'Image': IMAGE, 'Cmd': list(policy.COMMAND), 'Entrypoint': ['/usr/local/bin/python'],
        'User': '0:0', 'Env': None, 'WorkingDir': '/tmp', 'Labels': {'sciel.invocation-owner': 'e' * 32},
        'HostConfig': {'NetworkMode': 'none', 'ReadonlyRootfs': True, 'NanoCpus': 1_000_000_000,
            'Memory': 512 * 1024 ** 2, 'MemorySwap': 512 * 1024 ** 2, 'PidsLimit': 64,
            'CapDrop': ['ALL'], 'CapAdd': ['SETUID', 'SETGID'], 'SecurityOpt': ['no-new-privileges'],
            'CgroupnsMode': 'private', 'Tmpfs': dict(policy.TMPFS), 'LogConfig': {'Type': 'none', 'Config': {}},
            'Mounts': [{'Type': 'bind', 'Source': str(logical / name), 'Target': '/' + name,
                        'ReadOnly': True} for name in ('bundle', 'dependencies', 'runtime', 'request.json')]}}
    binding = {'schema': 'arena.engine-peer/1', 'run_id': RUN, 'container_id': 'f' * 64,
               'artifact_root': str(p.engine_staging_root / RUN / 'artifacts')}
    monkeypatch.setattr(evaluation_resources, 'require_parent_budget', lambda *a: None)
    # Production is UID0. On developer machines emulate only root's ability to
    # unlink its readonly snapshot, after real verification has already run.
    monkeypatch.setattr(research_tool_execution, 'shutil', SimpleNamespace(rmtree=remove_fixture_stage))
    proxy = ResearchProxy(config)
    daemon = Daemon(config)
    monkeypatch.setattr(proxy, 'request', daemon)
    yield proxy, daemon, body, binding
    # Test daemon cleanup only. Never a real Docker/network connection.
    daemon.failure = None
    proxy.close()


def create(lifecycle):
    proxy, _, body, binding = lifecycle
    return proxy.create(body, NAME, RUN, '', binding)


def abandon(proxy):
    """Emulate process death while keeping durable ownership and root snapshot."""
    os.close(proxy.lease)
    proxy.lease = None
    proxy.records.clear()


def restart(lifecycle):
    old, daemon, *_ = lifecycle
    abandon(old)
    proxy = ResearchProxy(old.config)
    proxy.request = daemon
    return proxy


def remove_fixture_stage(stage):
    for root, dirs, _ in os.walk(stage, followlinks=False):
        os.chmod(root, 0o700)
    shutil.rmtree(stage)
