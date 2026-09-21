"""Actual cooperative transaction journals are visible before scientific commit.

The real RunLog, WaveTransaction and CellRegistry write the fixture. No provider,
evaluator, generated program or tool execution is invoked.
"""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import fixture_pending as parallel_store
from fixture_pending import CellRegistry
from fixture_pending import RunLog
from arena.observers.sciel.data import RunStore
from arena.observers.sciel.research_tools import EVENT_SCHEMA
from test_dashboard_research_cells_detail import write


@pytest.fixture
def rig(tmp_path,monkeypatch):
    log=RunLog(str(tmp_path/'sciel_events.jsonl'))
    config={'research_tools':{'enabled':True},'parallel_search':{'enabled':True}}
    log.run_start(config=config,engine_contract='espalier-3.26')
    engine=SimpleNamespace(run_dir=str(tmp_path),log=log,cells=CellRegistry(tmp_path),config=config)
    def save(engine,milestone,*,path=None):
        target=Path(path or tmp_path/'checkpoint.json')
        state=dict(config=config,research_tools={'lifecycle':{'cells':engine.cells.state()}},
            provenance={'run_id':engine.log.run_id,'journal_anchor':engine.log.anchor()})
        parallel_store._write_json(target,state)
        engine._saved_checkpoint={'checkpoint_sha256':parallel_store._digest(target),'provenance':deepcopy(state['provenance'])}
        return str(target)
    monkeypatch.setattr(parallel_store.checkpoint,'save',save)
    save(engine,'initial')
    store=RunStore([tmp_path]);store._scan();run=next(iter(store._runs))
    yield engine,store,run
    tx=getattr(engine,'_parallel_transaction',None)
    if tx:tx.restore_log()
    engine.log.close()


def emit(engine,phase,**fields):
    engine.log.research_tool(schema=EVENT_SCHEMA,phase=phase,**fields)


def create_cell(engine,question='Investigate the observed search limit.'):
    cell=engine.cells.ensure_cell(0,question,{'kind':'proactive','attempt':1})
    cell=engine.cells.revise(cell['id'],phase='propose')
    emit(engine,'cell_created',cell_id=cell['id'],cell_revision_id=cell['head_revision'],
         question=cell['question'],origin_island_id=0,island_id=0)
    return cell


def decide(engine,cell,question='Does another saved search stage improve the result?'):
    action='a'*64
    payload={'action_id':action,'attempt':0,'prompt':'Exact saved question input.',
             'response':{'text':'Exact saved proposal.','cost':.02}}
    proposal=write(Path(engine.run_dir),'artifacts',dict(schema='sciel-research-tool-artifact/1',kind='proposal',payload=payload))
    emit(engine,'llm_result',cell_id=cell['id'],action_id=action,attempt=0,receipt_id=proposal,known_cost=.02)
    emit(engine,'research_decision',cell_id=cell['id'],cell_revision_id=cell['head_revision'],action_id=action,
         proposal_id=proposal,question=question,action='invoke_tool',experiment='Continue the exact saved state for another stage.',
         decision_if_supported='Continue the incumbent.',decision_if_refuted='Try another start.',
         next_decision='Compare measured gains under the same budget.',requested_limits={'cpu_seconds':120,'wall_seconds':180})
    return proposal,action


