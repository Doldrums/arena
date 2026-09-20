"""Read-only receipt fixtures: no Engine, model, tool or candidate execution."""
import hashlib
import json

import pytest

from arena.observers.sciel.effort import EffortMonitor, effort_basis
from arena.observers.sciel.parallel_cost import _digest


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def fixture(tmp_path, *, score=-2, unknown=False):
    source='def result(): return -2\n'
    start=dict(event='run_start',run_id='run-1',segment_id='s1',event_seq=1,
        timestamp='2026-09-20T10:00:00+00:00',task='test',config={'parallel_search':{'enabled':True}})
    rows=[start];directory=tmp_path/'.parallel/wave-0'
    for index,(key,kind,time,cost) in enumerate([
        ('G:0','llm','01',.2),('G:1','evaluation','03',None),
        ('C:0','llm','05',None if unknown else .3)],2):
        request={'model':'example/a','prompt':'secret prompt'} if kind=='llm' else {'source':source,'task_hash':'task-hash'}
        digest=_digest(dict(kind=kind,request=request));path=directory/'calls'/hashlib.sha256(key.encode()).hexdigest()
        write(path/'intent.json',dict(schema='sciel-parallel-call/1',key=key,kind=kind,request=request,request_sha256=digest))
        write(path/'dispatched.json',dict(request_sha256=digest,timestamp='2026-09-20T10:00:00+00:00'))
        value=dict(cost=cost,cost_provenance={'source':'provider_reported'}) if kind=='llm' else dict(result={'ok':True,'score':score,'cases':{'native':score,'validity':1}})
        payload=dict(request_sha256=digest,status='returned',completed_at='2026-09-20T10:00:'+time+'+00:00',value=value)
        write(path/'receipt.json',dict(payload=payload,sha256=_digest(payload)))
        rows.append(dict(event='decision',policy='parallel_search',action='io_receipt',wave=0,job_call=key,
            kind=kind,request_sha256=digest,receipt_sha256=_digest(payload),completed_at=payload['completed_at'],
            status='returned',run_id='run-1',segment_id='s1',event_seq=index))
    rows.append(dict(event='iteration',run_id='run-1',segment_id='s1',event_seq=5,iteration_no=1,child_id='p2',child_score=score,
        timestamp='2026-09-20T10:00:04+00:00',meta={'evaluations':[{'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
            'evaluation_id':'evaluation:run-1:wave:0:G:1','score':score,'ok':True}]}))
    rows.append(dict(event='decision',policy='parallel_search',action='wave_complete',wave=0,
        run_id='run-1',segment_id='s1',event_seq=6))
    journal=tmp_path/'sciel_events.jsonl';journal.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    raw=journal.read_bytes()
    write(directory/'transaction.json',dict(schema='sciel-wave-transaction/2',wave_id='0',phase='committed',
        journal_bytes=len(raw),journal_sha256=hashlib.sha256(raw).hexdigest()))
    write(tmp_path/'.parallel/current.json',dict(schema='sciel-wave-transaction/2',wave_id='0'))
    sources={'p2':{'code':source,'cases':{'native':score,'validity':1}}}
    basis=effort_basis(rows,sources,'p2',score,'task-hash',1)
    return start,rows,basis,directory


