"""Classify recorded provider failures without guessing from exception prose."""
import math


def provider_failure(error):
    """Keep numeric protocol facts only; never forward upstream bodies/messages."""
    if not isinstance(error, dict):
        return None
    status = error.get('http_status')
    if type(status) is not int or not 400 <= status <= 599:
        return None
    category = ('provider_rate_limit' if status == 429 else
                'provider_unavailable' if status >= 500 else
                'provider_authentication' if status in (401, 403) else
                'provider_request_rejected')
    result = dict(category=category, http_status=status)
    delay = error.get('retry_after_seconds')
    if type(delay) in (int, float) and math.isfinite(delay) and 0 <= delay <= 86400:
        result['retry_after_seconds'] = delay
    return result


def run_failure(rows, start, wave, status):
    """An error receipt is evidence of a provider failure, not proof of no charge.

    Unpublished calls are accepted only from WaveSpendMonitor's checksum-bound
    current wave. Earlier segments and arbitrary orphan traces cannot explain
    this segment's stop. Scientific outcomes and counters remain untouched.
    """
    if status not in {'stopped', 'failed', 'interrupted', 'paused'}:
        return None
    failures = []
    for row in rows:
        if (row.get('run_id') != start.get('run_id')
                or row.get('segment_id') != start.get('segment_id')
                or row.get('event') != 'research'
                or row.get('phase') not in {'generation_error', 'aux_stopped'}):
            continue
        error = provider_failure(row.get('llm_error'))
        if error:
            failures.append(dict(error, source='committed_journal',
                event_seq=row.get('event_seq'), outcome_unknown=
                row.get('generation_dispatch') != 'not_dispatched'))
    if isinstance(wave, dict) and wave.get('available') is True:
        failures.extend(dict(error, source='current_wave_receipt', wave=wave['wave'])
                        for error in wave.get('provider_failures', []))
    if not failures:
        return None
    codes = sorted({failure['http_status'] for failure in failures})
    labels = {429: 'Model API rate limit', 401: 'Model API authentication failed',
              403: 'Model API access rejected'}
    label = '; '.join(f"{labels.get(code, 'Model API error')} (HTTP {code})" for code in codes)
    unknown = any(item['outcome_unknown'] for item in failures)
    return dict(schema='arena.run-failure/1', category=failures[-1]['category'],
        http_statuses=codes, failures=failures, outcome_unknown=unknown,
        summary=label + ('. Dispatched call outcome or usage is unknown.' if unknown else '.'),
        automatic_replay_allowed=False,
        note='HTTP status observed by the engine on its model route. This alone does not distinguish the gateway from the upstream provider. Original termination reason is retained.')
