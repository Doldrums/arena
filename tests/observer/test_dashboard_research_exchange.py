"""Saved JSON only: queue and exact cross-island prompt provenance."""
from copy import deepcopy
import hashlib
import json
import pytest
from arena.observers.sciel.compat.models import content_hash, canonical_bytes
from arena.observers.sciel.compat.research_targets import input_binding
from arena.observers.sciel.research_tools import EVENT_SCHEMA, cell_detail, research_tools_view
from arena.observers.sciel.research_exchange import MARKER, SCHEMA


def write(root, folder, body):
    ident=content_hash(body); path=root/'research_tools'/folder/(ident+'.json')
    path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(canonical_bytes(body)); return ident


def event(phase,**values):
    return dict(event='research_tool',schema=EVENT_SCHEMA,phase=phase,**values)


def make_cell(root,island):
    cell=write(root,'cells/genesis',dict(schema='sciel-research-cell/1',question='Which check?',origin_island=island))
    revision=write(root,'cells/revisions',dict(schema='sciel-research-cell-revision/1',cell_id=cell,ordinal=1,previous_revision=None,evidence=[],tool_ids=[],phase='propose'))
    return cell,revision,event('cell_created',cell_id=cell,cell_revision_id=revision,island_id=island)


def fixture(root):
    origin,rev,created=make_cell(root,0); recipient,recipient_rev,other=make_cell(root,1)
    source='def solve(): return [1, 2]\n'; sha=hashlib.sha256(source.encode()).hexdigest();task={'task':'fixture','task_hash':'a'*64}
    selected=dict(kind='program',program_id='p1',source=source,source_sha256=sha,selection_score=1,
        measurement=dict(status='unavailable',record=None,aliases=[]),failure=None,
        saved_evaluation=dict(status='unavailable',reason='Not captured in fixture',reference=None,record=None))
    targets=dict(schema='sciel-research-targets/2',run_id='fixture',task_hash=task['task_hash'],frozen_at=dict(iteration=1,B_evals=1),
        ancestry_parent=dict(program_id='p1',source_sha256=sha),selected=selected,population_best=None)
    targets['sha256']=content_hash(targets)
    inputs=dict(task=task,research_targets=targets,parent_program_id='p1',parent_source=source,parent_score=None,ancestry_parent_id='p1')
    binding=input_binding(inputs)
    payload=dict(action_id='1'*64,cell_id=origin,cell_revision_id=rev,tool_id='b'*64,island_id=0,
        question='Does another stage help?',inputs=inputs,input_program_id='p1',target_binding=binding,
        result=dict(status='tool_error'),receipt=dict(dispatch_status='invoked',resources=dict(cpu_seconds=2.5),output={'observations':{'gain':0}},limits={'cpu_seconds':5}))
    receipt=write(root,'artifacts',dict(schema='sciel-research-tool-artifact/1',kind='invocation',payload=payload))
    head=write(root,'cells/revisions',dict(schema='sciel-research-cell-revision/1',cell_id=origin,ordinal=2,previous_revision=rev,
        evidence=[dict(kind='tool_invocation',id=receipt,tool_id='b'*64)],tool_ids=[],phase='research'))
    checkpoint={'research_tools':{'lifecycle':{'cells':{'schema':'sciel-research-cells/1','cells':{
        origin:dict(head_revision=head,active=False,affinities=[0]),recipient:dict(head_revision=recipient_rev,active=False,affinities=[1])}}}}}
    entry=dict(receipt_id=receipt,tool_id='b'*64,cell_id=origin,island_id=0,candidate_id='p1',target_source_sha256=sha,
        task=task,question=payload['question'],status='tool_error',resources=payload['receipt']['resources'],publication='unpublished',
        measurement={'output':{'observations':{'gain':0}},'error':None},decision=None)
    data=dict(schema=SCHEMA,total_checks=3,source_islands=[0,2],entries=[entry],omitted_count=2)
    prompt='Exact instructions\n'+MARKER+json.dumps(data)+'\nContinue.';action='2'*64
    proposal=write(root,'artifacts',dict(schema='sciel-research-tool-artifact/1',kind='proposal',payload=dict(
        action_id=action,attempt=0,cell_id=recipient,cell_revision_id=recipient_rev,target_binding=binding,
        prompt=prompt,response={'text':'Saved response'})))
    delivered=dict(receipt_id=receipt,source_cell_id=origin,source_island_id=0,source_candidate_id='p1',
        decision_proposal_id=None,detail_omitted=False,measurement_omitted=False,measurement_projection=None)
    rows=[created,other,event('invocation_result',cell_id=origin,cell_revision_id=rev,receipt_id=receipt,
        action_id=payload['action_id'],tool_id=payload['tool_id'],island_id=0,target_binding=binding),
        event('shared_observations_delivered',cell_id=recipient,action_id=action,attempt=0,island_id=1,
            recipient_candidate_id='p1',prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),evidence_schema=SCHEMA,
            total_checks=3,source_islands=[0,2],delivered=[delivered],omitted_count=2),
        event('llm_result',cell_id=recipient,action_id=action,attempt=0,island_id=1,receipt_id=proposal)]
    return recipient,checkpoint,rows


