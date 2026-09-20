"""Read-only journal compatibility extracted from sciel.research_tools.result_contract.

SCiEL source commit: 0d67f813dd4ac21dee304f2b0de0b0ce59bf4157.
Only dependency-reachable validators/readers/constants are retained.
"""
from __future__ import annotations

from .models import content_hash, detached


RESULT_SCHEMA = 'sciel-tool-result/1'


ASSESSMENT_SCHEMA = 'sciel-tool-result-assessment/1'


def parse_result(output):
    if (type(output) is not dict
            or set(output) != {'schema', 'status', 'observations', 'diagnostics', 'error'}
            or output.get('schema') != RESULT_SCHEMA
            or output.get('status') not in ('success', 'tool_error')
            or type(output.get('observations')) is not dict
            or type(output.get('diagnostics')) is not dict):
        raise ValueError('tool must return a sciel-tool-result/1 envelope with status, observations, diagnostics and error')
    error = output['error']
    if output['status'] == 'success':
        if error is not None:
            raise ValueError('successful tool result requires error=null')
    elif type(error) is not str or not error.strip():
        raise ValueError('tool_error requires a nonempty error string')
    return detached(output)


def assess_receipt(receipt):
    """Project a new-contract receipt without changing host evidence or cost."""
    host = receipt.get('status')
    result = dict(schema=ASSESSMENT_SCHEMA, host_status=host,
                  status='unknown' if host == 'unknown' else 'host_failed',
                  error=receipt.get('reason'), observations_sha256=None,
                  diagnostics_sha256=None)
    if host != 'ok' or receipt.get('dispatch_status') != 'invoked':
        return result
    try:
        output = parse_result(receipt.get('output'))
    except (ValueError, TypeError, RecursionError) as error:
        result.update(status='invalid_output', error=str(error))
        return result
    result.update(status=output['status'], error=output['error'],
                  observations_sha256=content_hash(output['observations']),
                  diagnostics_sha256=content_hash(output['diagnostics']))
    return result
