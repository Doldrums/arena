"""Join saved candidate, trial and lesson identities without filesystem access."""
import math
import re

from .run_values import _dict, _list, _number, _sha, _seed_record, _iteration, _payload



def checkpoint_boundary(checkpoint, rows):
    anchor = _dict(_dict(checkpoint.get("provenance")).get("journal_anchor"))
    if anchor:
        for i, row in enumerate(rows):
            if (row.get("segment_id"), row.get("event_seq")) == (anchor.get("segment_id"), anchor.get("event_seq")):
                return i
    return None


def source_records(checkpoint, rows):
    programs = _dict(checkpoint.get("db")).get("programs", [])
    if isinstance(programs, dict):
        programs = list(programs.values())
    result = {}
    for program in _list(programs):
        if isinstance(program, dict) and isinstance(program.get("id"), str):
            result[program["id"]] = dict(program, code_source="checkpoint")
    for row in rows:
        if _seed_record(row):
            code = row.get("source")
            if isinstance(code, str) and row.get("source_sha256") == _sha(code):
                ident = row["program_id"]
                result[ident] = dict(id=ident, code=code, parent_id=None,
                    score=_number(row.get("score")) if row.get("measured") is True else None,
                    island=row.get('island'), origin='seed',
                    code_source="journal.initialization.source")
        ident, code = row.get("child_id"), row.get("child_code")
        if row.get("event") == "iteration" and isinstance(ident, str) and isinstance(code, str):
            result[ident] = dict(result.get(ident, {}), id=ident, code=code, parent_id=row.get("parent_id"),
                parent_ids=row.get('parent_ids', _dict(row.get('meta')).get('parent_ids')),
                island=row.get('island'), score=row.get("child_score"), code_source="journal.child_code")
    return result


def empty_trial(ident):
    return dict(id=ident, candidate_id=None, parent_id=None, iteration=None, island=None,
                status="pending", score=None, actual_delta=None, forecast_verdict=None,
                hypothesis=None, conclusion=None, source_sha256=None, code_available=False)