def test_exact_shared_prompt_keeps_negative_unpublished_checks_and_omissions(tmp_path):
    cell,checkpoint,rows=fixture(tmp_path);before=deepcopy(checkpoint)
    detail=cell_detail(tmp_path,cell,checkpoint,rows);delivery=detail['related']['shared_observations'][0]
    assert delivery['verified'] and delivery['omitted_count']==2
    assert delivery['entries'][0]['status']=='tool_error'
    assert delivery['entries'][0]['publication']=='unpublished'
    assert 'causal benefit are not established' in delivery['scope']
    assert detail['related']['invocations']==[]  # Shared evidence is not execution by the recipient.
    assert checkpoint==before


@pytest.mark.parametrize('damage',['prompt_hash','source_cell','omission','recipient','rollback','missing_model','tampered_source'])
def test_unproven_delivery_is_withheld(tmp_path,damage):
    cell,checkpoint,rows=fixture(tmp_path)
    if damage=='prompt_hash':rows[-2]['prompt_sha256']='f'*64
    elif damage=='source_cell':rows[-2]['delivered'][0]['source_cell_id']=cell
    elif damage=='omission':rows[-2]['omitted_count']=0
    elif damage=='recipient':rows[-2]['recipient_candidate_id']='p999'
    elif damage=='rollback':checkpoint['research_tools']['lifecycle']['cells']['cells'].pop(rows[0]['cell_id'])
    elif damage=='missing_model':rows.pop()
    else:
        path=tmp_path/'research_tools/artifacts'/(rows[2]['receipt_id']+'.json');path.write_text('{}')
    detail=cell_detail(tmp_path,cell,checkpoint,rows)
    assert detail['related']['shared_observations']==[]
    coverage=detail['related_coverage']['shared_observations']
    assert coverage['awaiting_model_receipt' if damage=='missing_model' else 'verification_failed']==1


def test_queue_is_checkpoint_metadata_not_running_or_scientific_conclusion(tmp_path):
    cell,checkpoint,rows=fixture(tmp_path)
    entry=dict(snapshot_artifact_id='d'*64,status='waiting',reason='no_independent_branch',queue_sequence=0,
        dispatch_count=2,last_action_id='e'*64,last_completed_iteration=7)
    checkpoint['research_tools']['continuations']=dict(schema='sciel-research-continuations/1',next_sequence=1,items={cell:entry})
    view=research_tools_view({},checkpoint,rows);queue=view['continuations']
    assert queue['summary']['waiting']==1 and queue['summary']['ready']==0
    assert queue['items'][0]['snapshot_verified'] is False
    assert cell_detail(tmp_path,cell,checkpoint,rows)['summary']['continuation']['reason']=='no_independent_branch'
    entry['status']='scheduled'  # Successful published checkpoint cannot contain active lease.
    assert research_tools_view({},checkpoint,rows)['continuations']['summary']['invalid']==1
    assert research_tools_view({}, {}, [])['continuations']['available'] is False


