"""Chronological, read-only activity feed; large saved evidence is lazy.

The unpublished parallel wave is deliberately labelled pending. Its checkpoint,
journal prefix and manifest are verified before any of its records are exposed.
No status here commits experiments or reconstructs missing model text.
"""
from __future__ import annotations

from datetime import datetime
import difflib
import hashlib
import json
import math
from pathlib import Path
import re

from .llm_calls import collect_calls, detail as call_detail, metadata as call_metadata, _open_regular
from .methods import registered_artifacts
from .research_tools import artifact_detail, tool_detail

SCHEMA = 'sciel-workflow/1'
ACTORS = {'model', 'tool', 'task', 'system'}
MAX_PAGE = 100
MAX_WAVE_CALLS = 4096
MAX_WAVE_BYTES = 64 * 1024 * 1024
MAX_DETAIL_BYTES = 16 * 1024 * 1024
_SECRET = {'api_key', 'authorization', 'access_token', 'refresh_token', 'password', 'secret'}


def obj(value):
    return value if isinstance(value, dict) else {}


def number(value):
    try:
        return value if type(value) in (int, float) and math.isfinite(value) else None
    except OverflowError:
        return None


def text(value, limit=280):
    return ' '.join(value.split())[:limit] if isinstance(value, str) else None


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
        allow_nan=False).encode()).hexdigest()


def stamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return value if parsed.tzinfo is not None else None
    except (ValueError, OverflowError):
        return None


def clean(value, depth=0):
    if depth > 45:
        return '[nested data omitted]'
    if isinstance(value, dict):
        return {str(k): '[redacted]' if str(k).lower() in _SECRET else clean(v, depth+1) for k,v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v, depth+1) for v in value]
    if isinstance(value, float):
        return number(value)
    return value if value is None or type(value) in (str, int, bool) else str(value)


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


def refs(row):
    evidence=obj(row.get('evidence'));meta=obj(row.get('meta'))
    result={}
    sources={**evidence,**meta,**row}
    for key in ('program_id','child_id','parent_id','parent_program_id','child_program_id','experiment_id',
                'call_id','tool_id','receipt_id','cell_id','job_id','island_id','lab_id','wave','reference'):
        value=sources.get(key)
        if type(value) in (str,int):
            result[key]=str(value)[:128]
    result['program_id']=result.get('program_id') or result.get('child_id') or result.get('child_program_id')
    if result['program_id'] is None:
        result.pop('program_id')
    if 'research_id' in meta and 'experiment_id' not in result:
        result['experiment_id']=text(meta['research_id'],128)
    return result


def item(ident,actor,kind,title,summary,timestamp,**fields):
    return dict(id=ident,actor=actor,actor_label={'model':'Model','tool':'Tool','task':'Task','system':'System'}[actor],
        kind=kind,title=title,summary=text(summary,360) or '',timestamp=stamp(timestamp),timestamp_source=fields.pop('timestamp_source','journal'),
        elapsed_seconds=fields.pop('elapsed_seconds',None),duration_seconds=fields.pop('duration_seconds',None),
        cost=fields.pop('cost',None),status=fields.pop('status',None),iteration=fields.pop('iteration',None),
        model=fields.pop('model',None),refs=fields.pop('refs',{}),publication=fields.pop('publication','committed'),
        details_available=True,**fields)


def human(value):
    return str(value or 'event').replace('_',' ').replace('-',' ').capitalize()[:100]


