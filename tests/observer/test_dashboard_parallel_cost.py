"""Unpublished spend is bound to the current checkpoint, never guessed or replayed."""
import hashlib
import json
from pathlib import Path

import pytest

from arena.observers.sciel.data import RunStore
from arena.observers.sciel.parallel import runtime_parallel
from arena.observers.sciel.parallel_cost import WaveSpendMonitor


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return sha(path.read_bytes())


def wave(tmp_path):
    start = dict(event='run_start',run_id='run-a',segment_id='segment-a',event_seq=1,
        task='offline',config={'parallel_search':{'enabled':True}},counters={'cost_total':1.25})
    journal = tmp_path/'sciel_events.jsonl';journal.write_text(json.dumps(start)+'\n')
    directory = tmp_path/'.parallel/wave-0'
    anchor = dict(byte_offset=journal.stat().st_size,prefix_sha256=sha(journal.read_bytes()))
    baseline = dict(cost_total=1.25,iteration_no=0,provenance={'run_id':'run-a','journal_anchor':anchor})
    name = 'a'*32+'.baseline.json'
    baseline_hash = write(directory/name,baseline);write(tmp_path/'checkpoint.json',baseline)
    manifest = dict(schema='sciel-wave-transaction/2',wave_id='0',phase='active',baseline=name,
        baseline_sha256=baseline_hash,base_journal_bytes=anchor['byte_offset'],base_journal_sha256=anchor['prefix_sha256'])
    write(directory/'transaction.json',manifest)
    write(tmp_path/'.parallel/current.json',dict(schema=manifest['schema'],wave_id='0'))
    return start,directory,manifest


def call(directory, key, *, cost=.1, kind='llm', status='returned', dispatched=True, receipt=True, not_dispatched=False):
    path = directory/'calls'/sha(key.encode())
    request = {'prompt':'Private source and prompt text never projected'}
    request_hash = digest(dict(kind=kind,request=request))
    write(path/'intent.json',dict(schema='sciel-parallel-call/1',key=key,kind=kind,request=request,request_sha256=request_hash))
    if dispatched:write(path/'dispatched.json',dict(request_sha256=request_hash))
    payload = dict(status=status,request_sha256=request_hash)
    if status=='returned':payload['value']={'cost':cost,'text':'Response must stay private to the inspector'}
    else:payload.update(error={'category':'transport'},not_dispatched=not_dispatched)
    if receipt:write(path/'receipt.json',dict(payload=payload,sha256=digest(payload)))
    return path


def test_active_paused_wave_exposes_known_unknown_and_unsettled_without_mutating_counters(tmp_path):
    start,directory,_ = wave(tmp_path)
    call(directory,'known',cost=.15);call(directory,'unknown',cost=None)
    call(directory,'error',status='error');call(directory,'not-sent',status='error',not_dispatched=True)
    call(directory,'pending',receipt=False);call(directory,'intent-only',dispatched=False,receipt=False)
    call(directory,'eval',kind='evaluation',cost=500)
    before=(tmp_path/'checkpoint.json').read_bytes()
    view=WaveSpendMonitor().observe(tmp_path,start)
    assert view['available'] and view['known_cost']==.15 and view['known_spend']==1.4
    assert view['unknown_call_count']==2 and view['pending_call_count']==1
    assert view['status']=='partial' and view['included_in_stats'] is False
    assert 'Private' not in json.dumps(view) and 'Response' not in json.dumps(view)
    assert (tmp_path/'checkpoint.json').read_bytes()==before
    assert runtime_parallel(dict(schema='sciel-parallel-runtime/1',phase='paused'))['phase']=='paused'


def test_new_receipts_refresh_cached_monitor_without_recounting_prior_charges(tmp_path):
    start,directory,_=wave(tmp_path);monitor=WaveSpendMonitor()
    call(directory,'a',cost=.1);pending=call(directory,'b',receipt=False)
    assert monitor.observe(tmp_path,start)['known_cost']==.1
    call(directory,'b',cost=.2)
    view=monitor.observe(tmp_path,start)
    assert view['known_cost']==pytest.approx(.3) and view['pending_call_count']==0
    assert monitor.observe(tmp_path,start)==view
    assert pending.is_dir()


@pytest.mark.parametrize('change',['baseline','journal','run_id','intent','receipt','dispatch','pointer','symlink'])
def test_unbound_or_tampered_wave_is_unknown_not_zero(tmp_path,change):
    start,directory,manifest=wave(tmp_path);path=call(directory,'a')
    if change=='baseline':(tmp_path/'checkpoint.json').write_text('{}')
    elif change=='journal':(tmp_path/'sciel_events.jsonl').write_text('X'+(tmp_path/'sciel_events.jsonl').read_text()[1:])
    elif change=='run_id':start['run_id']='other'
    elif change=='intent':write(path/'intent.json',dict(schema='sciel-parallel-call/1',key='a',kind='llm',request={},request_sha256='wrong'))
    elif change=='receipt':write(path/'receipt.json',dict(payload={},sha256='wrong'))
    elif change=='dispatch':write(path/'dispatched.json',dict(request_sha256='wrong'))
    elif change=='pointer':write(tmp_path/'.parallel/current.json',dict(schema=manifest['schema'],wave_id='../outside'))
    else:
        data=(path/'receipt.json').read_bytes();(path/'receipt.json').unlink();outside=tmp_path/'outside.json';outside.write_bytes(data);(path/'receipt.json').symlink_to(outside)
    view=WaveSpendMonitor().observe(tmp_path,start)
    assert view['available'] is False and view['known_cost'] is None


