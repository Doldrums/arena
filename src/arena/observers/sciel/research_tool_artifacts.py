"""Bounded immutable research artifacts, verified against their journal lineage."""
from __future__ import annotations

import difflib
import hashlib
import json
import os
from pathlib import Path
import stat

from .research_tool_records import DETAIL_BYTES, HASH, _canonical, _events, _ids, _obj


def _read_object(run_dir, folder, ident, maximum):
    if not isinstance(ident,str) or not HASH.fullmatch(ident):
        raise ValueError('Invalid artifact ID')
    base = Path(run_dir).resolve()
    directory = base / 'research_tools'
    paths = [directory]
    for part in Path(folder).parts:
        paths.append(paths[-1] / part)
    for path in paths:
        if path.is_symlink() or not path.is_dir():
            raise ValueError('Tool artifact directory unavailable')
    path = directory/folder/(ident+'.json')
    if path.is_symlink():
        raise ValueError('Tool artifacts cannot be symbolic links')
    fd = os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            raise ValueError('Tool artifact exceeds read bound')
        with os.fdopen(fd,'rb',closefd=False) as handle:
            raw = handle.read(maximum+1)
    finally:
        os.close(fd)
    if len(raw)>maximum:
        raise ValueError('Tool artifact exceeds read bound')
    body = json.loads(raw)
    if not isinstance(body,dict) or hashlib.sha256(_canonical(body)).hexdigest()!=ident:
        raise ValueError('Tool artifact hash mismatch')
    return body


def _bundle(run_dir, ident, *, _reader=None):
    body = (_reader or (lambda folder, key, maximum: _read_object(run_dir, folder, key, maximum)))('objects',ident,1600*1024)
    files, manifest = _obj(body.get('files')),_obj(body.get('manifest'))
    protocol = _obj(manifest.get('protocol'))
    if (body.get('schema')!='sciel-method/1' or manifest.get('kind')!='tool' or manifest.get('entrypoint')!='tool.py:run'
            or set(files)!={'tool.py'} or not isinstance(files['tool.py'],str)
            or len(files['tool.py'].encode())>256*1024 or protocol.get('schema') not in ('sciel-research-tool/1','sciel-research-tool/2','sciel-research-tool/3')):
        raise ValueError('Unsupported tool artifact')
    if protocol['schema'] in ('sciel-research-tool/2','sciel-research-tool/3') and (protocol.get('result_schema')!='sciel-tool-result/1'
            or protocol.get('replay_policy') not in ('exact_observations','independent_execution')):
        raise ValueError('Unsupported tool result contract')
    if protocol['schema']=='sciel-research-tool/3' and protocol.get('research_targets_schema') not in ('sciel-research-targets/1','sciel-research-targets/2'):
        raise ValueError('Unsupported research input contract')
    return body


def tool_detail(run_dir, ident, rows):
    if not any(r.get('tool_id')==ident and r.get('phase') in ('registered','published') for r in _events(rows)):
        raise KeyError('Tool is not registered in this journal lineage')
    body = _bundle(run_dir,ident)
    code = body['files']['tool.py']; parents = []
    for parent in _ids(_obj(body.get('manifest')).get('parents'))[:16]:
        try:
            source = _bundle(run_dir,parent)['files']['tool.py']
            diff = ''.join(difflib.unified_diff(source.splitlines(keepends=True),code.splitlines(keepends=True),fromfile=parent,tofile=ident,n=3))
            parents.append(dict(id=parent,verified=True,diff=diff))
        except (OSError,ValueError,KeyError):
            parents.append(dict(id=parent,verified=False,diff=None,reason='Parent artifact unavailable or failed hash verification'))
    return dict(id=ident,verified=True,manifest=body['manifest'],files=body['files'],parents=parents,
        source_sha256=hashlib.sha256(code.encode()).hexdigest(),source_hash_scope='UTF-8 tool.py only; executor file-bundle hashes use a different scope.')