def journal_item(row,index,pending=False):
    event,phase=row.get('event'),row.get('phase')
    evidence=obj(row.get('evidence'))
    kind=str(phase or row.get('action') or event or 'event')
    actor='tool' if event=='research_tool' else 'task' if event in ('iteration','evaluation','seed','seed_evaluation') or phase=='outcome' else 'system'
    if event=='research' and phase in ('hypothesis','conclusion','reflection','idea','structured_response'):
        actor='model'
    title={'run_start':'Run resumed' if row.get('resumed') else 'Run started','run_end':'Run finished',
        'iteration':'Candidate evaluated','hypothesis':'Hypothesis recorded','conclusion':'Conclusion recorded',
        'reflection':'Research reflection','outcome':'Experiment outcome','checkpoint_restore':'Checkpoint restored'}.get(kind,human(kind))
    if phase in ('conclusion','reflection','hypothesis') and row.get('status') in ('skipped','rejected','invalid','failed'):
        title=human(phase)+' '+str(row['status'])
    tags=[]
    for key in ('policy','task','status','reason_code','operation','stage'):
        if isinstance(row.get(key),str):tags.append(text(row[key],100))
    for key,label in (('calls','model calls'),('evaluations','evaluations'),('tool_executions','tool executions')):
        if type(row.get(key)) is int:tags.append(f'{row[key]} {label}')
    if phase=='outcome' and evidence.get('status'):tags.append(human(evidence['status']))
    if event=='iteration' and number(row.get('child_score')) is not None:tags.append(f"Score {row['child_score']:.6g}")
    hypothesis=obj(row.get('hypothesis'))
    description=text(row.get('question') or row.get('description') or hypothesis.get('mechanism'))
    if description:tags.append(description)
    ident='event-'+digest([row.get('run_id'),row.get('segment_id'),row.get('event_seq',index),event,phase])[:32]
    return item(ident,actor,kind,title,' · '.join(tags)[:360],row.get('timestamp'),refs=refs(row),
        iteration=row.get('iteration_no',row.get('iteration',evidence.get('iteration'))),
        model=text(row.get('model') or row.get('model_used'),128),
        elapsed_seconds=number(row.get('segment_elapsed_seconds')),
        duration_seconds=number(row.get('elapsed_seconds')),cost=number(row.get('cost',row.get('known_cost'))),
        status=text(row.get('status') or evidence.get('status'),64),publication='pending' if pending else 'committed',_kind='journal',_row=row)


def call_items(call,pending=False):
    meta=call_metadata(call);role={'G':'Generation','C':'Conclusion','R':'Reflection','idea':'Idea'}.get(meta.get('role'),human(meta.get('role')))
    common=dict(refs=refs(dict(meta,call_id=meta['id'])),model=text(meta.get('model'),128),iteration=meta.get('iteration'),
        publication='pending' if pending else 'committed',timestamp_source='llm_trace' if meta['source']=='trace' else 'journal',_kind='call',_call=call)
    result=[item('call-'+meta['id']+'-request','task','model_request',role+' request',
        f"{meta.get('model') or 'Recorded model'} · {meta.get('prompt_chars') or 'Unknown'} prompt characters",
        meta.get('started_at'),status='recorded',**common)]
    if meta.get('ended_at') is not None or meta.get('status') in ('returned','failed'):
        records=[obj(call.get(key)) for key in ('_request','_terminal','_trace_request','_trace_terminal')]
        legacy=obj(call.get('_legacy'));records.extend(obj(legacy.get(key)) for key in ('_request','_terminal'))
        not_sent=any(r.get('generation_dispatch')=='not_dispatched' or r.get('dispatch_status')=='not_dispatched' or r.get('not_dispatched') is True for r in records)
        result.append(item('call-'+meta['id']+'-response','system' if not_sent else 'model','request_not_dispatched' if not_sent else 'model_response',
            role+' request not sent' if not_sent else role+' response' if meta['status']=='returned' else role+' request failed',
            'Stopped before provider dispatch' if not_sent else 'Response recorded' if meta['status']=='returned' else 'No usable terminal response recorded',meta.get('ended_at'),
            status='not_dispatched' if not_sent else meta['status'],duration_seconds=number(meta.get('elapsed_seconds')),cost=number(meta.get('cost')),**common))
    return result