def project_lineage(curves, trials, sources, evidence, rows):
    """Join explicit identities; never guess parents from score or iteration.

    A checkpoint-only migrant has a parent but no new evaluation coordinate.
    A research ID can alias a bootstrap storage ID only when its complete
    recorded fingerprint and ancestry identify exactly one stored program.
    """
    def parents(*records):
        result = []
        for record in records:
            if not isinstance(record, dict):
                continue
            values = [record.get('parent_id')] + _list(record.get('parent_ids'))
            for value in values:
                if isinstance(value, str) and value and value not in result:
                    result.append(value)
        return result

    def short_hypothesis(value):
        if isinstance(value, dict):
            value = value.get('text') or value.get('hypothesis')
        return value[:320] if isinstance(value, str) else None

    programs, fingerprints, bootstrap, seeds = {}, {}, {}, []
    for row in rows:
        if _seed_record(row) and row.get('program_id') in sources:
            seeds.append(row)
        if row.get('event') == 'decision' and row.get('policy') == 'portfolio_seed':
            research_id = _dict(row.get('meta')).get('research_id')
            if isinstance(research_id, str):
                bootstrap[research_id] = row
    for ident, source in sources.items():
        # _trials adds research source aliases; handle them through their
        # explicit trial below instead of inventing a second stored member.
        if ident in evidence:
            continue
        origin = source.get('origin')
        programs[ident] = dict(candidate_id=ident, alias_ids=[], parent_ids=parents(source),
            experiment_id=None, iteration=None, score=_number(source.get('score')),
            best_score=None, cost_total=None, island=source.get('island'), operator=None,
            status='stored', hypothesis=short_hypothesis(source.get('card')),
            parent_score=_number(sources.get(source.get('parent_id'), {}).get('score')),
            model=None, code_available=isinstance(source.get('code'), str), origin=origin,
            llm_available=False,
            lineage_note='Migrated copy; no separate evaluation or creation time was recorded.'
                if origin == 'migrant' else 'Stored program; evaluation position was not recorded.')
        if isinstance(source.get('code'), str):
            fingerprint = (_sha(source['code']), source.get('parent_id'), source.get('island'),
                           source.get('origin'), _number(source.get('score')))
            fingerprints.setdefault(fingerprint, []).append(ident)
    for row in seeds:
        program = programs.get(row['program_id'])
        if program is not None:
            program.update(iteration=0, status='seed' if row.get('measured') is True else 'unmeasured',
                score=_number(row.get('score')) if row.get('measured') is True else None,
                parent_ids=[], lineage_note='Initial source, evaluated once and copied into islands.')

    trial_programs = {}
    for trial in trials:
        ident = trial['id']
        candidate = trial.get('candidate_id') or ident
        admission = bootstrap.get(ident, {})
        aliases = [ident] if candidate != ident else []
        if trial.get('candidate_id') is None and trial.get('status') == 'evaluated':
            fingerprint = (trial.get('source_sha256'), trial.get('parent_id'), trial.get('island'),
                           admission.get('action', 'gen'), _number(trial.get('score')))
            matches = fingerprints.get(fingerprint, [])
            if len(matches) == 1:
                aliases.append(matches[0])
        base = programs.get(candidate) or next((programs[alias] for alias in aliases if alias in programs), {})
        program = dict(base, candidate_id=candidate, alias_ids=aliases,
            experiment_id=ident if ident in evidence else None,
            parent_ids=parents(evidence.get(ident), {'parent_id':trial.get('parent_id')}, base),
            iteration=trial.get('iteration'), score=trial.get('score') if trial.get('status') == 'evaluated' else None,
            best_score=None, cost_total=None, island=trial.get('island'),
            operator=trial.get('operator'), status=trial.get('status'),
            hypothesis=short_hypothesis(trial.get('hypothesis')),
            parent_score=trial.get('parent_score'), model=trial.get('model') or admission.get('model_used'),
            code_available=trial.get('code_available') is True,
            llm_available=ident in evidence or bool(trial.get('model') or admission.get('model_used')),
            origin=admission.get('action') or base.get('origin'), lineage_note=None)
        for alias in aliases:
            programs.pop(alias, None)
        programs[candidate] = program
        trial_programs[ident] = program

    for point in curves:
        index = point.pop('_row_index')
        row = rows[index]
        point['point_id'] = f"{row.get('segment_id', 'legacy')}:{row.get('event_seq', index)}:{point.get('kind', 'iteration')}"
        point['segment_id'] = row.get('segment_id')
        research_id = (point.get('experiment_id') or _dict(row.get('meta')).get('research_id'))
        program = trial_programs.get(research_id) if isinstance(research_id, str) else None
        if point.get('kind') == 'seed':
            program = programs.get(row.get('program_id'))
            point['candidate_ids'] = [seed['program_id'] for seed in seeds
                if seed.get('source_sha256') == row.get('source_sha256')
                and seed.get('score') == row.get('score') and seed.get('measured') is True]
        elif program is None and isinstance(row.get('child_id'), str):
            program = programs.get(row['child_id'])
        metadata = program or dict(candidate_id=None, alias_ids=[], experiment_id=research_id,
            parent_ids=parents(row, _dict(row.get('meta'))), island=row.get('island'),
            operator=row.get('op_used'), status=row.get('reason') or 'unknown',
            hypothesis=short_hypothesis(_dict(row.get('meta')).get('hypothesis')),
            parent_score=_number(sources.get(row.get('parent_id'), {}).get('score')),
            model=row.get('model_used'), code_available=False, llm_available=False)
        for key in ('candidate_id', 'alias_ids', 'experiment_id', 'parent_ids', 'island', 'operator',
                    'status', 'hypothesis', 'parent_score', 'model', 'code_available', 'llm_available', 'origin', 'lineage_note'):
            point[key] = metadata.get(key)
        if program is not None:
            point['score'] = program['score']
            if point.get('kind') == 'bootstrap' and program.get('iteration') is not None:
                point['iteration'] = program['iteration']
            program.update(point_id=point['point_id'], iteration=point['iteration'],
                best_score=point['best_score'], cost_total=point['cost_total'])
            if point.get('kind') == 'seed':
                for seed_id in point['candidate_ids']:
                    if seed_id in programs:
                        programs[seed_id].update(point_id=point['point_id'],
                            cost_total=point['cost_total'], best_score=point['best_score'])
        point['kind'] = point.get('kind', 'iteration')
    return list(programs.values())