def test_new_cell_and_real_pending_proposal_visible_before_commit_without_scientific_credit(rig):
    engine,store,run=rig
    tx=parallel_store.begin(engine,0)
    baseline=store.snapshot(run)
    main=Path(engine.run_dir)/'sciel_events.jsonl';original=main.read_bytes()
    cell=create_cell(engine);proposal,action=decide(engine,cell)
    emit(engine,'invocation_started',cell_id=cell['id'],action_id=action,invocation_id='queued')
    version,kind,live=store.stream_update(run,baseline['content_version'])
    assert kind=='runtime' and version==baseline['content_version'] and main.read_bytes()==original
    overlay=live['research_pending_cells']['cells'][0]
    assert overlay['id']==cell['id'] and overlay['committed'] is False
    assert overlay['active_decision']['status']=='awaiting_execution_receipt'
    assert overlay['active_decision']['requested_limits']['cpu_seconds']==120
    snapshot=store.snapshot(run)
    assert snapshot['stats']==baseline['stats']
    assert snapshot['research_tools']['summary']==baseline['research_tools']['summary']
    assert snapshot['research_tools']['cells']==[]
    body=store.research_cell(run,cell['id'])
    assert body['publication']=='pending' and body['research_state'] is None
    assert body['revision_history']==[] and body['related']=={}
    assert body['current_question'].startswith('Does another saved')
    proposal_body=store.research_tool_artifact(run,proposal)
    assert proposal_body['publication']=='pending' and proposal_body['kind']=='proposal'
    assert proposal_body['payload']['prompt']=='Exact saved question input.'
    # A result/finish does not make the first cell disappear during a long wave.
    emit(engine,'research_step',cell_id=cell['id'],action_id=action,proposal_id=proposal,
         known_cost=999,resources={'cpu_seconds':999},status='ok')
    emit(engine,'episode_finished',cell_id=cell['id'],action_id=action,known_cost=999)
    waiting=store.snapshot(run)['research_tools']['pending_cells']['cells'][0]
    assert waiting['active_decision'] is None
    assert waiting['pending_decision']['status']=='awaiting_wave_commit'
    # Check measured fields directly; authenticated hashes may contain "999".
    for projection in (waiting, waiting['pending_decision']):
        assert {'known_cost', 'resources'}.isdisjoint(projection)
    assert waiting['pending_decision']['requested_limits']=={'cpu_seconds':120,'wall_seconds':180}
    tx.commit()
    committed=store.snapshot(run)['research_tools']
    assert committed['pending_cells']['cells']==[] and len(committed['cells'])==1
    assert 'publication' not in store.research_cell(run,cell['id'])


def test_existing_cell_pending_question_does_not_replace_committed_history_and_cached_updates(rig,monkeypatch):
    engine,store,run=rig
    cell=create_cell(engine)
    tx=parallel_store.begin(engine,0)
    baseline=store.snapshot(run)['research_tools']['cells'][0]
    decide(engine,cell)
    snapshot=store.snapshot(run)
    assert snapshot['research_tools']['cells'][0]==baseline
    body=store.research_cell(run,cell['id'])
    assert len(body['revision_history'])==1 and body['publication']=='pending'
    assert body['summary']['counts']==baseline['counts']
    import arena.observers.sciel.research_pending as pending
    def forbidden(*args,**kwargs):raise AssertionError('Unchanged pending journal should reuse its bounded projection')
    monkeypatch.setattr(pending,'pending_wave',forbidden)
    assert store.snapshot(run)['research_tools']['pending_cells']==snapshot['research_tools']['pending_cells']
    tx.restore_log()


@pytest.mark.parametrize('tamper',['checkpoint_owner','prefix','delta_owner','pointer','symlink','genesis'])
def test_unbound_or_rolled_back_pending_cells_fail_closed(rig,tamper):
    engine,store,run=rig
    tx=parallel_store.begin(engine,0);cell=create_cell(engine);decide(engine,cell)
    assert len(store.snapshot(run)['research_tools']['pending_cells']['cells'])==1
    root=Path(engine.run_dir)
    if tamper=='checkpoint_owner':
        (root/'checkpoint.json').write_text(json.dumps({'provenance':{'run_id':'another-run'}}))
    elif tamper=='prefix':
        path=root/'sciel_events.jsonl';raw=path.read_bytes();path.write_bytes(b' '+raw[1:])
    elif tamper=='delta_owner':
        path=Path(engine.log.path);rows=[json.loads(line) for line in path.read_text().splitlines()]
        rows[-1]['run_id']='another-run';path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    elif tamper=='pointer':
        (root/'.parallel/current.json').unlink()
    elif tamper=='symlink':
        path=Path(engine.log.path);copy=root/'other';copy.write_bytes(path.read_bytes());path.unlink();path.symlink_to(copy)
    else:
        (root/'research_tools/cells/genesis'/(cell['id']+'.json')).write_text('{}')
    assert store.snapshot(run)['research_tools']['pending_cells']['cells']==[]
    with pytest.raises(KeyError):store.research_cell(run,cell['id'])


