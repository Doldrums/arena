"""Read-only journal compatibility extracted from sciel.engine.output_novelty.

SCiEL source commit: 0d67f813dd4ac21dee304f2b0de0b0ce59bf4157.
Only dependency-reachable validators/readers/constants are retained.
"""
from __future__ import annotations

from copy import deepcopy


from .output_identity import check_seal, digest, require, require_hash, validate_binding, validate_identity


VERDICT_SCHEMA = 'sciel-output-novelty-verdict/1'


def _id(value):
    require(type(value) is str and 0 < len(value) <= 512, 'invalid evaluation/program ID')
    return value


def _bound_identity(identity, binding):
    identity = validate_identity(identity)
    require(identity['scope']['task_hash'] == binding['task_hash']
            and identity['evidence']['source_sha256'] == binding['source_sha256']
            and identity['evidence']['binding_sha256'] == digest(binding), 'output/evaluation binding differs')
    return identity


def validate_verdict(value, *, source_sha256=None):
    check_seal(value)
    require(set(value) == {'schema', 'evaluation_id', 'accept', 'status', 'binding', 'identity',
                          'match', 'sha256'} and value['schema'] == VERDICT_SCHEMA,
            'invalid output novelty verdict fields/schema')
    _id(value['evaluation_id'])
    binding = validate_binding(value['binding'])
    if source_sha256 is not None:
        require_hash(source_sha256, 'expected source_sha256')
        require(binding['source_sha256'] == source_sha256, 'verdict source differs')
    status = value['status']
    require(status in ('unsupported', 'new_output', 'exact_recorded_repeat'), 'invalid output verdict status')
    require(type(value['accept']) is bool and value['accept'] is (status != 'exact_recorded_repeat'),
            'output admission differs from verdict')
    if status == 'unsupported':
        require(value['identity'] is None and value['match'] is None, 'unsupported evidence cannot match')
    else:
        _bound_identity(value['identity'], binding)
        if status == 'new_output':
            require(value['match'] is None, 'new output cannot have a match')
        else:
            match = value['match']
            require(type(match) is dict and set(match) == {'evaluation_id', 'source_sha256', 'island_id',
                'program_id'}, 'invalid output match fields')
            require(_id(match['evaluation_id']) != value['evaluation_id'], 'evaluation cannot repeat itself')
            validate_binding(dict(task_hash=binding['task_hash'], source_sha256=match['source_sha256'],
                                  island_id=match['island_id']))
            if match['program_id'] is not None:
                _id(match['program_id'])
    return deepcopy(value)