def test_committed_and_already_published_prepared_wave_never_double_count(tmp_path):
    start,directory,manifest=wave(tmp_path);call(directory,'a')
    monitor=WaveSpendMonitor();manifest['phase']='prepared';manifest['candidate_sha256']='b'*64
    write(directory/'transaction.json',manifest)
    assert monitor.observe(tmp_path,start)['known_cost']==.1
    manifest['candidate_sha256']=write(tmp_path/'checkpoint.json',dict(cost_total=1.35))
    write(directory/'transaction.json',manifest)
    assert monitor.observe(tmp_path,start) is None
    manifest['phase']='committed';write(directory/'transaction.json',manifest)
    (directory/manifest['baseline']).unlink()
    assert monitor.observe(tmp_path,start) is None


def test_read_only_runtime_stream_refreshes_spend_without_new_journal_or_checkpoint(tmp_path):
    start,directory,_=wave(tmp_path);call(directory,'a',cost=.15)
    store=RunStore([tmp_path],timing_cache_dir=tmp_path/'timings')
    ident=store.discover()[0]['id'];version,kind,snapshot=store.stream_update(ident)
    assert kind=='snapshot' and snapshot['runtime']['uncommitted_cost']['known_spend']==1.4
    committed=snapshot['stats']['cost_total'];call(directory,'b',cost=.25)
    newversion,kind,update=store.stream_update(ident,version)
    assert newversion==version and kind=='runtime'
    assert update['runtime']['uncommitted_cost']['known_spend']==1.65
    assert store.snapshot(ident)['stats']['cost_total']==committed


def test_missing_wal_stays_absent_and_nonfinite_prices_are_unknown(tmp_path):
    assert WaveSpendMonitor().observe(tmp_path,{}) is None
    start,directory,_=wave(tmp_path)
    for i,cost in enumerate([None,-1,True,'0']):call(directory,str(i),cost=cost)
    view=WaveSpendMonitor().observe(tmp_path,start)
    assert view['unknown_call_count']==4 and view['known_cost']==0


TOOL_KINDS = ('tool_execution', 'tool_job_submit', 'tool_job_poll', 'tool_job_cancel')


@pytest.mark.parametrize('kind', TOOL_KINDS)
@pytest.mark.parametrize('state', ['returned', 'error', 'pending', 'intent_only'])
def test_tool_calls_preserve_provider_spend_and_unknown_outcomes(tmp_path, kind, state):
    start,directory,_ = wave(tmp_path)
    call(directory,'paid',cost=.15)
    call(directory,'unknown-response',cost=None)
    call(directory,'cancelled-provider',status='error',not_dispatched=False)
    call(directory,'pending-provider',receipt=False)
    call(directory,'tool',kind=kind,cost=99999,
         status='error' if state=='error' else 'returned',
         dispatched=state!='intent_only',receipt=state in ('returned','error'))
    before=(tmp_path/'checkpoint.json').read_bytes()
    view=WaveSpendMonitor().observe(tmp_path,start)
    assert view['available'] and view['known_cost']==.15 and view['known_spend']==1.4
    assert view['unknown_call_count']==2 and view['pending_call_count']==1
    assert view['status']=='partial' and view['included_in_stats'] is False
    assert (tmp_path/'checkpoint.json').read_bytes()==before


@pytest.mark.parametrize('kind', TOOL_KINDS)
@pytest.mark.parametrize('change', ['request', 'dispatch', 'receipt', 'returned_shape', 'error_shape'])
def test_tool_envelopes_remain_authenticated_before_excluding_local_cost(tmp_path, kind, change):
    start,directory,_ = wave(tmp_path)
    call(directory,'paid',cost=.15)
    path=call(directory,'tool',kind=kind,status='error' if change=='error_shape' else 'returned')
    if change=='request':
        intent=json.loads((path/'intent.json').read_text())
        intent['request']['tampered']=True
        write(path/'intent.json',intent)
    elif change=='dispatch':
        write(path/'dispatched.json',dict(request_sha256='wrong'))
    else:
        envelope=json.loads((path/'receipt.json').read_text())
        if change=='receipt':
            envelope['sha256']='wrong'
        else:
            envelope['payload']['error' if change=='error_shape' else 'value']=[]
            envelope['sha256']=digest(envelope['payload'])
        write(path/'receipt.json',envelope)
    view=WaveSpendMonitor().observe(tmp_path,start)
    assert view['available'] is False and view['known_cost'] is None


def test_unrecognized_call_kind_is_not_silently_treated_as_free(tmp_path):
    start,directory,_ = wave(tmp_path)
    call(directory,'unknown-kind',kind='future_paid_provider')
    view=WaveSpendMonitor().observe(tmp_path,start)
    assert view['available'] is False and view['known_cost'] is None