def test_pointer_change_during_observation_does_not_publish_mixed_pending_state(rig,monkeypatch):
    engine,store,run=rig
    parallel_store.begin(engine,0);cell=create_cell(engine);decide(engine,cell)
    import arena.observers.sciel.research_pending as pending
    original=pending.pending_wave
    def change(*args,**kwargs):
        result=original(*args,**kwargs)
        (Path(engine.run_dir)/'.parallel/current.json').unlink()
        return result
    monkeypatch.setattr(pending,'pending_wave',change)
    result=store.snapshot(run)['research_tools']['pending_cells']
    assert result['cells']==[] and any('changed during observation' in w for w in result['warnings'])


def test_newly_discovered_artifact_cannot_change_between_authentication_and_cache(rig,monkeypatch):
    engine,store,run=rig
    parallel_store.begin(engine,0);cell=create_cell(engine);decide(engine,cell)
    import arena.observers.sciel.research_pending as pending
    original=pending._DetailReader.__call__
    def mutate(reader,folder,ident,maximum):
        result=original(reader,folder,ident,maximum)
        if folder=='cells/genesis':
            (Path(engine.run_dir)/'research_tools/cells/genesis'/(ident+'.json')).write_text('{}')
        return result
    monkeypatch.setattr(pending._DetailReader,'__call__',mutate)
    first=store.snapshot(run)['research_tools']['pending_cells']
    assert first['cells']==[] and any('changed during observation' in w for w in first['warnings'])
    assert store.snapshot(run)['research_tools']['pending_cells']['cells']==[]


def test_old_committed_cell_outside_summary_window_still_opens_and_gets_pending_plan(rig):
    engine,store,run=rig
    first=create_cell(engine,'First durable question.')
    for index in range(200):
        create_cell(engine,f'Another durable question {index}.')
    snapshot=store.snapshot(run)
    assert snapshot['research_tools']['summary']['cells']==201
    assert first['id'] not in {row['id'] for row in snapshot['research_tools']['cells']}
    original=store.research_cell(run,first['id'])
    assert original['verified'] and len(original['revision_history'])==1
    parallel_store.begin(engine,0)
    decide(engine,first,'Test a new stage on this older branch.')
    current=store.snapshot(run)['research_tools']
    assert current['pending_cells']['cells'][0]['id']==first['id']
    assert current['pending_cells']['cells'][0]['committed'] is True
    body=store.research_cell(run,first['id'])
    assert body['revision_history']==original['revision_history']
    assert body['current_question']=='Test a new stage on this older branch.'


def test_pending_continuation_is_lease_metadata_and_disappears_on_rollback(rig):
    engine,store,run=rig
    parallel_store.begin(engine,0);cell=create_cell(engine)
    emit(engine,'continuation_scheduled',cell_id=cell['id'],action_id='a'*64,snapshot_artifact_id='b'*64,
        status='scheduled',reason='research_open',queue_sequence=2,dispatch_count=1)
    snapshot=store.snapshot(run)
    overlay=snapshot['research_tools']['pending_cells']['cells'][0]
    assert overlay['pending_continuation']['status']=='scheduled'
    assert overlay['pending_continuation']['committed'] is False
    assert snapshot['research_tools']['continuations']['available'] is False
    assert store.research_cell(run,cell['id'])['pending_continuation']==overlay['pending_continuation']
    (Path(engine.run_dir)/'.parallel/current.json').unlink()
    assert store.snapshot(run)['research_tools']['pending_cells']['cells']==[]
