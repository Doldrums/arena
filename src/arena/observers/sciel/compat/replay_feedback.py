"""Read-only journal compatibility extracted from sciel.research_tools.replay_feedback.

SCiEL source commit: 0d67f813dd4ac21dee304f2b0de0b0ce59bf4157.
Only dependency-reachable validators/readers/constants are retained.
"""
from __future__ import annotations

import re


SCHEMA = 'sciel-replay-feedback/1'


PINNED = ('method_id', 'input_sha256', 'source_sha256', 'runtime_sha256', 'limits')


REASONS = ('observations_match', 'independent_execution_passed', 'observations_differ',
           'reference_not_successful', 'replay_not_successful', 'binding_mismatch')


FIELDS = {'schema', 'tool_id', 'policy', 'status', 'matched', 'measurement_reproduced',
          'reason', 'reference_receipt_id', 'replay_receipt_id',
          'reference_observations_sha256', 'replay_observations_sha256',
          'binding_mismatches', 'changed_paths', 'changed_paths_omitted'}


def validate_feedback(value):
    """Validate presentation shape/consistency; receipt readers bind the facts."""
    def is_hash(item):
        return type(item) is str and re.fullmatch('[0-9a-f]{64}', item) is not None
    if type(value) is not dict or set(value) != FIELDS or value.get('schema') != SCHEMA:
        return False
    if any(not is_hash(value[k]) for k in ('tool_id', 'reference_receipt_id', 'replay_receipt_id')):
        return False
    if any(value[k] is not None and not is_hash(value[k]) for k in
           ('reference_observations_sha256', 'replay_observations_sha256')):
        return False
    if (value['policy'] not in ('exact_observations', 'independent_execution')
            or type(value['matched']) is not bool or type(value['measurement_reproduced']) is not bool
            or value['reason'] not in REASONS):
        return False
    expected_status = ('reproduced' if value['measurement_reproduced'] else 'independently_executed') if value['matched'] else 'not_reproduced'
    if (value['status'] != expected_status
            or value['measurement_reproduced'] != (value['matched'] and value['policy'] == 'exact_observations')
            or value['matched'] != (value['reason'] in ('observations_match', 'independent_execution_passed'))
            or value['reason'] == 'observations_match' and value['policy'] != 'exact_observations'
            or value['reason'] == 'independent_execution_passed' and value['policy'] != 'independent_execution'):
        return False
    fields = value['binding_mismatches']
    rows = value['changed_paths']
    if (type(fields) is not list or any(type(k) is not str or k not in PINNED for k in fields)
            or len(fields) != len(set(fields)) or value['matched'] and fields
            or type(rows) is not list or len(rows) > 8
            or type(value['changed_paths_omitted']) is not int or value['changed_paths_omitted'] < 0):
        return False
    before, after = value['reference_observations_sha256'], value['replay_observations_sha256']
    if (value['matched'] and (before is None or after is None)
            or value['reason'] == 'binding_mismatch' and not fields
            or value['reason'] == 'observations_differ' and
                (value['policy'] != 'exact_observations' or fields or before is None or after is None or before == after)):
        return False
    for row in rows:
        if (type(row) is not dict or set(row) != {'path', 'reference', 'replay'}
                or type(row['path']) is not str or len(row['path']) > 128
                or row['path'] and not row['path'].startswith('/')
                or any(type(row[k]) is not str or len(row[k]) > 80 for k in ('reference', 'replay'))):
            return False
    if value['reason'] == 'observations_match' and (rows or value['changed_paths_omitted']
            or value['reference_observations_sha256'] is None
            or value['reference_observations_sha256'] != value['replay_observations_sha256']):
        return False
    return True