def test_physical_effort_at_best_is_not_generation_cost_or_final_total(tmp_path):
    start,rows,basis,_=fixture(tmp_path)
    before={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    view=EffortMonitor().observe(tmp_path,start,rows,basis)
    assert view['total']['reported_usd']==.5
    assert view['total']['physical_llm_calls']==2
    best=view['to_best']
    assert best['reported_usd']==.2 and best['physical_llm_calls']==1
    assert best['pending_llm_calls']==1 and best['status']=='partial'
    assert best['evaluator_cascades']==1 and best['ordinary_iterations']==0 and best['target_iteration']==1
    assert best['wall_seconds']==3 and best['cpu_seconds'] is None and best['cpu_usd'] is None
    assert best['model_count']==1 and best['models']==['example/a']
    assert 'secret prompt' not in json.dumps(view) and 'def result' not in json.dumps(view)
    assert before=={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


@pytest.mark.parametrize('mutation',['source','cases','evaluation_id','task'])
def test_best_requires_exact_source_cases_task_and_receipt_identity(tmp_path,mutation):
    start,rows,basis,_=fixture(tmp_path)
    if mutation=='source':basis['source_sha256']='0'*64
    if mutation=='cases':basis['cases']={'native':-2,'validity':0}
    if mutation=='evaluation_id':basis['evaluation_ids']=['unrelated']
    if mutation=='task':basis['task_hash']='unrelated'
    assert EffortMonitor().observe(tmp_path,start,rows,basis)['to_best'] is None


@pytest.mark.parametrize('mutation',['missing_directory','tamper_receipt','foreign_segment','appended_owner','symlink'])
def test_damaged_or_unbound_history_is_not_reported_as_complete(tmp_path,mutation):
    start,rows,basis,directory=fixture(tmp_path)
    call=directory/'calls'/hashlib.sha256(b'G:0').hexdigest()
    if mutation=='missing_directory':
        for p in call.iterdir():p.unlink()
        call.rmdir()
    elif mutation=='tamper_receipt':write(call/'receipt.json',{'payload':{},'sha256':'bad'})
    elif mutation=='foreign_segment':rows[1]['segment_id']='unrelated'
    elif mutation=='appended_owner':rows.append(dict(rows[1],event_seq=7))
    else:
        raw=(call/'receipt.json').read_bytes();(call/'receipt.json').unlink()
        (tmp_path/'elsewhere').write_bytes(raw);(call/'receipt.json').symlink_to(tmp_path/'elsewhere')
    view=EffortMonitor().observe(tmp_path,start,rows,basis)
    assert view['total']['history_complete'] is False and view['total']['status']=='partial'
    assert view['total']['reported_usd']==.3


def test_unknown_charge_is_not_zero_and_cached_receipts_revalidate(tmp_path):
    start,rows,basis,directory=fixture(tmp_path,unknown=True);monitor=EffortMonitor()
    first=monitor.observe(tmp_path,start,rows,basis)
    assert first['total']['reported_usd']==.2 and first['total']['unknown_cost_calls']==1
    path=directory/'calls'/hashlib.sha256(b'G:0').hexdigest()/'receipt.json'
    write(path,{'payload':{},'sha256':'bad'})
    updated=monitor.observe(tmp_path,start,rows,basis)
    assert updated['total']['reported_usd'] is None and updated['total']['history_complete'] is False


def test_missing_legacy_history_remains_unknown(tmp_path):
    view=EffortMonitor().observe(tmp_path,{},[],{})
    assert view['total'] is None and view['to_best'] is None


def test_live_uncommitted_call_refreshes_exact_cost_and_models_without_changing_history(tmp_path):
    start,rows,basis,_=fixture(tmp_path);monitor=EffortMonitor()
    raw=(tmp_path/'sciel_events.jsonl').read_bytes();directory=tmp_path/'.parallel/wave-1'
    anchor={'byte_offset':len(raw),'prefix_sha256':hashlib.sha256(raw).hexdigest()}
    checkpoint={'cost_total':.5,'iteration_no':1,'provenance':{'run_id':'run-1','journal_anchor':anchor}}
    name='a'*32+'.baseline.json';write(directory/name,checkpoint);write(tmp_path/'checkpoint.json',checkpoint)
    manifest=dict(schema='sciel-wave-transaction/2',phase='active',wave_id='1',baseline=name,
        baseline_sha256=hashlib.sha256((directory/name).read_bytes()).hexdigest(),base_journal_bytes=len(raw),base_journal_sha256=anchor['prefix_sha256'])
    write(directory/'transaction.json',manifest);write(tmp_path/'.parallel/current.json',{'schema':manifest['schema'],'wave_id':'1'})
    key='G:0';call=directory/'calls'/hashlib.sha256(key.encode()).hexdigest();request={'model':'example/b','prompt':'Private'}
    digest=_digest({'kind':'llm','request':request})
    write(call/'intent.json',{'schema':'sciel-parallel-call/1','kind':'llm','key':key,'request':request,'request_sha256':digest})
    write(call/'dispatched.json',{'timestamp':'2026-09-20T10:00:06+00:00','request_sha256':digest})
    first=monitor.observe(tmp_path,start,rows,basis)
    assert first['total']['reported_usd']==.5 and first['total']['pending_llm_calls']==1
    assert first['total']['model_count']==2
    payload={'status':'returned','completed_at':'2026-09-20T10:00:07+00:00','request_sha256':digest,
        'value':{'cost':.9,'model':'example/b','cost_provenance':{'source':'provider_reported'}}}
    write(call/'receipt.json',{'payload':payload,'sha256':_digest(payload)})
    second=monitor.observe(tmp_path,start,rows,basis)
    assert second['total']['reported_usd']==1.4 and second['total']['pending_llm_calls']==0
    assert second['total']['physical_llm_calls']==3 and second['to_best']==first['to_best']
    assert (tmp_path/'sciel_events.jsonl').read_bytes()==raw
    assert json.loads((tmp_path/'checkpoint.json').read_bytes())==checkpoint
