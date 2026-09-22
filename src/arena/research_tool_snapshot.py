"""Bounded input snapshots for the pinned foreground research-tool supervisor."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import stat

from .evaluator_policy import directory_fd, json_object, read_regular, require
from .research_tool_policy import HASH, RUNTIME_PINS, canonical, digest, exact_path, validate_limits

MAX_INPUT = 16 * 1024 ** 2
MAX_SOURCE = 256 * 1024
MAX_REQUEST = MAX_INPUT + 128 * 1024
REQUEST_KEYS = {'schema', 'method_id', 'invocation_id', 'plan_id', 'reservation_id', 'input',
                'input_sha256', 'source_sha256', 'runtime_sha256', 'limits', 'methods',
                'dependency_ids', 'request_sha256'}


def request_contract(raw, config):
    value = json_object(raw)
    require(set(value) == REQUEST_KEYS and value['schema'] == 'sciel-method-request/1')
    for key in ('method_id', 'input_sha256', 'source_sha256', 'runtime_sha256', 'request_sha256'):
        require(type(value[key]) is str and HASH.fullmatch(value[key]))
    for key in ('invocation_id', 'plan_id', 'reservation_id'):
        item = value[key]
        require(type(item) is str and 0 < len(item) <= 256 and all(ord(c) >= 32 for c in item))
    validate_limits(value['limits'])
    require(type(value['input']) is dict and len(canonical(value['input'])) <= MAX_INPUT)
    require(digest(value['input']) == value['input_sha256'])
    require(digest({k: v for k, v in value.items() if k != 'request_sha256'}) == value['request_sha256'])
    require(value['runtime_sha256'] == config.runtime_sha256, 'Executor identity differs from trusted runtime')
    deps = value['dependency_ids']
    require(type(deps) is list and len(deps) <= 64
            and all(type(p) is str and HASH.fullmatch(p) for p in deps))
    require(deps == sorted(set(deps)) and value['method_id'] not in deps)
    expected = {value['method_id']: {'root': '/bundle', 'entrypoint': 'tool.py:run'}}
    expected.update({p: {'root': '/dependencies/m_' + p + '/files', 'entrypoint': 'tool.py:run'} for p in deps})
    require(value['methods'] == expected, 'Research-only entrypoints and exact dependency roots required')
    return value


def dependency_wrapper(identity):
    return ('from sciel_method_runtime import invoke_dependency as _invoke\n'
            'METHOD_ID = ' + repr(identity) + '\ndef invoke(value):\n'
            '    return _invoke(METHOD_ID, value)\n').encode()


def _child_directory(parent, name, owner):
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    try:
        require(os.fstat(fd).st_uid == owner)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _read_tree(descriptor, structure, owner, prefix='', result=None):
    result = {} if result is None else result
    require(set(os.listdir(descriptor)) == set(structure), 'Unexpected research input tree member')
    for name, spec in structure.items():
        relative = prefix + name
        if type(spec) is dict:
            child = _child_directory(descriptor, name, owner)
            try:
                _read_tree(child, spec, owner, relative + '/', result)
            finally:
                os.close(child)
        else:
            result[relative] = read_regular(descriptor, name, spec, owner)
    require(set(os.listdir(descriptor)) == set(structure), 'Research directory changed during snapshot')
    return result


def _trusted_runtime(config):
    descriptor = directory_fd(config.runtime_dir)
    try:
        require(set(os.listdir(descriptor)) == set(RUNTIME_PINS))
        values = {name: read_regular(descriptor, name, 16384, os.geteuid()) for name in RUNTIME_PINS}
    finally:
        os.close(descriptor)
    require(all(hashlib.sha256(raw).hexdigest() == RUNTIME_PINS[name] for name, raw in values.items()),
            'Trusted supervisor source pin differs')
    return values


def snapshot_inputs(input_dir, stage, config):
    """Call only as the validated root service with a fresh server-chosen stage.

No tool import, AST execution, Docker call, writable result mount or host-code
execution occurs here. Method manifests are absent from this native interface;
this proof binds request/source bytes, not a reconstructed method-manifest ID.
"""
    input_dir, stage = exact_path(str(input_dir)), exact_path(str(stage))
    require(not stage.exists() and not stage.is_relative_to(input_dir)
            and not input_dir.is_relative_to(stage))
    parent = directory_fd(stage.parent)
    try:
        info = os.fstat(parent)
        require(info.st_uid == os.geteuid() and not info.st_mode & 0o022)
    finally:
        os.close(parent)
    descriptor = directory_fd(input_dir)
    try:
        require(os.fstat(descriptor).st_uid == config.worker_uid)
        request_raw = read_regular(descriptor, 'request.json', MAX_REQUEST, config.worker_uid)
        request = request_contract(request_raw, config)
        structure = {'bundle': {'tool.py': MAX_SOURCE}, 'runtime': {k: 16384 for k in RUNTIME_PINS},
                     'request.json': MAX_REQUEST, 'dependencies': {}}
        for dep in request['dependency_ids']:
            structure['dependencies']['m_' + dep] = {'files': {'tool.py': MAX_SOURCE}, '__init__.py': 1024}
        values = _read_tree(descriptor, structure, config.worker_uid)
    finally:
        os.close(descriptor)
    require(values['request.json'] == request_raw, 'Request changed during snapshot')
    trusted = _trusted_runtime(config)
    for name, raw in trusted.items():
        require(values['runtime/' + name] == raw, 'Worker replaced the privileged supervisor/runtime')
        values['runtime/' + name] = raw
    main_code = values['bundle/tool.py'].decode('utf-8')
    require(digest({'tool.py': main_code}) == request['source_sha256'], 'Main source differs from request')
    for dep in request['dependency_ids']:
        require(values['dependencies/m_' + dep + '/__init__.py'] == dependency_wrapper(dep))
        values['dependencies/m_' + dep + '/files/tool.py'].decode('utf-8')
    require(sum(len(raw) for name, raw in values.items() if name.endswith('/tool.py')) <= 32 * 1024 ** 2)
    # A prior read handle is never used as a Docker mount. Publish detached,
    # root-owned bytes into the private dedicated proxy staging tree.
    stage.mkdir(mode=0o755)
    stage.chmod(0o755)
    for name in ('bundle', 'dependencies', 'runtime'):
        (stage / name).mkdir(mode=0o755)
    for name, raw in values.items():
        target = stage / name
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        with target.open('xb') as out:
            out.write(raw)
        target.chmod(0o444)
    for path in stage.rglob('*'):
        info = path.lstat()
        require(not stat.S_ISLNK(info.st_mode) and info.st_uid == os.geteuid())
        if path.is_dir():
            path.chmod(0o555)
    stage.chmod(0o555)
    return {'schema': 'arena.research-tool-input-snapshot/1', 'method_id': request['method_id'],
            'request_sha256': request['request_sha256'], 'source_sha256': request['source_sha256'],
            'input_sha256': request['input_sha256'], 'runtime_sha256': request['runtime_sha256'],
            'limits': request['limits'], 'dependency_ids': request['dependency_ids'],
            'method_manifest_verified': False,
            'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
                      for name, raw in sorted(values.items())},
            'mounts': [{'Type': 'bind', 'Source': str(stage / name), 'Target': '/' + name, 'ReadOnly': True}
                       for name in ('bundle', 'dependencies', 'runtime', 'request.json')]}