def artifact_detail(run_dir, ident, rows, *, _reader=None):
    candidates = [row for row in _events(rows) if row.get('canonical_evaluation_id')==ident
        and row.get('phase')=='research_step' and row.get('action')=='submit_candidate']
    if candidates:
        return _candidate_evaluation_detail(run_dir,ident,rows,candidates,_reader)
    events = [row for row in _events(rows) if row.get('receipt_id')==ident and row.get('phase') in ('llm_result','invocation_result')]
    if not events:
        raise KeyError('Receipt is not bound to this journal lineage')
    body = (_reader or (lambda folder, key, maximum: _read_object(run_dir, folder, key, maximum)))('artifacts',ident,16*1024*1024)
    payload = _obj(body.get('payload'))
    if body.get('schema')!='sciel-research-tool-artifact/1' or body.get('kind') not in ('invocation','proposal'):
        raise ValueError('Unsupported tool receipt')
    expected_phase = 'invocation_result' if body['kind']=='invocation' else 'llm_result'
    binding = ('action_id','island_id','parent_program_id','tool_id','cell_id','cell_revision_id','stage') if body['kind']=='invocation' else ('action_id','attempt')
    if body['kind']=='invocation' and ('target_binding' in payload or 'research_targets' in _obj(payload.get('inputs'))):
        from .compat.research_targets import input_binding
        target_binding = input_binding(payload['inputs'])
        if payload.get('target_binding') != target_binding or payload.get('input_program_id') != target_binding['candidate_id']:
            raise ValueError('Receipt input identity differs from saved sources')
        events = [row for row in events if row.get('target_binding') == target_binding]
        binding += ('target_binding',)
    if not any(row.get('phase')==expected_phase and all(key not in row or row[key]==payload.get(key)
        for key in binding) for row in events):
        raise ValueError('Receipt does not match its journal binding')
    detail = dict(id=ident,verified=True,kind=body['kind'],payload=payload)
    if body['kind'] == 'invocation':
        detail['comparison_assessment'] = _comparison_assessment(run_dir, ident, payload, _reader)
    return detail


def _comparison_assessment(run_dir, ident, payload, reader=None):
    """Recompute comparison warnings from saved declarations and invocation output."""
    from .compat.comparison_assessment import from_record
    read = reader or (lambda folder, key, maximum: _read_object(run_dir, folder, key, maximum))

    def proposal(key):
        record = read('artifacts', key, 16 * 1024 * 1024)
        if record.get('schema') != 'sciel-research-tool-artifact/1' or record.get('kind') != 'proposal':
            raise ValueError('Comparison declaration is not a saved proposal')
        return _obj(record.get('payload'))

    return from_record(payload, ident, proposal)


def _candidate_evaluation_detail(run_dir, ident, rows, events, reader):
    read = reader or (lambda folder,key,maximum:_read_object(run_dir,folder,key,maximum))
    body = read('artifacts',ident,2*1024*1024)
    payload = _obj(body.get('payload')); provenance = _obj(payload.get('provenance'))
    source = payload.get('source'); evaluation = _obj(payload.get('evaluation'))
    digest = hashlib.sha256(source.encode()).hexdigest() if isinstance(source,str) else None
    if (body.get('schema')!='sciel-research-tool-artifact/1' or body.get('kind')!='candidate_evaluation'
            or provenance.get('schema')!='sciel-research-candidate-submission/1'
            or not digest or provenance.get('candidate_source_sha256')!=digest
            or evaluation.get('source_sha256')!=digest
            or not any(row.get('cell_id')==provenance.get('cell_id') and row.get('action_id')==provenance.get('action_id')
                and row.get('source_sha256')==digest for row in events)):
        raise ValueError('Candidate evaluation differs from its journal/source binding')
    origin_id = provenance.get('receipt_id')
    if read('artifacts',origin_id,16*1024*1024).get('kind')!='invocation':
        raise ValueError('Candidate origin must be an invocation artifact')
    original = artifact_detail(run_dir,origin_id,rows,_reader=reader)
    saved = original['payload']; receipt = _obj(saved.get('receipt'))
    if (original['kind']!='invocation' or saved.get('cell_id')!=provenance.get('cell_id')
            or saved.get('tool_id')!=provenance.get('tool_id')
            or receipt.get('invocation_id')!=provenance.get('invocation_id')
            or _obj(_obj(receipt.get('output')).get('observations')).get('candidate_source')!=source):
        raise ValueError('Candidate source differs from its saved tool result')
    return dict(id=ident,kind='candidate_evaluation',verified=True,payload=payload)


class _DetailReader:
    """One detail request has a shared read budget and no execution service."""
    def __init__(self, run_dir):
        self.run_dir, self.remaining, self.cache = run_dir, DETAIL_BYTES, {}

    def __call__(self, folder, ident, maximum):
        key = (folder, ident)
        if key not in self.cache:
            if self.remaining <= 0:
                raise ValueError('Cell detail artifact budget exhausted')
            body = _read_object(self.run_dir, folder, ident, min(maximum, self.remaining))
            self.remaining -= len(_canonical(body))
            self.cache[key] = body
        return self.cache[key]
