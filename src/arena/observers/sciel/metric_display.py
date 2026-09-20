"""Display recorded measurements without converting penalty scores into data.

This is a read-only projection. It neither evaluates candidates nor modifies
their scores, histories, validity decisions or task declarations.
"""
from __future__ import annotations

import copy
import hashlib
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

    trials = {}
    for trial in snapshot['trials']:
        record = evidence.get(trial['id'])
        current = display.record(record) if record else display.unknown(trial.get('score'))
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
