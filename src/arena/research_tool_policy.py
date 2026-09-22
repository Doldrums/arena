"""One opt-in foreground SCiEL research-tool capability, separate from evaluators.

This module neither executes submitted code nor authorizes Docker transport.
The HTTP/lifecycle owner must use authenticated engine_binding and durable intent.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re

from .evaluator_policy import Denied, RUN, directory_fd, engine_binding, json_object, only_defaults, read_regular, require

PROFILE = 'sciel-foreground-research-tool/1'
IMAGE = re.compile(r'sha256:[0-9a-f]{64}\Z')
HASH = re.compile(r'[0-9a-f]{64}\Z')
NAME = re.compile(r'sciel-method-[0-9a-f]{32}\Z')
TEMP = re.compile(r'sciel-method-[a-z0-9_]{8}\Z')
RUNTIME_PINS = {
    '_runner.py': 'a19034f5a17bb1a9b527fc8377058dfdc9edf7631c2e9f0e5055f796fb6d3f8e',
    '_loader.py': '141e4224f72ff74bcd10916159d34ac55a4eb5e8ca04dc914fec1ed5d14f90f7',
}
LIMITS = {'wall_seconds': 30.0, 'cpu_seconds': 20.0, 'memory_bytes': 512 * 1024 ** 2,
          'pids': 64, 'max_output_bytes': 65536, 'max_stderr_bytes': 8192}
TMPFS = {'/tmp': 'rw,noexec,nosuid,nodev,size=33554432,mode=1777'}
COMMAND = ['-I', '-B', '/runtime/_runner.py', '--supervise', '/request.json']
NATIVE_POLICY = dict(network='none', rootfs_read_only=True, bundle_mounts_read_only=True,
    candidate_uid=10001, candidate_gid=10001, cpus=1, credentials='no host environment passed',
    watchdog='root PID1 exits private PID namespace', swap='disabled',
    cpu_accounting='cgroup-v2 CPU observed before namespace exit; excludes Docker daemon',
    cpu_limit_scope='child phase cgroup delta; startup CPU is additionally measured',
    wall_accounting='host invocation total including staging/create/cleanup',
    dependency_invocations='not independently attested; top-level resource accounting only',
    tmpfs_bytes=33554432)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def exact_path(value):
    require(type(value) is str)
    path = Path(value)
    require(path.is_absolute() and '..' not in path.parts and str(path) == value)
    return path


def executor_identity(image_id, architecture, docker_server):
    """The caller must obtain platform/version from its trusted Docker daemon."""
    require(type(image_id) is str and IMAGE.fullmatch(image_id))
    require(architecture in {'amd64', 'arm64'} and type(docker_server) is str
            and re.fullmatch(r'[A-Za-z0-9_.+\-]{1,100}', docker_server))
    return dict(schema='sciel-method-executor/1', image_id=image_id, architecture=architecture,
                docker_server=docker_server, runner_sha256=RUNTIME_PINS['_runner.py'],
                loader_sha256=RUNTIME_PINS['_loader.py'], policy=dict(NATIVE_POLICY))


@dataclass(frozen=True)
class ResearchToolPolicy:
    image_id: str
    runtime_dir: Path
    run_roots: tuple[Path, ...]
    engine_registry: Path
    engine_staging_root: Path
    runtime_sha256: str
    worker_uid: int = 998
    worker_gid: int = 998
    cgroup_root: str = '/arena-workers'

    def validate(self):
        require(type(self.image_id) is str and IMAGE.fullmatch(self.image_id))
        require(type(self.runtime_sha256) is str and HASH.fullmatch(self.runtime_sha256))
        require(self.worker_uid == self.worker_gid == 998, 'Only the admitted worker UID998 is supported')
        require(self.cgroup_root == '/arena-workers')
        require(type(self.run_roots) is tuple and 1 <= len(self.run_roots) <= 8)
        for path in (self.runtime_dir, self.engine_registry, self.engine_staging_root, *self.run_roots):
            exact_path(str(path))
        require(len(set(self.run_roots)) == len(self.run_roots))
        return self

    def validate_host(self):
        """No writes; call before admitting any client or reading generated input."""
        self.validate()
        require(os.geteuid() == 0)
        for path in (self.runtime_dir, self.engine_registry, self.engine_staging_root):
            fd = directory_fd(path)
            os.close(fd)
            for ancestor in (path, *path.parents):
                info = ancestor.stat()
                require(info.st_uid == 0 and not info.st_mode & 0o022)
        fd = directory_fd(self.runtime_dir)
        try:
            require(set(os.listdir(fd)) == set(RUNTIME_PINS))
            for name, expected in RUNTIME_PINS.items():
                raw = read_regular(fd, name, 16384, 0)
                require(hashlib.sha256(raw).hexdigest() == expected, 'Untrusted supervisor/runtime bytes')
        finally:
            os.close(fd)


def peer_binding(connection, config):
    """SO_PEERCRED plus root-issued engine-container/cgroup identity; no /main."""
    binding = engine_binding(connection, config)
    require(binding is not None, 'Research tools require a registered private engine container')
    return binding


def validate_limits(value):
    require(type(value) is dict and set(value) == set(LIMITS))
    for key, bound in LIMITS.items():
        item = value[key]
        if key in {'wall_seconds', 'cpu_seconds'}:
            require(type(item) in (int, float) and 0 < item <= bound and math.isfinite(item))
        else:
            require(type(item) is int and item == bound, 'Fixed research resource/output envelope required')
    return dict(value)


def canonical_config(body, name, run_id, binding, config):
    """Return rebuilt config and mapped input directory; never pass client mounts."""
    require(type(name) is str and NAME.fullmatch(name) and RUN.fullmatch(run_id))
    require(type(binding) is dict and set(binding) == {'schema', 'run_id', 'container_id', 'artifact_root'})
    require(binding['schema'] == 'arena.engine-peer/1' and binding['run_id'] == run_id
            and type(binding['container_id']) is str and HASH.fullmatch(binding['container_id']))
    physical = config.engine_staging_root / run_id / 'artifacts'
    require(binding['artifact_root'] == str(physical))
    only_defaults(body, {'Image', 'Cmd', 'Entrypoint', 'User', 'Env', 'WorkingDir', 'Labels',
                         'HostConfig', 'NetworkingConfig', 'AttachStdout', 'AttachStderr'})
    require(body.get('Image') == config.image_id and body.get('Cmd') == COMMAND
            and body.get('Entrypoint') == ['/usr/local/bin/python'] and body.get('User') == '0:0'
            and body.get('WorkingDir') == '/tmp' and body.get('Env') in (None, []))
    require(body.get('NetworkingConfig', {}) in ({}, {'EndpointsConfig': {}}))
    labels = body.get('Labels')
    require(type(labels) is dict and set(labels) == {'sciel.invocation-owner'}
            and type(labels['sciel.invocation-owner']) is str and RUN.fullmatch(labels['sciel.invocation-owner']))
    host = body.get('HostConfig')
    only_defaults(host, {'NetworkMode', 'ReadonlyRootfs', 'NanoCpus', 'Memory', 'MemorySwap',
        'PidsLimit', 'CapDrop', 'CapAdd', 'SecurityOpt', 'Tmpfs', 'Mounts', 'LogConfig',
        'CgroupnsMode', 'Runtime', 'RestartPolicy', 'ConsoleSize', 'ShmSize', 'MemorySwappiness',
        'MaskedPaths', 'ReadonlyPaths'})
    require(host.get('NetworkMode') == 'none' and host.get('ReadonlyRootfs') is True)
    for key, value in {'NanoCpus': 1_000_000_000, 'Memory': LIMITS['memory_bytes'],
                       'MemorySwap': LIMITS['memory_bytes'], 'PidsLimit': LIMITS['pids']}.items():
        require(type(host.get(key)) is int and host[key] == value)
    # The pinned Docker CLI serializes these names with CAP_ prefixes. Accept
    # only the exact equivalent pair; the trusted rebuilt request stays fixed.
    aliases = {'SETUID': 'SETUID', 'SETGID': 'SETGID',
               'CAP_SETUID': 'SETUID', 'CAP_SETGID': 'SETGID'}
    require(host.get('CapDrop') == ['ALL'] and type(host.get('CapAdd')) is list
            and len(host['CapAdd']) == 2 and all(type(x) is str for x in host['CapAdd'])
            and {aliases.get(x) for x in host['CapAdd']} == {'SETUID', 'SETGID'})
    require(host.get('SecurityOpt') in (['no-new-privileges'], ['no-new-privileges=true']))
    require(host.get('Tmpfs') == TMPFS and host.get('CgroupnsMode') == 'private'
            and host.get('LogConfig') == {'Type': 'none', 'Config': {}})
    require(host.get('Runtime', '') in ('', 'runc'))
    require(host.get('RestartPolicy', {}) in ({}, {'Name': 'no', 'MaximumRetryCount': 0}))
    require(host.get('ConsoleSize', [0, 0]) == [0, 0] and host.get('ShmSize', 0) in (0, 64 * 1024 ** 2))
    require(host.get('MemorySwappiness', -1) == -1
            and host.get('MaskedPaths') is None and host.get('ReadonlyPaths') is None)
    mounts = host.get('Mounts')
    require(type(mounts) is list and len(mounts) == 4)
    sources = {}
    for mount in mounts:
        require(type(mount) is dict and set(mount) <= {'Type', 'Source', 'Target', 'ReadOnly', 'Consistency', 'BindOptions'})
        require(mount.get('Type') == 'bind' and mount.get('ReadOnly') is True
                and mount.get('Consistency', '') == '' and mount.get('BindOptions', {}) in ({}, {'Propagation': 'rprivate'}))
        target = mount.get('Target')
        require(type(target) is str and target in {'/bundle', '/dependencies', '/runtime', '/request.json'}
                and target not in sources)
        sources[target] = exact_path(mount.get('Source'))
    directory = sources['/request.json'].parent
    require(TEMP.fullmatch(directory.name))
    require(all(path == directory / target[1:] for target, path in sources.items()))
    roots = [root / run_id / 'artifacts' for root in config.run_roots
             if directory.parent == root / run_id / 'artifacts/research-tool-tmp']
    require(len(roots) == 1, 'Research input must belong to this run and its foreground tmp root')
    parent = config.cgroup_root + '/arena-control-' + run_id
    from .evaluation_resources import require_parent_budget
    try:
        require_parent_budget(parent, {'cpus': 1, 'memory_mb': 512, 'pids': 64})
    except (OSError, ValueError):
        raise Denied('Research resources exceed admitted parent envelope') from None
    rebuilt = {'Image': config.image_id, 'Cmd': list(COMMAND), 'Entrypoint': ['/usr/local/bin/python'],
        'User': '0:0', 'WorkingDir': '/tmp', 'Env': [], 'AttachStdout': True, 'AttachStderr': True,
        'OpenStdin': False, 'Tty': False, 'Labels': {**labels, 'arena.control-run': run_id,
        'arena.research-tool': PROFILE, 'arena.engine-container': binding['container_id']},
        'HostConfig': {'Runtime': 'runc', 'NetworkMode': 'none', 'ReadonlyRootfs': True,
            'NanoCpus': 1_000_000_000, 'Memory': LIMITS['memory_bytes'], 'MemorySwap': LIMITS['memory_bytes'],
            'PidsLimit': LIMITS['pids'], 'CapDrop': ['ALL'], 'CapAdd': ['SETUID', 'SETGID'],
            'SecurityOpt': ['no-new-privileges'], 'CgroupnsMode': 'private', 'CgroupParent': parent,
            'AutoRemove': False, 'Tmpfs': dict(TMPFS), 'LogConfig': {'Type': 'none', 'Config': {}}, 'Mounts': []}}
    return rebuilt, physical / directory.relative_to(roots[0])
