"""Work Flow uses inert saved records, never generation or evaluator execution."""
from datetime import datetime, timedelta, timezone
import hashlib
import http.client
import json
from pathlib import Path
import threading

import pytest

from arena.observers.sciel.data import RunStore
from arena.server import DashboardServer
from arena.observers.sciel.workflow import digest, pending_wave
from test_dashboard_llm_calls import trace_fixture, legacy_rows


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def journal(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    return path.read_bytes()


def store_for(path):
    store=RunStore([path]);store._scan()
    return store,next(iter(store._runs))


def test_exact_exchange_is_lazy_and_timestamps_duration_cost_preserved(tmp_path,monkeypatch):
    ident,_,prompt,response=trace_fixture(tmp_path)
    rows=legacy_rows();rows[2]['response_sha256']=hashlib.sha256(response.encode()).hexdigest()
    journal(tmp_path/'sciel_events.jsonl',rows)
    store,run=store_for(tmp_path)
    import arena.observers.sciel.llm_calls as calls
    original=calls._trace_text
    def no_read(*args):raise AssertionError('The feed must not read large transcript files')
    monkeypatch.setattr(calls,'_trace_text',no_read)
    page=store.workflow(run,limit=100)
    encoded=json.dumps(page)
    assert prompt not in encoded and response[:100] not in encoded
    reply=next(i for i in page['items'] if i['id']==f'call-{ident}-response')
    assert reply['actor']=='model' and reply['cost']==.12 and reply['duration_seconds']==2.5
    assert reply['timestamp']=='2026-09-19T00:00:02.500Z' and reply['timestamp_source']=='llm_trace'
    monkeypatch.setattr(calls,'_trace_text',original)
    detail=store.workflow_detail(run,reply['id'])
    assert next(s['text'] for s in detail['sections'] if s['label']=='Prompt')==prompt
    assert next(s['text'] for s in detail['sections'] if s['label']=='Model response')==response
    assert all(not key.startswith('_') for key in detail['item'])


def test_pagination_is_stable_across_appends_and_filters_search_metadata(tmp_path):
    rows=[dict(event='run_start',run_id='r',segment_id='s',event_seq=1)]
    for i in range(2,12):
        rows.append(dict(event='research_tool' if i%2 else 'decision',phase='invocation_result' if i%2 else None,
            event_seq=i,run_id='r',segment_id='s',timestamp=f'2026-09-19T00:00:{i:02}Z',tool_id='test-tool' if i%2 else None))
    path=tmp_path/'sciel_events.jsonl';journal(path,rows)
    store,run=store_for(tmp_path)
    first=store.workflow(run,limit=3)
    assert first['has_more'] and first['total']==11
    rows.append(dict(event='decision',event_seq=12,run_id='r',segment_id='s',timestamp='2026-09-19T00:00:12Z'))
    journal(path,rows)
    older=store.workflow(run,limit=3,before=first['next_before'])
    assert not ({i['id'] for i in first['items']} & {i['id'] for i in older['items']})
    assert older['items'][-1]['timestamp'] < first['items'][0]['timestamp']
    tools=store.workflow(run,actor='tool',query='test-tool')
    assert tools['total']==5 and all(i['actor']=='tool' for i in tools['items'])
    with pytest.raises(KeyError):store.workflow(run,before='untrusted-cursor')
    with pytest.raises(ValueError):store.workflow(run,limit=101)


def wave_fixture(tmp_path,kind='llm'):
    published=[dict(event='run_start',run_id='run',segment_id='segment',event_seq=1,timestamp='2026-09-19T00:00:00Z')]
    raw=journal(tmp_path/'sciel_events.jsonl',published)
    prefix=hashlib.sha256(raw).hexdigest()
    baseline=dict(provenance=dict(run_id='run',journal_anchor=dict(byte_offset=len(raw),prefix_sha256=prefix)))
    root=tmp_path/'.parallel';wave=root/'wave-1';name='a'*32
    sha=write(wave/(name+'.baseline.json'),baseline);write(tmp_path/'checkpoint.json',baseline)
    write(root/'current.json',dict(schema='sciel-wave-transaction/2',wave_id='1'))
    write(wave/'transaction.json',dict(schema='sciel-wave-transaction/2',wave_id='1',phase='active',
        baseline=name+'.baseline.json',baseline_sha256=sha,journal=name+'.journal.jsonl',base_journal_bytes=len(raw),base_journal_sha256=prefix))
    staged=[dict(event='research',phase='attempt',run_id='run',segment_id='segment',event_seq=2,
        experiment_id='r1',timestamp='2026-09-19T00:00:01Z')]
    journal(wave/(name+'.journal.jsonl'),staged)
    request=dict(prompt='saved pending prompt',model='fixture-model') if kind=='llm' else dict(source='x = 1',task_hash='task')
    key='fixture:1';call=wave/'calls'/hashlib.sha256(key.encode()).hexdigest()
    request_hash=digest(dict(kind=kind,request=request))
    write(call/'intent.json',dict(schema='sciel-parallel-call/1',key=key,kind=kind,request=request,request_sha256=request_hash))
    write(call/'dispatched.json',dict(request_sha256=request_hash,timestamp='2026-09-19T00:00:02Z'))
    value=dict(text='saved pending response',cost=.03) if kind=='llm' else dict(result=dict(score=.3,cases={}))
    payload=dict(status='returned',request_sha256=request_hash,value=value,elapsed_seconds=3,
        started_at='2026-09-19T00:00:02Z',completed_at='2026-09-19T00:00:05Z')
    write(call/'receipt.json',dict(sha256=digest(payload),payload=payload))
    return published,staged,wave,call


@pytest.mark.parametrize('kind',['llm','evaluation','tool_execution','tool_job_submit','tool_job_poll','tool_job_cancel'])
def test_pending_wave_receipts_are_visible_without_claiming_commit(tmp_path,kind):
    _,_,_,_=wave_fixture(tmp_path,kind)
    store,run=store_for(tmp_path);page=store.workflow(run,limit=100)
    receipt=next(i for i in page['items'] if i['kind']==kind+'_result')
    assert receipt['publication']=='pending' and receipt['commit_state']=='pending'
    assert receipt['timestamp']=='2026-09-19T00:00:05Z' and receipt['duration_seconds']==3
    assert receipt['cost']==(.03 if kind=='llm' else None)
    assert 'pending prompt' not in json.dumps(page)
    details=store.workflow_detail(run,receipt['id'])
    if kind=='llm':
        assert next(s['text'] for s in details['sections'] if s['label']=='Prompt')=='saved pending prompt'
        assert next(s['text'] for s in details['sections'] if s['label']=='Model response')=='saved pending response'


def test_unpublished_trace_is_visible_only_with_bound_staged_journal(tmp_path):
    published,_,wave,_=wave_fixture(tmp_path)
    ident,_,_,_=trace_fixture(tmp_path)
    store,run=store_for(tmp_path)
    assert any(i['id']==f'call-{ident}-response' and i['publication']=='pending' for i in store.workflow(run)['items'])
    # Tampering with the immutable baseline must remove both staged events and their traces.
    write(tmp_path/'checkpoint.json',{'provenance':{'run_id':'other'}})
    page=store.workflow(run)
    assert not any(i['id'].startswith('call-'+ident) for i in page['items'])
    assert page['warnings']==['Pending wave activity is unavailable or failed verification.']


def test_pending_receipt_checksum_symlink_and_prefix_tampering_fail_closed(tmp_path):
    published,_,wave,call=wave_fixture(tmp_path)
    receipt=json.loads((call/'receipt.json').read_text());receipt['payload']['value']['text']='tampered'
    write(call/'receipt.json',receipt)
    pending,calls,warnings=pending_wave(tmp_path,published)
    assert len(pending)==1 and not calls and any('failed verification' in w for w in warnings)
    # A symlinked staged transcript is never followed.
    staged=next(wave.glob('*.journal.jsonl'));outside=tmp_path/'outside';staged.rename(outside);staged.symlink_to(outside)
    assert not pending_wave(tmp_path,published)[0]
    staged.unlink();outside.rename(staged)
    with (tmp_path/'sciel_events.jsonl').open('ab') as f:f.write(b' ')  # append outside authenticated prefix is harmless
    assert pending_wave(tmp_path,published)[0]
    raw=(tmp_path/'sciel_events.jsonl').read_bytes();(tmp_path/'sciel_events.jsonl').write_bytes(b' '+raw[1:])
    assert not pending_wave(tmp_path,published)[0]


def test_cached_projection_avoids_rereading_unchanged_wave_and_invalidates_receipt(tmp_path,monkeypatch):
    _,_,_,call=wave_fixture(tmp_path)
    store,run=store_for(tmp_path);first=store.workflow(run)
    import arena.observers.sciel.workflow as workflow
    original=workflow.pending_wave
    def forbidden(*args):raise AssertionError('Unchanged base must be reused')
    monkeypatch.setattr(workflow,'pending_wave',forbidden)
    assert store.workflow(run)==first
    monkeypatch.setattr(workflow,'pending_wave',original)
    receipt=json.loads((call/'receipt.json').read_text());receipt['payload']['value']['cost']=.2;receipt['sha256']=digest(receipt['payload'])
    write(call/'receipt.json',receipt)
    changed=store.workflow(run)
    assert changed['version']!=first['version']
    assert any(i['cost']==.2 for i in changed['items'])


def test_missing_times_stay_unknown_and_terminal_runtime_does_not_leak_error_text(tmp_path):
    rows=[dict(event='run_start',run_id='r',segment_id='s',event_seq=1,config={'api_key':'secret'})]
    journal(tmp_path/'sciel_events.jsonl',rows)
    write(tmp_path/'runtime.json',dict(schema='sciel-runtime/1',run_id='r',segment_id='s',runtime_id='rt',
        status='failed',finished_at='2026-09-19T00:00:02Z',reason='sensitive provider body',error_type='ValueError'))
    store,run=store_for(tmp_path);page=store.workflow(run)
    assert page['items'][0]['timestamp'] is None
    assert page['items'][-1]['title']=='Session failed'
    assert 'sensitive provider body' not in json.dumps(page)
    detail=store.workflow_detail(run,page['items'][0]['id'])
    assert 'secret' not in json.dumps(detail) and '[redacted]' in json.dumps(detail)


def test_lazy_candidate_code_and_actual_parent_diff(tmp_path):
    rows=[dict(event='run_start',run_id='r',segment_id='s',event_seq=1),
        dict(event='iteration',child_id='p1',child_code='x = 1\n',event_seq=2),
        dict(event='iteration',child_id='p2',parent_id='p1',child_code='x = 2\n',child_score=.3,event_seq=3)]
    journal(tmp_path/'sciel_events.jsonl',rows)
    store,run=store_for(tmp_path);page=store.workflow(run)
    assert 'x = 2' not in json.dumps(page)
    entry=next(i for i in page['items'] if i['refs'].get('program_id')=='p2')
    detail=store.workflow_detail(run,entry['id'])
    diff=next(s['text'] for s in detail['sections'] if s['label']=='Code diff')
    assert '-x = 1' in diff and '+x = 2' in diff


def test_methods_registry_feed_and_lazy_source(tmp_path):
    from arena.observers.sciel.methods import digest as method_digest
    reg=tmp_path/'registry';(reg/'methods').mkdir(parents=True)
    tool=dict(schema='sciel-method/1',files={'tool.py':'print("fixture")\n'},manifest=dict(name='Fixture',parents=[]))
    tool_id=method_digest(tool);write(reg/'methods'/(tool_id+'.json'),tool)
    body=dict(schema='sciel-method-event/1',seq=1,prev='0'*64,at='2026-09-19T00:00:00Z',kind='method_registered',data={'id':tool_id})
    row=dict(body,id=method_digest(body));journal(reg/'journal.jsonl',[row])
    store,run=store_for(tmp_path);page=store.workflow(run)
    assert page['total']==1 and page['items'][0]['actor']=='tool'
    assert 'print(' not in json.dumps(page)
    detail=store.workflow_detail(run,page['items'][0]['id'])
    assert next(s['text'] for s in detail['sections'] if s['label']=='tool.py')==tool['files']['tool.py']


def test_http_routes_validate_ids_and_serve_only_registered_static_assets(tmp_path):
    journal(tmp_path/'sciel_events.jsonl',[dict(event='run_start',task='fixture')])
    server=DashboardServer(('127.0.0.1',0),[tmp_path]);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
        conn.request('GET','/api/runs');runs=json.loads(conn.getresponse().read());run=runs['runs'][0]['id']
        conn.request('GET',f'/api/runs/{run}/workflow');reply=conn.getresponse();page=json.loads(reply.read());assert reply.status==200
        conn.request('GET',f'/api/runs/{run}/workflow/'+page['items'][0]['id']);reply=conn.getresponse();assert reply.status==200;reply.read()
        conn.request('GET',f'/api/runs/{run}/workflow/..%2F..%2Fcheckpoint.json');reply=conn.getresponse();assert reply.status==404;reply.read()
        conn.request('GET',f'/api/runs/{run}/workflow?limit=100000');reply=conn.getresponse();assert reply.status==404;reply.read()
        conn.close()
    finally:server.shutdown();server.server_close();thread.join(timeout=2)


def test_skipped_conclusion_and_not_dispatched_auxiliary_are_not_model_results(tmp_path):
    rows=legacy_rows();rows[-1].update(dispatch_status='not_dispatched',cost=0,current_call_cost_unknown=False)
    rows.append(dict(event='research',phase='conclusion',experiment_id='r1',status='skipped',event_seq=7,
        run_id='run',segment_id='segment',timestamp='2026-09-19T00:00:09Z'))
    journal(tmp_path/'sciel_events.jsonl',rows)
    store,run=store_for(tmp_path);page=store.workflow(run)
    assert any(i['title']=='Conclusion skipped' for i in page['items'])
    declined=next(i for i in page['items'] if i['kind']=='request_not_dispatched')
    assert declined['actor']=='system' and declined['status']=='not_dispatched' and declined['cost']==0
    assert not any(i['title']=='Conclusion request failed' for i in page['items'])


def test_pending_evaluator_diff_uses_only_exact_saved_parent_and_source(tmp_path):
    _,_,_,call=wave_fixture(tmp_path,'evaluation')
    intent=json.loads((call/'intent.json').read_text());intent['request']['parent_code']='x = 0'
    binding=digest(dict(kind=intent['kind'],request=intent['request']));intent['request_sha256']=binding
    write(call/'intent.json',intent)
    dispatch=json.loads((call/'dispatched.json').read_text());dispatch['request_sha256']=binding;write(call/'dispatched.json',dispatch)
    receipt=json.loads((call/'receipt.json').read_text());receipt['payload']['request_sha256']=binding;receipt['sha256']=digest(receipt['payload']);write(call/'receipt.json',receipt)
    store,run=store_for(tmp_path);entry=next(i for i in store.workflow(run)['items'] if i['kind']=='evaluation_result')
    detail=store.workflow_detail(run,entry['id'])
    diff=next(s['text'] for s in detail['sections'] if s['label']=='Code diff')
    assert '-x = 0' in diff and '+x = 1' in diff


def test_detail_display_limit_is_explicit_and_never_modifies_saved_evidence(tmp_path,monkeypatch):
    import arena.observers.sciel.workflow as workflow
    source='saved-source\n'*100
    path=tmp_path/'sciel_events.jsonl'
    before=journal(path,[dict(event='iteration',child_id='p1',child_code=source)])
    monkeypatch.setattr(workflow,'MAX_DETAIL_BYTES',128)
    store,run=store_for(tmp_path);entry=store.workflow(run)['items'][0]
    detail=store.workflow_detail(run,entry['id'])
    assert sum(len(s['text'].encode()) for s in detail['sections'])<=128
    assert any(s.get('truncated') and 'saved evidence is unchanged' in s['note'] for s in detail['sections'])
    assert detail['warnings'] and path.read_bytes()==before


def test_methods_not_dispatched_receipts_are_system_events_with_zero_cost():
    from test_dashboard_methods import MethodsDashboardTests
    case=MethodsDashboardTests('runTest');case.setUp()
    try:
        context=case.artifact('proposal_context',{'lab_id':'lab'})
        call=case.artifact('call_receipt',dict(category='generation',status='failed',
            result=dict(status='failed',dispatch_status='not_dispatched'),actual=dict(dollars=0)))
        case.artifact('proposal_receipt',dict(lab_id='lab',context_id=context,call_receipt_id=call,
            draft=None,error='proposal_not_dispatched'))
        run=case.store.discover()[0]['id'];page=case.store.workflow(run)
        proposal=next(i for i in page['items'] if i['kind']=='proposal_receipt')
        receipt=next(i for i in page['items'] if i['kind']=='call_receipt')
        assert proposal['actor']==receipt['actor']=='system'
        assert proposal['status']==receipt['status']=='not_dispatched'
        assert proposal['cost']==receipt['cost']==0
        assert proposal['title']=='Proposal request not sent'
    finally:case.doCleanups()
