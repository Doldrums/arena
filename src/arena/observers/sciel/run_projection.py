"""Assemble an immutable run-content projection from already-read evidence."""
from .architecture import architecture, start_protocol
from .benchmarks import benchmark_for
from .effort import effort_basis
from .learning import learning_view
from .metric_display import project_metrics
from .parallel import parallel_view
from .population import population_view
from .reliability import reliability_view
from .research_tools import research_tools_view
from .result_history import result_history_view
from .run_lineage import (checkpoint_boundary, source_records, trial_records,
    lesson_records, project_lineage, saved_geometry)
from .run_values import (SCHEMA, _dict, _list, _number, _safe, _time, _iteration,
    _aux_key, _bootstrap_admission, _seed_record, _stop_detail)


def project_run(ident, path, *, rows, checkpoint, checkpoint_info, warnings,
                modified, name, engineering_only=False):
    boundary = checkpoint_boundary(checkpoint, rows)
    starts = [row for row in rows if row.get("event") == "run_start"]
    start = starts[-1] if starts else {}
    last_start = max((i for i, row in enumerate(rows) if row.get("event") == "run_start"), default=-1)
    ends = [row for row in rows[last_start + 1:] if row.get("event") == "run_end"]
    end = ends[-1] if ends else {}
    sources = source_records(checkpoint, rows)
    trials, evidence = trial_records(checkpoint, rows, sources)
    lessons = lesson_records(checkpoint, rows, boundary)
    metric = _dict(checkpoint.get("research")).get("metric")
    if not isinstance(metric, dict):
        metric = next((record.get("metric") for record in evidence.values() if isinstance(record.get("metric"), dict)), None)
    curves = []
    best = None
    observed_seed_score = None
    cost = None
    cost_source = "unavailable"
    cost_exact = False
    unknown_charge = (bool(checkpoint.get("_accounting_stopped_reason"))
        or any(_dict(receipt).get('unknown_cost') is True
               for receipt in _list(checkpoint.get('provider_recoveries'))))
    outcomes, bootstrap_candidates, aux_returns = {}, [], {}
    evaluations, iterations, remeasurements = None, None, None
    for index, row in enumerate(rows):
        if row.get("event") == "research":
            key = _aux_key(row)
            if row.get("phase") == "aux_start":
                aux_returns.pop(key, None)
            elif row.get("phase") == "aux_result" and _number(row.get("cost")) is not None and row["cost"] >= 0:
                aux_returns[key] = row.get("call_index")
            elif (row.get("phase") == "aux_stopped" and row.get("error_type") == "LLMError"
                    and row.get("stage") != "response" and row.get("generation_returned") is not True
                    and row.get("current_call_cost_unknown") is not False
                    and _number(row.get("cost")) is None):
                matched = key in aux_returns and (row.get("call_index") is None
                    or row["call_index"] == aux_returns[key])
                if not matched:
                    unknown_charge = True
        if row.get("event") == "research" and row.get("phase") == "outcome":
            record = _dict(row.get("evidence"))
            research_id = row.get("experiment_id")
            if isinstance(research_id, str) and record.get("id") == research_id:
                outcomes[research_id] = record
        bootstrap_score, bootstrap_id = _bootstrap_admission(row, outcomes)
        if (row.get("current_call_cost_unknown") is True
                or row.get("event") == "decision" and row.get("policy") == "cost_accounting"
                and row.get("action") == "unknown_cost"
                or row.get("event") == "run_end" and row.get("reason") == "accounting_stopped"):
            unknown_charge = True
        if row.get("event") == "run_start":
            counters = _dict(row.get("counters"))
            if _number(counters.get("cost_total")) is not None:
                cost = counters["cost_total"]
                cost_source, cost_exact = "run_start.counters", True
            # Fresh run_start precedes seed evaluation; its default 0 is
            # an initialized counter, not an observed zero-quality seed.
            if row.get("resumed") is True and _number(counters.get("seed_score")) is not None:
                seed_score = counters["seed_score"]
                best = max(best, seed_score) if best is not None else seed_score
            if type(counters.get("iteration_no")) is int:
                iterations = counters["iteration_no"]
            if type(counters.get("B_evals")) is int:
                evaluations = counters["B_evals"]
            if type(counters.get('n_remeasurements')) is int and counters['n_remeasurements'] >= 0:
                remeasurements = counters['n_remeasurements']
        if (row.get('event') == 'decision' and row.get('policy') == 'candidate_measurement'
                and row.get('action') == 'start' and row.get('remeasurement') is True):
            remeasurements = (remeasurements or 0) + 1
        if _seed_record(row) and row.get("measured") is True:
            seed_score = _number(row.get("seed_score"))
            if seed_score is not None:
                best = max(best, seed_score) if best is not None else seed_score
                # One evaluated source can seed several islands. It is one
                # baseline observation, not one evaluation per stored copy.
                if observed_seed_score is None:
                    observed_seed_score = seed_score
                    curves.append(dict(iteration=0, evaluations=0, score=seed_score,
                        best_score=seed_score, cost_total=_number(cost),
                        event_seq=row.get("event_seq"), kind="seed", _row_index=index))
        parent_score = _number(_dict(row.get("evidence")).get("parent_score"))
        if parent_score is not None:
            best = max(best, parent_score) if best is not None else parent_score
        charge = None
        if row.get("event") == "iteration":
            charge = _number(row.get("cost"))
            iterations = _iteration(row)
            evaluations = _number(row.get("B_evals"))
        elif row.get("event") == "research" and row.get("phase") == "aux_result":
            charge = _number(row.get("cost"))
        elif row.get("event") == "decision" and row.get("policy") in {"portfolio_seed", "paradigm_validation"}:
            # Bootstrap/spawn has no ordinary iteration row. Charge its
            # decision once, never the same outcome/validation trace again.
            charge = _number(row.get("cost"))
        elif (row.get("event") == "decision" and row.get("policy") == "cost_accounting"
                and row.get("action") == "unknown_cost"):
            # A stopped worker has no iteration row. Its earlier returned
            # calls are recorded here before the final checkpoint is saved.
            charge = _number(row.get("known_cost"))
        if charge is not None:
            cost = (cost or 0) + charge
            cost_source, cost_exact = "logged_known_charges", False
        if _number(row.get("cost_total")) is not None:
            cost, cost_source, cost_exact = row["cost_total"], "journal.cost_total", True
        if _number(row.get("pop_best")) is not None:
            best = row["pop_best"]
        elif row.get("event") == "iteration" and _number(row.get("child_score")) is not None:
            best = max(best, row["child_score"]) if best is not None else row["child_score"]
        if bootstrap_score is not None:
            best = max(best, bootstrap_score) if best is not None else bootstrap_score
            bootstrap_candidates.append((bootstrap_score, bootstrap_id))
        if boundary == index and _number(checkpoint.get("cost_total")) is not None:
            cost, cost_source, cost_exact = checkpoint["cost_total"], "checkpoint.cost_total", True
        if row.get("event") == "iteration":
            curves.append(dict(iteration=iterations, evaluations=evaluations,
                score=_number(row.get("child_score")), best_score=_number(best),
                cost_total=_number(cost), event_seq=row.get("event_seq"), _row_index=index))
        elif bootstrap_score is not None:
            curves.append(dict(iteration=iterations, evaluations=evaluations,
                score=bootstrap_score, best_score=_number(best), cost_total=_number(cost),
                event_seq=row.get("event_seq"), kind="bootstrap", experiment_id=bootstrap_id,
                _row_index=index))
    if not end and checkpoint and boundary is None and _number(checkpoint.get("cost_total")) is not None:
        cost, cost_source, cost_exact = checkpoint["cost_total"], "checkpoint.cost_total", True
    db = _dict(checkpoint.get("db"))
    best_program = sources.get(db.get("pop_best_id"), {})
    reported_best = [_number(end.get("pop_best")), _number(best_program.get("score")), _number(best)]
    finite_best = [value for value in reported_best if value is not None]
    best = finite_best[0] if end and reported_best[0] is not None else max(finite_best) if finite_best else None
    best_candidate_id = None
    if best is not None:
        # A checkpoint can lag a newly journaled child. Never pair its old
        # program ID with a newer score belonging to a different candidate.
        if _number(best_program.get("score")) == best:
            best_candidate_id = db.get("pop_best_id")
        if best_candidate_id is None:
            best_candidate_id = next((row["child_id"] for row in rows
                if row.get("event") == "iteration" and isinstance(row.get("child_id"), str)
                and _number(row.get("child_score")) == best), None)
        if best_candidate_id is None:
            best_candidate_id = next((row['measurement_program_id'] for row in rows
                if row.get('event') == 'iteration' and row.get('reason') == 'remeasurement'
                and row.get('measurement_ok') is True and isinstance(row.get('measurement_program_id'), str)
                and _number(row.get('measurement_score')) == best), None)
        if best_candidate_id is None:
            best_candidate_id = next((research_id for score, research_id in bootstrap_candidates
                if score == best and research_id is not None), None)
        if best_candidate_id is None:
            best_candidate_id = next((program["id"] for program in sources.values()
                if isinstance(program.get("id"), str) and _number(program.get("score")) == best), None)
    iterations = max((value for value in [iterations, checkpoint.get("iteration_no"), end.get("iteration_no")]
                      if type(value) is int), default=None)
    evaluations = max((value for value in [evaluations, checkpoint.get("B_evals"), end.get("B_evals")]
                       if type(value) is int), default=None)
    remeasurements = max((value for value in [remeasurements, checkpoint.get('n_remeasurements'), end.get('n_remeasurements')]
                          if type(value) is int and value >= 0), default=None)
    task = start.get("task") or _dict(checkpoint.get("identity")).get("task") or _dict(checkpoint.get("config")).get("task")
    scope, scope_note = "recorded_run", None
    if engineering_only:
        scope = "engineering"
        scope_note = "Engineering validation run; these scores do not establish benchmark superiority or memory benefit."
    run = dict(id=ident, name=name, path=str(path.parent), task=task,
        last_modified=_time(modified), event_count=len(rows),
        best_score=best, cost_total=_number(cost), run_id=start.get("run_id"),
        seed=start.get("seed"), models=_list(start.get("models")), scope=scope, scope_note=scope_note)
    events = []
    for index, row in enumerate(rows):
        phase = row.get("phase")
        summary = str(phase or row.get("event", "event"))
        for key in ("experiment_id", "child_id", "reason", "status"):
            if row.get(key) is not None:
                summary += " · " + str(row[key])[:160]
        events.append(dict(seq=index + 1, event=row.get("event"), phase=phase,
            event_seq=row.get("event_seq"), segment_id=row.get("segment_id"),
            iteration=_iteration(row), summary=summary, data=_safe(row, compact=True)))
    reflections = sum(row.get("event") == "research" and row.get("phase") == "reflection" for row in rows)
    config = start.get("config") if isinstance(start.get("config"), dict) else _dict(checkpoint.get("config"))
    subscription = _dict(config.get("llm")).get("provider") == "codex_responses"
    cost_status = "subscription_unpriced" if subscription else "reported" if cost_exact else "known_logged_lower_bound" if cost is not None else "unavailable"
    if not subscription and cost is not None and _dict(config.get("llm")).get("cost_reporting") == "estimated_uncached_token_rates":
        cost_status = "estimated"
        cost_source = "estimated_uncached_token_rates / " + cost_source
    if unknown_charge:
        warning = "At least one LLM charge is unknown; recorded spend excludes that call and is incomplete."
        if cost_status == "estimated":
            warning += " The recorded portion uses token-rate estimates, not provider billing."
        warnings.append(warning)
        if cost is not None:
            cost_status = "known_logged_lower_bound"
            cost_source = "unknown_charge / " + cost_source
    estimated = (not subscription and _dict(config.get('llm')).get('cost_reporting')
                 == 'estimated_uncached_token_rates')
    accounting = dict(recorded_llm_usd=_number(cost), provider_reported_llm_usd=None,
        estimated_llm_usd=_number(cost) if estimated else None,
        cost_basis='subscription_unpriced' if subscription else 'token_estimate' if estimated else 'unverified_recorded_accounting',
        cpu_usd=None, all_in_usd=None, cpu_cost_status='not_recorded')
    programs = project_lineage(curves, trials, sources, evidence, rows)
    measured_results = max((value for value in (
        checkpoint.get('n_evaluation_results'), end.get('n_evaluation_results'),
        *(row.get('n_evaluation_results') for row in rows if row.get('policy') == 'output_novelty'))
        if type(value) is int and value >= 0), default=None)
    repeated_outputs = max((value for value in (
        checkpoint.get('n_output_repeats'), end.get('n_output_repeats'),
        *(row.get('n_output_repeats') for row in rows if row.get('policy') == 'output_novelty'))
        if type(value) is int and value >= 0), default=None)
    output_resolution = _dict(config.get('candidate_novelty')).get('output_resolution')
    snapshot = dict(schema=SCHEMA, run=run, stats=dict(iterations=iterations, evaluations=evaluations,
        remeasurements=remeasurements,
        measured_results=measured_results, repeated_outputs=repeated_outputs,
        output_resolution=output_resolution,
        attempts=len(trials), hypotheses=sum(isinstance(item.get("hypothesis"), dict) for item in trials),
        lessons=sum(item["status"] == "active" for item in lessons), reflections=reflections,
        cost_total=_number(cost), cost_source=cost_source,
        cost_status=cost_status, billing_mode="subscription_unpriced" if subscription else None,
        unknown_cost_present=unknown_charge, llm_unpriced_calls=checkpoint.get("llm_unpriced_calls", 0),
        **accounting,
        best_score=best, seed_score=observed_seed_score if observed_seed_score is not None
            else _number(end.get("seed_score", checkpoint.get("seed_score")))),
        curves=curves, programs=programs, trials=trials, hypotheses=[item for item in trials if isinstance(item.get("hypothesis"), dict)],
        lessons=lessons, events=events, warnings=warnings, checkpoint=checkpoint_info, metric=metric,
        architecture=architecture(start, checkpoint, rows),
        research_tools=research_tools_view(start, checkpoint, rows),
        start_protocol=start_protocol(start, checkpoint, rows),
        population=population_view(checkpoint, rows, start, sources),
        parallel=parallel_view(start, checkpoint, rows),
        learning=learning_view(start, checkpoint, rows),
        reliability=reliability_view(start, checkpoint, rows, lessons),
        result_history=result_history_view(checkpoint, rows, sources),
        benchmark=None,
        best_candidate_id=best_candidate_id, geometry=saved_geometry(trials, evidence))
    display = project_metrics(snapshot, checkpoint, rows, sources, evidence)
    snapshot['benchmark'] = benchmark_for(task, display.metric, best,
        metric_display=snapshot['stats']['best_metric_display'])
    snapshot['_effort_basis'] = effort_basis(rows, sources, best_candidate_id, best,
        _dict(checkpoint.get('identity')).get('task_hash'), iterations)
    run['committed_effort'] = dict(scope='committed_journal', ordinary_iterations=iterations,
        ordinary_successful_evaluations=evaluations, known_llm_usd=None, cost_status=cost_status,
        **accounting,
        billing_mode="subscription_unpriced" if subscription else None, unknown_cost_present=unknown_charge,
        configured_models=_list(start.get('models')),
        note='Committed accounting amounts are not verified billing. Historical token-rate estimates, when declared, are shown separately. CPU/infrastructure and all-in costs are unavailable. Physical receipts and actual model use require the selected run view.')
    return snapshot, sources, evidence, (start, end, modified, _stop_detail(checkpoint, rows[last_start + 1:]))
