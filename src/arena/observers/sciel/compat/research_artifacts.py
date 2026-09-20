"""Read-only journal compatibility extracted from sciel.engine.research_artifacts.

SCiEL source commit: 0d67f813dd4ac21dee304f2b0de0b0ce59bf4157.
Only dependency-reachable validators/readers/constants are retained.
"""
from __future__ import annotations

from .models import canonical_bytes, content_hash, require_hash


SCHEMA = 'sciel-saved-evaluation/1'


MAX_RECORD_BYTES = 32 * 1024 * 1024


MAX_INLINE_BYTES = 512 * 1024


def _validate_record(record):
    fields = {'schema', 'run_id', 'task_hash', 'evaluation_id', 'source_sha256',
              'result', 'reached', 'confirmed', 'raw_first_score', 'conditions'}
    if (type(record) is not dict or set(record) != fields or record['schema'] != SCHEMA
            or any(type(record[key]) is not str or not record[key]
                   for key in ('run_id', 'task_hash', 'evaluation_id'))
            or record['reached'] not in ('smoke', 'full', 'confirm')
            or type(record['confirmed']) is not bool
            or type(record['raw_first_score']) not in (int, float)):
        raise ValueError('invalid saved evaluation record schema')
    require_hash(record['source_sha256'], 'saved evaluation source')
    result = record['result']
    if (type(result) is not dict
            or set(result) != {'ok', 'score', 'cases', 'stderr', 'timing', 'cost', 'artifacts', 'confirmed_sampled'}
            or any(type(result[key]) is not bool for key in ('ok', 'confirmed_sampled'))
            or any(type(result[key]) not in (int, float) for key in ('score', 'timing', 'cost'))
            or result['timing'] < 0 or result['cost'] < 0
            or type(result['cases']) is not dict or type(result['artifacts']) is not dict
            or type(result['stderr']) is not str):
        raise ValueError('invalid saved returned evaluator fields')
    conditions = record['conditions']
    if (type(conditions) is not dict
            or set(conditions) != {'evaluator_sha256', 'stage_timeouts_seconds', 'per_run_timeout_seconds',
                'cpu_limit_seconds', 'memory_limit_bytes', 'confirm_n', 'search_seed_config',
                'evaluator_seed_status', 'timing_scope', 'result_scope'}
            or type(conditions['stage_timeouts_seconds']) is not dict
            or set(conditions['stage_timeouts_seconds']) != {'smoke', 'full', 'confirm'}):
        raise ValueError('invalid saved evaluation conditions')
    if conditions['evaluator_sha256'] is not None:
        require_hash(conditions['evaluator_sha256'], 'saved evaluator source')
    canonical_bytes(record)
    return record


def validate_saved_evaluation(value, *, source_sha256, task_hash=None, run_id=None):
    fields = {'status', 'reason', 'reference', 'record'}
    if type(value) is not dict or set(value) != fields:
        raise ValueError('invalid saved evaluation access contract')
    reference, record = value['reference'], value['record']
    if reference is not None:
        if (type(reference) is not dict
                or set(reference) != {'sha256', 'bytes', 'evaluation_id', 'source_sha256', 'task_hash'}
                or reference['source_sha256'] != source_sha256
                or (task_hash is not None and reference['task_hash'] != task_hash)
                or type(reference['bytes']) is not int or not 0 < reference['bytes'] <= MAX_RECORD_BYTES
                or type(reference['evaluation_id']) is not str or not reference['evaluation_id']):
            raise ValueError('saved evaluation reference differs from source/task')
        require_hash(reference['sha256'], 'saved evaluation reference')
    if value['status'] == 'unavailable':
        if record is not None or type(value['reason']) is not str or not value['reason']:
            raise ValueError('unavailable saved evaluation contains claimed values')
        return
    if (value['status'] != 'available' or value['reason'] is not None or reference is None
            or type(record) is not dict or record.get('schema') != SCHEMA
            or (run_id is not None and record.get('run_id') != run_id)
            or content_hash(record) != reference['sha256']
            or len(canonical_bytes(record)) != reference['bytes'] or reference['bytes'] > MAX_INLINE_BYTES
            or any(record.get(key) != reference[key] for key in ('source_sha256', 'task_hash', 'evaluation_id'))):
        raise ValueError('saved evaluation value differs from its immutable reference')
    _validate_record(record)
