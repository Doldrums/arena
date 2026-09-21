"""Read-only cells: configuration, lineage scoping, bounded authenticated detail."""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from arena.observers.sciel.compat.models import canonical_bytes, content_hash
from arena.observers.sciel.research_tools import EVENT_SCHEMA, cell_detail, research_tools_view


def event(phase, **values):
    return dict(event='research_tool', schema=EVENT_SCHEMA, phase=phase, **values)


def write(root, folder, value):
    ident = content_hash(value)
    path = root / 'research_tools' / folder / (ident + '.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))
    return ident


def cell(root, question='What can this check establish?'):
    ident = write(root, 'cells/genesis', dict(schema='sciel-research-cell/1', question=question, origin_island=0))
    revision = write(root, 'cells/revisions', dict(schema='sciel-research-cell-revision/1', cell_id=ident,
        ordinal=1, previous_revision=None, phase='propose', tool_ids=[], evidence=[]))
    return ident, revision, event('cell_created', cell_id=ident, cell_revision_id=revision, island_id=0, question=question)


@pytest.mark.parametrize('enabled,status', [(True,'enabled'), (False,'disabled'), (None,'not_recorded')])
def test_configuration_is_not_inferred_from_empty_activity(enabled, status):
    config = {} if enabled is None else {'research_tools': {'enabled':enabled}}
    view = research_tools_view({'config':config}, {}, [])
    assert view['configuration']['status'] == status
    assert view['configuration']['enabled'] is enabled
    assert view['cells'] == [] and view['summary']['actual_invocations'] == 0
    assert view['available'] is (enabled is True)


def test_configuration_checkpoint_fallback_and_explicit_disabled_with_history(tmp_path):
    ident, _, created = cell(tmp_path)
    checkpoint = {'config': {'research_tools': {'enabled':True}}}
    assert research_tools_view({},checkpoint,[])['configuration']['source'] == 'checkpoint'
    view = research_tools_view({'config':{'research_tools':{'enabled':False}}},checkpoint,[created])
    assert view['configuration']['status'] == 'disabled'
    assert view['configuration']['source'] == 'run_start'
    assert view['cells'][0]['id'] == ident  # History remains accessible, never rewritten.
    assert research_tools_view({'config':{'research_tools':{'enabled':0}}},{},[])['configuration']['status'] == 'not_recorded'


def test_recorded_current_contract_default_is_disabled_but_missing_config_or_unknown_archive_is_not():
    assert research_tools_view({'engine_contract':'espalier-3.21','config':{'population_size':24}}, {}, [])['configuration']['status'] == 'disabled'
    assert research_tools_view({'engine_contract':'espalier-3.22','config':{'population_size':24}}, {}, [])['configuration']['status'] == 'disabled'
    assert research_tools_view({'engine_contract':'espalier-3.23','config':{'population_size':24}}, {}, [])['configuration']['status'] == 'disabled'
    assert research_tools_view({'engine_contract':'espalier-3.24','config':{'population_size':24}}, {}, [])['configuration']['status'] == 'disabled'
    assert research_tools_view({'engine_contract':'espalier-3.25','config':{'population_size':24}}, {}, [])['configuration']['status'] == 'disabled'
    assert research_tools_view({'engine_contract':'espalier-3.26','config':{'population_size':24}}, {}, [])['configuration']['status'] == 'disabled'
    assert research_tools_view({'engine_contract':'espalier-3.27','config':{'population_size':24}}, {}, [])['configuration']['status'] == 'disabled'
    assert research_tools_view({'engine_contract':'espalier-3.28','config':{'population_size':24}}, {}, [])['configuration']['status'] == 'disabled'
    assert research_tools_view({'engine_contract':'espalier-3.35','config':{'population_size':24}}, {}, [])['configuration']['status'] == 'disabled'
    assert research_tools_view({'engine_contract':'espalier-3.36','config':{'population_size':24}}, {}, [])['configuration']['status'] == 'disabled'
    for start in ({'engine_contract':'espalier-3.21'}, {'engine_contract':'unknown','config':{}}, {'config':{}}):
        assert research_tools_view(start,{},[])['configuration']['status'] == 'not_recorded'
    assert research_tools_view({}, {'identity':{'engine_contract':'espalier-3.21'},'config':{}}, [])['configuration']['status'] == 'disabled'


def test_cell_scoping_uses_explicit_cell_or_unique_action_not_shared_tool(tmp_path):
    a, _, created_a = cell(tmp_path, 'A'); b, _, created_b = cell(tmp_path, 'B')
    rows = [created_a, created_b,
        event('cell_activated',cell_id=a,action_id='a'), event('cell_activated',cell_id=b,action_id='b'),
        event('llm_start',action_id='a',attempt=0), event('llm_start',action_id='b',attempt=0),
        event('context_prepared',cell_id=a,action_id='a',tool_ids=['f'*64]),
        event('child_link',cell_id=b,action_id='b',tool_ids=['f'*64],child_program_id='p9'),
        event('cell_activated',cell_id=a,action_id='ambiguous'),event('cell_activated',cell_id=b,action_id='ambiguous'),
        event('llm_start',action_id='ambiguous',attempt=0)]
    detail = cell_detail(tmp_path,a,{},rows)
    assert [row['action_id'] for row in detail['related']['llm_calls']] == ['a']
    assert detail['related']['child_links'] == []
    assert detail['summary']['counts']['prepared_contexts'] == 1
    assert detail['summary']['counts']['actual_invocations'] == 0
    assert detail['summary']['coverage']['model_use'] == 'unknown'


def test_cell_failed_invocations_match_summary_and_do_not_count_unknown_or_undispatched(tmp_path):
    ident, _, created = cell(tmp_path)
    outcomes = [dict(status='failed'),
        *[dict(status='ok',result_schema='sciel-tool-result/1',tool_result_status=status)
            for status in ('tool_error','invalid_output','host_failed')],
        dict(status='ok',result_schema='sciel-tool-result/1',tool_result_status='success'),
        dict(status='unknown',dispatch_status='unknown'),
        dict(status='failed',dispatch_status='not_dispatched')]
    rows = [created] + [event('invocation_result',cell_id=ident,invocation_id=str(index),receipt_id=f'{index:064x}',
        **{'dispatch_status':'invoked',**outcome}) for index,outcome in enumerate(outcomes)]
    # Duplicate results and a late start must not inflate or erase a failure.
    rows += [rows[1],event('invocation_started',cell_id=ident,invocation_id='0')]
    view = research_tools_view({}, {}, rows)
    assert view['cells'][0]['counts']['failed_invocations'] == view['summary']['failed_invocations'] == 4
    assert view['cells'][0]['counts']['actual_invocations'] == 5


def test_verified_proposal_and_forged_cross_cell_receipt_are_distinct(tmp_path):
    a, _, created_a = cell(tmp_path, 'A'); b, _, created_b = cell(tmp_path, 'B')
    receipt = write(tmp_path,'artifacts',dict(schema='sciel-research-tool-artifact/1',kind='proposal',
        payload=dict(action_id='a',attempt=0,prompt='EXACT PROMPT',response={'text':'saved','cost':0})))
    rows = [created_a,created_b,event('llm_result',cell_id=a,action_id='a',attempt=0,receipt_id=receipt,known_cost=0),
        event('llm_result',cell_id=b,action_id='b',attempt=0,receipt_id=receipt,known_cost=0)]
    good = cell_detail(tmp_path,a,{},rows)
    assert good['related']['llm_calls'][0]['verified'] is True
    assert good['related']['llm_calls'][0]['known_cost'] == 0
    bad = cell_detail(tmp_path,b,{},rows)
    assert bad['related']['llm_calls'] == []
    assert bad['related_coverage']['llm_calls']['verification_failed'] == 1
    # A valid file alone grants no visibility, and its body is never returned here.
    assert 'EXACT PROMPT' not in str(good)
    assert cell_detail(tmp_path,a,{},[created_a])['related']['llm_calls'] == []
    # Even a matching proposal action cannot be reassigned to another cell.
    conflicting = rows[:3] + [event('llm_result',cell_id=b,action_id='a',attempt=0,receipt_id=receipt)]
    assert cell_detail(tmp_path,b,{},conflicting)['related']['llm_calls'] == []


def test_detail_bounds_apply_after_cell_scoping_and_preserve_total_counts(tmp_path):
    a, _, created = cell(tmp_path)
    rows = [created] + [event('llm_start',cell_id=a,action_id=str(n),attempt=0) for n in range(260)]
    detail = cell_detail(tmp_path,a,{},rows)
    assert len(detail['related']['llm_calls']) == 50
    assert detail['related']['llm_calls'][0]['action_id'] == '210'
    assert detail['related_coverage']['llm_calls'] == dict(recorded=260,visible=50,omitted=210,verification_failed=0)
    assert detail['summary']['counts']['llm_calls'] == 260
    before = detail['summary']['detail_version']
    rows.append(event('episode_finished',cell_id=a,action_id='259',status='skip'))
    assert cell_detail(tmp_path,a,{},rows)['summary']['detail_version'] != before


def followup_fixture(root, *, status='evaluated'):
    source = Path(__file__).with_name('fixtures') / ('followup_' + status)
    shutil.copytree(source, root, dirs_exist_ok=True)
    view = json.loads((root / 'view.json').read_text())
    return view['cell_id'], view['checkpoint'], view['events'], view['followup']


@pytest.mark.parametrize('status', ['evaluated','eval_failed'])
def test_checkpoint_followup_requires_saved_outcome_and_invocation_not_preparation(tmp_path,status):
    ident, checkpoint, rows, followup = followup_fixture(tmp_path,status=status)
    original = deepcopy(checkpoint)
    detail = cell_detail(tmp_path,ident,checkpoint,rows)
    shown = detail['related']['followups']
    assert len(shown) == 1 and shown[0]['verified'] is True
    assert shown[0]['outcome_status'] == status
    assert shown[0]['model_use'] == shown[0]['causal_benefit'] == 'unknown'
    assert shown[0]['score'] == (0 if status == 'evaluated' else None)
    assert checkpoint == original
    assert cell_detail(tmp_path,ident,{},rows)['related']['followups'] == []
    # Removing the invocation lineage or replacing it with preparation is not proof.
    without_invocation = rows[:-1] + [event('context_prepared',cell_id=ident,receipt_ids=[rows[-1]['receipt_id']])]
    hidden = cell_detail(tmp_path,ident,checkpoint,without_invocation)
    assert hidden['related']['followups'] == []
    assert hidden['related_coverage']['followups']['verification_failed'] == 1
    # Resealing checkpoint metadata cannot change the immutable evidence artifact.
    checkpoint['research_tools']['followups']['records'][0]['iteration'] += 1
    state = checkpoint['research_tools']['followups']; modified = state['records'][0]
    modified['sha256'] = content_hash({k:v for k,v in modified.items() if k != 'sha256'})
    state['sha256'] = content_hash({k:v for k,v in state.items() if k != 'sha256'})
    assert cell_detail(tmp_path,ident,checkpoint,rows)['related']['followups'] == []


def test_followup_artifact_tamper_and_per_request_read_budget_fail_closed(tmp_path,monkeypatch):
    ident, checkpoint, rows, followup = followup_fixture(tmp_path)
    path = tmp_path/'research_tools/artifacts'/(followup['evidence_artifact_id']+'.json')
    path.write_text('{}')
    detail = cell_detail(tmp_path,ident,checkpoint,rows)
    assert detail['related']['followups'] == []
    assert detail['related_coverage']['followups']['verification_failed'] == 1
    monkeypatch.setattr('arena.observers.sciel.research_tools.DETAIL_BYTES',1)
    bounded = cell_detail(tmp_path,ident,checkpoint,rows)
    assert bounded['related']['versions'] == bounded['related']['invocations'] == []
    assert bounded['related_coverage']['versions']['verification_failed'] == 1


def test_checkpoint_only_cell_has_no_invented_activity_and_jobs_are_cell_scoped(tmp_path):
    a, rev_a, _ = cell(tmp_path,'A'); b, rev_b, _ = cell(tmp_path,'B')
    checkpoint = {'research_tools':{'lifecycle':{'cells':{'schema':'sciel-research-cells/1','cells':{
        a:dict(head_revision=rev_a,active=False,affinities=[0]),b:dict(head_revision=rev_b,active=False,affinities=[1])}}},
        'jobs':{'f'*64:dict(tool_id='e'*64,owner={'cell_id':b})}}}
    detail = cell_detail(tmp_path,a,checkpoint,[])
    assert detail['summary']['state_source'] == 'checkpoint'
    assert detail['summary']['activity_status'] == 'no_activity_recorded'
    assert detail['related']['jobs'] == []
    assert all(value == 0 for value in detail['summary']['counts'].values())


def test_current_research_state_preserves_decisions_zero_and_bounded_stage_evidence(tmp_path):
    ident, revision, created = cell(tmp_path, 'Generic scheduling question')
    state = dict(question='Does continuation improve the saved incumbent?', current_experiment='Continue exact state',
        decision_if_supported='Continue', decision_if_refuted='Try new initial states', next_decision='Compare results',
        status='open', scope='cell_cumulative', scientific_steps=45, known_llm_cost=0, unknown_llm_calls=1,
        resources=dict(cpu_seconds=0,wall_seconds=1,unknown_cpu_invocations=1), steps_omitted=4,
        steps=[dict(action='execute',status='success',proposal_id=f'{n:064x}',receipt_id='e'*64,
            requested_limits={'cpu_seconds':60,'wall_seconds':120},resources={'cpu_seconds':0},
            observed_at='2026-09-20T12:00:00Z') for n in range(40)])
    checkpoint = {'research_tools':{'lifecycle':{'research_state':{ident:state}}}}
    original = deepcopy(checkpoint)
    detail = cell_detail(tmp_path,ident,checkpoint,[created])
    assert detail['current_question'] == state['question']
    assert detail['question_scope'] == 'Recorded research plan'
    assert detail['genesis']['question'] == 'Generic scheduling question'
    shown = detail['research_state']
    assert shown['decision_if_refuted'] == state['decision_if_refuted']
    assert shown['known_llm_cost'] == shown['resources']['cpu_seconds'] == 0
    assert shown['resources']['unknown_cpu_invocations'] == shown['unknown_llm_calls'] == 1
    assert len(shown['steps']) == 32 and shown['steps_omitted'] == 12
    assert shown['steps'][0]['requested_limits']['cpu_seconds'] == 60
    assert checkpoint == original
    assert research_tools_view({},checkpoint,[created])['cells'][0]['current_question'] == state['question']


def test_research_state_journal_tail_cannot_replace_newer_checkpoint_with_older_plan(tmp_path):
    ident, _, created = cell(tmp_path)
    checkpoint = {'provenance':{'journal_anchor':{'segment_id':'segment','event_seq':10}},
        'research_tools':{'lifecycle':{'research_state':{ident:dict(question='Committed plan')}}}}
    prior = event('research_state',cell_id=ident,segment_id='segment',event_seq=9,research_state={'question':'Older plan'})
    newer = event('research_state',cell_id=ident,segment_id='segment',event_seq=11,research_state={'question':'New experiment'})
    assert cell_detail(tmp_path,ident,checkpoint,[created,prior])['current_question'] == 'Committed plan'
    assert cell_detail(tmp_path,ident,checkpoint,[created,prior,newer])['current_question'] == 'New experiment'
    del checkpoint['provenance']
    assert cell_detail(tmp_path,ident,checkpoint,[created,newer])['current_question'] == 'Committed plan'


def test_historical_question_and_compute_budget_come_from_verified_invocation(tmp_path):
    ident, revision, created = cell(tmp_path, 'Generic scheduling question')
    payload = dict(action_id='action',island_id=0,cell_id=ident,cell_revision_id=revision,tool_id='c'*64,
        question='Does local search improve the supplied state?',inputs={},receipt=dict(limits={'cpu_seconds':60,'wall_seconds':120},resources={'cpu_seconds':0,'wall_seconds':1}))
    receipt = write(tmp_path,'artifacts',dict(schema='sciel-research-tool-artifact/1',kind='invocation',payload=payload))
    result = event('invocation_result',action_id='action',cell_id=ident,tool_id='c'*64,invocation_id='d'*64,receipt_id=receipt)
    detail = cell_detail(tmp_path,ident,{},[created,result])
    assert detail['research_state'] is None
    assert detail['current_question'] == payload['question']
    assert detail['question_scope'] == 'Last verified experiment question'
    call = detail['related']['invocations'][0]
    assert call['resources']['cpu_seconds'] == 0
    assert call['requested_limits']['cpu_seconds'] == 60
    path = tmp_path/'research_tools/artifacts'/(receipt+'.json')
    path.write_text('{}')
    bad = cell_detail(tmp_path,ident,{},[created,result])
    assert bad['current_question'] is None
    assert bad['related_coverage']['invocations']['verification_failed'] == 1


def test_candidate_evaluation_links_exact_tool_output_and_journal_source(tmp_path):
    import hashlib
    from arena.observers.sciel.research_tools import artifact_detail
    ident, revision, created = cell(tmp_path)
    source = 'def candidate():\n    return 0\n'; digest = hashlib.sha256(source.encode()).hexdigest()
    invocation = dict(action_id='action',cell_id=ident,cell_revision_id=revision,tool_id='c'*64,
        inputs={},receipt=dict(invocation_id='d'*64,output=dict(status='success',observations={'candidate_source':source})))
    original = write(tmp_path,'artifacts',dict(schema='sciel-research-tool-artifact/1',kind='invocation',payload=invocation))
    provenance = dict(schema='sciel-research-candidate-submission/1',cell_id=ident,action_id='action',
        receipt_id=original,tool_id='c'*64,invocation_id='d'*64,candidate_source_sha256=digest)
    value = dict(schema='sciel-research-tool-artifact/1',kind='candidate_evaluation',payload=dict(source=source,
        provenance=provenance,evaluation=dict(source_sha256=digest,status='evaluated',score=0)))
    receipt = write(tmp_path,'artifacts',value)
    rows = [created,event('invocation_result',action_id='action',cell_id=ident,tool_id='c'*64,receipt_id=original),
        event('research_step',action='submit_candidate',action_id='action',cell_id=ident,
            source_sha256=digest,canonical_evaluation_id=receipt)]
    shown = artifact_detail(tmp_path,receipt,rows)
    assert shown['kind'] == 'candidate_evaluation' and shown['verified'] is True
    assert shown['payload']['evaluation']['score'] == 0
    # Neither an unbound candidate, a foreign cell, nor invented tool output can be presented.
    with pytest.raises(KeyError):
        artifact_detail(tmp_path,receipt,rows[:-1])
    forged = deepcopy(rows); forged[-1]['cell_id'] = 'f'*64
    with pytest.raises(ValueError):
        artifact_detail(tmp_path,receipt,forged)
    changed = deepcopy(value); changed['payload']['source'] += '# altered\n'
    changed_digest = hashlib.sha256(changed['payload']['source'].encode()).hexdigest()
    changed['payload']['provenance']['candidate_source_sha256'] = changed_digest
    changed['payload']['evaluation']['source_sha256'] = changed_digest
    altered = write(tmp_path,'artifacts',changed)
    forged[-1].update(cell_id=ident,source_sha256=changed_digest,canonical_evaluation_id=altered)
    with pytest.raises(ValueError,match='saved tool result'):
        artifact_detail(tmp_path,altered,forged)


def test_compact_state_events_retain_checkpoint_steps_and_add_only_committed_tail(tmp_path):
    ident, _, created = cell(tmp_path)
    first = dict(action='use',status='success',proposal_id='a'*64,receipt_id='b'*64)
    checkpoint = {'provenance':{'journal_anchor':{'segment_id':'s','event_seq':10}},
        'research_tools':{'lifecycle':{'research_state':{ident:dict(question='First',steps=[first])}}}}
    next_step = event('research_step',cell_id=ident,segment_id='s',event_seq=11,action='use',status='success',
        proposal_id='c'*64,receipt_id='d'*64,timestamp='2026-09-20T12:01:00Z')
    state = event('research_state',cell_id=ident,segment_id='s',event_seq=12,
        research_state=dict(question='Next',steps_omitted=0))
    not_committed = event('research_step',cell_id=ident,segment_id='s',event_seq=13,
        action='use',status='success',proposal_id='e'*64,receipt_id='f'*64)
    detail = cell_detail(tmp_path,ident,checkpoint,[created,next_step,state,not_committed])
    steps = detail['research_state']['steps']
    assert [row['proposal_id'] for row in steps] == ['a'*64,'c'*64]
    assert steps[-1]['timestamp'] == '2026-09-20T12:01:00Z'
    # Without any checkpoint, the latest saved state still wins over earlier states.
    first_state = event('research_state',cell_id=ident,research_state={'question':'Old'})
    assert cell_detail(tmp_path,ident,{},[created,first_state,next_step,state])['current_question'] == 'Next'


@pytest.mark.parametrize('terminal_phase',['research_step','episode_finished'])
def test_pending_model_decision_is_visible_without_committing_usage_or_outcomes(tmp_path,terminal_phase):
    ident, _, created = cell(tmp_path,'Generic scheduling question')
    committed = dict(question='Previous committed question',status='closed',known_llm_cost=.4,
        scope='cell_cumulative',resources={'cpu_seconds':2,'wall_seconds':3},steps=[])
    checkpoint = {'research_tools':{'lifecycle':{'research_state':{ident:committed}}}}
    decision = event('research_decision',cell_id=ident,action_id='a1',proposal_id='d'*64,
        action='create',status='planned',question='Will an extended continuation improve this saved state?',
        experiment='Continue the saved state for 60 CPU seconds.',decision_if_supported='Continue',
        decision_if_refuted='Try new starts',next_decision='Inspect improvement per CPU second.',
        requested_limits={'cpu_seconds':60,'wall_seconds':90})
    rows=[created,decision]
    pending=cell_detail(tmp_path,ident,checkpoint,rows)
    assert pending['current_question']==decision['question']
    assert pending['question_scope']=='Pending model decision; uncommitted'
    assert pending['active_decision']['committed'] is False
    assert pending['research_state']['question']==committed['question']
    assert pending['research_state']['resources']==committed['resources']
    assert pending['research_state']['known_llm_cost']==.4
    assert pending['summary']['counts']['actual_invocations']==0
    assert pending['related']['invocations']==[]
    rows.append(event('invocation_started',cell_id=ident,action_id='a1',invocation_id='i1'))
    assert cell_detail(tmp_path,ident,checkpoint,rows)['active_decision']['status']=='awaiting_execution_receipt'
    # A sibling episode/result cannot dismiss this decision.
    rows.append(event('research_step',cell_id=ident,action_id='other',proposal_id='d'*64))
    assert cell_detail(tmp_path,ident,checkpoint,rows)['active_decision'] is not None
    rows.append(event(terminal_phase,cell_id=ident,action_id='a1',proposal_id='d'*64))
    settled=cell_detail(tmp_path,ident,checkpoint,rows)
    assert settled['active_decision'] is None
    assert settled['current_question']==committed['question']
