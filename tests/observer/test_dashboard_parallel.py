"""Dashboard execution evidence stays recorded, bounded and source-bound."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
import socket

from arena.observers.sciel.architecture import architecture
from arena.observers.sciel.data import RunStore
from arena.observers.sciel.parallel import parallel_view, runtime_parallel
from arena.observers.sciel.population import population_view


def config():
    return dict(parallel_search=dict(enabled=True, workers=4, host_llm_slots=12,
        provider_slots=8, host_evaluator_slots=2, max_inflight_per_island=1,
        max_inflight_per_parent=1))


def test_old_serial_and_missing_records_are_not_relabelled_parallel():
    old = parallel_view({'config': {'inflight_cap': 4}}, {}, [])
    assert old['status'] == 'unknown' and set(old['limits'].values()) == {None}
    assert old['feedback'] is None
    disabled = parallel_view({'config': {'parallel_search': {'enabled': False, 'workers': 4}}}, {}, [])
    assert disabled['status'] == 'disabled' and disabled['feedback'] is None
    assert parallel_view({}, {'config': config()}, [])['source'] == 'checkpoint.config.parallel_search'


def test_config_limits_and_bounded_committed_wave_history_are_not_utilization():
    rows = []
    for wave in range(35):
        base = dict(event='decision', policy='parallel_search', wave=wave)
        rows += [dict(base, action='wave_dispatch', jobs=4, workers=4, bootstrap=False),
                 dict(base, action='io_receipt', kind='llm', status='returned'),
                 dict(base, action='io_receipt', kind='evaluation', status='returned'),
                 dict(base, action='wave_complete', calls=2, evaluations=1, elapsed_seconds=4., cost_total=wave*.1)]
    original = deepcopy(rows)
    view = parallel_view({'config': config()}, {}, rows)
    assert rows == original and view['status'] == 'enabled'
    assert view['limits'] == {key: value for key, value in config()['parallel_search'].items() if key != 'enabled'}
    assert view['observed_waves'] == 35 and view['history_limited']
    assert len(view['waves']) == 30 and view['waves'][0]['wave'] == 5
    assert view['waves'][-1]['recorded_llm_receipts'] == 1
    assert view['waves'][-1]['recorded_evaluation_receipts'] == 1
    assert view['waves'][-1]['status'] == 'committed'
    assert 'not measured' in view['notes'][0]
    fields = {f['key']: f for section in architecture({'config': config()}, {}, [])['sections'] for f in section['fields']}
    assert fields['parallel_search.host_evaluator_slots']['value'] == 2
    assert fields['feedback_timing']['status'] == 'recorded'
    assert 'feedback_timing' not in {f['key'] for section in architecture({}, {}, [])['sections'] for f in section['fields']}


def test_runtime_parallel_fields_require_schema_and_valid_literal_counts():
    assert runtime_parallel({}) is None
    value = runtime_parallel(dict(schema='sciel-parallel-runtime/1', wave=3, phase='generation',
        workers=4, jobs=4, pending_calls=3, pending_llm_calls=2, pending_evaluations=1,
        secret='must not project'))
    assert value['pending_calls'] == 3 and 'secret' not in value
    invalid = runtime_parallel(dict(schema='sciel-parallel-runtime/1', phase='<img>', workers=True,
        pending_calls=-1, pending_llm_calls='2', pending_evaluations=float('nan')))
    assert all(invalid[key] is None for key in ('phase', 'workers', 'pending_calls', 'pending_llm_calls', 'pending_evaluations'))


def test_interleaved_fresh_start_progress_counts_attempts_and_keeps_historical_runs_unchanged():
    fields = dict(portfolio_schedule='interleaved', wave_kind='evolution',
        portfolio_attempted=4, portfolio_total=24, eligible_islands=[0, 1, 2, 3],
        allocation=dict(schema='sciel-portfolio-allocation/1', next_kind='evolution'))
    runtime = runtime_parallel(dict(schema='sciel-parallel-runtime/1', workers=4, **fields))
    progress = runtime['portfolio']
    assert progress['attempted'] == progress['initial_batch_attempted'] == progress['initial_batch_total'] == 4
    assert progress['remaining'] == 20 and progress['eligible_islands'] == 4
    assert progress['wave_kind'] == 'evolution' and 'including failures' in progress['scope']
    policy = config();policy['parallel_search']['portfolio_schedule'] = 'interleaved'
    cp = dict(portfolio_bootstrap=dict(next_island=4, islands=24),
              parallel_search=dict(allocation=fields['allocation']))
    rows = [dict(event='decision',policy='parallel_search',action='wave_dispatch',wave=2,jobs=4,**fields)]
    view = parallel_view({'config':policy}, cp, rows)
    assert view['portfolio']['attempted'] == 4 and view['waves'][0]['portfolio']['wave_kind'] == 'evolution'
    assert 'portfolio' not in runtime_parallel(dict(schema='sciel-parallel-runtime/1', workers=4))
    assert 'portfolio' not in parallel_view({'config':config()}, cp, [])
    assert runtime_parallel(dict(schema='sciel-parallel-runtime/1', workers=4, **{
        **fields, 'portfolio_attempted':25}))['portfolio'] is None
    assert parallel_view({'config':policy}, {}, [])['portfolio'] is None


def test_runtime_matching_segment_controls_parallel_telemetry_and_snapshot_integration(tmp_path, monkeypatch):
    run = tmp_path/'run';run.mkdir()
    start = dict(event='run_start', run_id='scientific-a', segment_id='segment-a',
                 task='offline', config=config(), event_seq=1)
    journal = run/'sciel_events.jsonl';journal.write_text(json.dumps(start)+'\n')
    runtime = dict(schema='sciel-runtime/1', run_id='scientific-a', segment_id='segment-a',
        hostname=socket.gethostname(), pid=os.getpid(), status='running', stage='generating',
        stale_after_seconds=10, heartbeat_at=datetime.now(timezone.utc).isoformat(),
        parallel=dict(schema='sciel-parallel-runtime/1', wave=7, phase='generation', workers=4,
                      jobs=4, pending_calls=2, pending_llm_calls=1, pending_evaluations=1))
    path = run/'runtime.json';path.write_text(json.dumps(runtime))
    monkeypatch.setattr('arena.observers.sciel.data.process_matches', lambda _: True)
    store = RunStore([tmp_path])
    ident = store.discover()[0]['id'];snapshot = store.snapshot(ident)
    assert snapshot['parallel']['limits']['workers'] == 4
    assert snapshot['runtime']['active'] is True and snapshot['runtime']['parallel']['wave'] == 7
    runtime['segment_id'] = 'other';path.write_text(json.dumps(runtime))
    stale = store.snapshot(ident)['runtime']
    assert stale['verification'] == 'different_run' and not stale.get('parallel')


def test_source_diversity_counts_full_saved_membership_not_ids_or_rendered_subset(monkeypatch):
    cp = dict(iteration_no=2, db=dict(programs=[], islands=[
        dict(idx=0, members=['seed0', 'new'], grid={}),
        dict(idx=1, members=['seed1'], grid={})]))
    sources = {'seed0': {'code': 'x = 1\n'}, 'seed1': {'code': 'x = 1\n'}, 'new': {'code': 'x = 2\n'}}
    monkeypatch.setattr('arena.observers.sciel.population.MAX_MEMBERS', 1)
    result = population_view(cp, [], {}, sources)
    assert sum(len(island['members']) for island in result['islands']) == 2
    summary = result['source_summary']
    assert summary['member_count'] == 3 and summary['source_bound_members'] == 3
    assert summary['unique_sources'] == 2 and summary['known_identical_source_copies'] == 1
    assert summary['complete'] is True and summary['iteration'] == 2
    result = population_view(cp, [], {}, {'seed0': sources['seed0']})
    assert result['source_summary']['unique_sources'] is None
    assert result['source_summary']['known_unique_sources'] == 1
    assert result['source_summary']['complete'] is False


def test_unknown_population_count_or_missing_member_list_never_claims_complete_diversity():
    rows = [dict(event='population', iteration_no=1, islands=[dict(idx=0, n=4,
             members=[['p1', .2, 0]])])]
    view = population_view({}, rows, {}, {'p1': {'code': 'x=1'}})
    assert view['source_summary']['member_count'] == 4
    assert view['source_summary']['source_bound_members'] == 1
    assert view['source_summary']['unique_sources'] is None
    assert population_view({}, [], {}, {})['source_summary']['unique_sources'] is None