def durable_items(call,matched_calls):
    intent=call['intent'];request=obj(intent.get('request'));receipt=call['receipt'];dispatch=call['dispatch']
    kind=intent['kind'];value=obj(receipt.get('value'))
    # Traces already provide the complete exchange; receipts fill genuine gaps.
    if kind=='llm':
        prompt_sha=hashlib.sha256(str(request.get('prompt','')).encode()).hexdigest()
        candidates=[]
        for c in matched_calls:
            trace_request=obj(c.get('_trace_request'))
            job=trace_request.get('parallel_job')
            if (c.get('prompt_sha256')==prompt_sha and c.get('model')==request.get('model')
                    and isinstance(job,str) and intent['key'].rsplit(':',1)[0]==job
                    and stamp(c.get('started_at')) and stamp(dispatch.get('timestamp'))):
                delta=datetime.fromisoformat(c['started_at'].replace('Z','+00:00')).timestamp()-datetime.fromisoformat(dispatch['timestamp'].replace('Z','+00:00')).timestamp()
                if 0<=delta<5:candidates.append(c)
        # Ambiguous provenance is shown separately rather than silently hidden.
        if len(candidates)==1:
            return []
    actor='model' if kind=='llm' else 'task' if kind=='evaluation' else 'tool'
    label={'llm':'Model call','evaluation':'Evaluator','tool_execution':'Tool execution','tool_job_submit':'Background job submission',
        'tool_job_poll':'Background job poll','tool_job_cancel':'Background job cancellation'}.get(kind,human(kind))
    common=dict(refs=dict(wave=call['wave'],reference=intent['key']),model=text(request.get('model'),128),
        publication='pending',timestamp_source='durable_receipt',_kind='durable',_durable=call)
    result=[item('io-'+call['wave']+'-'+call['id']+'-request','task' if kind=='llm' else actor,kind+'_request',
        label+(' started' if dispatch else ' queued'),text(intent['key']),dispatch.get('timestamp'),status='dispatched' if dispatch else 'queued',**common)]
    if receipt:
        result.append(item('io-'+call['wave']+'-'+call['id']+'-result',actor,kind+'_result',label+(' returned' if receipt['status']=='returned' else ' failed'),
            text(intent['key']),receipt.get('completed_at'),status=receipt['status'],duration_seconds=number(receipt.get('elapsed_seconds')),
            cost=number(value.get('cost')) if kind=='llm' else None,**common))
    return result


def public(entry):
    result = {key:value for key,value in entry.items() if not key.startswith('_')}
    result['commit_state'] = result.get('publication')
    call=obj(entry.get('_call'));receipt=obj(obj(entry.get('_durable')).get('receipt'))
    result['detail_version'] = digest(clean([result, {key:call.get(key) for key in ('status','ended_at','cost','response_sha256','error')},
        {key:receipt.get(key) for key in ('status','completed_at','elapsed_seconds','request_sha256')},obj(entry.get('_durable')).get('receipt_sha256')]))
    return result


def file_signature(path):
    try:
        value=path.lstat()
        return value.st_ino,value.st_mode,value.st_size,value.st_mtime_ns,value.st_ctime_ns
    except OSError:
        return None



