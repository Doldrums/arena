"""Read-only journal compatibility extracted from sciel.eval.output_identity.

SCiEL source commit: 0d67f813dd4ac21dee304f2b0de0b0ce59bf4157.
Only dependency-reachable validators/readers/constants are retained.
"""
from __future__ import annotations

from copy import deepcopy


import hashlib


import json


import math


import re


SCHEMA = 'sciel-output-identity/1'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    """Strict JSON; no tuples, non-string keys, NaN, or implicit coercions."""
    def check(item, depth=0):
        require(depth <= 64, 'output identity JSON is too deep')
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is float:
            require(math.isfinite(item), 'nonfinite output identity number')
        elif type(item) is list:
            for child in item:
                check(child, depth + 1)
        elif type(item) is dict:
            require(all(type(key) is str for key in item), 'non-string JSON key')
            for child in item.values():
                check(child, depth + 1)
        else:
            raise ValueError('non-JSON output identity value')
    check(value)
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def require_hash(value, name):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None,
            'invalid ' + name)
    return value


def check_seal(value):
    require(type(value) is dict, 'sealed evidence must be an object')
    require_hash(value.get('sha256'), 'evidence sha256')
    require(value['sha256'] == digest({k: v for k, v in value.items() if k != 'sha256'}),
            'output evidence digest differs')


def validate_binding(value):
    require(type(value) is dict and {'task_hash', 'source_sha256', 'island_id'} <= set(value),
            'missing evaluation binding')
    for key in ('task_hash', 'source_sha256'):
        require_hash(value[key], key)
    island = value['island_id']
    require(island is None or (type(island) is int and island >= 0)
            or (type(island) is str and 0 < len(island) <= 256), 'invalid island_id')
    for key in ('request_sha256', 'receipt_sha256'):
        if key in value:
            require_hash(value[key], key)
    require(len(canonical(value)) <= 8192, 'evaluation binding exceeds limit')
    return deepcopy(value)


def _stage(reached, confirmed, confirmation):
    require(reached in ('smoke', 'full', 'confirm') and type(confirmed) is bool,
            'invalid selected output stage')
    if reached == 'confirm':
        require(type(confirmation) is dict and set(confirmation) == {
            'trials', 'selected_trial', 'selection'}, 'missing confirmation selection')
        require(type(confirmation['trials']) is int and confirmation['trials'] >= 1
                and type(confirmation['selected_trial']) is int
                and 0 <= confirmation['selected_trial'] < confirmation['trials']
                and type(confirmation['selection']) is str
                and 0 < len(confirmation['selection']) <= 128,
                'invalid confirmation selection')
        require(not confirmed or confirmation['trials'] >= 2, 'invalid confirmed trials')
        selected = {k: confirmation[k] for k in ('trials', 'selection')}
    else:
        require(confirmation is None and confirmed is False, 'unexpected confirmation selection')
        selected = None
    # Trial index identifies the observed draw, not the comparison population.
    # This matches only the selected output, never all confirmation trial outputs.
    return dict(reached=reached, confirmed=confirmed, confirmation=selected,
                selected_output_only=True)


def validate_identity(value):
    check_seal(value)
    require(set(value) == {'schema', 'scope', 'output_sha256', 'evidence', 'sha256'}
            and value['schema'] == SCHEMA, 'invalid output identity fields/schema')
    require_hash(value['output_sha256'], 'output_sha256')
    scope, evidence = value['scope'], value['evidence']
    require(type(scope) is dict and set(scope) == {'task_hash', 'evaluator_sha256', 'adapter',
        'stage', 'inputs', 'seeds', 'representation'}, 'invalid output identity scope')
    for key in ('task_hash', 'evaluator_sha256'):
        require_hash(scope[key], key)
    require(scope['adapter'] in ('canonical-json/1', 'native-circle-geometry/1'), 'unknown adapter')
    require(type(evidence) is dict and set(evidence) == {'source_sha256', 'artifact_sha256',
        'binding_sha256', 'invocation_id', 'selected_trial'}, 'invalid output evidence fields')
    for key in ('source_sha256', 'artifact_sha256', 'binding_sha256'):
        require_hash(evidence[key], key)
    require(type(evidence['invocation_id']) is str and 0 < len(evidence['invocation_id']) <= 128,
            'invalid output invocation_id')
    stage = scope['stage']
    require(type(stage) is dict and set(stage) == {'reached', 'confirmed', 'confirmation',
            'selected_output_only'} and stage['selected_output_only'] is True, 'invalid output stage scope')
    confirmation = stage['confirmation']
    if confirmation is not None:
        require(type(confirmation) is dict and set(confirmation) == {'trials', 'selection'},
                'invalid confirmation scope')
        confirmation = dict(confirmation, selected_trial=evidence['selected_trial'])
    else:
        require(evidence['selected_trial'] is None, 'unexpected selected trial')
    require(_stage(stage['reached'], stage['confirmed'], confirmation) == stage, 'stage scope differs')
    for name, kinds in (('inputs', ('task_fixed', 'artifact_sha256')),
                        ('seeds', ('unpaired', 'input_seed'))):
        item = scope[name]
        require(type(item) is dict and set(item) == {'kind', 'sha256'} and item['kind'] in kinds,
                'invalid ' + name + ' scope')
        if item['kind'] == 'unpaired':
            require(item['sha256'] is None, 'unpaired seed cannot claim a seed binding')
        else:
            require_hash(item['sha256'], name + ' sha256')
        if item['kind'] == 'task_fixed':
            require(item['sha256'] == scope['task_hash'], 'fixed input task differs')
    representation = scope['representation']
    if scope['adapter'] == 'canonical-json/1':
        require(representation == {'format': 'canonical-json/1'}, 'invalid JSON representation')
    else:
        require(type(representation) is dict and set(representation) == {
            'format', 'centers_dtype', 'radii_dtype'}
            and representation['format'] == 'centers26x2-radii26/1'
            and all(representation[k] in ('float16', 'float32', 'float64')
                    for k in ('centers_dtype', 'radii_dtype')), 'invalid geometry representation')
    require(len(canonical(value)) <= 16384, 'output identity exceeds limit')
    return deepcopy(value)
