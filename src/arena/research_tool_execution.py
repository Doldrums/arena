"""Root-owned lifecycle for one bounded foreground research-tool capability."""
from __future__ import annotations

import fcntl
import hashlib
import http.client
import os
import re
import shutil
import stat
import threading
import time
from urllib.parse import quote
import uuid

from .evaluator_policy import Denied, DockerConnection, MAX_RESPONSE, RUN, json_object, require
from .research_tool_policy import HASH, canonical, canonical_config, digest, executor_identity
from .research_tool_recovery import (image_proof, load_record, snapshot_paths, verify_container, verify_snapshot,
                                     write_json, write_record)
from .research_tool_snapshot import snapshot_inputs
from .research_tool_stream import retain_stream


class ResearchProxy:
    def __init__(self, config):
        require(config.max_containers == 4 and config.timeout_seconds == 30)
        self.config, self.records = config, {}
        self.lock, self.stopping = threading.RLock(), threading.Event()
        self.lease = os.open(config.receipts_root / '.proxy.lock',
            os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(self.lease)
            require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid()
                    and info.st_nlink == 1 and not info.st_mode & 0o077)
            fcntl.flock(self.lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            os.close(self.lease)
            raise

    def request(self, method, path, body=None, timeout=30):
        connection = DockerConnection(self.config.docker_socket, min(timeout, 30))
        try:
            connection.request(method, path, body=body, headers={'Content-Type': 'application/json'})
            response = connection.getresponse()
            raw = response.read(MAX_RESPONSE + 1)
            require(len(raw) <= MAX_RESPONSE, 'Research Docker response exceeds limit')
            return response.status, dict(response.getheaders()), raw
        finally:
            connection.close()

    def verify_runtime(self):
        """Only the trusted daemon supplies image/platform/version; never the caller."""
        policy = self.config.policy
        status, _, raw = self.request('GET', '/images/' + quote(policy.image_id, safe='') + '/json')
        require(status == 200, 'Research image inspection failed')
        proof = image_proof(json_object(raw), policy.image_id)
        status, _, raw = self.request('GET', '/version')
        require(status == 200, 'Research daemon version unavailable')
        version = json_object(raw)
        require(version.get('Os') == 'linux' and version.get('Arch') == proof['architecture'])
        identity = executor_identity(policy.image_id, proof['architecture'], version.get('Version'))
        require(digest(identity) == policy.runtime_sha256, 'Research executor runtime changed')
        proof['runtime_sha256'] = policy.runtime_sha256
        proof['docker_server'] = version['Version']
        return proof

    def image_info(self):
        proof = self.verify_runtime()
        return {'Id': proof['image_id'], 'Os': proof['os'], 'Architecture': proof['architecture']}

    def version_info(self):
        proof = self.verify_runtime()
        return {'Version': proof['docker_server'], 'Os': proof['os'], 'Arch': proof['architecture']}

    def _ownership_path(self, record):
        return self.config.receipts_root / (record['stage'].name + '.ownership.json')

    def _save(self, record):
        write_record(self._ownership_path(record), record['saved'])

    def create(self, body, name, run_id, version, binding):
        require(type(version) is str and re.fullmatch(r'(?:/v1\.[0-9]{1,3})?', version))
        rebuilt, incoming = canonical_config(body, name, run_id, binding, self.config.policy)
        with self.lock:
            require(not self.stopping.is_set() and len(self.records) < 4 and name not in self.records
                    and all(record['run'] != run_id for record in self.records.values()),
                    'Research capacity reached: at most one foreground tool per run and four globally')
            image = self.verify_runtime()
            stage = self.config.staging_root / uuid.uuid4().hex
            stage.mkdir(mode=0o755)
            stage.chmod(0o755)
            persisted = False
            try:
                snapshot = snapshot_inputs(incoming, stage / 'inputs', self.config.policy)
                rebuilt['HostConfig']['Mounts'] = snapshot['mounts']
                now = time.time()
                saved = {'schema': 'arena.research-tool-ownership/1', 'name': name, 'run': run_id,
                    'id': None, 'created': now, 'deadline': now + min(30, snapshot['limits']['wall_seconds']),
                    'config': rebuilt, 'image': image, 'snapshot': snapshot}
                record = {'id': None, 'run': run_id, 'stage': stage, 'saved': saved,
                    'expires': time.monotonic() + saved['deadline'] - now}
                self._save(record)
                persisted = True
                self.records[name] = record
                # From this point even an exception/invalid Docker response owns
                # capacity until inspection proves the exact container absent.
                result = self.request('POST', version + '/containers/create?name=' + name, canonical(rebuilt))
                if result[0] == 201:
                    ident = json_object(result[2]).get('Id')
                    require(type(ident) is str and HASH.fullmatch(ident))
                    record['id'] = saved['id'] = ident
                    self._save(record)
                    require(self._inspect(record) == ident, 'Created research container could not be verified')
                return result
            finally:
                if not persisted:
                    shutil.rmtree(stage)

    def _inspect(self, record):
        saved = record['saved']
        snapshot_paths(record['stage'], saved)
        status, _, raw = self.request('GET', '/containers/' + (record['id'] or saved['name']) + '/json')
        if status == 404:
            return None
        require(status == 200, 'Research ownership cannot be established')
        if record['stage'].exists():
            verify_snapshot(record['stage'], saved)
        image = self.verify_runtime()
        ident = verify_container(json_object(raw), saved, image)
        if record['id'] is None:
            record['id'] = saved['id'] = ident
            self._save(record)
        return ident

    def owned(self, ident, run_id):
        with self.lock:
            for name, record in self.records.items():
                if ident in (name, record['id']):
                    require(record['run'] == run_id, 'Research container belongs to another run')
                    if self._inspect(record) is None:
                        raise KeyError(ident)
                    return name, record
        raise KeyError(ident)

    def publish(self, record):
        """Output crosses only the fixed Docker attach stream, never a host mount."""

    def record_output(self, record, raw):
        require(type(raw) is bytes and len(raw) <= 256 * 1024)
        proof = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        with self.lock:
            require(not record.get('closed') and self.records.get(record['saved']['name']) is record)
            require(record['saved'].get('output', proof) == proof, 'Research output stream changed')
            require(record['stage'].parent == self.config.staging_root)
            retain_stream(self.config.receipts_root, record['stage'].name, raw)
            record['saved']['output'] = proof
            self._save(record)

    def remove(self, name, record, daemon_status=None):
        with self.lock:
            require(daemon_status in (204, 404), 'Research cleanup requires confirmed daemon deletion')
            if record.get('closed'):
                return
            require(self.records.get(name) is record and record['saved']['name'] == name)
            receipt = {'schema': 'arena.research-tool-lifecycle/1', 'ownership': record['saved'],
                'deletion': {'daemon_status': daemon_status, 'confirmed_at': time.time()},
                'output_verified': False, 'method_manifest_verified': False}
            write_json(self.config.receipts_root / (record['stage'].name + '.receipt.json'), receipt)
            if record['stage'].exists():
                shutil.rmtree(record['stage'])
            self._ownership_path(record).unlink()
            directory = os.open(self.config.receipts_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            record['closed'] = True
            self.records.pop(name)

    def _terminate(self, name, record):
        with self.lock:
            if record.get('closed'):
                return
            ident = self._inspect(record)
            status = 404 if ident is None else self.request('DELETE', '/containers/' + ident + '?force=1')[0]
            require(status in (204, 404), 'Research daemon did not confirm deletion')
            self.remove(name, record, status)

    def reap(self):
        while not self.stopping.wait(1):
            with self.lock:
                expired = [(name, record) for name, record in self.records.items()
                           if time.monotonic() >= record['expires']]
            for name, record in expired:
                try:
                    self._terminate(name, record)
                except (OSError, ValueError, http.client.HTTPException):
                    pass  # Durable ownership and occupied capacity survive ambiguity.

    def recover(self):
        """Before accepting clients, resolve every durable root-issued intent."""
        with self.lock:
            require(not self.records)
            for path in sorted(self.config.receipts_root.glob('*.ownership.json')):
                stage_id = path.name.removesuffix('.ownership.json')
                require(RUN.fullmatch(stage_id))
                saved = load_record(path)
                require(saved['config']['Image'] == self.config.policy.image_id
                        and saved['image']['runtime_sha256'] == self.config.policy.runtime_sha256
                        and saved['name'] not in self.records)
                self.records[saved['name']] = {'saved': saved, 'id': saved['id'], 'run': saved['run'],
                    'stage': self.config.staging_root / stage_id, 'expires': time.monotonic()}
            for name, record in list(self.records.items()):
                self._terminate(name, record)
            # A stage without durable intent was never submitted to Docker.
            for stage in self.config.staging_root.iterdir():
                require(RUN.fullmatch(stage.name) and not stage.is_symlink() and stage.is_dir())
                shutil.rmtree(stage)

    def close(self):
        self.stopping.set()
        with self.lock:
            for name, record in list(self.records.items()):
                try:
                    self._terminate(name, record)
                except (OSError, ValueError, http.client.HTTPException):
                    pass
            if self.lease is not None:
                os.close(self.lease)
                self.lease = None
