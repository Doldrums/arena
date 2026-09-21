"""Display recorded measurements without converting penalty scores into data.

This is a read-only projection. It neither evaluates candidates nor modifies
their scores, histories, validity decisions or task declarations.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re

from .compat.measurement import validate_metric_context


SCHEMA = "sciel-metric-display/1"


def _dict(value):
    return value if isinstance(value, dict) else {}


def _number(value):
    if type(value) not in (int, float):
        return None
    try:
        return value if math.isfinite(value) else None
    except OverflowError:
        return None


class MetricDisplay:
    """A task-bound descriptor; absent or incompatible metadata stays unknown."""

    def __init__(self, metric, *, task, task_hash):
        self.metric = None
        self.reason = 'missing_metric'
        try:
            checked = validate_metric_context(metric)
        except (ValueError, TypeError, OverflowError, RecursionError):
            return
        if (not isinstance(task, str) or not isinstance(task_hash, str)
                or checked['task_name'] != task or checked['task_hash'] != task_hash):
            self.reason = 'task_mismatch'
            return
        self.metric = checked
        self.reason = None

    def unknown(self, score=None, reason=None):
        metric = self.metric or {}
        semantics = metric.get('semantics', {})
        native = semantics.get('kind') == 'validity_gated_ratio'
        return dict(schema=SCHEMA, status='unknown', value=None,
            label=semantics['numerator_case'] if native else metric.get('primary_metric') or 'Controller score',
            units=semantics.get('numerator_units') if native else semantics.get('score_units'),
            raw_score=_number(score), reason=reason or self.reason or 'missing_observation',
            metric_sha256=metric.get('sha256'))

    def observation(self, score, *, cases=None, status='evaluated', ok=None, metric=None):
        value = self.unknown(score)
        if status in {'eval_failed', 'eval_fail', 'failed'} or ok is False:
            value.update(status='failed', reason='evaluation_failed')
            return value
        if self.metric is None:
            return value
        if metric is not None:
            try:
                supplied = validate_metric_context(metric)
            except (ValueError, TypeError, OverflowError, RecursionError):
                value['reason'] = 'invalid_observation_metric'
                return value
            if supplied != self.metric:
                value['reason'] = 'observation_metric_mismatch'
                return value
        score = _number(score)
        if status not in {'evaluated', 'stored', 'seed'} or score is None:
            return value
        semantics = self.metric['semantics']
        if semantics['kind'] == 'unknown':
            # This is the recorded controller metric, with no native-unit claim.
            value.update(status='measured', value=score, reason=None)
            return value
        cases = _dict(cases)
        validity = _number(cases.get(semantics['validity_case']))
        if validity is None:
            value['reason'] = 'missing_validity'
            return value
        if validity != semantics['valid_value']:
            value.update(status='invalid_penalty' if score == semantics['invalid_score'] else 'unknown',
                reason='invalid_task_result' if score == semantics['invalid_score'] else 'invalid_penalty_mismatch')
            return value
        numerator = _number(cases.get(semantics['numerator_case']))
        if numerator is None:
            value['reason'] = 'missing_native_measurement'
            return value
        # Never reconstruct this from score * denominator: the case is the
        # saved observation, including a legitimate zero and its exact float.
        value.update(status='measured', value=numerator, reason=None)
        return value

    def record(self, record):
        record = _dict(record)
        evaluation = _dict(record.get('evaluation'))
        score = record.get('score')
        if record.get('metric') is None and record.get('status') == 'evaluated':
            return self.unknown(score, 'missing_observation_metric')
        if record.get('status') == 'evaluated' and (
                evaluation.get('ok') is not True
                or _number(score) != _number(evaluation.get('score'))):
            return self.unknown(score, 'inconsistent_evaluation')
        return self.observation(score, cases=evaluation.get('cases'), status=record.get('status'),
            ok=evaluation.get('ok'), metric=record.get('metric'))


def _delta(child, parent):
    if (child['status'] != 'measured' or parent['status'] != 'measured'
            or child['metric_sha256'] != parent['metric_sha256']):
        return None
    return _number(child['value'] - parent['value'])


def _canonical_tool_observations(rows, *, run_id, task_hash):
    """Bind admitted tool results to their immutable canonical journal evidence.

    These candidates deliberately have no ordinary hypothesis/KB experiment.
    Their submission payload is also saved in the iteration; hashing its exact
    artifact envelope authenticates it against the preceding research step.
    No tool-reported observation or current checkpoint score supplies a value.
    """
    steps, observations = {}, {}
    if not isinstance(run_id, str) or not isinstance(task_hash, str):
        return observations
    for row in rows:
        if row.get('run_id') != run_id:
            continue
        if (row.get('event') == 'research_tool' and row.get('phase') == 'research_step'
                and row.get('action') == 'submit_candidate' and row.get('status') == 'evaluated'):
            ident = row.get('canonical_evaluation_id')
            if isinstance(ident, str):
                steps.setdefault(ident, []).append(row)
        if (row.get('event') != 'iteration' or row.get('op_used') != 'research_tool'
                or row.get('reason') not in (None, 'evaluated')
                or not isinstance(row.get('child_id'), str)):
            continue
        meta = _dict(row.get('meta'))
        submission = _dict(_dict(meta.get('research_tools')).get('candidate_submission'))
        source, provenance = submission.get('source'), _dict(submission.get('provenance'))
        evaluation = _dict(submission.get('evaluation'))
        if not isinstance(source, str) or source != row.get('child_code'):
            continue
        digest = hashlib.sha256(source.encode('utf-8', errors='surrogatepass')).hexdigest()
        score, evaluation_id = _number(row.get('child_score')), evaluation.get('evaluation_id')
        if (provenance.get('schema') != 'sciel-research-candidate-submission/1'
                or provenance != meta.get('research_candidate')
                or provenance.get('candidate_origin') != 'research_tool'
                or provenance.get('candidate_source_sha256') != digest
                or any(not isinstance(provenance.get(key), str) or not provenance[key]
                       for key in ('cell_id', 'action_id'))
                or evaluation.get('schema') != 'sciel-research-candidate-evaluation/1'
                or evaluation.get('source_sha256') != digest or evaluation.get('status') != 'evaluated'
                or not isinstance(evaluation_id, str) or meta.get('evaluation_id') != evaluation_id
                or score is None or _number(evaluation.get('score')) != score
                or not isinstance(evaluation.get('cases'), dict) or evaluation['cases'] != row.get('cases')):
            continue
        selected = [item for item in meta.get('evaluations', []) if isinstance(item, dict)
                    and item.get('evaluation_id') == evaluation_id] if isinstance(meta.get('evaluations'), list) else []
        if (len(selected) != 1 or selected[0].get('ok') is not True
                or selected[0].get('admission') != 'candidate'
                or selected[0].get('source_sha256') != digest or _number(selected[0].get('score')) != score):
            continue
        novelty = evaluation.get('output_novelty')
        if novelty is not None and (_dict(_dict(novelty).get('binding')).get('task_hash') != task_hash
                or _dict(_dict(novelty).get('binding')).get('source_sha256') != digest):
            continue
        try:
            encoded = json.dumps(dict(schema='sciel-research-tool-artifact/1', kind='candidate_evaluation',
                payload=submission), sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()
        except (ValueError, TypeError, OverflowError, RecursionError):
            continue
        if len(encoded) > 2 * 1024 * 1024:
            continue
        canonical_id = hashlib.sha256(encoded).hexdigest()
        matches = [step for step in steps.get(canonical_id, [])
            if step.get('source_sha256') == digest
            and all(step.get(key) == provenance.get(key) for key in ('cell_id', 'action_id'))
            and all(isinstance(provenance.get(key), str) and step.get('candidate_' + key) == provenance[key]
                    for key in ('receipt_id', 'tool_id', 'invocation_id'))]
        if matches:
            observations[row['child_id']] = dict(source_sha256=digest, score=score,
                cases=evaluation['cases'], canonical_evaluation_id=canonical_id)
    return observations


def project_metrics(snapshot, checkpoint, rows, sources, evidence):
    """Attach bounded display fields through explicit observation/program IDs.

    Population journal scores may be rounded and lack candidate identities.
    They cannot borrow a native value from a coincident score. Historical best
    curves carry forward only a previously bound measurement, never a search
    through unrelated programs with the same score.
    """
    identity = _dict(checkpoint.get('identity'))
    display = MetricDisplay(snapshot.get('metric'), task=snapshot['run'].get('task'),
        task_hash=identity.get('task_hash'))
    snapshot['metric_display'] = display.unknown()
    raw_programs = _dict(checkpoint.get('db')).get('programs', [])
    if isinstance(raw_programs, dict):
        raw_programs = list(raw_programs.values())
    saved = {p['id']: p for p in raw_programs if isinstance(p, dict) and isinstance(p.get('id'), str)}
    measured_again = {r.get('measurement_program_id') for r in rows
        if r.get('event') == 'iteration' and r.get('reason') == 'remeasurement'}
    unmeasured_seeds = {r.get('program_id') for r in rows
        if r.get('policy') == 'initialization' and r.get('action') == 'seed_program'
        and r.get('measured') is not True}

    def stored(ident, score=None, *, historical=False):
        program = saved.get(ident)
        if not program or historical and ident in measured_again:
            return display.unknown(score, 'unbound_program_measurement')
        if ident in unmeasured_seeds and ident not in measured_again:
            return display.unknown(score, 'unmeasured_seed')
        recorded_score = _number(program.get('score'))
        if recorded_score != _number(score):
            return display.unknown(score, 'program_score_mismatch')
        return display.observation(recorded_score, cases=program.get('cases'), status='stored')

    def parent(record):
        record = _dict(record)
        # The record captures the parent at this attempt. A later parent
        # remeasurement must not overwrite that historical observation.
        source = _dict(sources.get(record.get('parent_id'))).get('code')
        expected = record.get('parent_source_sha256')
        if isinstance(source, str) and expected and hashlib.sha256(
                source.encode('utf-8', errors='surrogatepass')).hexdigest() != expected:
            return display.unknown(record.get('parent_score'), 'parent_source_mismatch')
        if not isinstance(expected, str) or re.fullmatch('[0-9a-f]{64}', expected) is None:
            return display.unknown(record.get('parent_score'), 'missing_parent_binding')
        if record.get('metric') is None:
            return display.unknown(record.get('parent_score'), 'missing_observation_metric')
        return display.observation(record.get('parent_score'), cases=record.get('parent_cases'),
            metric=record.get('metric'))

    tool_observations = _canonical_tool_observations(rows,
        run_id=snapshot['run'].get('run_id'), task_hash=identity.get('task_hash'))
    trials = {}
    for trial in snapshot['trials']:
        record = evidence.get(trial['id'])
        current = display.record(record) if record else display.unknown(trial.get('score'))
        tool = tool_observations.get(trial.get('candidate_id')) if not record else None
        if (tool and trial.get('operator') == 'research_tool' and trial.get('status') == 'evaluated'
                and tool['source_sha256'] == trial.get('source_sha256')
                and tool['score'] == _number(trial.get('score'))):
            current = display.observation(tool['score'], cases=tool['cases'])
            trial['cases'] = copy.deepcopy(tool['cases'])
        prior = parent(record)
        trial.update(metric_display=current, parent_metric_display=prior,
            display_delta=_delta(current, prior))
        if record:
            trial['cases'] = copy.deepcopy(_dict(_dict(record.get('evaluation')).get('cases')))
        trials[trial['id']] = trial

    programs = {}
    for program in snapshot['programs']:
        trial = trials.get(program.get('experiment_id'))
        if trial:
            program.update({key: copy.deepcopy(trial[key]) for key in
                ('metric_display', 'parent_metric_display', 'display_delta')})
        else:
            program.update(metric_display=stored(program['candidate_id'], program.get('score')),
                parent_metric_display=display.unknown(program.get('parent_score')), display_delta=None)
        for ident in [program['candidate_id'], *program.get('alias_ids', [])]:
            programs[ident] = program

    def candidate(ident, score=None, *, historical=False):
        program = programs.get(ident)
        if program and (not historical or ident not in measured_again):
            value = program['metric_display']
            if _number(score) == value['raw_score']:
                return copy.deepcopy(value)
        return stored(ident, score, historical=historical)

    previous_best = display.unknown()
    previous_best_score = None
    seed = display.unknown(snapshot['stats'].get('seed_score'))
    for point in snapshot['curves']:
        trial = trials.get(point.get('experiment_id'))
        if trial:
            point.update({key: copy.deepcopy(trial[key]) for key in
                ('metric_display', 'parent_metric_display', 'display_delta')})
        else:
            point.update(metric_display=candidate(point.get('candidate_id'), point.get('score'), historical=True),
                parent_metric_display=display.unknown(point.get('parent_score')), display_delta=None)
        if point.get('kind') == 'seed':
            seed = copy.deepcopy(point['metric_display'])
        best_score = _number(point.get('best_score'))
        current = point['metric_display']
        if (current['status'] == 'measured' and current['raw_score'] == best_score
                and (point.get('kind') == 'seed' or previous_best_score is not None
                     and best_score is not None and best_score > previous_best_score)):
            previous_best = copy.deepcopy(current)
        elif previous_best['status'] != 'measured' or previous_best['raw_score'] != best_score:
            previous_best = display.unknown(best_score, 'unbound_best_measurement')
        point['best_metric_display'] = copy.deepcopy(previous_best)
        previous_best_score = best_score
    snapshot['stats']['seed_metric_display'] = seed
    best_score = snapshot['stats'].get('best_score')
    best_id = _dict(checkpoint.get('db')).get('pop_best_id')
    best = (stored(best_id, best_score) if best_id in saved
        and _number(saved[best_id].get('score')) == _number(best_score)
        else copy.deepcopy(previous_best) if previous_best['raw_score'] == _number(best_score)
        else display.unknown(best_score, 'unbound_best_measurement'))
    snapshot['stats']['best_metric_display'] = best
    snapshot['run']['best_metric_display'] = copy.deepcopy(best)

    population = snapshot.get('population', {})
    def member_value(ident, score):
        return (stored(ident, score) if population.get('source') == 'checkpoint'
                else display.unknown(score, 'unbound_population_measurement'))
    for island in population.get('islands', []):
        island['best_metric_display'] = member_value(island.get('best_candidate_id'), island.get('best_score'))
        for member in island.get('members', []):
            member['metric_display'] = member_value(member.get('id'), member.get('score'))
        for cell in island.get('grid', []):
            cell['metric_display'] = member_value(cell.get('candidate_id'), cell.get('score'))
    for member in _dict(population.get('archive')).get('members', []):
        member['metric_display'] = member_value(member.get('id'), member.get('score'))
    storage = _dict(population.get('storage'))
    for binding in storage.get('assignments', []):
        binding['metric_display'] = member_value(binding.get('program_id'), binding.get('score'))
    projection = _dict(storage.get('projection'))
    # Saved vector geometry can precede a newer journal population. Bind its
    # own IDs/scores to the checkpoint that produced it, never current members.
    for point in [*projection.get('points', []), *projection.get('assignments', [])]:
        if point.get('program_id') is not None:
            point['metric_display'] = (stored(point['program_id'], point.get('score'))
                if projection.get('iteration') == checkpoint.get('iteration_no')
                else display.unknown(point.get('score'), 'unbound_geometry_measurement'))
    return display
