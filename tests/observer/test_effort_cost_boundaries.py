"""Execution time stops at evidence; historical tariffs never become billing."""
from datetime import datetime, timezone
import json

import pytest

from arena.observers.sciel import effort
from arena.observers.sciel.cost_accounting import receipt_amounts
from test_dashboard_effort import fixture


def clock(monkeypatch):
    class Clock(datetime):
        current = '2026-09-20T11:00:00+00:00'

        @classmethod
        def now(cls, tz=None):
            return datetime.fromisoformat(cls.current).astimezone(tz or timezone.utc)

    monkeypatch.setattr(effort, 'datetime', Clock)
    return Clock


@pytest.mark.parametrize('reason', ['budget', 'error', 'paused', 'interrupted'])
def test_recorded_run_end_freezes_elapsed_but_keeps_late_billing_receipts(tmp_path, monkeypatch, reason):
    timer = clock(monkeypatch)
    start, rows, basis, _ = fixture(tmp_path)
    end = dict(event='run_end', run_id='run-1', segment_id='s1', reason=reason,
               timestamp='2026-09-20T10:00:04+00:00')
    rows.append(end)
    with (tmp_path / 'sciel_events.jsonl').open('a') as stream:
        stream.write(json.dumps(end) + '\n')
    original = {str(p): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    monitor = effort.EffortMonitor()
    first = monitor.observe(tmp_path, start, rows, basis)['total']
    timer.current = '2026-10-20T11:00:00+00:00'
    later = monitor.observe(tmp_path, start, rows, basis)['total']
    assert first['wall_seconds'] == later['wall_seconds'] == 4
    assert later['terminal'] is True and later['live'] is False
    assert later['wall_source'] == 'journal_run_end'
    # The second paid response arrives after the terminal timestamp. Its
    # authenticated charge is retained without extending execution time.
    assert first['reported_usd'] == later['reported_usd'] == .5
    assert later['physical_llm_calls'] == 2
    assert original == {str(p): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


@pytest.mark.parametrize('status', ['completed', 'failed', 'interrupted', 'paused', 'stopped'])
def test_same_run_terminal_runtime_without_run_end_freezes_elapsed(tmp_path, monkeypatch, status):
    timer = clock(monkeypatch)
    start, rows, basis, _ = fixture(tmp_path)
    runtime = dict(available=True, verification='terminal_recorded', status=status,
        active=False, finished_at='2026-09-20T10:00:07+00:00')
    monitor = effort.EffortMonitor()
    first = monitor.observe(tmp_path, start, rows, basis, runtime=runtime)['total']
    timer.current = '2026-10-20T11:00:00+00:00'
    last = monitor.observe(tmp_path, start, rows, basis, runtime=runtime)['total']
    assert first['wall_seconds'] == last['wall_seconds'] == 7
    assert last['terminal'] is True and last['wall_source'] == 'runtime_terminal'


def test_missing_terminal_evidence_uses_recorded_boundary_without_claiming_completion(tmp_path, monkeypatch):
    timer = clock(monkeypatch)
    start, rows, basis, _ = fixture(tmp_path)
    monitor = effort.EffortMonitor()
    first = monitor.observe(tmp_path, start, rows, basis)['total']
    timer.current = '2026-10-20T11:00:00+00:00'
    last = monitor.observe(tmp_path, start, rows, basis,
        runtime={'verification':'different_run','finished_at':timer.current})['total']
    assert first['wall_seconds'] == last['wall_seconds'] == 5
    assert last['terminal'] is False and last['live'] is False
    assert last['wall_source'] == 'last_recorded_boundary'


def test_only_verified_live_runtime_advances_elapsed(tmp_path, monkeypatch):
    timer = clock(monkeypatch)
    start, rows, basis, _ = fixture(tmp_path)
    runtime = dict(available=True, verification='live_process', status='running', active=True)
    monitor = effort.EffortMonitor()
    timer.current = '2026-09-20T10:00:10+00:00'
    assert monitor.observe(tmp_path, start, rows, basis, runtime=runtime)['total']['wall_seconds'] == 10
    timer.current = '2026-09-20T10:00:12+00:00'
    last = monitor.observe(tmp_path, start, rows, basis, runtime=runtime)['total']
    assert last['wall_seconds'] == 12 and last['live'] is True and last['terminal'] is False


def test_old_segment_end_does_not_stop_resumed_live_run(tmp_path, monkeypatch):
    timer = clock(monkeypatch)
    start, rows, basis, _ = fixture(tmp_path)
    rows += [dict(event='run_end', run_id='run-1', segment_id='s1', timestamp='2026-09-20T10:00:07+00:00'),
             dict(start, segment_id='s2', timestamp='2026-09-20T10:00:10+00:00')]
    timer.current = '2026-09-20T10:00:20+00:00'
    boundary = effort.effort_boundary(rows, [], rows[-1],
        {'available':True,'status':'running','active':True,'verification':'live_process'}, timer.current)
    assert boundary == (timer.current, 'verified_live', False, True)


@pytest.mark.parametrize('kind,field', [('token_estimate','estimated_usd'), ('legacy','unattributed_recorded_usd')])
def test_historical_tariff_or_unclassified_counter_is_not_reported_billing(tmp_path, kind, field):
    start, rows, basis, _ = fixture(tmp_path, cost_kind=kind)
    view = effort.EffortMonitor().observe(tmp_path, start, rows, basis)
    assert view['total']['reported_usd'] is None
    assert view['total'][field] == .5 and view['to_best'][field] == .2
    assert view['total']['unknown_cost_calls'] == 2
    assert view['total']['cpu_seconds'] is None and view['total']['cpu_usd'] is None
    assert view['total']['all_in_usd'] is None and view['total']['cpu_cost_status'] == 'not_recorded'


@pytest.mark.parametrize('provenance', [None, {'source':'provider_reported'},
    {'schema':'sciel-llm-cost-provenance/1','source':'provider_reported','reported_cost':2},
    {'schema':'sciel-llm-cost-provenance/1','source':'token_estimate','pricing_key':'default',
     'prompt_usd_per_1k':.01,'completion_usd_per_1k':0}])
def test_invalid_cost_provenance_preserves_amount_without_billing_claim(provenance):
    result = receipt_amounts({'cost':1,'prompt_tokens':1000,'completion_tokens':0,'cost_provenance':provenance})
    assert result['reported_usd'] is None and result['estimated_usd'] is None
    assert result['unattributed_recorded_usd'] == result['recorded_usd'] == 1


def test_legacy_accounting_projection_keeps_raw_values_without_asserting_paid_dollars(tmp_path):
    from arena.observers.sciel.data import RunStore
    rows = [dict(event='run_start', run_id='r', segment_id='s', timestamp='2026-09-20T10:00:00+00:00',
                 config={'llm':{'cost_reporting':'estimated_uncached_token_rates'}}),
            dict(event='run_end', run_id='r', segment_id='s', timestamp='2026-09-20T10:00:07+00:00', cost_total=12.5)]
    path = tmp_path / 'sciel_events.jsonl'
    path.write_text(''.join(json.dumps(r) + '\n' for r in rows))
    raw = path.read_bytes()
    store = RunStore([tmp_path], timing_cache_dir=tmp_path/'timing')
    run = store.discover()[0]
    snapshot = store.snapshot(run['id'])
    assert snapshot['stats']['cost_total'] == snapshot['stats']['estimated_llm_usd'] == 12.5
    assert run['committed_effort']['known_llm_usd'] is None
    assert run['committed_effort']['provider_reported_llm_usd'] is None
    assert run['committed_effort']['cost_basis'] == 'token_estimate'
    assert path.read_bytes() == raw


def test_runstore_passes_same_run_failed_runtime_to_effort_cutoff(tmp_path, monkeypatch):
    from arena.observers.sciel.data import RunStore
    timer = clock(monkeypatch)
    start, rows, basis, _ = fixture(tmp_path)
    runtime = dict(schema='sciel-runtime/1', run_id=start['run_id'], segment_id=start['segment_id'],
        status='failed', stage='finished', started_at=start['timestamp'],
        finished_at='2026-09-20T10:00:09+00:00', heartbeat_at='2026-09-20T10:00:09+00:00')
    (tmp_path/'runtime.json').write_text(json.dumps(runtime))
    store = RunStore([tmp_path], timing_cache_dir=tmp_path/'timings')
    run = store.discover()[0]
    first = store.snapshot(run['id'])
    timer.current = '2026-10-20T11:00:00+00:00'
    later = store.snapshot(run['id'])
    assert first['effort']['total']['wall_seconds'] == later['effort']['total']['wall_seconds'] == 9
    assert later['effort']['total']['wall_source'] == 'runtime_terminal'
    assert later['effort']['total']['terminal'] is True
    assert later['runtime']['status'] == 'failed'


def test_elapsed_does_not_start_at_a_foreign_run_in_reused_archive():
    rows = [dict(event='run_start', run_id='old', timestamp='2026-09-01T10:00:00+00:00'),
            dict(event='run_start', run_id='new', timestamp='2026-09-20T10:00:00+00:00')]
    scope = effort.EffortMonitor._scope([], '2026-09-20T10:00:05+00:00', True, rows, run_id='new')
    assert scope['wall_seconds'] == 5
