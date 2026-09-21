"""Bounded record projections shared by read-only research-tool views."""
from __future__ import annotations

import json
import math
import re

EVENT_SCHEMA = 'sciel-research-tool-event/1'
HASH = re.compile(r'[0-9a-f]{64}\Z')
LIMIT = 200
DETAIL_LIMIT = 50
DETAIL_BYTES = 8 * 1024 * 1024


def _obj(value):
    return value if isinstance(value, dict) else {}


def _text(value, limit=512):
    return value[:limit] if isinstance(value, str) else None


def _island(value):
    return value if type(value) in (str, int) else None


def _ids(values):
    return list(dict.fromkeys(v for v in values if isinstance(v, str) and HASH.fullmatch(v))) if isinstance(values, list) else []


def _events(rows):
    return [row for row in rows if row.get('event') == 'research_tool' and row.get('schema') == EVENT_SCHEMA]


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()


def _job_number(value):
    return value if type(value) in (int,float) and math.isfinite(value) and value >= 0 else None


def _compact(row):
    keys = ('phase', 'action_id', 'tool_id', 'invocation_id', 'receipt_id', 'name', 'description',
        'source_sha256', 'status', 'dispatch_status', 'parent_program_id', 'child_program_id',
        'iteration', 'iteration_no', 'timestamp', 'event_seq', 'segment_id', 'attempt', 'error',
        'input_sha256', 'output_sha256', 'context_sha256', 'known_cost', 'charge_id', 'stage', 'availability', 'model', 'link_kind', 'link_basis', 'evaluation_id',
        'cell_id', 'cell_revision_id', 'question', 'reference_receipt_id', 'adoption_revision_id', 'matched', 'benefit', 'comparison')
    keys += ('job_id','parent_job_id','request_hash','cancel_requested',
        'result_schema','tool_result_status','tool_result_error','replay_policy','measurement_reproduced')
    keys += ('experiment_id','followup_sha256','evidence_artifact_id','dispatch','outcome_status',
        'relation','model_use','causal_benefit','reason','cadence_reason')
    keys += ('action','proposal_id','scientific_steps','experiment','next_decision','observed_at',
        'decision_if_supported','decision_if_refuted','conclusion','steps_omitted','canonical_evaluation_id',
        'candidate_receipt_id','candidate_tool_id','candidate_source_sha256','candidate_invocation_id')
    keys += ('snapshot_artifact_id','continuation_snapshot_id','continuation_sequence','queue_sequence',
        'dispatch_count','last_action_id','last_completed_iteration','recipient_candidate_id','prompt_sha256',
        'evidence_schema','total_checks','omitted_count','scope','sharing_work_id','sharing_stage')
    result = {key:row[key] if type(row[key]) in (int, float, bool) or row[key] is None else _text(row[key], 1500)
        for key in keys if key in row and not isinstance(row[key], (dict, list))}
    if isinstance(row.get('error'), dict):
        result['error'] = {key:_text(row['error'].get(key), 1000) for key in ('code','reason','message','type') if key in row['error']}
    for key in ('island_id', 'author_island_id', 'origin_island_id'):
        if key in row:
            result[key] = _island(row[key])
    for key in ('tool_ids','receipt_ids','parent_tool_ids','dependency_tool_ids','llm_call_ids'):
        if key in row:
            result[key] = _ids(row[key])
    if isinstance(row.get('target_binding'), dict):
        result['target_binding'] = {key: _text(row['target_binding'].get(key)) for key in (
            'candidate_id','target_kind','target_source_sha256','ancestry_parent_id',
            'research_targets_sha256','population_best_id','population_best_source_sha256')}
    result['resources'] = {key:_obj(row.get('resources')).get(key) for key in ('cpu_seconds','wall_seconds')
        if type(_obj(row.get('resources')).get(key)) in (int, float) and math.isfinite(row['resources'][key])}
    if isinstance(row.get('requested_limits'), dict):
        result['requested_limits'] = {key:_job_number(row['requested_limits'].get(key)) for key in ('cpu_seconds','wall_seconds')}
    if isinstance(row.get('research_state'), dict):
        result['research_state'] = _research_state(row['research_state'])
    if isinstance(row.get('comparison_report_assessment'), dict):
        from .compat.comparison_assessment import SCHEMA, validate
        assessment = row['comparison_report_assessment']
        envelope = dict(schema=SCHEMA, receipt_id=row.get('receipt_id'),
            proposal_id=row.get('proposal_id'), status='assessed', assessment=assessment)
        if validate(envelope, row.get('receipt_id')):
            result['comparison_report_assessment'] = json.loads(_canonical(assessment))
    if row.get('phase') == 'shared_observations_delivered':
        result['source_islands'] = [_island(value) for value in row.get('source_islands',[])[:16]] if isinstance(row.get('source_islands'),list) else []
        result['delivered'] = [{**{key:_text(value.get(key),128) for key in ('receipt_id','source_cell_id','source_candidate_id','decision_proposal_id','measurement_projection')},
            'source_island_id':_island(value.get('source_island_id')), 'detail_omitted':value.get('detail_omitted') is True,
            'measurement_omitted':value.get('measurement_omitted') is True}
            for value in row.get('delivered',[])[:32] if isinstance(value,dict)] if isinstance(row.get('delivered'),list) else []
    return result


