"""Provider failures survive a native CampaignStopped without replay or repricing."""
import json

import pytest

from arena.observers.sciel.data import RunStore
from arena.observers.sciel.failures import provider_failure, run_failure
from arena.observers.sciel.parallel_cost import WaveSpendMonitor
from test_dashboard_parallel_cost import call, digest, wave, write


@pytest.mark.parametrize('code,category', [(500, 'provider_unavailable'), (429, 'provider_rate_limit')])
def test_stopped_wave_exposes_bound_error_in_detail_and_list(tmp_path, code, category):
    start, directory, _ = wave(tmp_path)
    path = call(directory, 'failed-call', status='error')
    receipt = json.loads((path / 'receipt.json').read_text())
    receipt['payload']['error'] = dict(http_status=code, cause_type='Private body',
        message='Bearer PRIVATE', retry_after_seconds=1)
    receipt['sha256'] = digest(receipt['payload'])
    write(path / 'receipt.json', receipt)
    write(tmp_path / 'runtime.json', dict(schema='sciel-runtime/1', run_id=start['run_id'],
        segment_id=start['segment_id'], status='failed', reason='CampaignStopped'))
    before = (tmp_path / 'checkpoint.json').read_bytes()
    store = RunStore([tmp_path], timing_cache_dir=tmp_path / 'timings')
    listed = store.discover()[0]
    assert listed['status_reason'] == 'CampaignStopped'
    assert f'HTTP {code}' in listed['stop_detail']
    failure = listed['failure']
    assert failure['category'] == category and failure['outcome_unknown']
    assert failure['automatic_replay_allowed'] is False
    assert failure['failures'][0]['receipt_sha256'] == receipt['sha256']
    assert failure['failures'][0]['source'] == 'current_wave_receipt'
    assert 'PRIVATE' not in json.dumps(failure) and 'Private body' not in json.dumps(failure)
    snap = store.snapshot(listed['id'])
    assert snap['run']['failure'] == failure
    assert (tmp_path / 'checkpoint.json').read_bytes() == before


def test_tampered_error_and_orphan_trace_cannot_explain_stop(tmp_path):
    start, directory, _ = wave(tmp_path)
    path = call(directory, 'failed-call', status='error')
    value = json.loads((path / 'receipt.json').read_text())
    value['payload']['error'] = {'http_status': 429}  # Deliberately stale digest.
    write(path / 'receipt.json', value)
    write(tmp_path / 'artifacts/llm_calls.jsonl', {'event': 'error', 'llm_error': {'http_status': 500}})
    view = WaveSpendMonitor().observe(tmp_path, start)
    assert view['available'] is False
    assert run_failure([], start, view, 'failed') is None


def test_completed_run_and_earlier_segments_are_not_reclassified():
    start = dict(run_id='a', segment_id='new')
    row = dict(run_id='a', segment_id='old', event='research', phase='generation_error',
               llm_error={'http_status': 429})
    assert run_failure([row], start, None, 'failed') is None
    row['segment_id'] = 'new'
    assert run_failure([row], start, None, 'completed') is None
    result = run_failure([row], start, None, 'stopped')
    assert result['http_statuses'] == [429]
    assert result['failures'][0]['source'] == 'committed_journal'


@pytest.mark.parametrize('status', [True, '429', None, 0, 399, 600])
def test_invalid_http_status_never_becomes_a_provider_failure(status):
    assert provider_failure({'http_status': status}) is None


def test_untrusted_retry_after_is_omitted():
    assert provider_failure({'http_status': 429, 'retry_after_seconds': float('nan')}) == {
        'category': 'provider_rate_limit', 'http_status': 429}
