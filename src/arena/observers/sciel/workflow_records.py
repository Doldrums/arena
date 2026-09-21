"""Public workflow record formatting, chronology and bounded display values."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import math

from .llm_calls import metadata as call_metadata

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