def _research_state(value):
    """Bound recorded planner claims without manufacturing scientific outcomes."""
    if not isinstance(value, dict):
        return None
    result = {key:_text(value.get(key), 8000) for key in ('question','decision_if_supported',
        'decision_if_refuted','current_experiment','next_decision','status','conclusion','scope')
        if isinstance(value.get(key),str)}
    for key in ('scientific_steps','known_llm_cost','unknown_llm_calls','steps_omitted'):
        if _job_number(value.get(key)) is not None:
            result[key] = value[key]
    result['resources'] = {key:value['resources'][key] for key in
        ('cpu_seconds','wall_seconds','unknown_cpu_invocations')
        if _job_number(_obj(value.get('resources')).get(key)) is not None}
    steps = value.get('steps') if isinstance(value.get('steps'),list) else []
    result['steps'] = [_compact({key:item for key,item in row.items() if key != 'research_state'})
        for row in steps[-32:] if isinstance(row,dict)]
    result['steps_omitted'] = result.get('steps_omitted',0) + max(0,len(steps)-32)
    pending = _obj(value.get('pending_method_trial'))
    if pending:
        result['pending_method_trial'] = _method_trial(pending)
    backlog = value.get('pending_method_trial_backlog')
    if isinstance(backlog,list):
        recorded = [row for row in backlog if isinstance(row,dict)]
        result['pending_method_trial_backlog'] = [_method_trial(row) for row in recorded[:32]]
        result['pending_method_trials_total'] = int(bool(pending)) + len(recorded)
        result['pending_method_trials_omitted'] = max(0,len(recorded)-32)
    if type(value.get('transfer_review_pending')) is bool:
        result['transfer_review_pending'] = value['transfer_review_pending']
    if value.get('transfer_review_pending') is not True:
        candidates=([pending] if pending else [])+[row for row in (backlog if isinstance(backlog,list) else []) if isinstance(row,dict)]
        progress=_background_transfer(value.get('background_transfer'),candidates)
        if progress is not None:
            result['background_transfer']=progress
    return result


def _background_transfer(value, pending):
    """Bound recorded transfer cursors; lazy job/receipt views verify their bodies."""
    if not isinstance(value,dict) or value.get('schema') != 'sciel-background-method-transfer/1':
        return None
    fields=('submission_receipt_id','snapshot_artifact_id')
    if any(not isinstance(value.get(k),str) or not HASH.fullmatch(value[k]) for k in fields):
        return None
    refs,jobs,results=(value.get(k) for k in ('reference_receipt_ids','job_ids','stage_results'))
    if (not isinstance(refs,list) or not 1<=len(refs)<=16 or not isinstance(jobs,list)
            or not 1<=len(jobs)<=len(refs) or not isinstance(results,list)
            or not len(jobs)-1<=len(results)<=len(jobs)):
        return None
    if any(_ids(ids)!=ids for ids in (refs,jobs)):
        return None
    for index,row in enumerate(results):
        if (not isinstance(row,dict) or row.get('job_id')!=jobs[index]
                or row.get('status') not in ('success','tool_error','invalid_output','host_failed','unknown')
                or index<len(jobs)-1 and row['status']!='success'):
            return None
        receipt=row.get('receipt_id')
        if (receipt is None and row['status']!='unknown') or (receipt is not None
                and (not isinstance(receipt,str) or not HASH.fullmatch(receipt))):
            return None
    if not any(row.get('submission_receipt_id')==value['submission_receipt_id'] for row in pending):
        return None
    return dict(schema=value['schema'],**{k:value[k] for k in fields},
        reference_receipt_ids=refs[:],job_ids=jobs[:],
        stage_results=[{k:row.get(k) for k in ('job_id','receipt_id','status')} for row in results],
        total_stages=len(refs),submitted_stages=len(jobs),collected_stages=len(results),
        successful_stages=sum(row['status']=='success' for row in results),
        current_job_id=jobs[-1] if len(jobs)>len(results) else None,
        scope='Recorded cell state; job and receipt bodies are verified when opened. No method benefit is established.')


def _method_trial(value):
    result = {key:_text(value.get(key),128) for key in
        ('tool_id','source_program_id','source_sha256','submission_receipt_id')}
    if isinstance(value.get('blocked_reason'),str):
        result['blocked_reason'] = _text(value['blocked_reason'],128)
    for key in ('pipeline_stages','scientific_step_limit'):
        if type(value.get(key)) is int and value[key] >= 0:
            result[key] = value[key]
    return result
