"""Committed cell, continuation and sharing metadata projections."""
from __future__ import annotations

import hashlib

from .research_tool_jobs import _job_bindings
from .research_tool_records import (DETAIL_LIMIT, EVENT_SCHEMA, HASH, LIMIT,
    _canonical, _compact, _ids, _obj, _research_state, _text)


def _continuations(checkpoint, cells):
    """Checkpoint scheduler metadata only; never infer execution from queue age."""
    state = _obj(_obj(checkpoint.get('research_tools')).get('continuations'))
    empty = dict(available=False, items=[], summary={}, scope='not_recorded')
    if not state:
        return empty
    if state.get('schema') not in ('sciel-research-continuations/1','sciel-research-continuations/2') or not isinstance(state.get('items'), dict) or type(state.get('next_sequence')) is not int or state['next_sequence'] < 0:
        return dict(empty, reason='Continuation state has an unsupported or malformed schema.')
    items, invalid, sequences = [], 0, set()
    for cell_id, item in state['items'].items():
        if (cell_id not in cells or not isinstance(cell_id,str) or not HASH.fullmatch(cell_id)
                or not isinstance(item,dict) or item.get('status') not in {'ready','waiting','closed'}
                or not isinstance(item.get('snapshot_artifact_id'),str) or not HASH.fullmatch(item['snapshot_artifact_id'])
                or any(type(item.get(key)) is not int or item[key] < 0 for key in ('queue_sequence','dispatch_count'))
                or item['queue_sequence'] >= state['next_sequence'] or item['queue_sequence'] in sequences
                or not isinstance(item.get('reason'),str)
                or (state['schema']=='sciel-research-continuations/2' and
                    item.get('last_work_kind') not in (None,'question','method_transfer'))
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
        if item.get('last_work_kind') in ('question','method_transfer'):
            row['last_work_kind'] = item['last_work_kind']
        sequences.add(item['queue_sequence'])
        items.append(row)
        cells[cell_id]['continuation'] = row
    items.sort(key=lambda row:(row['status']=='closed',row['queue_sequence'],row['cell_id']))
    summary={status:sum(row['status']==status for row in items) for status in ('ready','waiting','closed')}
    summary.update(total=len(items),omitted=max(0,len(items)-LIMIT),invalid=invalid)
    return dict(available=True,items=items[:LIMIT],summary=summary,scope='committed_checkpoint',
        note='Recorded queue state. Snapshot artifact content is not authenticated by this metadata projection.')


def _sharing(checkpoint, cells):
    """Display committed assignment metadata; lifecycle receipts prove execution."""
    state = _obj(_obj(checkpoint.get('research_tools')).get('sharing'))
    empty = dict(available=False, items=[], summary={}, scope='not_recorded')
    if not state:
        return empty
    if (state.get('schema') != 'sciel-research-sharing/1'
            or not isinstance(state.get('items'), dict)
            or not isinstance(state.get('waiting_methods'), dict)
            or type(state.get('next_sequence')) is not int or state['next_sequence'] < 0
            or state.get('last_queue') not in (None, 'question', 'sharing')):
        return dict(empty, reason='Sharing state has an unsupported or malformed schema.')
    items, invalid, sequences = [], 0, set()
    for ident, item in state['items'].items():
        if not isinstance(item, dict):
            invalid += 1
            continue
        required = ('tool_id', 'cell_id', 'snapshot_artifact_id', 'reference_receipt_id')
        optional = ('action_id', 'receipt_id')
        clock, jobs = item.get('completed_iteration'), item.get('job_ids')
        if (not isinstance(ident, str) or not HASH.fullmatch(ident)
                or any(not isinstance(item.get(k), str) or not HASH.fullmatch(item[k]) for k in required)
                or any(item.get(k) is not None and
                    (not isinstance(item[k], str) or not HASH.fullmatch(item[k])) for k in optional)
                or item['cell_id'] not in cells
                or item.get('stage') not in ('independent_replay', 'adopt_trial', 'use_again')
                or item.get('status') not in ('ready', 'waiting', 'completed')
                or not isinstance(item.get('reason'), str)
                or type(item.get('queue_sequence')) is not int
                or not 0 <= item['queue_sequence'] < state['next_sequence']
                or item['queue_sequence'] in sequences
                or not isinstance(jobs, list) or len(jobs) > 1 or _ids(jobs) != jobs
                or clock is not None and (type(clock) is not int or clock < 0)
                or (item.get('status') == 'completed') != (clock is not None)
                or hashlib.sha256(_canonical({k:item[k] for k in ('tool_id','stage','cell_id')})).hexdigest() != ident):
            invalid += 1
            continue
        row = {k:item[k] for k in (*required, 'stage', 'status', 'queue_sequence', 'job_ids')}
        row.update(id=ident, reason=_text(item['reason'],256),
            **{k:item.get(k) for k in (*optional, 'completed_iteration')},
            scope='committed_checkpoint', snapshot_verified=False)
        sequences.add(item['queue_sequence'])
        items.append(row)
        cells[item['cell_id']].setdefault('sharing', []).append(row)
    items.sort(key=lambda row:(row['status']=='completed',row['queue_sequence'],row['id']))
    waits = [dict(tool_id=ident,reason=reason) for ident,reason in state['waiting_methods'].items()
        if isinstance(ident,str) and HASH.fullmatch(ident) and reason=='no_recipient_yet']
    invalid += len(state['waiting_methods']) - len(waits)
    summary = {status:sum(row['status']==status for row in items) for status in ('ready','waiting','completed')}
    summary.update(total=len(items),omitted=max(0,len(items)-LIMIT),invalid=invalid,
        no_recipient_yet=len(waits),omitted_waiting_methods=max(0,len(waits)-LIMIT))
    for cell in cells.values():
        if 'sharing' in cell:
            cell['sharing_total'] = len(cell['sharing'])
            cell['sharing'] = cell['sharing'][-DETAIL_LIMIT:]
    return dict(available=True,items=items[:LIMIT],summary=summary,waiting_methods=waits[:LIMIT],
        last_queue=state.get('last_queue'),scope='committed_checkpoint',
        note='Recorded assignments only. Completion is not successful replay, adoption, later use, or measured benefit. Artifact bodies are verified when opened.')


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
        if contract in {'espalier-3.21', 'espalier-3.22', 'espalier-3.23', 'espalier-3.24', 'espalier-3.25', 'espalier-3.26', 'espalier-3.27', 'espalier-3.28','espalier-3.29','espalier-3.30','espalier-3.31','espalier-3.32','espalier-3.33', 'espalier-3.34', 'espalier-3.35', 'espalier-3.36', 'espalier-3.37', 'espalier-3.38', 'espalier-3.39', 'espalier-3.40', 'espalier-3.41', 'espalier-3.42', 'espalier-3.43', 'espalier-3.44', 'espalier-3.45', 'espalier-3.46', 'espalier-3.47','espalier-3.48', 'espalier-3.49', 'espalier-3.50', 'espalier-3.51', 'espalier-3.52', 'espalier-3.53', 'espalier-3.54', 'espalier-3.55', 'espalier-3.56', 'espalier-3.57', 'espalier-3.58', 'espalier-3.59'} and isinstance(config, dict) and 'research_tools' not in config:
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