def trial_records(checkpoint, rows, sources):
    trials, evidence, responses = {}, {}, {}
    research = _dict(checkpoint.get("research"))
    knowledge = _dict(research.get("knowledge"))
    for record in _list(knowledge.get("experiments")) + _list(research.get("queue")):
        if isinstance(record, dict) and isinstance(record.get("id"), str):
            evidence[record["id"]] = dict(record)
    for record in _dict(research.get("pending")).values():
        if isinstance(record, dict) and isinstance(record.get("id"), str):
            evidence[record["id"]] = dict(record)
    for row in rows:
        if row.get("event") == "research" and row.get("phase") in ("attempt", "hypothesis", "outcome"):
            record = _dict(row.get("evidence"))
            ident = row.get("experiment_id") or record.get("id")
            if isinstance(ident, str):
                evidence.setdefault(ident, {}).update(record)
                if isinstance(row.get("response"), str):
                    responses[ident] = row["response"]
    for ident, record in evidence.items():
        trial = empty_trial(ident)
        for key in ("parent_id", "iteration", "island", "status", "forecast_verdict", "hypothesis", "source_sha256"):
            trial[key] = record.get(key, trial[key])
        trial.update(candidate_id=record.get("child_id"), score=_number(record.get("score")),
                     actual_delta=_number(record.get("actual_delta")),
                     parent_score=_number(record.get("parent_score")), failure=record.get("failure"),
                     operator=record.get("operator"), injected_ids=_list(record.get("injected_ids")),
                     generation_cost=_number(record.get("generation_cost")))
        # A failed evaluator's sentinel score is not a measured candidate.
        if trial["status"] != "evaluated":
            trial["score"] = trial["actual_delta"] = None
        trials[ident] = trial
    for index, row in enumerate(rows):
        if row.get("event") != "iteration":
            continue
        meta = _dict(row.get("meta"))
        ident = meta.get("research_id") or row.get("child_id")
        if not isinstance(ident, str):
            # dup_cap/no-child summaries can omit research_id, even though
            # each rejected G already has an ordinary research attempt.
            matching = [trial for trial in trials.values() if trial.get("iteration") == _iteration(row)
                        and trial.get("island") == row.get("island")]
            ident = matching[-1]["id"] if matching else f"iteration:{_iteration(row)}:{index}"
        trial = trials.setdefault(ident, empty_trial(ident))
        trial.update(iteration=_iteration(row), island=row.get("island"),
                     candidate_id=row.get("child_id") or trial.get("candidate_id"),
                     parent_id=row.get("parent_id") or trial.get("parent_id"),
                     model=row.get("model_used"), operator=row.get("op_used") or meta.get("op_used"),
                     cost=_number(row.get("cost")), iteration_reason=row.get("reason"))
        if ident not in evidence:
            trial.update(status=row.get("reason") or ("evaluated" if "child_score" in row else "unknown"),
                         score=_number(row.get("child_score")), hypothesis=meta.get("hypothesis"))
        if row.get('reason') == 'remeasurement':
            trial.update(status='remeasurement', score=None, actual_delta=None,
                measurement_program_id=row.get('measurement_program_id'),
                measurement_score=_number(row.get('measurement_score')) if row.get('measurement_ok') is True else None,
                measurement_ok=row.get('measurement_ok'))
        if trial["score"] is not None and trial.get("parent_score") is None:
            parent = sources.get(trial["parent_id"], {})
            trial["parent_score"] = _number(parent.get("score"))
            if trial["parent_score"] is not None:
                trial["actual_delta"] = trial["score"] - trial["parent_score"]
    conclusions = _dict(research.get("conclusions")).copy()
    for row in rows:
        if row.get("event") == "research" and row.get("phase") == "conclusion":
            conclusions[row.get("experiment_id")] = row
    for ident, trial in trials.items():
        conclusion = _dict(conclusions.get(ident))
        trial["conclusion"] = conclusion.get("llm")
        trial["conclusion_status"] = conclusion.get("status")
        source = sources.get(trial.get("candidate_id"), {})
        code = source.get("code")
        expected = trial.get("source_sha256")
        if not isinstance(code, str):
            record = evidence.get(ident, {})
            fragment = record.get("code_fragment")
            if isinstance(fragment, str) and fragment and expected and _sha(fragment) == expected:
                code = fragment
                source = dict(code=code, code_source="journal.code_fragment", parent_id=trial.get("parent_id"))
            else:
                # Full Python fence only, and only when exact evaluated SHA matches.
                for match in re.finditer(r"^```(?:python)?[^\S\n]*\n([\s\S]*?)^```[^\S\n]*$",
                                         responses.get(ident, ""), re.MULTILINE):
                    options = (match.group(1), match.group(1).rstrip("\n"), match.group(1).strip())
                    code = next((value for value in options if expected and _sha(value) == expected), None)
                    if code is not None:
                        source = dict(code=code, code_source="journal.hash_bound_response", parent_id=trial.get("parent_id"))
                        break
        if isinstance(code, str) and (not expected or _sha(code) == expected):
            trial["code_available"] = True
            sources[ident] = source
            trial["source_sha256"] = expected or _sha(code)
        trial["change_excerpt_available"] = bool(evidence.get(ident, {}).get("change_excerpt"))
    return sorted(trials.values(), key=lambda item: (item["iteration"] if type(item["iteration"]) is int else -1, item["id"])), evidence