class WorkflowView:
    def __init__(self,store,run_id):
        self.store=store;self.run_id=run_id;self.path=store._path(run_id);self.rows=[];self.calls=[]
        self.methods=store._methods(self.path) if self.path.name=='journal.jsonl' else None
        self._binding_cache={}
        self._base_cache=None

    def signature(self):
        if self.methods is not None:
            return self.methods.signature()
        root=self.path.parent
        paths=[self.path,root/'checkpoint.json',root/'artifacts/llm_calls.jsonl',root/'.parallel/current.json']
        try:
            pointer,_=read_json(root,root/'.parallel/current.json',65536)
            wave=pointer.get('wave_id')
            if isinstance(wave,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}',wave):
                directory=root/'.parallel'/('wave-'+wave)
                paths.extend((root,root/'.parallel',directory,directory/'transaction.json',directory/'calls'))
                manifest,_=read_json(root,directory/'transaction.json',65536)
                name=manifest.get('journal')
                if isinstance(name,str) and re.fullmatch(r'[a-f0-9]{32}\.journal\.jsonl',name):paths.append(directory/name)
                calls=directory/'calls'
                if calls.is_dir() and not calls.is_symlink():
                    for index,child in enumerate(sorted(calls.iterdir())):
                        if index>=MAX_WAVE_CALLS:break
                        paths.extend((child,child/'intent.json',child/'dispatched.json',child/'receipt.json'))
        except (OSError,ValueError,TypeError,RecursionError):pass
        return tuple((str(path),file_signature(path)) for path in paths)

    def entries(self):
        signature=self.signature()
        if self._base_cache is None or self._base_cache[0]!=signature:
            base,warnings=self.base_entries()
            if signature==self.signature():self._base_cache=(signature,base,warnings)
        else:
            _,base,warnings=self._base_cache
        entries=list(base);warnings=list(warnings)
        if self.methods is not None:
            identity_row=next((r for r in self.rows if r.get('kind')=='coordinator_identity'),{})
            data=obj(identity_row.get('data'))
            runtime=self.methods.runtime(obj(data.get('identity')),data.get('started_at'))
        else:
            published,_=self.store._journal(self.path)
            start=next((r for r in reversed(published) if r.get('event')=='run_start'),{})
            runtime=self.store._runtime(self.path,start)
        if runtime.get('verification')=='terminal_recorded':
            status=runtime['status'];finished=runtime.get('finished_at')
            entries.append(item('runtime-'+digest([runtime.get('runtime_id'),status,finished])[:32],'system','runtime_terminal',
                'Session '+status,'Recorded terminal runtime status',finished,status=status,timestamp_source='runtime',
                _kind='runtime',_runtime={key:runtime.get(key) for key in ('status','stage','started_at','finished_at','verification','error_type')}))
        return entries,warnings

    def base_entries(self):
        if self.methods is not None:
            return self.method_entries()
        published,warnings=self.store._journal(self.path)
        pending,durable,more=pending_wave(self.path.parent,published,self._binding_cache);warnings+=more
        self.rows=published+pending
        entries=[journal_item(row,index,index>=len(published)) for index,row in enumerate(self.rows)]
        self.calls=collect_calls(self.path.parent,self.rows)
        pending_keys={(r.get('segment_id'),r.get('event_seq')) for r in pending}
        for call in self.calls:
            request=call.get('_request',{})
            is_pending=((request.get('segment_id'),request.get('journal_event_seq',request.get('event_seq'))) in pending_keys)
            entries.extend(call_items(call,is_pending))
        for call in durable:
            entries.extend(durable_items(call,self.calls))
        return entries,warnings

    def method_entries(self):
        self.rows,warnings=self.methods.rows()
        projection=self.store._methods_projection(self.run_id,self.path).get('methods',{})
        proposals={p['id']:p for p in projection.get('proposals',[]) if isinstance(p,dict) and p.get('id')}
        receipts={r['id']:r for r in projection.get('receipts',[]) if isinstance(r,dict) and r.get('id')}
        entries=[]
        for row in self.rows:
            data=obj(row.get('data'));kind=data.get('kind') if row.get('kind')=='artifact_registered' else row.get('kind')
            actor='tool' if kind in ('method_registered','method_status') else 'task' if kind in ('experiment','experiment_plan','solution','proposal_context') else 'system'
            title={'proposal_receipt':'Proposal receipt recorded','proposal_context':'Proposal context prepared','method_registered':'Tool registered',
                'lab_created':'Research lab created','lab_revised':'Research lab revised','call_receipt':'Invocation receipt recorded'}.get(kind,human(kind))
            status=None;cost=None
            if kind=='proposal_receipt' and data.get('id') in proposals:
                saved=proposals[data['id']];status=saved.get('status');cost=number(saved.get('cost'))
                if saved.get('dispatch_status')=='not_dispatched':
                    actor='system';title='Proposal request not sent';status='not_dispatched'
                else:
                    actor='model';title='Proposal '+str(status) if status in ('invalid','refused','failed') else 'Model proposal recorded'
            elif kind=='call_receipt' and data.get('id') in receipts:
                saved=receipts[data['id']];status=saved.get('status')
                category=saved.get('category');cost=number(obj(saved.get('actual')).get('dollars'))
                if saved.get('dispatch_status')=='not_dispatched':
                    actor='system';title='Request not dispatched';status='not_dispatched'
                elif category=='generation':actor='model';title='Model call receipt recorded'
                elif category in ('execution','replication'):actor='tool';title='Tool invocation receipt recorded'
                elif category=='measurement':actor='task';title='Measurement receipt recorded'
            summary=' · '.join(str(data[k])[:96] for k in ('lab_id','status','id') if type(data.get(k)) in (str,int))
            entries.append(item('method-'+row['id'],actor,str(kind),title,summary,row.get('at'),refs=refs(data),
                timestamp_source='registry',status=status,cost=cost,_kind='method',_row=row))
        return entries,warnings

    def page(self,*,limit=60,before=None,actor='all',query=''):
        if type(limit) is not int or not 1<=limit<=MAX_PAGE or actor not in ACTORS|{'all'}:
            raise ValueError('Invalid workflow page')
        entries,warnings=self.entries()
        # Sorting by parsed UTC makes equivalent offsets chronological; file order breaks ties.
        entries.sort(key=lambda e: datetime.fromisoformat(e['timestamp'].replace('Z','+00:00')).timestamp() if e['timestamp'] else -math.inf)
        if actor!='all':entries=[e for e in entries if e['actor']==actor]
        if query:
            needle=str(query).lower()[:256]
            entries=[e for e in entries if needle in ' '.join(str(e.get(k) or '') for k in ('title','summary','status','model','refs','iteration')).lower()]
        total=len(entries)
        if before:
            index=next((i for i,e in enumerate(entries) if e['id']==before),None)
            if index is None:
                raise KeyError('Workflow cursor is unavailable')
            entries=entries[:index]
        page=entries[-limit:];has_more=len(entries)>limit
        result=dict(schema=SCHEMA,items=[public(e) for e in page],total=total,has_more=has_more,
            next_before=page[0]['id'] if has_more else None,warnings=list(dict.fromkeys(warnings))[:20],
            note='Only saved activity. Missing timestamps and text are not reconstructed; pending wave records are not committed results.')
        result['version']=digest(result)
        return clean(result)

    def detail(self,ident):
        entries,warnings=self.entries()
        entry=next((e for e in entries if e['id']==ident),None)
        if entry is None:raise KeyError('Unknown workflow event')
        sections=[];detail_bytes=0;seen_sections=set()
        def add(label,value,fmt='json',note=None):
            nonlocal detail_bytes
            if value is None:return
            value=clean(value)
            section=dict(label=label,format=fmt,text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),**({'note':note} if note else {}))
            encoded=section['text'].encode('utf-8',errors='replace')
            section_key=(label,fmt,hashlib.sha256(encoded).hexdigest(),note)
            if section_key in seen_sections:return
            seen_sections.add(section_key)
            remaining=max(0,MAX_DETAIL_BYTES-detail_bytes)
            if len(encoded)>remaining:
                section['text']=encoded[:remaining].decode('utf-8',errors='ignore')
                section['note']=((note+' ') if note else '')+'Display truncated at the 16 MiB detail limit; saved evidence is unchanged.'
                warnings.append('Some detail text exceeds the 16 MiB inspector limit and is truncated.')
                section['truncated']=True
            detail_bytes+=len(section['text'].encode('utf-8',errors='replace'))
            sections.append(section)
        kind=entry['_kind']
        if kind=='call':
            saved=call_detail(self.path.parent,entry['_call'])
            for side,label in (('prompt','Prompt'),('response','Model response')):
                record=saved[side]
                add(label,record.get('text'),'text',record.get('note'))
                if not record.get('available'):add(label,None if not record.get('note') else record['note'],'text')
            add('Call metadata',{k:v for k,v in saved.items() if k not in ('prompt','response')})
        elif kind=='durable':
            saved=entry['_durable'];request=obj(saved['intent'].get('request'));receipt=saved['receipt'];value=obj(receipt.get('value'))
            add('Prompt',request.get('prompt'),'text');add('Model response',value.get('text'),'text')
            add('Evaluated source',request.get('source'),'code')
            parent=request.get('parent_source',request.get('parent_code'))
            source=request.get('source')
            if isinstance(parent,str) and isinstance(source,str):
                add('Code diff',''.join(difflib.unified_diff(parent.splitlines(True),source.splitlines(True),fromfile='saved parent',tofile='evaluated source',n=3)),'diff')
            add('Request',{k:v for k,v in request.items() if k not in ('prompt','source')})
            add('Receipt',{**receipt,'value':{k:v for k,v in value.items() if k!='text'}})
        elif kind=='runtime':add('Session status',entry['_runtime'])
        elif kind=='method':
            row=entry['_row'];data=obj(row.get('data'))
            try:
                if row['kind']=='artifact_registered':
                    artifact_kind=data.get('kind');artifact_id=data.get('id')
                    if artifact_kind=='proposal_receipt':
                        saved=self.methods.proposal_detail(artifact_id)
                        add('Prompt',saved.get('request'),'text' if isinstance(saved.get('request'),str) else 'json')
                        add('Model response',saved.get('response'),'text')
                        add('Proposal receipt',saved.get('receipt'));add('Research context',saved.get('context'));add('Call receipt',saved.get('call_receipt'))
                    else:add(human(artifact_kind),self.methods.artifact(artifact_kind,artifact_id,registered_artifacts(self.rows)))
                elif row['kind']=='method_registered':
                    saved=self.methods.method_detail(data.get('id'))
                    for name,source in obj(saved.get('files')).items():add(str(name),source,'code')
                    add('Diff',saved.get('diff'),'diff');add('Manifest',saved.get('manifest'))
                elif row['kind'] in ('lab_created','lab_revised'):
                    add('Lab revision',self.methods._object('revisions',data.get('revision_id')))
            except (OSError,ValueError,KeyError):warnings.append('Saved method detail is unavailable or failed verification.')
            add('Registry event',row)
        else:
            row=entry['_row']
            for key,label,fmt in (('prompt','Prompt','text'),('response','Model response','text'),('code','Code','code'),('child_code','Candidate source','code')):
                add(label,row.get(key),fmt)
            excerpt=obj(row.get('evidence')).get('change_excerpt')
            add('Recorded change',excerpt,'diff')
            if row.get('event')=='research_tool':
                try:
                    if row.get('receipt_id') and row.get('phase') in ('llm_result','invocation_result'):
                        add('Tool receipt',artifact_detail(self.path.parent,row['receipt_id'],self.rows))
                    if row.get('tool_id') and row.get('phase') in ('registered','published'):
                        saved=tool_detail(self.path.parent,row['tool_id'],self.rows)
                        for name,source in obj(saved.get('files')).items():add(str(name),source,'code')
                        for parent in saved.get('parents',[]):add('Tool diff',parent.get('diff'),'diff')
                except (OSError,ValueError,KeyError):warnings.append('Saved tool detail is unavailable or failed verification.')
            add('Recorded event',{k:v for k,v in row.items() if k not in ('prompt','response','code','child_code')})
        program=entry['refs'].get('program_id')
        if not program and entry['refs'].get('experiment_id'):
            experiment=entry['refs']['experiment_id']
            program=next((refs(r).get('program_id') for r in reversed(self.rows)
                if refs(r).get('experiment_id')==experiment and refs(r).get('program_id')),None)
        if entry['refs'].get('experiment_id') and self.methods is None:
            related=next((obj(r.get('evidence')).get('change_excerpt') for r in reversed(self.rows)
                if refs(r).get('experiment_id')==entry['refs']['experiment_id'] and isinstance(obj(r.get('evidence')).get('change_excerpt'),str)),None)
            if related is not None:add('Recorded change',related,'diff', 'Saved research excerpt; may omit portions of the full source diff.')
        if program and self.methods is None:
            try:
                saved=self.store.detail(self.run_id,program)
                add('Candidate source',saved.get('code'),'code');add('Code diff',saved.get('diff'),'diff')
            except (OSError,ValueError,KeyError):
                checkpoint,_,_=self.store._checkpoint(self.path,self.rows)
                sources=self.store._sources(checkpoint,self.rows);source=obj(sources.get(program));parent=obj(sources.get(source.get('parent_id')))
                add('Candidate source',source.get('code'),'code')
                if isinstance(source.get('code'),str) and isinstance(parent.get('code'),str):
                    add('Code diff',''.join(difflib.unified_diff(parent['code'].splitlines(True),source['code'].splitlines(True),
                        fromfile=str(source.get('parent_id')),tofile=program,n=3)),'diff')
        return clean(dict(schema=SCHEMA,item=public(entry),sections=sections,warnings=list(dict.fromkeys(warnings))[:20]))
