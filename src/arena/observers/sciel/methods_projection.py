"""Assemble the method-registry dashboard from verified saved records."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib

from .methods_records import (HASH, MAX_ARTIFACT, MAX_PROJECTION_BYTES,
    MAX_PROJECTION_OBJECTS, clean, digest, number, obj, observability,
    registered_artifacts, seq, signature, validate_shape)


def build_methods_projection(view, run_id):
    rows, warnings = view.rows()
    registered = registered_artifacts(rows)
    artifacts, methods, revisions, labs, statuses, events = {}, {}, {}, {}, {}, []
    identity, started_at, registry_started_at = {}, None, None
    artifact_meta, method_meta = {}, {}
    # Preselect from the newest records, so an old, large request history
    # cannot consume unbounded memory or hide the newest visible activity.
    allowed_objects, projection_bytes, omitted_objects = set(), 0, 0
    for row in reversed(rows):
        data, kind = row['data'], row.get('kind')
        directory = ('methods' if kind == 'method_registered' else 'revisions'
            if kind in ('lab_created', 'lab_revised') else 'artifacts'
            if kind == 'artifact_registered' and data.get('kind') not in
                ('proposal_context', 'solution_source', 'budget_checkpoint') else None)
        ident = data.get('revision_id') if directory == 'revisions' else data.get('id')
        if directory is None or not isinstance(ident, str) or not HASH.fullmatch(ident):
            continue
        key = (directory, ident)
        if key in allowed_objects:
            continue
        stamp = signature(view.registry / directory / (ident + '.json'))
        size = stamp[1] if stamp else 0
        if (len(allowed_objects) >= MAX_PROJECTION_OBJECTS or size > MAX_ARTIFACT
                or projection_bytes + size > MAX_PROJECTION_BYTES):
            omitted_objects += 1
            continue
        projection_bytes += size
        allowed_objects.add(key)
    if omitted_objects:
        warnings.append(f'Display scan bound reached: {omitted_objects} older/oversized objects omitted. Counts describe loaded records, not complete history.')

    def revision_unavailable(data, row):
        # New events identify the lab independently of their artifact. For
        # legacy events that omit it, any existing lab could be affected;
        # do not present last-known membership as verified current state.
        named = data.get('lab_id')
        affected = [named] if isinstance(named, str) else list(labs)
        for lab_id in affected:
            old = labs.get(lab_id, {})
            last = old.get('last_verified_revision')
            if old.get('revision_available', True) and old.get('revision_id'):
                last = dict(id=old['revision_id'], number=old.get('revision_number'),
                    active_methods=old.get('active_methods', []),
                    active_adapters=old.get('active_adapters', []))
            labs[lab_id] = dict(old, id=lab_id, status=old.get('status', 'trial'),
                mode=old.get('mode', data.get('mode')), agenda=old.get('agenda', data.get('agenda')),
                budget_account=old.get('budget_account'), revision_available=False,
                revision_id=data.get('revision_id') if named else None,
                announced_revision_id=data.get('revision_id'),
                revision_number=(old.get('revision_number', 0) + 1
                    if named and type(old.get('revision_number', 0)) is int else None),
                revision=None, last_verified_revision=last, revision_at=row.get('at'),
                active_methods=[], active_adapters=[], evidence_refs=[], capabilities={},
                current_stage='revision_unavailable', last_activity_at=row.get('at'))
    for row in rows:
        kind, data = row.get('kind'), row['data']
        ident = data.get('id')
        try:
            validate_shape(data)
            if kind == 'coordinator_identity':
                identity, started_at = obj(data.get('identity')), row.get('at')
                registry_started_at = data.get('started_at')
            elif kind == 'method_registered':
                if ('methods', ident) not in allowed_objects:
                    continue
                methods[ident] = validate_shape(view._object('methods', ident))
                method_meta[ident] = row
                statuses[ident] = dict(status='draft', evidence_refs=[])
            elif kind == 'method_status' and ident in methods:
                statuses[ident] = dict(status=data.get('status'), evidence_refs=list(dict.fromkeys(
                    statuses[ident]['evidence_refs'] + seq(data.get('evidence_refs')))))
            elif kind in ('lab_created', 'lab_revised'):
                revision_id = data.get('revision_id')
                if ('revisions', revision_id) not in allowed_objects:
                    revision_unavailable(data, row)
                    continue
                revision = validate_shape(view._object('revisions', revision_id))
                revisions[revision_id] = revision
                lab_id = revision.get('lab_id')
                if not isinstance(lab_id, str):
                    raise ValueError('revision has no lab identity')
                if data.get('lab_id', lab_id) != lab_id:
                    raise ValueError('announced lab differs from revision')
                old = labs.get(lab_id, {})
                labs[lab_id] = dict(old, id=lab_id, mode=data.get('mode', old.get('mode')),
                    agenda=data.get('agenda', old.get('agenda')), status=old.get('status', 'trial'),
                    created_at=row.get('at') if kind == 'lab_created' else old.get('created_at'),
                    revision_at=row.get('at'),
                    revision_id=revision_id,
                    # A named announcement still advances the version even
                    # when its artifact was unavailable. An unidentified
                    # legacy gap leaves the ordinal unknown, not reset to 1.
                    revision_number=(old.get('revision_number', 0) + 1
                        if type(old.get('revision_number', 0)) is int else None),
                    revision_available=True, announced_revision_id=revision_id,
                    last_verified_revision=None,
                    active_methods=seq(revision.get('active_methods')), active_adapters=seq(revision.get('active_adapters')),
                    budget_account=revision.get('budget_account'), capabilities=obj(revision.get('capabilities')),
                    evidence_refs=seq(revision.get('evidence_refs')), last_activity_at=row.get('at'),
                    current_stage=revision.get('reason'), revision=revision)
            elif kind == 'lab_lifecycle' and data.get('lab_id') in labs:
                labs[data['lab_id']].update(status=data.get('status'), current_stage=data.get('reason'))
            elif kind == 'artifact_registered':
                artifact_meta[ident] = row
                # Large saved prompts are fetched only when opened.
                if data.get('kind') not in ('proposal_context', 'solution_source', 'budget_checkpoint'):
                    if ('artifacts', ident) not in allowed_objects:
                        continue
                    artifacts[ident] = view.artifact(data.get('kind'), ident, registered)
        except (KeyError, ValueError, OSError, UnicodeError, RecursionError, TypeError):
            if kind in ('lab_created', 'lab_revised'):
                revision_unavailable(data, row)
            warnings.append(f'Unavailable {kind} artifact at registry record {row.get("seq")}.')
        if kind not in ('artifact_registered', 'funding_state'):
            events.append(dict(id=row.get('id'), seq=row.get('seq'), at=row.get('at'), kind=kind, data=data))
    by_kind = lambda k: [(i, b) for i, b in artifacts.items() if registered.get(i) == k]
    calls = dict(by_kind('call_receipt'))
    invoked = [(i, b) for i, b in calls.items() if obj(b.get('result')).get('dispatch_status') == 'invoked']
    invocation_counts = Counter(obj(b.get('result')).get('method_id') for _, b in invoked)
    experiments = []
    for ident, body in by_kind('experiment'):
        plan = artifacts.get(body.get('plan_id'), {})
        metric = obj(plan.get('criterion')).get('metric')
        def score(arm):
            values = [number(obj(obj(r.get('measurement')).get('metrics')).get(metric))
                for r in seq(obj(body.get('results')).get(arm)) if isinstance(r, dict)]
            return sum(values) / len(values) if values and all(v is not None for v in values) else None
        def native_score(arm):
            values = [number(obj(obj(r.get('measurement')).get('observables')).get('sum_radii',
                obj(obj(r.get('measurement')).get('metrics')).get('sum_radii')))
                for r in seq(obj(body.get('results')).get(arm)) if isinstance(r, dict)]
            return sum(values) / len(values) if values and all(v is not None for v in values) else None
        control_score, treatment_score = score('control'), score('treatment')
        native_control, native_treatment = native_score('control'), native_score('treatment')
        task_schema = obj(plan.get('task')).get('schema') or obj(identity.get('task')).get('schema')
        native_metric = ('sum_radii' if metric == 'combined_score'
            and task_schema == 'sciel-method-circle26-task/1'
            and (native_control is not None or native_treatment is not None) else None)
        experiments.append(dict(body, id=ident, at=artifact_meta[ident].get('at'),
            created_at=artifact_meta[ident].get('at'), registration_seq=artifact_meta[ident].get('seq'),
            proposal_id=plan.get('proposal_id') if registered.get(plan.get('proposal_id')) == 'proposal_receipt' else None,
            lab_id=plan.get('lab_id'), purpose=plan.get('purpose'), question=plan.get('question'),
            scope=plan.get('scope'), treatment=seq(plan.get('treatment')), control=seq(plan.get('control')),
            criterion=plan.get('criterion'), metric=metric, control_score=control_score, treatment_score=treatment_score,
            native_metric=native_metric,
            native_control_score=native_control, native_treatment_score=native_treatment,
            display_metric=native_metric or metric,
            display_control_score=native_control if native_metric else control_score,
            display_treatment_score=native_treatment if native_metric else treatment_score,
            effect=body.get('mean_effect'), passed=body.get('rule_passed'), source_plan=plan.get('source_plan')))
    proposals = []
    steps = [dict(r['data'], at=r.get('at')) for r in rows if r.get('kind') == 'episode_step'
        and isinstance(r['data'].get('lab_id'), str) and isinstance(r['data'].get('proposal_id'), str)]
    for ident, body in by_kind('proposal_receipt'):
        if not body.get('context_id'):
            continue
        call = calls.get(body.get('call_receipt_id'), {})
        step = next((s for s in steps if s.get('proposal_id') == ident), {})
        refusal = artifacts.get(step.get('refusal_id'), {})
        proposals.append(dict(id=ident, lab_id=body.get('lab_id'), at=artifact_meta[ident].get('at'),
            index=step.get('index'), status='refused' if refusal else ('invalid' if body.get('error') else step.get('status') or call.get('status')),
            kind=obj(body.get('draft')).get('kind'), error=body.get('error') or refusal.get('error'),
            diagnostic=refusal.get('diagnostic') or body.get('diagnostic'), novelty=refusal.get('novelty'),
            method_id=step.get('method_id'), experiment_id=step.get('experiment_id'), cost=obj(call.get('actual')).get('dollars'),
            actual=call.get('actual'), call_receipt_id=body.get('call_receipt_id'),
            dispatch_status=(obj(call.get('result')).get('dispatch_status') or
                obj(body.get('diagnostic')).get('dispatch_status') or
                ('not_dispatched' if body.get('error') == 'proposal_not_dispatched' else None)),
            source_read=body.get('source_read'), evidence_refs=body.get('evidence_refs')))
    transfers = []
    for ident, body in by_kind('adoption'):
        at = artifact_meta[ident].get('at')
        next_use = next((e for e in experiments if e.get('lab_id') == body.get('lab_id')
            and e.get('at', '') > at and body.get('method_id') in seq(e.get('invoked_methods'))), {})
        transfers.append(dict(body, id=ident, kind='adoption', at=at, revision_id=body.get('new_revision'),
            next_use_experiment_id=next_use.get('id'), next_use_at=next_use.get('at')))
    for ident, body in by_kind('solution_transfer'):
        transfers.append(dict(body, id=ident, kind='solution_transfer', at=artifact_meta[ident].get('at')))
    tools = []
    for ident, body in methods.items():
        manifest = obj(body.get('manifest'))
        is_solution_bundle = obj(manifest.get('protocol')).get('permanent_toolbox_method') is False
        evidence = [artifacts.get(ref, {}) for ref in statuses[ident]['evidence_refs']]
        tools.append(dict(id=ident, **{k: manifest.get(k) for k in
            ('name', 'kind', 'author_lab', 'parents', 'dependencies', 'scope', 'protocol', 'entrypoint', 'resources')},
            created_at=method_meta[ident].get('at'), registration_seq=method_meta[ident].get('seq'),
            **statuses[ident], source_sha256=digest(obj(body.get('files'))),
            record_kind='solution_execution_bundle' if is_solution_bundle else 'reusable_method',
            provenance='solution_execution_adapter' if is_solution_bundle else
                'common_toolbox' if ident in seq(identity.get('common_methods')) else 'lab_created',
            invocations=invocation_counts[ident], evidence=evidence,
            adopted_by=[t.get('lab_id') for t in transfers if t.get('kind') == 'adoption' and t.get('method_id') == ident],
            active_in=[l['id'] for l in labs.values() if ident in l['active_methods'] or ident in l['active_adapters']],
            replayed=any(e.get('level') == 'replayed' for e in evidence)))
    execution_bundles = [t for t in tools if t['record_kind'] == 'solution_execution_bundle']
    tools = [t for t in tools if t['record_kind'] == 'reusable_method']
    solutions = []
    experiments_by_id = {e['id']:e for e in experiments}
    for ident, body in by_kind('solution'):
        program, evaluation = obj(body.get('program')), obj(body.get('evaluation'))
        call = calls.get(body.get('call_receipt_id'), {})
        execution = obj(call.get('result'))
        bundle = methods.get(execution.get('method_id'), {})
        experiment = experiments_by_id.get(body.get('experiment_id'), {})
        code = program.get('code')
        # Quality comes from an admitted Program and its actual bound
        # evaluation, never from arbitrary method-state trial measurements.
        if (not isinstance(program.get('id'), str) or not isinstance(code, str)
                or number(program.get('score')) is None or program.get('score') != evaluation.get('score')
                or evaluation.get('ok') is not True or experiment.get('valid_treatment') is not True
                or execution.get('dispatch_status') != 'invoked' or execution.get('status') != 'ok'
                or execution.get('plan_id') != experiment.get('plan_id')
                or body.get('call_receipt_id') not in seq(experiment.get('invocation_refs'))
                or execution.get('source_sha256') != digest(obj(bundle.get('files')))
                or obj(bundle.get('files')).get('candidate.py') != code):
            warnings.append('A solution record is missing its bound valid Program/evaluation; omitted from task quality.')
            continue
        cases = obj(evaluation.get('cases'))
        native = number(cases.get('sum_radii'))
        # Link only explicit saved bindings, never program-name conventions
        # or whichever proposal happened nearest in wall-clock time.
        proposal_ids = {s['proposal_id'] for s in steps if s.get('solution_id') == ident
            and s.get('lab_id') == body.get('lab_id')
            and registered.get(s['proposal_id']) == 'proposal_receipt'}
        if experiment.get('lab_id') == body.get('lab_id') and experiment.get('proposal_id'):
            proposal_ids.add(experiment['proposal_id'])
        solutions.append(dict(id=ident, record_kind='solution', program_id=program['id'],
            lab_id=body.get('lab_id'), at=artifact_meta[ident].get('at'),
            created_at=artifact_meta[ident].get('at'), registration_seq=artifact_meta[ident].get('seq'),
            proposal_id=next(iter(proposal_ids)) if len(proposal_ids) == 1 else None,
            experiment_id=body.get('experiment_id'), call_receipt_id=body.get('call_receipt_id'),
            method_id=execution.get('method_id'), score=program['score'], cases=cases,
            native_metric='sum_radii' if native is not None else None, native_score=native,
            valid=True, source_sha256=hashlib.sha256(code.encode()).hexdigest(),
            confirmed=obj(body.get('cascade')).get('confirmed'), evaluation_protocol=body.get('evaluation_protocol')))
    direction = obj(identity.get('task')).get('direction', 'max')
    best_solution = (min if direction == 'min' else max)(solutions,
        key=lambda s:s['score'], default=None)
    quality = dict(best_solution_id=best_solution.get('id') if best_solution else None,
        best_score=best_solution.get('score') if best_solution else None,
        best_native_metric=best_solution.get('native_metric') if best_solution else None,
        best_native_score=best_solution.get('native_score') if best_solution else None,
        metric=obj(identity.get('solution_task')).get('metric') or obj(identity.get('task')).get('metric'),
        direction=direction, valid_solutions=len(solutions),
        scope='Observed valid Program evaluations only. Method-state trials are separate; no independent-repeat or held-out benefit claim.')
    budget, budget_warnings = view.budget()
    warnings.extend(budget_warnings)
    claims = [dict(b, id=i, at=artifact_meta[i].get('at')) for i, b in by_kind('knowledge_claim')]
    for lab in labs.values():
        local_steps = [s for s in steps if s.get('lab_id') == lab['id']]
        lab.update(steps=len(local_steps), experiments=sum(e.get('lab_id') == lab['id'] for e in experiments),
            tools=sum(t.get('author_lab') == lab['id'] for t in tools),
            solutions=sum(s.get('lab_id') == lab['id'] for s in solutions),
            claims=sum(any(m in lab['active_methods'] for m in seq(c.get('methods'))) for c in claims),
            budget=budget['accounts'].get(lab['budget_account'], {}))
        if local_steps:
            lab.update(last_activity_at=local_steps[-1].get('at'), current_stage=local_steps[-1].get('status'))
        local_experiments = [e for e in experiments if e.get('lab_id') == lab['id']]
        if local_experiments:
            latest = local_experiments[-1]
            lab['last_outcome'] = dict(experiment_id=latest['id'], passed=latest.get('passed'),
                effect=latest.get('effect'), at=latest.get('at'), purpose=latest.get('purpose'))
            if latest.get('at', '') >= (lab.get('last_activity_at') or '') or not local_steps:
                lab.update(last_activity_at=latest.get('at'), current_stage=(
                    'Replay completed' if latest.get('purpose') == 'replay' else 'Evaluation completed'))
        pending = [r for r in budget['current_operations'] if r.get('account_id') == lab['budget_account']]
        if pending:
            lab['current_stage'] = pending[-1]['category'] + (' · outcome unknown' if pending[-1]['status'] == 'unknown' else '')
        lab['current_operations'] = pending
        if lab.get('revision_available') is False:
            lab['current_stage'] = 'revision_unavailable'
    runtime = view.runtime(identity, registry_started_at)
    report = view.terminal_report(rows, identity, registered)
    modified = view.journal.stat().st_mtime
    status = runtime['status'] if runtime['available'] else 'historical'
    if report and not runtime['available']:
        status = report['status']
    summary = dict(labs=len(labs), methods=len(tools), released=sum(t['status'] == 'released' for t in tools),
        solutions=len(solutions), execution_bundles=len(execution_bundles),
        experiments=len(experiments), proposals=len(proposals), invocations=len(invoked), claims=len(claims),
        adoptions=sum(t['kind'] == 'adoption' for t in transfers),
        unknown=len(budget['unknown_reservations']), failed_calls=sum(c.get('status') == 'failed' for c in calls.values()),
        history_complete=not omitted_objects and not warnings)
    observation = observability(artifacts=artifacts, registered=registered, metadata=artifact_meta,
        labs=labs, statuses=statuses, rows=rows, experiments=experiments, proposals=proposals,
        solutions=solutions, complete=summary['history_complete'])
    classification = report.get('classification') if report else None
    if classification is None:
        try:
            classification = obj(view._json(view.root / 'run-config.json')).get('claim')
        except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
            pass
    if classification not in ('local_episode', 'bounded_arm', 'continuous_run'):
        classification = None
    run_policy = dict(classification=classification, **{key:identity[key] for key in
        ('max_steps', 'calendar_seconds', 'storage_bytes', 'capacity_wait_seconds', 'resources') if key in identity})
    run_name = view.root.name
    if run_name == 'run' and view.root.parent.parent.name == 'units':
        run_name = view.root.parent.parent.parent.name + ' · ' + view.root.parent.name
    run = dict(id=run_id, kind='methods', name=run_name, label=run_name, status=status, classification=classification,
        status_reason=report.get('reason') if report and not runtime['available'] else runtime.get('reason'),
        terminal_source=report.get('source') if report else None, started_at=started_at,
        last_modified=datetime.fromtimestamp(modified, timezone.utc).isoformat(),
        task=obj(identity.get('task')).get('schema', 'Research practices'), iteration=len(steps),
        cost_total=budget['spent']['dollars'], best_score=quality['best_score'])
    visible_versions = tools[-500:] + execution_bundles[-200:]
    edge_limit = 2000
    parent_edges, dependency_edges = [], []
    edge_counts = dict(parents=0, dependencies=0)
    for version in visible_versions:
        for key, edges in (('parents', parent_edges), ('dependencies', dependency_edges)):
            refs = seq(version.get(key))
            edge_counts[key] += len(refs)
            edges.extend(dict(source=ref, target=version['id']) for ref in refs[:max(0, edge_limit-len(edges))])
    storage = dict(kind='content_addressed_registry', label='Immutable method registry',
        history_scope='One append-only run journal across all labs; inactive and superseded versions remain in history.',
        selection='Lab revisions explicitly select active method and adapter versions.',
        coordinates=None,
        active_versions=[dict(lab_id=lab['id'], revision_id=lab['revision_id'],
            membership_known=lab.get('revision_available', True),
            last_verified_revision=lab.get('last_verified_revision'),
            method_ids=lab['active_methods'][:500], adapter_ids=lab['active_adapters'][:500],
            omitted_methods=max(0, len(lab['active_methods'])-500),
            omitted_adapters=max(0, len(lab['active_adapters'])-500)) for lab in labs.values()],
        parent_edges=parent_edges, dependency_edges=dependency_edges,
        omitted_parent_edges=edge_counts['parents']-len(parent_edges),
        omitted_dependency_edges=edge_counts['dependencies']-len(dependency_edges),
        edge_scope='Edges of displayed versions; source versions may be outside the displayed window. Dependencies declare source inclusion, not invocation.',
        history_complete=summary['history_complete'],
        display_scope='Active lists and counts reflect the loaded journal projection; display bounds do not remove registry history.')
    data = dict(schema='sciel-method-dashboard/1', identity=identity, registry_started_at=registry_started_at, summary=summary, report=report, run_policy=run_policy,
        storage=storage, observability=observation,
        labs=list(labs.values()), tools=tools[-500:], experiments=experiments[-200:], claims=claims[-200:],
        execution_bundles=execution_bundles[-200:], solutions=solutions[-200:], quality=quality,
        proposals=proposals[-200:], transfers=transfers[-200:], events=events[-200:], budget=budget,
        steps=steps[-200:], receipts=[dict(id=i, category=b.get('category'), status=b.get('status'),
            actual=b.get('actual'), method_id=obj(b.get('result')).get('method_id'),
            plan_id=obj(b.get('result')).get('plan_id'), dispatch_status=obj(b.get('result')).get('dispatch_status'),
            dependency_use_attested=obj(b.get('result')).get('dependency_use_attested')) for i,b in list(calls.items())[-200:]],
        display_limits=dict(tools=500, execution_bundles=200, solutions=200, experiments=200, claims=200, proposals=200, transfers=200, events=200),
        projection=dict(loaded_objects=len(allowed_objects),loaded_bytes=projection_bytes,omitted_objects=omitted_objects,
            max_bytes=MAX_PROJECTION_BYTES,max_objects=MAX_PROJECTION_OBJECTS,newest_first=True,history_complete=not omitted_objects and not warnings),
        interpretation='Read-only saved records. Source inclusion and dependencies are not evidence of invocation; release is not evidence of general benefit.')
    return clean(dict(schema='sciel-dashboard/1', kind='methods', run=run, runtime=runtime,
        timing=dict(elapsed_seconds=runtime.get('elapsed_seconds'), session=dict(elapsed_seconds=runtime.get('elapsed_seconds'))), methods=data, warnings=warnings[:50]))