def test_saved_prompt_cannot_rewrite_receipt_measurement_even_with_matching_prompt_hash(tmp_path):
    cell,checkpoint,rows=fixture(tmp_path)
    path=tmp_path/'research_tools/artifacts'/(rows[-1]['receipt_id']+'.json');body=json.loads(path.read_text())
    prompt=body['payload']['prompt'];data=json.JSONDecoder().raw_decode(prompt.split(MARKER,1)[1])[0]
    data['entries'][0]['measurement']['output']['observations']['gain']=False  # Not the exact saved numeric zero.
    body['payload']['prompt']=MARKER+json.dumps(data)
    rows[-1]['receipt_id']=write(tmp_path,'artifacts',body)
    rows[-2]['prompt_sha256']=hashlib.sha256(body['payload']['prompt'].encode()).hexdigest()
    result=cell_detail(tmp_path,cell,checkpoint,rows)
    assert result['related']['shared_observations']==[]
    assert result['related_coverage']['shared_observations']['verification_failed']==1


def test_atomic_measurement_projection_preserves_values_counts_and_omission_state():
    from arena.observers.sciel.research_exchange import _measurement
    source={'receipt':{'output':{'observations':{'gain':0,'state':[1,2,3]}}},'result':{'error':None}}
    original={'output':{'observations':{'gain':0,'state':[1,2,3]}},'error':None}
    value=dict(schema='sciel-tool-result-projection/1',original_sha256=content_hash(original),
        fields=[{'path':'/output/observations/gain','value':0}],observations_state='partial',
        omitted_fields=2,omitted_observation_fields=1,omitted_paths=['/error'],omitted_paths_omitted=1)
    _measurement(value,source)
    value['fields'][0]['value']=.1
    with pytest.raises(ValueError):_measurement(value,source)
    _measurement({'omitted':True},source)


@pytest.mark.parametrize('reduced',[False,True])
def test_shared_terminal_interpretation_authenticates_bounded_excerpt_or_explicit_omission(tmp_path,reduced):
    from arena.observers.sciel.compat.decision_projection import project_decision
    cell,checkpoint,rows=fixture(tmp_path);origin=rows[0]['cell_id'];original=rows[2]['receipt_id']
    saved=dict(action_id='3'*64,attempt=0,cell_id=origin,cell_revision_id=rows[0]['cell_revision_id'],
        evidence_receipt_ids=[original],prompt='Finish decision',response={'text':json.dumps(dict(action='finish',
            conclusion='refuted',question='Does another stage help?',reason='No improvement. '*300,next_decision='Try another state.'))})
    decision_id=write(tmp_path,'artifacts',dict(schema='sciel-research-tool-artifact/1',kind='proposal',payload=saved))
    state=checkpoint['research_tools']['lifecycle']['cells']['cells'][origin]
    state['head_revision']=write(tmp_path,'cells/revisions',dict(schema='sciel-research-cell-revision/1',cell_id=origin,
        ordinal=3,previous_revision=state['head_revision'],evidence=[dict(kind='research_decision',id=decision_id)],tool_ids=[],phase='closed'))
    decision=project_decision(saved,decision_id,text_limits=(40,80,40))
    if reduced:decision={key:decision[key] for key in ('proposal_id','conclusion','scope')}|{'text_omitted':True}
    event_delivery=rows[-2];result=rows[-1]
    body=json.loads((tmp_path/'research_tools/artifacts'/(result['receipt_id']+'.json')).read_text())
    data=json.JSONDecoder().raw_decode(body['payload']['prompt'].split(MARKER,1)[1])[0]
    data['entries'][0]['decision']=decision;body['payload']['prompt']=MARKER+json.dumps(data)
    result['receipt_id']=write(tmp_path,'artifacts',body);event_delivery['prompt_sha256']=hashlib.sha256(body['payload']['prompt'].encode()).hexdigest()
    event_delivery['delivered'][0]['decision_proposal_id']=decision_id
    rows.append(event('llm_result',cell_id=origin,action_id='3'*64,attempt=0,receipt_id=decision_id))
    detail=cell_detail(tmp_path,cell,checkpoint,rows)
    assert detail['related']['shared_observations'][0]['entries'][0]['decision']==decision