def lesson_records(checkpoint, rows, boundary):
    research = _dict(checkpoint.get("research"))
    known = {}
    history_complete = bool(rows and rows[0].get("event") == "run_start"
                            and rows[0].get("resumed") is False)
    saved = [lesson for lesson in _list(_dict(research.get("knowledge")).get("lessons"))
             if isinstance(lesson, dict) and isinstance(lesson.get("id"), str)]

    def overlay_checkpoint():
        current = {lesson["id"] for lesson in saved}
        for ident, lesson in known.items():
            if ident not in current and lesson["status"] == "active":
                # Capacity eviction is not a model-authorized retirement.
                lesson["status"] = "not_retained"
        for lesson in saved:
            ident = lesson["id"]
            prior = known.get(ident, {})
            exposures = set(prior.get("_exposures", ()))
            exposures.update(value for value in _list(lesson.get("exposure_ids")) if isinstance(value, str))
            known[ident] = dict(prior, **lesson, status="active", data_source="checkpoint",
                _exposures=exposures,
                _exposures_known=prior.get("_exposures_known", False) or isinstance(lesson.get("exposure_ids"), list))

    # With no known prefix, the checkpoint's current subset is all we can
    # safely place in time. Do not apply potentially older journal writes.
    if checkpoint and boundary is None:
        overlay_checkpoint()
        replay_rows = []
    else:
        replay_rows = rows
    auxiliary = {}
    for index, row in enumerate(replay_rows):
        if row.get("event") == "research":
            phase = row.get("phase")
            if phase == "aux_result":
                key = (row.get("segment_id"), row.get("kind"), row.get("reference"))
                auxiliary[key] = {} if row.get("response_truncated") else _payload(row.get("response"))
            proposals, ids, retired = [], [], []
            if phase == "conclusion" and row.get("status") == "parsed":
                proposals = _list(_dict(row.get("llm")).get("lessons"))
                ids = _list(row.get("accepted_lesson_ids"))
            elif phase == "reflection" and isinstance(row.get("applied"), dict) and not row.get("error"):
                key = (row.get("segment_id"), "reflection", row.get("through"))
                proposals = _list(auxiliary.get(key, {}).get("lessons"))
                ids = _list(row["applied"].get("lesson_ids"))
                retired = _list(row["applied"].get("retired_ids"))
            # Only an explicit accepted ID gives a proposal a lesson identity.
            # When ordering is ambiguous, preserve that ID without claiming
            # that an arbitrary proposed text was admitted.
            for offset, ident in enumerate(ids):
                if not isinstance(ident, str):
                    continue
                proposal = proposals[offset] if len(ids) == len(proposals) else {}
                if isinstance(proposal, dict):
                    prior = known.get(ident, {})
                    combined = list(dict.fromkeys(_list(prior.get("evidence_ids")) + _list(proposal.get("evidence_ids"))))
                    known[ident] = dict(prior, **proposal, id=ident, status="active", data_source="journal",
                        _exposures=set(prior.get("_exposures", ())),
                        _exposures_known=prior.get("_exposures_known", history_complete))
                    known[ident]["evidence_ids"] = combined
                    if isinstance(known[ident].get("rule"), str):
                        known[ident]["rule"] = known[ident]["rule"].strip()
            for ident in retired:
                if isinstance(ident, str) and ident in known:
                    known[ident]["status"] = "retired"
            if phase == "outcome":
                record = _dict(row.get("evidence"))
                observation = row.get("experiment_id") or record.get("id")
                if isinstance(observation, str) and record.get("generation_dispatch") != "not_dispatched":
                    for ident in _list(record.get("injected_ids")):
                        if isinstance(ident, str) and ident in known:
                            known[ident]["_exposures"].add(observation)
                            # These are known direct exposures, not source
                            # support, inherited benefit or causal effects.
                            known[ident]["_exposures_known"] = True
        if boundary == index:
            overlay_checkpoint()
    result = []
    for ident, lesson in known.items():
        result.append(dict(id=ident, rule=lesson.get("rule", ""), polarity=lesson.get("polarity"),
            scope=lesson.get("scope"), branch=lesson.get("branch"),
            evidence_ids=_list(lesson.get("evidence_ids")), confidence=_number(lesson.get("confidence")),
            exposure_count=len(lesson.get("_exposures", ())) if lesson.get("_exposures_known") else None,
            exposure_count_scope="known_direct", status=lesson["status"],
            data_source=lesson["data_source"]))
    return result


def saved_geometry(trials, evidence):
    for trial in sorted(trials, key=lambda item: item.get("score") if item.get("score") is not None else -math.inf, reverse=True):
        if trial.get("status") != "evaluated" or trial.get("score") is None:
            continue
        record = evidence.get(trial["id"], {})
        geometry = _dict(_dict(record.get("evaluation")).get("native_geometry"))
        numeric = _dict(geometry.get("numeric"))
        centers, radii = numeric.get("centers"), numeric.get("radii")
        if geometry.get("source_sha256") != trial.get("source_sha256") or not trial.get("source_sha256"):
            continue
        if not isinstance(centers, list) or not isinstance(radii, list) or not centers or len(centers) != len(radii):
            continue
        if not all(isinstance(center, list) and len(center) == 2 and all(_number(x) is not None for x in center) for center in centers):
            continue
        if not all(_number(radius) is not None and radius >= 0 for radius in radii):
            continue
        return dict(candidate_id=trial["candidate_id"] or trial["id"], experiment_id=trial["id"],
            source_sha256=trial["source_sha256"], centers=centers, radii=radii,
            score=trial["score"], kind="persisted_native_geometry", verified_by_dashboard=False)
    return None
