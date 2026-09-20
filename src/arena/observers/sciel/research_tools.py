"""Read-only receipts for executable tools in the ordinary island Engine.

Artifacts are read lazily, by authenticated IDs, never by journal-supplied paths.
This projection does not create Programs, H/C/L records, rewards or usage credit.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat

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


def _compact(row):
    keys = ('phase', 'action_id', 'tool_id', 'invocation_id', 'receipt_id', 'name', 'description',
        'source_sha256', 'status', 'dispatch_status', 'parent_program_id', 'child_program_id',
        'iteration', 'iteration_no', 'timestamp', 'event_seq', 'segment_id', 'attempt', 'error',
        'input_sha256', 'output_sha256', 'context_sha256', 'known_cost', 'charge_id', 'stage', 'availability', 'model', 'link_kind',
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
        'evidence_schema','total_checks','omitted_count','scope')
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
        result['pending_method_trial'] = {key:_text(pending.get(key),128) for key in
            ('tool_id','source_program_id','source_sha256','submission_receipt_id')}
    return result


def _continuations(checkpoint, cells):
    """Checkpoint scheduler metadata only; never infer execution from queue age."""
    state = _obj(_obj(checkpoint.get('research_tools')).get('continuations'))
    empty = dict(available=False, items=[], summary={}, scope='not_recorded')
    if not state:
        return empty
    if state.get('schema') != 'sciel-research-continuations/1' or not isinstance(state.get('items'), dict) or type(state.get('next_sequence')) is not int or state['next_sequence'] < 0:
        return dict(empty, reason='Continuation state has an unsupported or malformed schema.')
    items, invalid, sequences = [], 0, set()
    for cell_id, item in state['items'].items():
        if (cell_id not in cells or not isinstance(cell_id,str) or not HASH.fullmatch(cell_id)
                or not isinstance(item,dict) or item.get('status') not in {'ready','waiting','closed'}
                or not isinstance(item.get('snapshot_artifact_id'),str) or not HASH.fullmatch(item['snapshot_artifact_id'])
                or any(type(item.get(key)) is not int or item[key] < 0 for key in ('queue_sequence','dispatch_count'))
                or item['queue_sequence'] >= state['next_sequence'] or item['queue_sequence'] in sequences
                or not isinstance(item.get('reason'),str)
                or (item.get('last_action_id') is not None and (not isinstance(item['last_action_id'],str) or not HASH.fullmatch(item['last_action_id'])))
                or (item.get('last_completed_iteration') is not None and
                    (type(item['last_completed_iteration']) is not int or item['last_completed_iteration'] < 0))):
            invalid += 1
            continue
        row = dict(cell_id=cell_id, status=item['status'], snapshot_artifact_id=item['snapshot_artifact_id'],
            reason=_text(item.get('reason'),256),
            queue_sequence=item['queue_sequence'], dispatch_count=item['dispatch_count'],
            last_action_id=_text(item.get('last_action_id'),256), last_completed_iteration=item.get('last_completed_iteration'),
            scope='committed_checkpoint', snapshot_verified=False)
        sequences.add(item['queue_sequence'])
        items.append(row)
        cells[cell_id]['continuation'] = row
    items.sort(key=lambda row:(row['status']=='closed',row['queue_sequence'],row['cell_id']))
    summary={status:sum(row['status']==status for row in items) for status in ('ready','waiting','closed')}
    summary.update(total=len(items),omitted=max(0,len(items)-LIMIT),invalid=invalid)
    return dict(available=True,items=items[:LIMIT],summary=summary,scope='committed_checkpoint',
        note='Recorded queue state. Snapshot artifact content is not authenticated by this metadata projection.')


def _job_bindings(checkpoint):
    """Only committed controller state grants visibility; disk/tail events do not."""
    saved = _obj(_obj(checkpoint.get('research_tools')).get('jobs'))
    return {ident:value for ident,value in saved.items() if isinstance(ident,str) and HASH.fullmatch(ident)
        and isinstance(value,dict) and isinstance(value.get('tool_id'),str) and HASH.fullmatch(value['tool_id'])}


def _job_base(checkpoint, configured):
    bindings = _job_bindings(checkpoint)
    collected = _obj(_obj(checkpoint.get('research_tools')).get('collected_jobs'))
    items = [dict(id=ident,tool_id=value['tool_id'],owner=_obj(value.get('owner')),
        request_hash=value.get('request_hash'),collected=ident in collected)
        for ident,value in list(bindings.items())[-LIMIT:]]
    return dict(available=bool(bindings) or _obj(configured.get('jobs')).get('enabled') is True,
        items=items,summary=dict(total=len(bindings),visible=len(items),omitted=max(0,len(bindings)-LIMIT)))


def _bound_job(run_dir, binding, *, include_receipt=False):
    # Import the public pure reader, never construct a manager/service to view data.
    from .compat.jobs import read_job
    job = read_job(run_dir,binding['id'],include_receipt=include_receipt)
    if (job.get('tool_id') != binding['tool_id'] or job.get('owner') != binding.get('owner',{})
            or (binding.get('request_hash') is not None and job.get('request_hash') != binding['request_hash'])):
        raise ValueError('Background job differs from committed controller binding')
    return job


def _job_number(value):
    return value if type(value) in (int,float) and math.isfinite(value) and value >= 0 else None


def _job_row(run_dir, binding):
    base = dict(id=binding['id'],tool_id=binding['tool_id'],collected=binding.get('collected',False))
    try:
        job = _bound_job(run_dir,binding)
        owner = _obj(job.get('owner'))
        base.update(status=job['status'],cancel_requested=job.get('cancel_requested') is True,
            cell_id=owner.get('cell_id'),island_id=_island(owner.get('island_id')),
            parent_program_id=_text(owner.get('parent_program_id')),parent_job_id=job.get('parent_job_id'),
            receipt_id=job.get('receipt_id'),dispatch_status=job.get('dispatch_status'),
            requested={key:_job_number(_obj(job.get('requested_limits')).get(key)) for key in ('cpu_seconds','wall_seconds')},
            actual={key:_job_number(_obj(job.get('resources')).get(key)) for key in ('cpu_seconds','wall_seconds')},
            error=({key:_text(job['error'].get(key),1000) for key in ('code','reason','message','type') if key in job['error']}
                if isinstance(job.get('error'),dict) else _text(job.get('error'),1500)))
        for key in ('created_at','started_at','finished_at','updated_at'):
            base[key] = _text(job.get(key),128)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        base.update(status='unknown',cancel_requested=False,requested={},actual={},receipt_id=None,
            error='Saved job unavailable or failed verification: '+str(exc)[:300])
    return base


class BackgroundJobView:
    """Refresh a bounded sidecar window without replaying the Engine journal."""
    def __init__(self, run_dir):
        self.run_dir = Path(run_dir)
        self.cache = {}

    def project(self, base):
        items, retained = [], set()
        for binding in base.get('items',[])[:LIMIT]:
            ident = binding['id'];retained.add(ident)
            directory = self.run_dir/'research_tools'/'jobs'/ident
            signatures = []
            # A parent-directory replacement must invalidate a previously
            # verified read even when the target files retain their metadata.
            for path in (self.run_dir,self.run_dir/'research_tools',directory.parent,directory):
                try:
                    info = path.lstat();signatures.append((info.st_ino,info.st_mode))
                except OSError:
                    signatures.append(None)
            for name in ('spec.json','status.json','cancel.request','receipt.json'):
                path = directory/name
                try:
                    info = path.lstat();signatures.append((info.st_ino,info.st_size,info.st_mtime_ns,info.st_mode))
                except OSError:
                    signatures.append(None)
            signature = (hashlib.sha256(_canonical(binding)).hexdigest(),tuple(signatures))
            cached = self.cache.get(ident)
            if cached is None or cached[0] != signature:
                cached = (signature,_job_row(self.run_dir,binding));self.cache[ident] = cached
            items.append(cached[1])
        self.cache = {ident:value for ident,value in self.cache.items() if ident in retained}
        summary = dict(base.get('summary',{}))
        for status in ('queued','running','completed','failed','cancelled','unknown'):
            summary[status] = sum(row.get('status')==status for row in items)
        summary['cancel_requested'] = sum(row.get('cancel_requested') is True and row.get('status') in ('queued','running') for row in items)
        cpu = [row.get('actual',{}).get('cpu_seconds') for row in items]
        known = [value for value in cpu if value is not None]
        summary.update(observed_cpu_seconds=sum(known) if known else None,observed_cpu_jobs=len(known),unknown_cpu_jobs=len(items)-len(known))
        result = dict(available=base.get('available',False),items=items,summary=summary,
            scope='Committed jobs only. Status is the latest saved backend observation; a cancellation request is not proof of completion. Usage covers the visible window and excludes unobserved CPU and infrastructure overhead.')
        result['version'] = hashlib.sha256(_canonical(result)).hexdigest()
        return result


def job_detail(run_dir, ident, checkpoint):
    bindings = _job_bindings(checkpoint)
    if ident not in bindings:
        raise KeyError('Job is not committed in this controller checkpoint')
    binding = dict(id=ident,tool_id=bindings[ident]['tool_id'],owner=_obj(bindings[ident].get('owner')),
        request_hash=bindings[ident].get('request_hash'))
    job = _bound_job(run_dir,binding,include_receipt=True)
    return dict(id=ident,kind='job',verified=True,request=job.get('request'),status=job['status'],
        receipt=job.get('receipt'),snapshot={key:value for key,value in job.items() if key not in ('request','receipt')})


def _cells_view(checkpoint, rows):
    saved = _obj(_obj(_obj(checkpoint.get('research_tools')).get('lifecycle')).get('cells'))
    anchor = _obj(_obj(checkpoint.get('provenance')).get('journal_anchor'))
    boundary = next((index for index,row in enumerate(rows) if anchor and
        row.get('segment_id')==anchor.get('segment_id') and row.get('event_seq')==anchor.get('event_seq')),None)
    cells = {}
    if saved.get('schema') == 'sciel-research-cells/1':
        for ident, value in _obj(saved.get('cells')).items():
            if isinstance(ident, str) and HASH.fullmatch(ident) and isinstance(value, dict):
                cells[ident] = dict(id=ident,head_revision=value.get('head_revision'),
                    scheduled=value.get('active'),affinities=value.get('affinities',[]),state_source='checkpoint',
                    stage=None,question=None,tool_ids=[],evidence=[])
    latest = {}
    for index,source in enumerate(rows):
        if source.get('event') != 'research_tool' or source.get('schema') != EVENT_SCHEMA:
            continue
        ident, phase = source.get('cell_id'), source.get('phase')
        if not isinstance(ident,str) or not HASH.fullmatch(ident):
            continue
        if phase not in ('cell_created','cell_activated','cell_revision','adopted'):
            continue
        latest[ident] = index
        row = _compact(source)
        cell = cells.setdefault(ident,dict(id=ident,head_revision=None,scheduled=False,
            affinities=[],stage=None,question=None,tool_ids=[],evidence=[]))
        cell.update(state_source='selected_journal',last_event=phase,last_activity_at=row.get('timestamp'))
        for key in ('question','origin_island_id'):
            if row.get(key) is not None:
                cell[key] = row[key]
        if isinstance(row.get('cell_revision_id'),str) and HASH.fullmatch(row['cell_revision_id']):
            cell['head_revision'] = row['cell_revision_id']
        if phase == 'cell_created':
            cell.update(stage='propose',created_at=row.get('timestamp'),affinities=[row.get('island_id')])
        if phase == 'cell_activated':
            cell.update(stage=row.get('stage'),scheduled=True)
        if phase == 'cell_revision' and row.get('stage') in ('research','independent_replay','adopt_trial','use_again','background_submitted','background_deferred'):
            cell.update(stage='adopted_for_trials' if cell.get('stage')=='adopted_for_trials' and row['stage']=='adopt_trial' else row['stage'],scheduled=False)
        if phase == 'adopted':
            cell['stage'] = 'adopted_for_trials'
        if 'tool_ids' in row:
            cell['tool_ids'] = row['tool_ids']
        if isinstance(source.get('evidence'),list):
            cell['evidence'] = [dict(kind=_text(item.get('kind'),80),id=item['id'],tool_id=item.get('tool_id'))
                for item in source['evidence'][:LIMIT] if isinstance(item,dict) and isinstance(item.get('id'),str) and HASH.fullmatch(item['id'])]
    # Older journal metadata cannot move a committed head backwards. If its
    # anchor is unavailable, keep the checkpoint head and label that scope.
    if saved.get('schema') == 'sciel-research-cells/1':
        for ident,value in _obj(saved.get('cells')).items():
            if ident in cells and isinstance(value,dict) and (boundary is None or latest.get(ident,-1)<=boundary):
                cell = cells[ident]
                if cell.get('head_revision') != value.get('head_revision'):
                    cell.update(stage=None,tool_ids=[],evidence=[])
                cell.update(head_revision=value.get('head_revision'),scheduled=value.get('active'),
                    affinities=value.get('affinities',[]),state_source='checkpoint')
    return cells


def _configuration(start, checkpoint):
    for source, value in (('run_start', start), ('checkpoint', checkpoint)):
        config = value.get('config')
        configured = _obj(_obj(config).get('research_tools'))
        if type(configured.get('enabled')) is bool:
            enabled = configured['enabled']
            return dict(status='enabled' if enabled else 'disabled', enabled=enabled, source=source,
                reason=('Research tools are enabled in the recorded configuration. Activity starts only when scheduling permits.'
                    if enabled else 'Research tools are disabled in the recorded configuration; no tool activity is expected.'))
        contract = value.get('engine_contract') or _obj(value.get('identity')).get('engine_contract')
        # This recorded contract initializes tools only for an enabled block
        # (Engine.__init__). Do not apply today's default to unknown archives.
        if contract in {'espalier-3.21', 'espalier-3.22', 'espalier-3.23', 'espalier-3.24', 'espalier-3.25', 'espalier-3.26', 'espalier-3.27', 'espalier-3.28','espalier-3.29','espalier-3.30','espalier-3.31','espalier-3.32','espalier-3.33', 'espalier-3.34'} and isinstance(config, dict) and 'research_tools' not in config:
            return dict(status='disabled', enabled=False, source=source,
                reason=f'The recorded configuration has no research_tools block. In its recorded Engine contract ({contract}), tools are disabled unless explicitly enabled.')
    return dict(status='not_recorded', enabled=None, source=None,
        reason='Research-tool enablement was not recorded. Missing activity does not establish that tools were disabled.')


def _cell_events(events):
    """Attribute by explicit cell or unambiguous action, never by shared tool ID."""
    owners, indexed = {}, {}
    for row in events:
        ident, action = row.get('cell_id'), row.get('action_id')
        if isinstance(ident, str) and HASH.fullmatch(ident) and isinstance(action, str):
            owners.setdefault(action, set()).add(ident)
    for row in events:
        ident = row.get('cell_id')
        if ident is None:
            candidates = owners.get(row.get('action_id'), set())
            ident = next(iter(candidates)) if len(candidates) == 1 else None
        if isinstance(ident, str) and HASH.fullmatch(ident):
            indexed.setdefault(ident, []).append(row)
    return indexed


def _committed_followups(checkpoint):
    state = _obj(_obj(checkpoint.get('research_tools')).get('followups'))
    # A checkpoint grants visibility, but its digest is not proof of execution.
    if (state.get('schema') != 'sciel-method-followups/1' or not isinstance(state.get('records'), list)
            or state.get('identity_sha256') != _obj(checkpoint.get('research_tools')).get('identity_sha256')):
        return []
    try:
        if state.get('sha256') != hashlib.sha256(_canonical({k:v for k,v in state.items() if k != 'sha256'})).hexdigest():
            return []
    except (ValueError, TypeError):
        return []
    return [record for record in state['records'] if isinstance(record, dict)]


def _enrich_cells(cells, events, checkpoint):
    indexed = _cell_events(events)
    event_indices = {id(row):index for index,row in enumerate(events)}
    saved_states = _obj(_obj(_obj(checkpoint.get('research_tools')).get('lifecycle')).get('research_state'))
    anchor = _obj(_obj(checkpoint.get('provenance')).get('journal_anchor'))
    boundary = next((index for index,row in enumerate(events) if anchor and
        row.get('segment_id')==anchor.get('segment_id') and row.get('event_seq')==anchor.get('event_seq')),None)
    jobs, followups = {}, {}
    for ident, binding in _job_bindings(checkpoint).items():
        jobs.setdefault(_obj(binding.get('owner')).get('cell_id'), []).append({**binding, 'id':ident})
    for record in _committed_followups(checkpoint):
        for ident in {card.get('cell_id') for card in _obj(record.get('exposures')).get('cards', []) if isinstance(card, dict)}:
            followups.setdefault(ident, []).append(record.get('sha256'))
    for ident, cell in cells.items():
        scoped = indexed.get(ident, [])
        active_decision = None
        for row in scoped:
            if row.get('phase')=='research_decision' and isinstance(row.get('proposal_id'),str):
                active_decision = _compact(row)
                active_decision.update(status='planned',committed=False,evidence_scope='selected_journal_pending_decision')
            elif active_decision and row.get('action_id')==active_decision.get('action_id'):
                if (row.get('phase')=='episode_finished' or row.get('phase')=='research_step'
                        and row.get('proposal_id')==active_decision.get('proposal_id')):
                    active_decision = None
                elif row.get('phase')=='invocation_started':
                    active_decision['status'] = 'awaiting_execution_receipt'
                elif row.get('phase')=='invocation_result':
                    active_decision['status'] = 'result_recorded_uncommitted'
        if active_decision and any(row.get('proposal_id')==active_decision.get('proposal_id')
                for row in _obj(saved_states.get(ident)).get('steps',[]) if isinstance(row,dict)):
            active_decision = None
        cell['active_decision'] = active_decision
        cell['research_state'] = _research_state(saved_states.get(ident))
        committed_steps = list(_obj(cell['research_state']).get('steps',[]))
        state_event_index = None
        # A selected journal tail may be newer than the checkpoint. With no
        # available anchor, prefer the committed state over an older event.
        for row in scoped:
            index = event_indices[id(row)]
            after_anchor = (boundary is not None and index > boundary) or (
                anchor.get('segment_id') == row.get('segment_id') and isinstance(row.get('event_seq'),int)
                and isinstance(anchor.get('event_seq'),int) and row['event_seq'] > anchor['event_seq'])
            if row.get('cell_id') == ident and row.get('phase') == 'research_state' and (
                    saved_states.get(ident) is None or after_anchor):
                cell['research_state'] = _research_state(row.get('research_state'))
                state_event_index = index
        if cell['research_state'] and state_event_index is not None:
            # State events are compact summaries. Recover their stage links
            # only through the selected journal up to that recorded state,
            # retaining checkpoint stages when the old journal was rotated.
            steps = list(cell['research_state'].get('steps')) or committed_steps
            seen = {tuple(row.get(key) for key in ('action','status','proposal_id','receipt_id','canonical_evaluation_id')) for row in steps}
            for row in scoped:
                index = event_indices[id(row)]
                if index > state_event_index or row.get('phase')!='research_step':
                    continue
                after_anchor = (boundary is not None and index > boundary) or (
                    anchor.get('segment_id')==row.get('segment_id') and isinstance(row.get('event_seq'),int)
                    and isinstance(anchor.get('event_seq'),int) and row['event_seq']>anchor['event_seq'])
                if saved_states.get(ident) is not None and not after_anchor:
                    continue
                key = tuple(row.get(key) for key in ('action','status','proposal_id','receipt_id','canonical_evaluation_id'))
                if key not in seen:
                    steps.append(_compact(row));seen.add(key)
            cell['research_state']['steps'] = steps[-32:]
            cell['research_state']['steps_omitted'] = max(cell['research_state']['steps_omitted'],len(steps)-32)
        if cell['research_state'] and cell['research_state'].get('question'):
            cell['current_question'] = cell['research_state']['question']
        if active_decision and active_decision.get('question'):
            cell['current_question'] = active_decision['question']
        if cell['research_state']:
            for step in cell['research_state']['steps']:
                matches = [row for row in scoped if row.get('phase')=='research_step'
                    and row.get('action')==step.get('action') and any(step.get(key) for key in
                        ('proposal_id','receipt_id','canonical_evaluation_id'))
                    and all(row.get(key)==step.get(key) for key in
                        ('proposal_id','receipt_id','canonical_evaluation_id'))]
                if len(matches)==1 and isinstance(matches[0].get('timestamp'),str):
                    step['timestamp'] = matches[0]['timestamp']
        invocations, calls, contexts, links, tools = {}, {}, set(), set(), set(cell.get('tool_ids', []))
        for row in scoped:
            phase = row.get('phase')
            if isinstance(row.get('tool_id'), str) and HASH.fullmatch(row['tool_id']):
                tools.add(row['tool_id'])
            tools.update(_ids(row.get('tool_ids')))
            if phase in ('invocation_started', 'invocation_result'):
                key = row.get('invocation_id')
                if phase == 'invocation_result' or key not in invocations:
                    invocations[key] = row
            if phase in ('llm_start','llm_result','llm_abandoned'):
                calls[(row.get('action_id'), row.get('attempt'))] = row
            if phase == 'context_prepared':
                contexts.add(row.get('action_id'))
            if phase == 'child_link' and isinstance(row.get('child_program_id'), str):
                links.add(row['child_program_id'])
        cell['counts'] = dict(versions=len(tools), invocations=len(invocations),
            actual_invocations=sum(row.get('dispatch_status') == 'invoked' for row in invocations.values()),
            failed_invocations=sum(row.get('dispatch_status') == 'invoked' and (row.get('status') == 'failed'
                or (row.get('result_schema') == 'sciel-tool-result/1'
                    and row.get('tool_result_status') in ('tool_error','invalid_output','host_failed')))
                for row in invocations.values()),
            llm_calls=len(calls), prepared_contexts=len(contexts), linked_programs=len(links),
            jobs=len(jobs.get(ident, [])), followups=len(set(followups.get(ident, []))), events=len(scoped))
        cell['activity_status'] = 'scheduled' if cell.get('scheduled') else ('activity_recorded' if scoped else 'no_activity_recorded')
        timestamps = [row.get('timestamp') for row in scoped if isinstance(row.get('timestamp'), str)]
        if timestamps:
            cell['last_activity_at'] = timestamps[-1]
        cell['coverage'] = dict(scope='Counts are selected-journal metadata; jobs and followups are checkpoint references. Artifact bodies are verified on opening.',
            benefit='not_established', model_use='unknown')
        cell['detail_version'] = hashlib.sha256(_canonical(dict(cell=cell, events=[_compact(row) for row in scoped],
            jobs=jobs.get(ident, []), followups=followups.get(ident, [])))).hexdigest()
    return cells


def research_tools_view(start, checkpoint, rows):
    config = _obj(start.get('config')) or _obj(checkpoint.get('config'))
    configured = _obj(config.get('research_tools'))
    events = _events(rows)
    versions, invocations, calls, contexts, children = {}, {}, {}, {}, {}
    for source in events:
        row = _compact(source)
        phase, ident = row.get('phase'), row.get('tool_id')
        if phase in ('registered','published') and isinstance(ident,str) and HASH.fullmatch(ident):
            version = versions.setdefault(ident,dict(id=ident,status='registered',parents=[],created_at=row.get('timestamp')))
            for field in ('name','description','source_sha256','author_island_id','action_id','parent_program_id','cell_id','result_schema','replay_policy'):
                if field in row and field not in version:
                    version[field] = row[field]
            if row.get('parent_tool_ids'):
                version['parents'] = row['parent_tool_ids']
            if row.get('dependency_tool_ids'):
                version['dependencies'] = row['dependency_tool_ids']
            if phase == 'published':
                version.update(status='published',published_at=row.get('timestamp'),availability=row.get('availability'))
        elif phase in ('invocation_started','invocation_result') and isinstance(row.get('invocation_id'),str):
            call = invocations.setdefault(row['invocation_id'],dict(id=row['invocation_id'],status='pending'))
            # A late duplicated start must not erase an already recorded result.
            if phase == 'invocation_result' or 'receipt_id' not in call:
                call.update(row)
        elif phase in ('llm_start','llm_result','llm_abandoned'):
            key = (row.get('action_id'),row.get('attempt'))
            call = calls.setdefault(key,dict(id=str(row.get('action_id'))+':'+str(row.get('attempt')),status='pending'))
            if phase in ('llm_result','llm_abandoned') or 'receipt_id' not in call:
                call.update(row)
                if phase == 'llm_abandoned':
                    call['status'] = 'unknown'
                if phase == 'llm_result' and call.get('status') == 'pending':
                    call['status'] = 'returned'
        elif phase == 'rejected':
            key = (row.get('action_id'),row.get('attempt'))
            if key in calls:
                calls[key].update(status=row.get('status') or 'rejected',error=row.get('error'))
        elif phase == 'context_prepared':
            contexts[row.get('action_id') or (row.get('segment_id'),row.get('event_seq'))] = row
        elif phase == 'child_link' and row.get('child_program_id'):
            row['id'] = ':'.join(str(row.get(key,'')) for key in ('action_id','child_program_id','island_id','link_kind'))
            children[row['id']] = row
    uses_by_tool, links_by_tool = {}, {}
    for row in invocations.values():
        author = versions.get(row.get('tool_id'),{}).get('author_island_id')
        row['actual_execution'] = row.get('dispatch_status') == 'invoked'
        row['foreign_execution'] = bool(row['actual_execution'] and author is not None and row.get('island_id') is not None
            and str(author) != str(row['island_id']))
        if row['actual_execution']:
            uses_by_tool.setdefault(row.get('tool_id'), []).append(row)
    for row in children.values():
        for ident in row.get('tool_ids', []):
            links_by_tool.setdefault(ident, []).append(row)
    for version in versions.values():
        uses = uses_by_tool.get(version['id'], [])
        links = links_by_tool.get(version['id'], [])
        version.update(invocations=len(uses),foreign_invocations=sum(row['foreign_execution'] for row in uses),
            used_by=list(dict.fromkeys(str(row['island_id']) for row in uses if row.get('island_id') is not None)),
            children=[dict(program_id=row['child_program_id'],island_id=row.get('island_id'),link_kind=row.get('link_kind'),receipt_ids=row.get('receipt_ids',[])) for row in links[-LIMIT:]])
    actual = [row for row in invocations.values() if row['actual_execution']]
    cells = _cells_view(checkpoint, rows)
    continuations = _continuations(checkpoint,cells)
    cells = _enrich_cells(cells, events, checkpoint)
    lifecycle_events = [_compact(row) for row in events if row.get('phase') in ('replay_result','adopted','post_adoption_attempt','post_adoption_use')]
    lifecycle_events = list({(row.get('phase'),row.get('cell_id'),row.get('tool_id'),row.get('receipt_id')):row for row in lifecycle_events}.values())
    actual_receipts = {row.get('receipt_id') for row in actual}
    counts = dict(proposed_cells=len(cells),local_trials=sum(row.get('stage')=='research' for row in actual),
        independent_replays=sum(row.get('phase')=='replay_result' for row in lifecycle_events),
        matched_replays=sum(row.get('phase')=='replay_result' and row.get('matched') is True for row in lifecycle_events),
        reproduced_measurements=sum(row.get('phase')=='replay_result' and row.get('measurement_reproduced') is True for row in lifecycle_events),
        independent_execution_checks=sum(row.get('phase')=='replay_result' and row.get('matched') is True and row.get('replay_policy')=='independent_execution' for row in lifecycle_events),
        adoptions=sum(row.get('phase')=='adopted' and row.get('status')=='adopted_for_trials' for row in lifecycle_events),
        post_adoption_uses=sum(row.get('phase')=='post_adoption_use' and row.get('receipt_id') in actual_receipts for row in lifecycle_events))
    return dict(schema='sciel-engine-tool-dashboard/1',available=bool(events) or configured.get('enabled') is True,
        configured=configured,configuration=_configuration(start, checkpoint),summary=dict(versions=len(versions),published=sum(v['status']=='published' for v in versions.values()),
            invocations=len(invocations),actual_invocations=len(actual),foreign_invocations=sum(r['foreign_execution'] for r in actual),
            failed_invocations=sum(r.get('status')=='failed' or (r.get('result_schema')=='sciel-tool-result/1' and r.get('tool_result_status') in ('tool_error','invalid_output','host_failed')) for r in actual),
            host_failed_invocations=sum(r.get('status')=='failed' for r in actual),
            tool_failed_invocations=sum(r.get('result_schema')=='sciel-tool-result/1' and r.get('tool_result_status') in ('tool_error','invalid_output') for r in actual),
            unknown_invocations=sum(r.get('status')=='unknown' or r.get('dispatch_status')=='unknown' for r in invocations.values()),prepared_contexts=len(contexts),
            linked_programs=len({row['child_program_id'] for row in children.values()}),linked_records=len(children),llm_calls=len(calls),cells=len(cells)),
        cells=list(cells.values())[-LIMIT:],lifecycle=dict(counts=counts,events=lifecycle_events[-LIMIT:],
            recorded=bool(cells),scope='Counts describe different transitions in the selected journal lineage, not a success funnel or evidence of task benefit. Missing historical events are not reconstructed.'),
        versions=list(versions.values())[-LIMIT:],invocations=list(invocations.values())[-LIMIT:],
        jobs=_job_base(checkpoint,configured),continuations=continuations,
        llm_calls=list(calls.values())[-LIMIT:],contexts=list(contexts.values())[-LIMIT:],
        child_links=list(children.values())[-LIMIT:],events=[_compact(row) for row in events[-LIMIT:]],
        coverage=dict(limit=LIMIT,scope='Selected Engine journal lineage after checkpoint restoration; artifact bodies load only when opened.',
            omitted_versions=max(0,len(versions)-LIMIT),omitted_invocations=max(0,len(invocations)-LIMIT),omitted_cells=max(0,len(cells)-LIMIT)),
        notes=['Shared availability, prepared context and actual execution are different observations.',
            'context_prepared records Snapshot preparation, not proven delivery to an LLM prompt.',
            'A child link associates a candidate with preceding tool calls; it does not establish causal utility or give tool reward credit.',
            'Tool LLM charges are already included in Engine spend. CPU observations exclude Docker daemon and VM overhead.'])


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()


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
    return dict(id=ident,verified=True,kind=body['kind'],payload=payload)


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


def _cell_followup(run_dir, record, ident, history_ids, rows, reader, registered):
    """Authenticate committed chronology, without claiming use or causal benefit."""
    from .compat.followups import build_followup, validate_followup
    from .compat.result_contract import assess_receipt
    from .compat.research_targets import input_binding
    record = validate_followup(record)
    artifact = reader('artifacts', record['evidence_artifact_id'], 16*1024*1024)
    if artifact.get('schema') != 'sciel-research-tool-artifact/1' or artifact.get('kind') != 'method_followup_evidence':
        raise ValueError('Unsupported followup evidence artifact')
    saved = artifact['payload']
    expected = build_followup(saved['research_record'], child_program_id=saved['child_program_id'],
        link_kind=saved['link_kind'], observed_record=saved['observed_record'], evidence_artifact_id=record['evidence_artifact_id'])
    if expected != record:
        raise ValueError('Followup differs from saved canonical research evidence')
    cards = [card for card in record['exposures']['cards'] if card['cell_id'] == ident and card['source']['tool_id'] is not None]
    if not cards:
        raise ValueError('Followup has no linked exposure to this cell')
    for card in cards:
        if card['revision_id'] not in history_ids:
            raise ValueError('Exposure revision is outside the verified retained cell history')
        source = card['source']
        if source['tool_id'] not in registered:
            raise ValueError('Exposure method is not registered in the controller checkpoint')
        detail = artifact_detail(run_dir, source['receipt_id'], rows, _reader=reader)
        if detail['kind'] != 'invocation':
            raise ValueError('Exposure must reference an invocation')
        payload = detail['payload']; receipt = payload['receipt']; inputs = payload['inputs']
        bundle = _bundle(run_dir, source['tool_id'], _reader=reader)
        binding = input_binding(inputs)
        expected_source = dict(tool_id=payload['tool_id'], invocation_id=receipt['invocation_id'],
            receipt_id=source['receipt_id'], **binding)
        if (source != expected_source or payload.get('target_binding') != binding or payload.get('cell_id') != ident
                or payload.get('result') != assess_receipt(receipt)
                or card['observation_status'] != payload['result']['status']
                or receipt.get('method_id') != source['tool_id'] or receipt.get('plan_id') != payload.get('action_id')
                or receipt.get('reservation_id') != receipt.get('invocation_id')
                or receipt.get('source_sha256') != hashlib.sha256(_canonical(bundle['files'])).hexdigest()
                or receipt.get('input_sha256') != hashlib.sha256(_canonical(inputs)).hexdigest()
                or receipt.get('receipt_sha256') != hashlib.sha256(_canonical({k:v for k,v in receipt.items() if k != 'receipt_sha256'})).hexdigest()):
            raise ValueError('Exposure differs from its saved invocation')
    outcome = record['outcome']
    return dict(id=record['sha256'], followup_sha256=record['sha256'], experiment_id=record['experiment_id'],
        evidence_artifact_id=record['evidence_artifact_id'], evidence_sha256=record['evidence_sha256'],
        iteration=record['iteration'], island_id=record['island_id'], parent_program_id=record['parent']['program_id'],
        child_program_id=outcome['child_program_id'], link_kind=outcome['link_kind'],
        tool_ids=list(dict.fromkeys(card['source']['tool_id'] for card in cards)),
        receipt_ids=list(dict.fromkeys(card['source']['receipt_id'] for card in cards)),
        prompt_sha256=record['exposures']['prompt_sha256'], generation=record['generation'],
        outcome_status=outcome['status'], score=outcome['score'], actual_delta=outcome['actual_delta'],
        metric_sha256=outcome['metric']['sha256'], task_hash=outcome['metric']['task_hash'],
        score_scope='Recorded controller-score units, not inferred native measurements or method benefit.',
        model_use='unknown', causal_benefit='unknown', relation=record['relation'], verified=True,
        evidence_scope='checkpoint_and_immutable_artifacts')


def _terminal_decision(ident, checkpoint, history, research_state, reader):
    """Show a saved accepted planner closure, never upgrade it to measurement."""
    from .compat.research_cells_context import _card
    from .compat.decision_projection import authenticate_projection
    card = _obj(_obj(_obj(checkpoint.get('research_tools')).get('lifecycle')).get('cards')).get(ident)
    if not isinstance(card, dict) or card.get('schema') != 'sciel-research-check/4':
        return None
    decision = card.get('decision')
    if decision is None:
        return None
    try:
        if _card(card) is None or card.get('cell_id') != ident:
            raise ValueError('Invalid retained decision card')
        revisions = {row['id'] for row in history}
        references = {(ref.get('kind'), ref.get('id')) for row in history
            for ref in row.get('evidence', []) if isinstance(ref, dict)}
        proposal_id = decision['proposal_id']
        if card['revision_id'] not in revisions or ('research_decision', proposal_id) not in references:
            raise ValueError('Terminal proposal is not committed in this cell history')
        state = _obj(research_state)
        steps = state.get('steps', [])
        # A newer committed episode or pending plan must not inherit a previous
        # closure as its current conclusion. Historical evidence remains saved.
        if (state.get('status') != 'closed' or not steps or steps[-1].get('action') != 'finish'
                or steps[-1].get('status') != 'closed' or steps[-1].get('proposal_id') != proposal_id):
            return None
        artifact = reader('artifacts', proposal_id, 16 * 1024 * 1024)
        payload = _obj(artifact.get('payload'))
        if (artifact.get('schema') != 'sciel-research-tool-artifact/1' or artifact.get('kind') != 'proposal'
                or payload.get('cell_id') != ident or payload.get('cell_revision_id') not in revisions):
            raise ValueError('Terminal proposal belongs to another cell revision')
        verified = authenticate_projection(decision, payload, proposal_id)
        receipt_ids = payload['evidence_receipt_ids']
        if len(receipt_ids) > 128:
            raise ValueError('Terminal evidence exceeds detail read bound')
        records = {}
        for receipt_id in receipt_ids:
            if ('tool_invocation', receipt_id) not in references:
                raise ValueError('Terminal evidence is not committed in this cell history')
            record = reader('artifacts', receipt_id, 16 * 1024 * 1024)
            if (record.get('kind') != 'invocation' or record.get('schema') != 'sciel-research-tool-artifact/1'
                    or _obj(record.get('payload')).get('cell_id') != ident):
                raise ValueError('Terminal evidence belongs to another cell')
            records[receipt_id] = record['payload']
        source = card['source']
        if source['receipt_id'] is not None:
            record = records.get(source['receipt_id'])
            if (record is None or source['tool_id'] != record.get('tool_id')
                    or record.get('action_id') != decision['action_id']
                    or source['invocation_id'] != _obj(record.get('receipt')).get('invocation_id')
                    or {key: source.get(key) for key in _obj(record.get('target_binding'))} != record.get('target_binding')
                    or card['question'] != record.get('question')
                    or card['observations']['status'] != _obj(record.get('result')).get('status')
                    or card['observations']['resources'] != _obj(record.get('receipt')).get('resources')):
                raise ValueError('Decision card observation differs from its saved invocation')
        elif {key: source.get(key) for key in _obj(payload.get('target_binding'))} != payload.get('target_binding'):
            raise ValueError('Decision target differs from its saved proposal')
        return dict(verified, verified=True, evidence_scope='saved_proposal_and_committed_cell_revision')
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _cell_related(run_dir, ident, checkpoint, rows, history, *, reader=None):
    events = _events(rows)
    scoped = _cell_events(events).get(ident, [])
    action_cells = {}
    for row in events:
        if isinstance(row.get('action_id'),str) and isinstance(row.get('cell_id'),str):
            action_cells.setdefault(row['action_id'],set()).add(row['cell_id'])
    tool_ids = {value for revision in history for value in _ids(revision.get('tool_ids'))}
    for row in scoped:
        tool_ids.update(_ids(row.get('tool_ids')))
        if isinstance(row.get('tool_id'), str) and HASH.fullmatch(row['tool_id']):
            tool_ids.add(row['tool_id'])
    registrations = [row for row in events if row.get('phase') in ('registered','published') and row.get('tool_id') in tool_ids]
    # Shared registration metadata is relevant; executions in other cells are not.
    projected = research_tools_view({}, {}, scoped + [row for row in registrations if row not in scoped])
    reader = reader or _DetailReader(run_dir)
    related, coverage = {}, {}
    for key in ('versions','invocations','llm_calls','child_links','events'):
        source = projected[key] if key != 'events' else [_compact(row) for row in scoped]
        items, rejected = [], 0
        for row in source[-DETAIL_LIMIT:]:
            row = dict(row, evidence_scope='selected_journal')
            try:
                if key == 'versions':
                    bundle = _bundle(run_dir, row['id'], _reader=reader)
                    row.update(verified=True, name=bundle['manifest'].get('name'), description=bundle['manifest'].get('description'),
                        evidence_scope='selected_journal_and_immutable_artifact')
                elif key in ('invocations','llm_calls') and row.get('receipt_id'):
                    if len(action_cells.get(row.get('action_id'),set())) > 1:
                        raise ValueError('Artifact action has conflicting cell owners')
                    artifact = artifact_detail(run_dir, row['receipt_id'], scoped, _reader=reader)
                    row.update(verified=True, evidence_scope='selected_journal_and_immutable_artifact')
                    if key == 'invocations':
                        payload = artifact['payload']
                        row['question'] = _text(payload.get('question'),8000)
                        row['requested_limits'] = {key:_job_number(_obj(_obj(payload.get('receipt')).get('limits')).get(key))
                            for key in ('cpu_seconds','wall_seconds')}
                        row['resources'] = {key:_job_number(_obj(_obj(payload.get('receipt')).get('resources')).get(key))
                            for key in ('cpu_seconds','wall_seconds')}
                items.append(row)
            except (OSError, ValueError, KeyError, TypeError):
                rejected += 1
        related[key] = items
        total = projected['summary'].get({'versions':'versions','invocations':'invocations','llm_calls':'llm_calls','child_links':'linked_records'}.get(key), len(source))
        coverage[key] = dict(recorded=total, visible=len(items), omitted=max(0,total-DETAIL_LIMIT), verification_failed=rejected)
    lifecycle = list({(row.get('phase'),row.get('cell_id'),row.get('tool_id'),row.get('receipt_id')):_compact(row)
        for row in scoped if row.get('phase') in ('replay_result','adopted','post_adoption_attempt','post_adoption_use')}.values())
    related['lifecycle_events'] = [dict(row,evidence_scope='selected_journal') for row in lifecycle[-DETAIL_LIMIT:]]
    coverage['lifecycle_events'] = dict(recorded=len(lifecycle),visible=len(related['lifecycle_events']),omitted=max(0,len(lifecycle)-DETAIL_LIMIT),verification_failed=0)
    bindings = [{**value,'id':key} for key,value in _job_bindings(checkpoint).items() if _obj(value.get('owner')).get('cell_id') == ident]
    collected = _obj(_obj(checkpoint.get('research_tools')).get('collected_jobs'))
    related['jobs'] = [_job_row(run_dir, dict(binding,collected=binding['id'] in collected)) for binding in bindings[-DETAIL_LIMIT:]]
    for row in related['jobs']:
        row['evidence_scope'] = 'checkpoint_and_latest_saved_job_status'
    coverage['jobs'] = dict(recorded=len(bindings),visible=len(related['jobs']),omitted=max(0,len(bindings)-DETAIL_LIMIT),verification_failed=sum(row['status']=='unknown' for row in related['jobs']))
    candidates = [record for record in _committed_followups(checkpoint) if any(
        isinstance(card,dict) and card.get('cell_id') == ident for card in _obj(record.get('exposures')).get('cards', []))]
    related['followups'] = []; rejected = 0
    for record in candidates[-DETAIL_LIMIT:]:
        try:
            related['followups'].append(_cell_followup(run_dir,record,ident,{revision['id'] for revision in history},scoped,reader,
                set(_ids(_obj(checkpoint.get('research_tools')).get('registered')))))
        except (OSError,ValueError,KeyError,TypeError):
            rejected += 1
    coverage['followups'] = dict(recorded=len(candidates),visible=len(related['followups']),omitted=max(0,len(candidates)-DETAIL_LIMIT),verification_failed=rejected)
    from .research_exchange import deliveries
    related['shared_observations'], coverage['shared_observations'] = deliveries(run_dir,ident,checkpoint,rows,reader)
    return related, coverage


def cell_detail(run_dir, ident, checkpoint, rows):
    """Only retained journal/checkpoint IDs grant visibility; never discover by files."""
    cells = _cells_view(checkpoint, rows)
    _continuations(checkpoint,cells)
    if ident not in cells:
        raise KeyError('Cell is not recorded in the selected journal/checkpoint lineage')
    genesis = _read_object(run_dir, 'cells/genesis', ident, 256*1024)
    if genesis.get('schema') != 'sciel-research-cell/1' or not isinstance(genesis.get('question'),str):
        raise ValueError('Unsupported research cell genesis')
    head = cells[ident]['head_revision']
    history, seen, ordinal, byte_count = [], set(), None, 0
    cursor = head
    while cursor is not None and len(history) < LIMIT and byte_count < 4*1024*1024:
        if cursor in seen:
            raise ValueError('Cyclic cell history')
        seen.add(cursor)
        body = _read_object(run_dir, 'cells/revisions', cursor, 256*1024)
        if (body.get('schema') != 'sciel-research-cell-revision/1' or body.get('cell_id') != ident
                or type(body.get('ordinal')) is not int or body['ordinal'] < 1
                or (ordinal is not None and body['ordinal'] != ordinal-1)):
            raise ValueError('Cell revision lineage mismatch')
        history.append(dict(id=cursor,**body));byte_count += len(_canonical(body))
        ordinal, cursor = body['ordinal'], body.get('previous_revision')
        if cursor is None and ordinal != 1:
            raise ValueError('Cell history ended before its first revision')
        if cursor is not None and (not isinstance(cursor,str) or not HASH.fullmatch(cursor)):
            raise ValueError('Invalid cell predecessor')
    summary = _enrich_cells({ident:cells[ident]}, _events(rows), checkpoint)[ident]
    research_state = summary.get('research_state')
    reader = _DetailReader(run_dir)
    terminal_decision = _terminal_decision(ident, checkpoint, history, research_state, reader)
    related, coverage = _cell_related(run_dir, ident, checkpoint, rows, history, reader=reader)
    latest_question = next((row['question'] for row in reversed(related['invocations']) if row.get('question')),None)
    current_question = _obj(summary.get('active_decision')).get('question') or _obj(research_state).get('question') or latest_question
    return dict(id=ident,kind='cell',verified=True,genesis=genesis,head_revision=head,
        revision_history=history,history_truncated=cursor is not None,next_revision_id=cursor,
        summary=summary, related=related, related_coverage=coverage, research_state=research_state,
        terminal_decision=terminal_decision,
        active_decision=summary.get('active_decision'),
        current_question=current_question,
        question_scope=('Pending model decision; uncommitted' if _obj(summary.get('active_decision')).get('question') else
            'Recorded research plan' if _obj(research_state).get('question') else
            'Last verified experiment question' if latest_question else 'Scheduling question only'),
        detail_scope='Cell genesis and retained revisions are verified. Related metadata is cell/action scoped; bodies must pass immutable-artifact bindings. Prepared context is not delivery; replay is not measured benefit.',
        history_scope='Newest retained revisions, limited to 200 records or 4 MiB. Revision stages record protocol transitions, not measured task benefit.')
