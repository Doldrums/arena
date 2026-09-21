"""Committed background-job bindings and cached read-only status views."""
from __future__ import annotations

import hashlib
from pathlib import Path

from .research_tool_records import (HASH, LIMIT, _canonical, _island, _job_number,
                                    _obj, _text)


def _job_bindings(checkpoint):
    """Only committed controller state grants visibility; disk/tail events do not."""
    saved = _obj(_obj(checkpoint.get('research_tools')).get('jobs'))
    return {ident:value for ident,value in saved.items() if isinstance(ident,str) and HASH.fullmatch(ident)
        and isinstance(value,dict) and isinstance(value.get('tool_id'),str) and HASH.fullmatch(value['tool_id'])}


def _job_base(checkpoint, configured):
    bindings = _job_bindings(checkpoint)
    collected = _obj(_obj(checkpoint.get('research_tools')).get('collected_jobs'))
    items = [dict(id=ident,tool_id=value['tool_id'],owner=_obj(value.get('owner')),
        request_hash=value.get('request_hash'),collected=ident in collected)
        for ident,value in list(bindings.items())[-LIMIT:]]
    return dict(available=bool(bindings) or _obj(configured.get('jobs')).get('enabled') is True,
        items=items,summary=dict(total=len(bindings),visible=len(items),omitted=max(0,len(bindings)-LIMIT)))


def _bound_job(run_dir, binding, *, include_receipt=False):
    # Import the public pure reader, never construct a manager/service to view data.
    from .compat.jobs import read_job
    job = read_job(run_dir,binding['id'],include_receipt=include_receipt)
    if (job.get('tool_id') != binding['tool_id'] or job.get('owner') != binding.get('owner',{})
            or (binding.get('request_hash') is not None and job.get('request_hash') != binding['request_hash'])):
        raise ValueError('Background job differs from committed controller binding')
    return job


def _job_row(run_dir, binding):
    base = dict(id=binding['id'],tool_id=binding['tool_id'],collected=binding.get('collected',False))
    try:
        job = _bound_job(run_dir,binding)
        owner = _obj(job.get('owner'))
        base.update(status=job['status'],cancel_requested=job.get('cancel_requested') is True,
            cell_id=owner.get('cell_id'),island_id=_island(owner.get('island_id')),
            parent_program_id=_text(owner.get('parent_program_id')),parent_job_id=job.get('parent_job_id'),
            receipt_id=job.get('receipt_id'),dispatch_status=job.get('dispatch_status'),
            requested={key:_job_number(_obj(job.get('requested_limits')).get(key)) for key in ('cpu_seconds','wall_seconds')},
            actual={key:_job_number(_obj(job.get('resources')).get(key)) for key in ('cpu_seconds','wall_seconds')},
            error=({key:_text(job['error'].get(key),1000) for key in ('code','reason','message','type') if key in job['error']}
                if isinstance(job.get('error'),dict) else _text(job.get('error'),1500)))
        for key in ('created_at','started_at','finished_at','updated_at'):
            base[key] = _text(job.get(key),128)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        base.update(status='unknown',cancel_requested=False,requested={},actual={},receipt_id=None,
            error='Saved job unavailable or failed verification: '+str(exc)[:300])
    return base


class BackgroundJobView:
    """Refresh a bounded sidecar window without replaying the Engine journal."""
    def __init__(self, run_dir):
        self.run_dir = Path(run_dir)
        self.cache = {}

    def project(self, base):
        items, retained = [], set()
        for binding in base.get('items',[])[:LIMIT]:
            ident = binding['id'];retained.add(ident)
            directory = self.run_dir/'research_tools'/'jobs'/ident
            signatures = []
            # A parent-directory replacement must invalidate a previously
            # verified read even when the target files retain their metadata.
            for path in (self.run_dir,self.run_dir/'research_tools',directory.parent,directory):
                try:
                    info = path.lstat();signatures.append((info.st_ino,info.st_mode,info.st_ctime_ns))
                except OSError:
                    signatures.append(None)
            for name in ('spec.json','status.json','cancel.request','receipt.json'):
                path = directory/name
                try:
                    info = path.lstat();signatures.append((info.st_ino,info.st_size,info.st_mtime_ns,
                                                          info.st_ctime_ns,info.st_mode))
                except OSError:
                    signatures.append(None)
            signature = (hashlib.sha256(_canonical(binding)).hexdigest(),tuple(signatures))
            cached = self.cache.get(ident)
            if cached is None or cached[0] != signature:
                cached = (signature,_job_row(self.run_dir,binding));self.cache[ident] = cached
            items.append(cached[1])
        self.cache = {ident:value for ident,value in self.cache.items() if ident in retained}
        summary = dict(base.get('summary',{}))
        for status in ('queued','running','completed','failed','cancelled','unknown'):
            summary[status] = sum(row.get('status')==status for row in items)
        summary['cancel_requested'] = sum(row.get('cancel_requested') is True and row.get('status') in ('queued','running') for row in items)
        cpu = [row.get('actual',{}).get('cpu_seconds') for row in items]
        known = [value for value in cpu if value is not None]
        summary.update(observed_cpu_seconds=sum(known) if known else None,observed_cpu_jobs=len(known),unknown_cpu_jobs=len(items)-len(known))
        result = dict(available=base.get('available',False),items=items,summary=summary,
            scope='Committed jobs only. Status is the latest saved backend observation; a cancellation request is not proof of completion. Usage covers the visible window and excludes unobserved CPU and infrastructure overhead.')
        result['version'] = hashlib.sha256(_canonical(result)).hexdigest()
        return result


def job_detail(run_dir, ident, checkpoint):
    bindings = _job_bindings(checkpoint)
    if ident not in bindings:
        raise KeyError('Job is not committed in this controller checkpoint')
    binding = dict(id=ident,tool_id=bindings[ident]['tool_id'],owner=_obj(bindings[ident].get('owner')),
        request_hash=bindings[ident].get('request_hash'))
    job = _bound_job(run_dir,binding,include_receipt=True)
    return dict(id=ident,kind='job',verified=True,request=job.get('request'),status=job['status'],
        receipt=job.get('receipt'),snapshot={key:value for key,value in job.items() if key not in ('request','receipt')})
