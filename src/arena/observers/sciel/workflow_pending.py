"""Authenticated pending-wave reads, separate from committed journal records."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from .llm_calls import _open_regular
from .workflow_records import MAX_WAVE_BYTES, MAX_WAVE_CALLS, digest, obj


def read_bytes(root, path, maximum):
    path = Path(path)
    if not path.is_relative_to(root) or any(p.is_symlink() for p in (path, *path.parents) if p == root or p.is_relative_to(root)):
        raise ValueError('Unsafe saved artifact')
    with _open_regular(path) as stream:
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError('Saved artifact exceeds the display limit')
    return raw


def read_json(root, path, maximum=16*1024*1024):
    raw = read_bytes(root, path, maximum)
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('Saved artifact is not an object')
    return value, hashlib.sha256(raw).hexdigest()


def file_signature(path):
    try:
        value=path.lstat()
        return value.st_ino,value.st_mode,value.st_size,value.st_mtime_ns,value.st_ctime_ns
    except OSError:
        return None


def pending_wave(run_dir, rows, cache=None, *, include_calls=True):
    """Authenticate the one current wave and its durable receipts, without replay."""
    root = Path(run_dir)
    pointer_path = root / '.parallel' / 'current.json'
    if not pointer_path.exists() and not pointer_path.is_symlink():
        return [], [], []
    warnings = []
    cache = cache if cache is not None else {}
    try:
        pointer, pointer_hash = read_json(root, pointer_path,65536)
        wave = pointer.get('wave_id')
        if (pointer.get('schema') != 'sciel-wave-transaction/2' or not isinstance(wave,str)
                or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}',wave)):
            raise ValueError('Invalid current wave')
        directory = root / '.parallel' / ('wave-' + wave)
        manifest_path = directory / 'transaction.json'
        manifest, manifest_hash = read_json(root, manifest_path,65536)
        if manifest.get('schema') != pointer['schema'] or manifest.get('wave_id') != wave:
            raise ValueError('Wave manifest identity mismatch')
        if manifest.get('phase') == 'committed':
            return [], [], []
        if manifest.get('phase') not in ('active','prepared'):
            raise ValueError('Wave baseline is not published')
        baseline_name, journal_name = manifest.get('baseline'), manifest.get('journal')
        if (not isinstance(baseline_name,str) or not re.fullmatch(r'[a-f0-9]{32}\.baseline\.json',baseline_name)
                or not isinstance(journal_name,str) or not re.fullmatch(r'[a-f0-9]{32}\.journal\.jsonl',journal_name)):
            raise ValueError('Invalid wave artifact names')
        start = next((r for r in reversed(rows) if r.get('event')=='run_start'),{})
        binding_key = (manifest_hash, file_signature(directory/baseline_name), file_signature(root/'checkpoint.json'),
            file_signature(root/'sciel_events.jsonl'), file_signature(root), file_signature(root/'.parallel'), file_signature(directory))
        if cache.get('binding') != binding_key:
            baseline, baseline_hash = read_json(root, directory / baseline_name, 128*1024*1024)
            _, main_hash = read_json(root, root/'checkpoint.json',128*1024*1024)
            if manifest['phase']=='prepared' and main_hash==manifest.get('candidate_sha256'):
                return [], [], []
            provenance = obj(baseline.get('provenance'));anchor=obj(provenance.get('journal_anchor'))
            boundary = manifest.get('base_journal_bytes')
            if (not start.get('run_id') or provenance.get('run_id')!=start['run_id']
                    or baseline_hash!=manifest.get('baseline_sha256') or main_hash!=baseline_hash
                    or type(boundary) is not int or not 0 <= boundary <= 512*1024*1024
                    or anchor.get('byte_offset')!=boundary or anchor.get('prefix_sha256')!=manifest.get('base_journal_sha256')):
                raise ValueError('Wave baseline binding mismatch')
            remaining=boundary;hasher=hashlib.sha256()
            journal = root/'sciel_events.jsonl'
            if journal.is_symlink():
                raise ValueError('Unsafe journal')
            with _open_regular(journal) as stream:
                while remaining:
                    chunk=stream.read(min(1024*1024,remaining))
                    if not chunk:
                        raise ValueError('Incomplete baseline journal')
                    remaining-=len(chunk);hasher.update(chunk)
            if hasher.hexdigest()!=manifest.get('base_journal_sha256'):
                raise ValueError('Wave journal prefix mismatch')
            cache['binding'] = binding_key
        pending=[]
        if (directory/journal_name).exists():
            raw=read_bytes(root,directory/journal_name,MAX_WAVE_BYTES)
            known={(r.get('segment_id'),r.get('event_seq')) for r in rows if type(r.get('event_seq')) is int}
            previous=max((r.get('event_seq',0) for r in rows if r.get('segment_id')==start.get('segment_id')),default=0)
            for line in raw.splitlines(keepends=True):
                if not line.endswith(b'\n'):
                    warnings.append('An incomplete pending record is waiting for its writer.');break
                r=json.loads(line)
                if (not isinstance(r,dict) or r.get('run_id')!=start['run_id'] or r.get('segment_id')!=start.get('segment_id')
                        or type(r.get('event_seq')) is not int):
                    raise ValueError('Unbound pending journal record')
                key=(r['segment_id'],r['event_seq'])
                if key in known:
                    continue
                if r['event_seq'] <= previous:
                    raise ValueError('Pending journal order changed')
                previous=r['event_seq'];known.add(key);pending.append(r)
        if not include_calls:
            return pending, [], warnings
        calls=[];call_bytes=0
        call_dir=directory/'calls'
        if call_dir.exists():
            if call_dir.is_symlink():
                raise ValueError('Unsafe call directory')
            for child in sorted(call_dir.iterdir()):
                if len(calls)>=MAX_WAVE_CALLS:
                    warnings.append('Pending call display limit reached.');break
                if not re.fullmatch('[a-f0-9]{64}',child.name) or child.is_symlink():
                    continue
                try:
                    sizes=[file_signature(child/name) for name in ('intent.json','dispatched.json','receipt.json')]
                    call_bytes+=sum(sig[2] for sig in sizes if sig)
                    if call_bytes>MAX_WAVE_BYTES:
                        warnings.append('Pending receipt byte limit reached; later receipts are omitted.');break
                    intent,_=read_json(root,child/'intent.json')
                    kind,key=intent.get('kind'),intent.get('key')
                    if (intent.get('schema')!='sciel-parallel-call/1' or not isinstance(key,str)
                            or hashlib.sha256(key.encode()).hexdigest()!=child.name
                            or kind not in ('llm','evaluation','tool_execution','tool_job_submit','tool_job_poll','tool_job_cancel')
                            or intent.get('request_sha256')!=digest(dict(kind=kind,request=intent.get('request')))):
                        raise ValueError('Invalid pending intent')
                    dispatch, receipt={},{};receipt_sha=None
                    if (child/'dispatched.json').exists():
                        dispatch,_=read_json(root,child/'dispatched.json')
                        if dispatch.get('request_sha256')!=intent['request_sha256']:
                            raise ValueError('Dispatch mismatch')
                    if (child/'receipt.json').exists():
                        envelope,_=read_json(root,child/'receipt.json')
                        receipt=obj(envelope.get('payload'));receipt_sha=envelope.get('sha256')
                        if (not dispatch or envelope.get('sha256')!=digest(receipt)
                                or receipt.get('request_sha256')!=intent['request_sha256']
                                or receipt.get('status') not in ('returned','error')):
                            raise ValueError('Receipt mismatch')
                    calls.append(dict(id=child.name,wave=wave,intent=intent,dispatch=dispatch,receipt=receipt,receipt_sha256=receipt_sha))
                except (OSError,ValueError,TypeError,RecursionError):
                    warnings.append('A pending call is unavailable or failed verification.')
        if read_json(root,manifest_path)[1]!=manifest_hash or read_json(root,pointer_path)[1]!=pointer_hash:
            raise ValueError('Wave changed during projection')
        warnings.append('Pending wave records are saved activity, not committed scientific results.')
        return pending,calls,warnings
    except (OSError,ValueError,KeyError,TypeError,RecursionError,OverflowError):
        return [],[],['Pending wave activity is unavailable or failed verification.']
