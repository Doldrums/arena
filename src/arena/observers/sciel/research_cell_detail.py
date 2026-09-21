"""Verified cell history and related evidence; never execute research code."""
from __future__ import annotations

import hashlib

from .research_cell_state import (_cell_events, _cells_view, _committed_followups,
                                  _continuations, _enrich_cells, _sharing)
from .research_tool_artifacts import (_DetailReader, _bundle, _comparison_assessment,
                                      _read_object, artifact_detail)
from .research_tool_jobs import _job_bindings, _job_row
from .research_tool_projection import research_tools_view
from .research_tool_records import (DETAIL_LIMIT, HASH, LIMIT, _canonical, _compact,
                                    _events, _ids, _job_number, _obj, _text)


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
    if not isinstance(card, dict) or card.get('schema') not in ('sciel-research-check/4', 'sciel-research-check/5'):
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
            if card.get('schema') == 'sciel-research-check/5' and card.get('comparison_assessment') != _comparison_assessment(
                    run_dir=None, ident=source['receipt_id'], payload=record, reader=reader):
                raise ValueError('Decision comparison assessment differs from its saved invocation')
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
    _sharing(checkpoint,cells)
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
