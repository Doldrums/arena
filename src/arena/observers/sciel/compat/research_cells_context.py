"""Read-only journal compatibility extracted from sciel.engine.research_cells_context.

SCiEL source commit: 0d67f813dd4ac21dee304f2b0de0b0ce59bf4157.
Only dependency-reachable validators/readers/constants are retained.
"""
from __future__ import annotations

from copy import deepcopy


import json


from .replay_feedback import validate_feedback


from .decision_projection import validate_decision


CARD_SCHEMA = 'sciel-research-check/3'


def _json(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _identifier(value, *, optional=False):
    return ((optional and value is None) or
            (type(value) is str and 0 < len(value) <= 256
             and not any(ord(character) < 32 for character in value)))


def _card(value):
    fields = {'schema', 'cell_id', 'revision_id', 'question', 'source', 'observations',
              'interpretation', 'next_check', 'limitations', 'replay_comparison'}
    if type(value) is not dict:
        return None
    if value.get('schema') == 'sciel-research-check/4':
        fields.add('decision')
        if not validate_decision(value.get('decision')):
            return None
    elif value.get('schema') != CARD_SCHEMA:
        return None
    if set(value) != fields:
        return None
    if not all(_identifier(value[key]) for key in ('cell_id', 'revision_id')):
        return None
    if not all(type(value[key]) is str for key in ('question', 'interpretation', 'next_check')):
        return None
    if (type(value['limitations']) is not list or len(value['limitations']) > 32
            or any(type(item) is not str for item in value['limitations'])):
        return None
    source = value['source']
    if (type(source) is not dict or set(source) != {'tool_id', 'invocation_id', 'receipt_id', 'candidate_id',
                'target_kind','target_source_sha256','ancestry_parent_id','research_targets_sha256',
                'population_best_id','population_best_source_sha256'}
            or not all(_identifier(item, optional=True) for item in source.values())):
        return None
    if (source['target_kind'] not in ('program','failed_candidate')
            or (source['target_kind'] == 'failed_candidate' and source['candidate_id'] is not None)
            or (source['target_kind'] == 'program' and source['candidate_id'] is None)):
        return None
    if (source['ancestry_parent_id'] is None
            or (source['population_best_id'] is None) != (source['population_best_source_sha256'] is None)):
        return None
    for key in ('target_source_sha256','research_targets_sha256') + (
            ('population_best_source_sha256',) if source['population_best_id'] is not None else ()):
        if (type(source[key]) is not str or len(source[key]) != 64
                or any(c not in '0123456789abcdef' for c in source[key])):
            return None
    comparison = value['replay_comparison']
    if comparison is not None and (not validate_feedback(comparison)
            or comparison['tool_id'] != source['tool_id']
            or comparison['replay_receipt_id'] != source['receipt_id']):
        return None
    observation = value['observations']
    if (type(observation) is not dict or set(observation) != {'status', 'output_excerpt', 'resources'}
            or type(observation['status']) is not str or type(observation['output_excerpt']) is not str
            or type(observation['resources']) is not dict):
        return None
    try:
        _json(value)
    except (TypeError, ValueError, RecursionError):
        return None
    return deepcopy(value)
