"""Durable ownership and exact recovery proofs for foreground research tools."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import uuid

from .evaluator_policy import RUN, directory_fd, json_object, read_regular, require
from .research_tool_policy import HASH, NAME, PROFILE, canonical, digest

RECORD_LIMIT = 128 * 1024
ENV_KEYS = frozenset(('PATH LANG GPG_KEY PYTHON_VERSION PYTHON_SHA256 PYTHONDONTWRITEBYTECODE '
    'OPENBLAS_NUM_THREADS OMP_NUM_THREADS MKL_NUM_THREADS NUMEXPR_NUM_THREADS PYTHONPATH '
    'GIT_OPTIONAL_LOCKS USER LOGNAME HOME').split())


def write_json(path, value):
    """A successful return means both replacement and parent directory are synced."""
    raw = canonical(value)
    require(len(raw) <= RECORD_LIMIT, 'Research ownership metadata exceeds limit')
    temporary = path.parent / ('.record-' + uuid.uuid4().hex)
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, 'wb', closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(descriptor)
        os.replace(temporary, path)
        directory = directory_fd(path.parent)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.close(descriptor)
        temporary.unlink(missing_ok=True)


def write_record(path, saved):
    # Reserve acknowledged ID and bounded output proof before any Docker POST.
    worst = saved | {'id': '0' * 64, 'output': {'sha256': '0' * 64, 'bytes': 262144}}
    require(len(canonical(worst)) <= RECORD_LIMIT - 2048)
    write_json(path, saved)


def image_proof(native, image_id):
    require(native.get('Id') == image_id and native.get('Os') == 'linux'
            and native.get('Architecture') == 'amd64', 'Research image platform/identity differs')
    config = native.get('Config')
    require(type(config) is dict)
    require(all(config.get(key) is None for key in ('Volumes', 'Healthcheck', 'OnBuild')),
            'Research image has additional implicit execution or mounts')
    environment = config.get('Env')
    require(type(environment) is list and len(environment) == len(ENV_KEYS)
            and all(type(item) is str and '=' in item and '\x00' not in item for item in environment))
    keys = [item.split('=', 1)[0] for item in environment]
    require(len(set(keys)) == len(keys) and set(keys) == ENV_KEYS
            and len(canonical(environment)) <= 16384, 'Unexpected inherited research image environment')
    labels = config.get('Labels')
    labels = {} if labels is None else labels
    require(type(labels) is dict and all(type(k) is str and type(v) is str for k, v in labels.items())
            and len(canonical(labels)) <= 32768)
    return {'image_id': image_id, 'os': 'linux', 'architecture': 'amd64',
            'environment': environment, 'labels': labels}


def load_record(path):
    directory = directory_fd(path.parent)
    try:
        info = os.fstat(directory)
        require(info.st_uid == os.geteuid() and not info.st_mode & 0o022)
        saved = json_object(read_regular(directory, path.name, RECORD_LIMIT, os.geteuid()))
    finally:
        os.close(directory)
    keys = {'schema', 'name', 'run', 'id', 'created', 'deadline', 'config', 'image', 'snapshot'}
    require(keys <= set(saved) and not set(saved) - keys - {'output'})
    require(saved['schema'] == 'arena.research-tool-ownership/1'
            and type(saved['name']) is str and NAME.fullmatch(saved['name'])
            and type(saved['run']) is str and RUN.fullmatch(saved['run'])
            and (saved['id'] is None or type(saved['id']) is str and HASH.fullmatch(saved['id'])))
    for field in ('created', 'deadline'):
        require(type(saved[field]) in (float, int) and 0 < saved[field] < 10 ** 12)
    require(0 < saved['deadline'] - saved['created'] <= 30)
    return saved


def snapshot_paths(stage, saved):
    proof = saved['snapshot']
    require(type(proof) is dict and proof.get('schema') == 'arena.research-tool-input-snapshot/1'
            and proof.get('method_manifest_verified') is False)
    expected = proof.get('files')
    require(type(expected) is dict and 4 <= len(expected) <= 133)
    root = stage / 'inputs'
    mounts = [{'Type': 'bind', 'Source': str(root / name), 'Target': '/' + name, 'ReadOnly': True}
              for name in ('bundle', 'dependencies', 'runtime', 'request.json')]
    require(proof.get('mounts') == mounts and saved['config']['HostConfig']['Mounts'] == mounts)
    return proof


def verify_snapshot(stage, saved):
    proof = snapshot_paths(stage, saved)
    expected = proof['files']
    root = stage / 'inputs'
    directories = {'.', 'bundle', 'dependencies', 'runtime'}
    for name in expected:
        relative = Path(name)
        require(type(name) is str and not relative.is_absolute() and '..' not in relative.parts
                and str(relative) == name)
        directories.update(str(p) for p in relative.parents)
    observed = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        path = Path(directory)
        info = path.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid() and not info.st_mode & 0o222)
        require(str(path.relative_to(root)) in directories)
        require(all(not (path / child).is_symlink() for child in dirs))
        descriptor = directory_fd(path)
        try:
            for name in files:
                relative = str((path / name).relative_to(root))
                require(relative in expected)
                info = (path / name).lstat()
                require(not info.st_mode & 0o222)
                raw = read_regular(descriptor, name, 17 * 1024 ** 2, os.geteuid())
                observed[relative] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        finally:
            os.close(descriptor)
    require(observed == expected, 'Root research snapshot differs from durable creation proof')
    return proof


def verify_container(native, saved, trusted_image):
    ident = native.get('Id')
    require(type(ident) is str and HASH.fullmatch(ident) and saved['id'] in (None, ident)
            and native.get('Name') == '/' + saved['name'], 'Research container name/ID differs')
    expected, actual = saved['config'], native.get('Config', {})
    require(saved['image'] == trusted_image and native.get('Image') == trusted_image['image_id'])
    for key in ('Image', 'Cmd', 'Entrypoint', 'User', 'WorkingDir', 'Tty', 'OpenStdin'):
        require(canonical(actual.get(key)) == canonical(expected[key]), 'Research container command identity differs')
    require(actual.get('Labels') == trusted_image['labels'] | expected['Labels']
            and actual.get('Env') == trusted_image['environment'], 'Research inherited configuration differs')
    labels = expected['Labels']
    require(labels.get('arena.control-run') == saved['run'] and labels.get('arena.research-tool') == PROFILE)
    host = native.get('HostConfig', {})
    for key, value in expected['HostConfig'].items():
        if key != 'Mounts':
            require(canonical(host.get(key)) == canonical(value), 'Research resource/parent identity differs')
    for key in ('Privileged', 'PublishAllPorts'):
        require(host.get(key) in (None, False))
    for key in ('Binds', 'Devices', 'DeviceRequests', 'VolumesFrom', 'Links', 'ExtraHosts', 'GroupAdd', 'PortBindings'):
        require(host.get(key) in (None, [], {}))
    require(host.get('PidMode', '') == '' and host.get('IpcMode', 'private') == 'private'
            and host.get('UsernsMode', '') == '')
    mounts = native.get('Mounts')
    require(type(mounts) is list and len(mounts) == 4)
    observed = {}
    for mount in mounts:
        target = mount.get('Destination')
        require(type(target) is str and target not in observed and mount.get('Type') == 'bind'
                and mount.get('RW') is False and mount.get('Propagation', 'rprivate') == 'rprivate')
        observed[target] = mount.get('Source')
    require(observed == {m['Target']: m['Source'] for m in expected['HostConfig']['Mounts']},
            'Research container is not bound to this exact root snapshot')
    return ident
