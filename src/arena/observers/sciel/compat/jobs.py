"""Read-only journal compatibility extracted from sciel.research_tools.jobs.

SCiEL source commit: 0d67f813dd4ac21dee304f2b0de0b0ce59bf4157.
Only dependency-reachable validators/readers/constants are retained.
"""
from __future__ import annotations

import math


import os


from pathlib import Path


import stat


from .models import content_hash, detached, require_hash


from .library import _decode


SCHEMA = 'sciel-research-tool-job/1'


TERMINAL = frozenset({'completed', 'failed', 'cancelled', 'unknown'})


MAX_BYTES = 20 * 1024 * 1024


def _root(run_dir):
    supplied = Path(run_dir).expanduser().absolute()
    if supplied.is_symlink():
        raise ValueError('job run directory cannot be a symbolic link')
    supplied = supplied.parent.resolve() / supplied.name
    _no_links(supplied)
    return supplied / 'research_tools' / 'jobs'


def _no_links(path):
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError('job storage refuses symbolic links')


def read_json(path):
    _no_links(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
            raise ValueError('job object must be a bounded regular file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(MAX_BYTES + 1)
        after = os.fstat(fd)
        if (len(raw) > MAX_BYTES or len(raw) != before.st_size or
                (before.st_ino, before.st_size, before.st_mtime_ns) !=
                (after.st_ino, after.st_size, after.st_mtime_ns)):
            raise ValueError('job object changed during read')
        return _decode(raw)
    finally:
        os.close(fd)


def _spec(root, job_id):
    require_hash(job_id, 'job ID')
    value = read_json(root / job_id / 'spec.json')
    if (value.get('schema') != SCHEMA or value.get('job_id') != job_id or
            value.get('request_hash') != content_hash(value.get('request')) or
            job_id != content_hash({'schema': SCHEMA, 'job_key': value.get('job_key')})):
        raise ValueError('job spec identity differs')
    return value


def _receipt(spec, root, value=None):
    value = read_json(root / spec['job_id'] / 'receipt.json') if value is None else value
    request = spec['request']
    if (value.get('method_id') != request['tool_id'] or
            value.get('invocation_id') != spec['job_id'] or
            value.get('plan_id') != request['owner'].get('action_id', spec['request_hash']) or
            value.get('reservation_id') != spec['job_id'] or
            value.get('input_sha256') != content_hash(request['inputs']) or
            value.get('source_sha256') != request['source_sha256'] or
            value.get('runtime_sha256') != request['runtime_sha256'] or
            value.get('dependency_ids') != request['dependency_ids'] or
            value.get('limits') != request['limits'] or
            value.get('status') not in ('ok', 'failed', 'unknown') or
            value.get('dispatch_status') not in ('invoked', 'not_dispatched', 'unknown')):
        raise ValueError('job receipt differs from its immutable request')
    if value.get('receipt_sha256') != content_hash({k:v for k,v in value.items() if k != 'receipt_sha256'}):
        raise ValueError('job receipt checksum differs')
    if value['status'] == 'ok' and (value.get('dispatch_status') != 'invoked' or
            value.get('output_sha256') != content_hash(value.get('output'))):
        raise ValueError('job successful output is not bound')
    resources = value.get('resources')
    if type(resources) is not dict:
        raise ValueError('job receipt lacks resource accounting')
    if value['status'] != 'unknown' and any(type(resources.get(key)) not in (int,float)
            or not math.isfinite(resources[key]) or resources[key] < 0 for key in ('cpu_seconds','wall_seconds')):
        raise ValueError('job terminal receipt lacks measured resources')
    return value


def read_job(run_dir, job_id, *, include_receipt=False):
    """Pure bounded dashboard read. Never starts a service, executes or reconciles."""
    root = _root(run_dir)
    spec = _spec(root, job_id)
    state = read_json(root / job_id / 'status.json')
    if (state.get('schema') != SCHEMA or state.get('job_id') != job_id or
            state.get('request_hash') != spec['request_hash'] or
            state.get('status') not in TERMINAL | {'queued', 'running'}):
        raise ValueError('job status differs from its immutable spec')
    request = spec['request']
    result = dict(state, tool_id=request['tool_id'], owner=detached(request['owner']),
        parent_job_id=request['parent_job_id'], requested_limits=detached(request['limits']))
    cancel = root / job_id / 'cancel.request'
    if cancel.exists() or cancel.is_symlink():
        ack = read_json(cancel)
        if ack != {'job_id':job_id, 'request_hash':spec['request_hash'], 'cancel_requested':True}:
            raise ValueError('job cancellation request differs')
        result['cancel_requested'] = True
    else:
        result['cancel_requested'] = False
    if state.get('receipt_id') is not None:
        receipt = _receipt(spec, root)
        if content_hash(receipt) != state['receipt_id']:
            raise ValueError('job status terminal receipt differs')
        if (state.get('resources') != receipt.get('resources') or
                state.get('dispatch_status') != receipt['dispatch_status'] or
                (state['status']=='completed') != (receipt['status']=='ok') or
                (state['status']=='unknown') != (receipt['status']=='unknown')):
            raise ValueError('job terminal status/accounting differs from receipt')
        if include_receipt:
            result['receipt'] = receipt
    if include_receipt:
        result['request'] = detached(spec['request'])
    return result
