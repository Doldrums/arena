"""Research-tool overview: metadata only, with lazy artifact verification."""
from __future__ import annotations

from .research_cell_state import (_cells_view, _configuration, _continuations,
                                  _enrich_cells, _sharing)
from .research_tool_jobs import _job_base
from .research_tool_records import HASH, LIMIT, _compact, _events, _obj


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
            children=[dict(program_id=row['child_program_id'],island_id=row.get('island_id'),link_kind=row.get('link_kind'),receipt_ids=row.get('receipt_ids',[]),
                **{key:row[key] for key in ('link_basis','candidate_source_sha256','canonical_evaluation_id',
                    'evaluation_id','candidate_invocation_id','scope') if key in row}) for row in links[-LIMIT:]])
    actual = [row for row in invocations.values() if row['actual_execution']]
    cells = _cells_view(checkpoint, rows)
    continuations = _continuations(checkpoint,cells)
    sharing = _sharing(checkpoint,cells)
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
        jobs=_job_base(checkpoint,configured),continuations=continuations,sharing=sharing,
        llm_calls=list(calls.values())[-LIMIT:],contexts=list(contexts.values())[-LIMIT:],
        child_links=list(children.values())[-LIMIT:],events=[_compact(row) for row in events[-LIMIT:]],
        coverage=dict(limit=LIMIT,scope='Selected Engine journal lineage after checkpoint restoration; artifact bodies load only when opened.',
            omitted_versions=max(0,len(versions)-LIMIT),omitted_invocations=max(0,len(invocations)-LIMIT),omitted_cells=max(0,len(cells)-LIMIT)),
        notes=['Shared availability, prepared context and actual execution are different observations.',
            'context_prepared records Snapshot preparation, not proven delivery to an LLM prompt.',
            'A canonical producer link identifies the saved source and evaluator record. Observation links record exposure before generation; historical links without a basis remain recorded associations. None establishes causal utility or gives tool reward credit.',
            'Tool LLM charges are already included in Engine spend. CPU observations exclude Docker daemon and VM overhead.'])
