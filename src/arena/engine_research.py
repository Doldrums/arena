"""Opt-in, exact-configuration grants for the native foreground research mode."""
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import stat

from .evaluator_policy import directory_fd, json_object, read_regular, require
from .sciel_research_profile import ENGINE_COMMIT, profile_identity

RESEARCH_SOCKET = '/run/arena-research-tools/docker.sock'
CLI_TARGET = '/run/arena-research-cli/docker'


@dataclass(frozen=True)
class ResearchGrant:
    socket_path: Path
    cli_path: Path
    cli_sha256: str
    image_id: str
    config_sha256: tuple[str, ...]

    @classmethod
    def read(cls, value):
        require(type(value) is dict and set(value) == {
            'socket_path', 'cli_path', 'cli_sha256', 'image_id', 'config_sha256'})
        require(type(value['image_id']) is str and re.fullmatch(r'sha256:[a-f0-9]{64}', value['image_id']))
        require(type(value['cli_sha256']) is str and re.fullmatch(r'[a-f0-9]{64}', value['cli_sha256']))
        configs = value['config_sha256']
        require(type(configs) is list and 1 <= len(configs) <= 8
                and all(type(v) is str and re.fullmatch(r'[a-f0-9]{64}', v) for v in configs)
                and len(set(configs)) == len(configs), 'Exact bounded pilot configuration grants required')
        paths = {}
        for name in ('socket_path', 'cli_path'):
            require(type(value[name]) is str)
            paths[name] = Path(value[name])
            require(paths[name].is_absolute() and '..' not in paths[name].parts)
        return cls(**paths, cli_sha256=value['cli_sha256'], image_id=value['image_id'], config_sha256=tuple(configs))

    def validate_host(self):
        for path in (self.socket_path.parent, self.cli_path.parent):
            fd = directory_fd(path)
            os.close(fd)
            for ancestor in (path, *path.parents):
                info = ancestor.stat()
                require(info.st_uid == 0 and not info.st_mode & 0o022)
        fd = directory_fd(self.cli_path.parent)
        try:
            raw = read_regular(fd, self.cli_path.name, 65536, 0)
            mode = os.stat(self.cli_path.name, dir_fd=fd, follow_symlinks=False).st_mode
            require(stat.S_IMODE(mode) in (0o555, 0o755), 'Research CLI must be executable by the worker')
            require(hashlib.sha256(raw).hexdigest() == self.cli_sha256)
        finally:
            os.close(fd)
        info = self.socket_path.lstat()
        require(stat.S_ISSOCK(info.st_mode) and info.st_uid == 0 and info.st_gid == 998
                and stat.S_IMODE(info.st_mode) == 0o660)


def admit(config, raw, *, request, engine_commit):
    native = json_object(raw)
    tools = native.get('research_tools')
    if not isinstance(tools, dict) or tools.get('enabled') is not True:
        return None
    grant = config.research_tools
    require(isinstance(grant, ResearchGrant), 'Research tools require a separately installed executor grant')
    require(config.worker_uid == config.worker_gid == 998)
    require(hashlib.sha256(raw).hexdigest() in grant.config_sha256,
            'Research configuration is not an explicitly admitted pilot')
    identity = profile_identity(native)
    require(identity['tool_image_id'] == grant.image_id)
    require(engine_commit == ENGINE_COMMIT, 'Research capability requires the exact reviewed native engine')
    for flag, native_key in (('budget', 'budget'), ('seed', 'random_seed')):
        require(flag not in request or type(request[flag]) is int and request[flag] == native.get(native_key),
                'CLI overrides cannot change the admitted research protocol')
    return identity


def prepare(config, plan, artifacts, body):
    """Called only after immutable config admission; no new grant from a flag."""
    identity = plan.get('research_profile')
    if identity is None:
        return
    grant = config.research_tools
    grant.validate_host()
    temporary = artifacts / 'research-tool-tmp'
    temporary.mkdir(mode=0o700)
    os.chown(temporary, config.worker_uid, config.worker_gid)
    body['Env'].extend(['TMPDIR=' + str(plan['logical'] / 'research-tool-tmp'),
                        'PATH=/run/arena-research-cli:/usr/local/bin:/usr/bin:/bin'])
    body['HostConfig']['Mounts'].extend([
        {'Type': 'bind', 'Source': str(grant.socket_path), 'Target': RESEARCH_SOCKET, 'ReadOnly': True},
        {'Type': 'bind', 'Source': str(grant.cli_path), 'Target': CLI_TARGET, 'ReadOnly': True},
    ])
