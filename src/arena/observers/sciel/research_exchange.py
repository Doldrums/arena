"""Read-only cross-island delivery proof, separate from method use or benefit."""
import hashlib
import json

MARKER = 'SHARED_RESEARCH_OBSERVATIONS_JSON:\n'
SCHEMA = 'sciel-shared-research-observations/1'


def _measurement(value, source):
    """Verify full observations or exact historical/paired saved projections."""
    output=source.get('receipt',{}).get('output')
    expected={'output':{'observations':output.get('observations') if isinstance(output,dict) else None},
        'error':source.get('result',{}).get('error')}
    from .compat.result_projection import verify_projection
    verify_projection(value, expected)


def _history(checkpoint, cell_id, reader):
    from .research_tools import _obj
    saved = _obj(_obj(_obj(_obj(checkpoint.get('research_tools')).get('lifecycle')).get('cells')).get('cells'))
    cursor = _obj(saved.get(cell_id)).get('head_revision')
    revisions, references = set(), set()
    while cursor is not None:
        if cursor in revisions or len(revisions) >= 200:
            raise ValueError('Shared source history exceeds its read bound')
        revision = reader('cells/revisions',cursor,256*1024)
        if revision.get('schema') != 'sciel-research-cell-revision/1' or revision.get('cell_id') != cell_id:
            raise ValueError('Shared source revision belongs to another cell')
        revisions.add(cursor)
        references.update((item.get('kind'),item.get('id')) for item in revision.get('evidence',[]) if isinstance(item,dict))
        cursor = revision.get('previous_revision')
    return revisions, references


def deliveries(run_dir, cell_id, checkpoint, rows, reader, *, limit=20):
    from .research_tools import _events, _obj, artifact_detail
    from .compat.decision_projection import proposal_decision, authenticate_projection
    events = _events(rows)
    candidates = [row for row in events if row.get('phase') == 'shared_observations_delivered' and row.get('cell_id') == cell_id]
    result, rejected, awaiting, histories = [], 0, 0, {}
    for event in candidates[-limit:]:
        try:
            ids = {row.get('receipt_id') for row in events if row.get('phase') == 'llm_result'
                and row.get('action_id') == event.get('action_id') and row.get('attempt') == event.get('attempt')
                and row.get('cell_id') == cell_id}
            if not ids:
                awaiting += 1
                continue
            if len(ids) != 1:
                raise ValueError('No unique completed model request')
            proposal_id = next(iter(ids))
            proposal = artifact_detail(run_dir,proposal_id,rows,_reader=reader)
            payload = proposal['payload']; prompt = payload.get('prompt')
            if (proposal['kind'] != 'proposal' or not isinstance(prompt,str)
                    or hashlib.sha256(prompt.encode()).hexdigest() != event.get('prompt_sha256')
                    or payload.get('cell_id') != cell_id or payload.get('action_id') != event.get('action_id')
                    or payload.get('attempt') != event.get('attempt') or MARKER not in prompt
                    or _obj(payload.get('target_binding')).get('candidate_id') != event.get('recipient_candidate_id')):
                raise ValueError('Shared observations differ from the saved recipient prompt')
            data = json.JSONDecoder().raw_decode(prompt.split(MARKER,1)[1])[0]
            if (not isinstance(data,dict) or data.get('schema') != SCHEMA
                    or not isinstance(data.get('entries'),list) or len(data['entries']) > 32
                    or type(data.get('total_checks')) is not int or data['total_checks'] < 0
                    or type(data.get('omitted_count')) is not int or data['omitted_count'] < 0
                    or data['total_checks'] != len(data['entries'])+data['omitted_count']):
                raise ValueError('Invalid shared observation view')
            expected = []
            for entry in data['entries']:
                if not isinstance(entry,dict):
                    raise ValueError('Invalid shared observation entry')
                origin = artifact_detail(run_dir,entry.get('receipt_id'),rows,_reader=reader)
                source = origin['payload']; binding = _obj(source.get('target_binding'))
                source_cell = entry.get('cell_id')
                if source_cell not in histories:
                    histories[source_cell] = _history(checkpoint,source_cell,reader)
                revisions, references = histories[source_cell]
                if (origin['kind'] != 'invocation' or source.get('cell_id') != source_cell
                        or source.get('tool_id') != entry.get('tool_id') or source.get('island_id') != entry.get('island_id')
                        or _obj(source.get('receipt')).get('dispatch_status')!='invoked'
                        or source.get('cell_revision_id') not in revisions
                        or ('tool_invocation',entry['receipt_id']) not in references
                        or binding.get('candidate_id') != entry.get('candidate_id')
                        or binding.get('target_source_sha256') != entry.get('target_source_sha256')
                        or source.get('question') != entry.get('question')
                        or _obj(source.get('inputs')).get('task') != entry.get('task')
                        or _obj(source.get('receipt')).get('resources') != entry.get('resources')
                        or _obj(source.get('result')).get('status') != entry.get('status')):
                    raise ValueError('Shared source binding differs from committed evidence')
                _measurement(entry.get('measurement'),source)
                decision = entry.get('decision')
                if decision is not None:
                    decision_id = decision['proposal_id']
                    if ('research_decision',decision_id) not in references:
                        raise ValueError('Shared interpretation is not committed')
                    saved = artifact_detail(run_dir,decision_id,rows,_reader=reader)['payload']
                    if saved.get('cell_id') != source_cell or saved.get('cell_revision_id') not in revisions:
                        raise ValueError('Shared interpretation belongs to another cell')
                    if entry['receipt_id'] not in saved.get('evidence_receipt_ids',[]):
                        raise ValueError('Shared interpretation does not cite this observation')
                    if decision.get('schema')=='sciel-research-decision/1':
                        authenticate_projection(decision,saved,decision_id)
                    else:
                        exact = proposal_decision(saved)
                        if decision.get('text_omitted') is not True or decision.get('conclusion')!=exact['conclusion']:
                            raise ValueError('Shared interpretation differs from saved response')
                expected.append(dict(receipt_id=entry['receipt_id'],source_cell_id=source_cell,
                    source_island_id=entry['island_id'],source_candidate_id=entry['candidate_id'],
                    decision_proposal_id=_obj(decision).get('proposal_id'),detail_omitted=entry.get('detail_omitted',False),
                    measurement_omitted=(_obj(entry.get('measurement')).get('omitted',False) or _obj(entry.get('measurement')).get('observations_state')=='all_omitted'),
                    measurement_projection=_obj(entry.get('measurement')).get('observations_state')))
            if any(event.get(key) != value for key,value in dict(evidence_schema=SCHEMA,total_checks=data['total_checks'],
                    source_islands=data.get('source_islands'),delivered=expected,omitted_count=data['omitted_count']).items()):
                raise ValueError('Delivery accounting differs from exact prompt')
            result.append(dict(verified=True,proposal_id=proposal_id,action_id=event.get('action_id'),
                prompt_sha256=event['prompt_sha256'],attempt=event['attempt'],timestamp=event.get('timestamp'),
                recipient_cell_id=cell_id,recipient_island_id=event.get('island_id'),
                recipient_candidate_id=event.get('recipient_candidate_id'),entries=data['entries'],
                total_checks=data['total_checks'],omitted_count=data['omitted_count'],
                scope='Exact saved prompt excerpt and committed source receipts. Model use, adoption and causal benefit are not established.'))
        except (OSError, ValueError, KeyError, TypeError, UnicodeError, RecursionError):
            rejected += 1
    return result, dict(recorded=len(candidates),visible=len(result),awaiting_model_receipt=awaiting,
        omitted=max(0,len(candidates)-limit),verification_failed=rejected)
