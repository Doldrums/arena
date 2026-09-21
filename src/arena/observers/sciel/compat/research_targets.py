"""Read-only journal compatibility extracted from sciel.engine.research_targets.

SCiEL source commit: 0d67f813dd4ac21dee304f2b0de0b0ce59bf4157.
Only dependency-reachable validators/readers/constants are retained.
"""
from __future__ import annotations

from copy import deepcopy


import hashlib


import math


from .models import content_hash, require_hash


from .observed_changes import _validate_record


from .research_artifacts import validate_saved_evaluation


SCHEMA = 'sciel-research-targets/2'


FAILURE_SCHEMA = 'sciel-failed-research-target/1'


def source_sha256(source):
    return hashlib.sha256(source.encode('utf-8', errors='surrogatepass')).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError('research targets: ' + message)


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_failure(value, source, artifacts=None):
    fields = {'schema','source_sha256','iteration','B_evals','evaluation_id','reached',
              'confirmed','artifacts','artifacts_sha256','sha256'}
    _require(type(value) is dict and set(value) == fields and value['schema'] == FAILURE_SCHEMA,
             'invalid failure provenance')
    _require(value['source_sha256'] == source_sha256(source)
             and value['sha256'] == content_hash({k:v for k,v in value.items() if k != 'sha256'}),
             'failure source/digest differs')
    require_hash(value['artifacts_sha256'], 'failed artifacts')
    _require(type(value['artifacts']) is dict
             and value['artifacts_sha256'] == content_hash(value['artifacts']), 'failure artifacts digest differs')
    _require(all(type(value[k]) is int and value[k] >= 0 for k in ('iteration','B_evals')),
             'invalid failure counters')
    _require(value['evaluation_id'] is None or type(value['evaluation_id']) is str,
             'invalid failed evaluation reference')
    _require(type(value['confirmed']) is bool and type(value['reached']) is str,
             'invalid failure stage')
    if artifacts is not None:
        _require(value['artifacts_sha256'] == content_hash(artifacts), 'failure artifacts differ')
    return deepcopy(value)


def _validate_reference(value):
    fields = {'kind','program_id','source','source_sha256','selection_score','measurement','failure','saved_evaluation'}
    _require(type(value) is dict and set(value) == fields and type(value['source']) is str,
             'invalid input source fields')
    _require(value['source_sha256'] == source_sha256(value['source']), 'input source hash differs')
    validate_saved_evaluation(value['saved_evaluation'], source_sha256=value['source_sha256'])
    measure = value['measurement']
    _require(type(measure) is dict and set(measure) == {'status','record','aliases'}
             and type(measure['aliases']) is list, 'invalid measurement fields')
    if value['kind'] == 'failed_candidate':
        _require(value['program_id'] is None and value['selection_score'] is None,
                 'failed source cannot claim an admitted program or score')
        validate_failure(value['failure'], value['source'])
        _require(measure == dict(status='unavailable', record=None, aliases=[]),
                 'failed source cannot borrow a canonical measurement')
        return
    _require(value['kind'] == 'program' and type(value['program_id']) is str and value['program_id']
             and _number(value['selection_score']) and value['failure'] is None, 'invalid admitted source')
    if measure['status'] == 'unavailable':
        _require(measure == dict(status='unavailable', record=None, aliases=[]),
                 'unavailable measurement contains evidence')
        return
    _require(measure['status'] == 'recorded', 'unknown measurement status')
    record = _validate_record(measure['record'])
    _require(record['scope'] == 'unpaired' and record['child_source_sha256'] == value['source_sha256'],
             'measurement source differs')
    ident, seen = value['program_id'], set()
    for alias in measure['aliases']:
        _require(type(alias) is dict and alias.get('program_id') == ident and ident not in seen
                 and alias.get('source_sha256') == value['source_sha256']
                 and alias.get('reference_record_sha256') == record['record_sha256']
                 and alias.get('score') == record['child_observation']['score'], 'measurement alias differs')
        cases = record['child_observation'].get('case_vector')
        _require(cases is None or alias.get('cases_sha256') == cases['cases_sha256'], 'alias cases differ')
        seen.add(ident)
        ident = alias.get('reference_program_id')
    _require(record['child_program_id'] == ident, 'measurement program differs')


def validate_targets(value, *, snapshot=None, task_hash=None):
    fields = {'schema','run_id','task_hash','frozen_at','ancestry_parent','selected','population_best','sha256'}
    _require(type(value) is dict and set(value) == fields and value['schema'] == SCHEMA,
             'missing/unsupported frozen input contract')
    _require(all(type(value[k]) is str and value[k] for k in ('run_id','task_hash')), 'missing run/task identity')
    _require(value['sha256'] == content_hash({k:v for k,v in value.items() if k != 'sha256'}), 'snapshot digest differs')
    frozen = value['frozen_at']
    _require(type(frozen) is dict and set(frozen) == {'iteration','B_evals'}
             and all(type(n) is int and n >= 0 for n in frozen.values()), 'invalid frozen counters')
    ancestry = value['ancestry_parent']
    _require(type(ancestry) is dict and set(ancestry) == {'program_id','source_sha256'}
             and type(ancestry['program_id']) is str and ancestry['program_id'], 'invalid ancestry reference')
    require_hash(ancestry['source_sha256'], 'ancestry source')
    _validate_reference(value['selected'])
    selected = value['selected']
    validate_saved_evaluation(selected['saved_evaluation'], source_sha256=selected['source_sha256'],
                             task_hash=value['task_hash'], run_id=value['run_id'])
    if selected['kind'] == 'program':
        _require(selected['program_id'] == ancestry['program_id']
                 and selected['source_sha256'] == ancestry['source_sha256'], 'selected ancestry differs')
    if value['population_best'] is not None:
        _validate_reference(value['population_best'])
        _require(value['population_best']['kind'] == 'program', 'champion is not an admitted program')
        validate_saved_evaluation(value['population_best']['saved_evaluation'],
            source_sha256=value['population_best']['source_sha256'], task_hash=value['task_hash'], run_id=value['run_id'])
    if task_hash is not None:
        _require(value['task_hash'] == task_hash, 'input belongs to another task')
    if snapshot is not None:
        _require(selected['source'] == snapshot.parent_code
                 and ancestry['program_id'] == snapshot.parent_id, 'input differs from generation snapshot')
    return deepcopy(value)


def input_binding(inputs):
    targets = validate_targets(inputs.get('research_targets'), task_hash=inputs['task'].get('task_hash'))
    selected, best = targets['selected'], targets['population_best']
    score = (selected['measurement']['record']['child_observation']['score']
             if selected['measurement']['status'] == 'recorded' else None)
    _require(inputs.get('parent_program_id') == selected['program_id']
             and inputs.get('parent_source') == selected['source']
             and inputs.get('parent_score') == score
             and inputs.get('ancestry_parent_id') == targets['ancestry_parent']['program_id'],
             'compatibility input aliases differ from frozen sources')
    return dict(candidate_id=selected['program_id'], target_kind=selected['kind'],
        target_source_sha256=selected['source_sha256'],
        ancestry_parent_id=targets['ancestry_parent']['program_id'], research_targets_sha256=targets['sha256'],
        population_best_id=best['program_id'] if best else None,
        population_best_source_sha256=best['source_sha256'] if best else None)
