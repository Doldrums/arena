"""Root-owned configuration for the separate research execution socket."""
from dataclasses import dataclass
import os
from pathlib import Path
import re
import socket
import stat

from .evaluator_policy import directory_fd, json_object, require
from .research_tool_policy import ResearchToolPolicy


@dataclass(frozen=True)
class Config:
    policy: ResearchToolPolicy
    docker_socket: Path
    socket_path: Path
    staging_root: Path
    receipts_root: Path
    max_containers: int = 4
    timeout_seconds: int = 30

    @classmethod
    def read(cls, path):
        data = json_object(Path(path).read_bytes())
        required = {'policy', 'docker_socket', 'socket_path', 'staging_root', 'receipts_root'}
        require(set(data) == required)
        policy = data['policy']
        require(type(policy) is dict and set(policy) == {
            'image_id', 'runtime_dir', 'run_roots', 'engine_registry', 'engine_staging_root', 'runtime_sha256'})
        for key in ('runtime_dir', 'engine_registry', 'engine_staging_root'):
            require(type(policy[key]) is str)
            policy[key] = Path(policy[key])
        require(type(policy['run_roots']) is list and all(type(p) is str for p in policy['run_roots']))
        policy['run_roots'] = tuple(Path(p) for p in policy['run_roots'])
        data['policy'] = ResearchToolPolicy(**policy).validate()
        for key in required - {'policy'}:
            require(type(data[key]) is str)
            data[key] = Path(data[key])
            require(data[key].is_absolute() and '..' not in data[key].parts)
        config = cls(**data)
        roots = (config.staging_root, config.receipts_root, config.policy.runtime_dir,
                 config.policy.engine_registry, config.policy.engine_staging_root)
        require(all(not a.is_relative_to(b) and not b.is_relative_to(a)
                    for i, a in enumerate(roots) for b in roots[i + 1:]),
                'Research capability directories must be separate')
        require(config.socket_path != config.docker_socket)
        return config

    def validate_host(self):
        self.policy.validate_host()
        require(hasattr(socket, 'SO_PEERCRED'))
        for path in (self.staging_root, self.receipts_root, self.socket_path.parent):
            fd = directory_fd(path)
            os.close(fd)
            for ancestor in (path, *path.parents):
                info = ancestor.stat()
                require(info.st_uid == 0 and not info.st_mode & 0o022)
        require(all(stat.S_IMODE(path.stat().st_mode) == 0o700
                    for path in (self.staging_root, self.receipts_root)))
        mounts = []
        for line in Path('/proc/self/mountinfo').read_text().splitlines():
            before, after = line.split(' - ', 1)
            if before.split()[4] == str(self.staging_root):
                mounts.append(after.split())
        require(mounts and all(item == mounts[0] for item in mounts))
        require(mounts[0][0] == 'tmpfs', 'Research staging requires dedicated bounded tmpfs')
        sizes = [p[5:] for p in mounts[0][2].split(',') if p.startswith('size=')]
        require(len(sizes) == 1)
        match = re.fullmatch(r'(\d+)([kmg]?)', sizes[0])
        require(match is not None)
        size = int(match[1]) * {'': 1, 'k': 1024, 'm': 1024 ** 2, 'g': 1024 ** 3}[match[2]]
        require(16 * 1024 ** 2 <= size <= 256 * 1024 ** 2)
