"""Native display needs observed task validity, never a zero-score heuristic."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from arena.observers.sciel.compat.measurement import metric_context
from arena.observers.sciel.data import RunStore
from arena.observers.sciel.metric_display import MetricDisplay


def metric(*, ratio=True, task='synthetic/resource_yield', task_hash='a' * 64):
    semantics = dict(kind='validity_gated_ratio', score_units='dimensionless',
        numerator_case='completed_work', numerator_units='work_units', denominator=10.,
        validity_case='accepted', valid_value=1., invalid_score=0., invalid_numerator_value=0.,
        invalid_numerator_semantics='penalty_sentinel_not_physical_measurement') if ratio else None
    return metric_context(SimpleNamespace(qualified_name=task, task_hash=task_hash,
        primary_metric='yield_score', research_metric=semantics))


def display(m=None):
    m = metric() if m is None else m
    return MetricDisplay(m, task=m['task_name'], task_hash=m['task_hash'])


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def record(ident, score, numerator, *, valid=1., status='evaluated', source='child', m=None):
    m = metric() if m is None else m
    return dict(id=ident, child_id=ident.replace('r', 'p'), parent_id='p0', branch='p0',
        parent_source_sha256=sha('seed'), parent_score=.2,
        parent_cases={'accepted':1., 'completed_work':2.}, metric=m,
        iteration=1, island=0, operator='diff', source_sha256=sha(source), code_fragment=source,
        status=status, score=score, actual_delta=score - .2 if score is not None else None,
        evaluation=dict(ok=status == 'evaluated', score=score if score is not None else 0.,
            cases={'accepted':valid, 'completed_work':numerator}, reached='full',
            confirmed=False, raw_first_score=score if score is not None else 0.))


def test_generic_ratio_distinguishes_penalty_and_valid_zero_without_changing_scores():
    d = display()
    invalid, zero = record('r1', 0., 0., valid=0.), record('r2', 0., 0.)
    before = deepcopy([invalid, zero])
    a, b = d.record(invalid), d.record(zero)
    assert (a['status'], a['value'], a['raw_score']) == ('invalid_penalty', None, 0.)
    assert a['reason'] == 'invalid_task_result'
    assert (b['status'], b['value'], b['raw_score']) == ('measured', 0., 0.)
    assert b['label'] == 'completed_work' and b['units'] == 'work_units'
    assert [invalid, zero] == before


def test_value_comes_from_recorded_case_not_inverse_score_conversion():
    r = record('r1', .3, 3.0000000000000004)
    assert display().record(r)['value'] == r['evaluation']['cases']['completed_work']
    assert display().record(r)['value'] != .3 * 10


def test_failed_sentinels_never_become_measurements():
    r = record('r1', None, 0., valid=0., status='eval_failed')
    value = display().record(r)
    assert value['status'] == 'failed' and value['value'] is None and value['raw_score'] is None


@pytest.mark.parametrize('alter', ['missing_cases', 'missing_validity', 'missing_numerator',
    'bad_number', 'missing_metric', 'bad_hash', 'wrong_task', 'wrong_score', 'wrong_penalty'])
def test_incomplete_or_incompatible_observation_is_unknown(alter):
    r = record('r1', .4, 4.)
    if alter == 'missing_cases': r['evaluation'].pop('cases')
    elif alter == 'missing_validity': r['evaluation']['cases'].pop('accepted')
    elif alter == 'missing_numerator': r['evaluation']['cases'].pop('completed_work')
    elif alter == 'bad_number': r['evaluation']['cases']['completed_work'] = float('nan')
    elif alter == 'missing_metric': r.pop('metric')
    elif alter == 'bad_hash': r['metric']['sha256'] = '0' * 64
    elif alter == 'wrong_task': r['metric'] = metric(task='other/task')
    elif alter == 'wrong_score': r['evaluation']['score'] = .9
    else: r['evaluation']['cases']['accepted'] = 0.
    assert display().record(r)['status'] == 'unknown'
    assert display().record(r)['value'] is None


def test_unknown_legacy_descriptor_and_wrong_run_task_never_get_native_units():
    r = record('r1', 0., 0.)
    for d in [MetricDisplay(None, task='x', task_hash='a'*64),
              MetricDisplay(metric(), task='wrong', task_hash='a'*64),
              MetricDisplay(metric(), task='synthetic/resource_yield', task_hash='b'*64)]:
        result = d.record(r)
        assert result['status'] == 'unknown' and result['value'] is None
        assert result['raw_score'] == 0. and result['label'] == 'Controller score'


def test_ordinary_metric_uses_recorded_score_without_native_conversion():
    m = metric(ratio=False)
    r = record('r1', 0., 99., valid=0., m=m)
    value = display(m).record(r)
    assert value['status'] == 'measured' and value['value'] == 0.
    assert value['label'] == 'yield_score' and value['units'] is None


def write_run(tmp_path, *, tie=False, remeasured_parent=False, metadata=True):
    m = metric()
    records = [record('r1', 0., 0., valid=0., source='invalid'),
               record('r2', 0., 0., source='zero'),
               record('r3', None, 0., valid=0., status='eval_failed', source='failure')]
    if tie:
        records = [record('r1', .2, 2.0000000000000004, source='tie')]
    if not metadata:
        for r in records:
            r.pop('metric')
    programs = [dict(id='p0', code='seed', score=.2, cases={'accepted':1., 'completed_work':2.},
        island=0, parent_id=None, origin='seed')]
    rows = [dict(event='run_start', task=m['task_name'], resumed=False,
                 counters=dict(cost_total=0, iteration_no=0, B_evals=0)),
            dict(event='decision', policy='initialization', action='seed_program',
                 schema='sciel-initialization/1', program_id='p0', source='seed', source_sha256=sha('seed'),
                 measured=True, score=.2, seed_score=.2, island=0)]
    for i, r in enumerate(records, 1):
        rows.extend([dict(event='research', phase='outcome', experiment_id=r['id'], evidence=r),
            dict(event='iteration', iteration_no=i, B_evals=i, child_id=r['child_id'],
                parent_id='p0', child_code=r['code_fragment'], child_score=r['score'], pop_best=.2,
                island=0, meta={'research_id':r['id']}, reason='evaluated' if r['score'] is not None else 'eval_fail')])
        if r['score'] is not None:
            programs.append(dict(id=r['child_id'], code=r['code_fragment'], score=r['score'],
                cases=r['evaluation']['cases'], island=0, origin='gen', parent_id='p0'))
    if remeasured_parent:
        programs[0]['cases']['completed_work'] = 2.000000000000001
        rows.append(dict(event='iteration', reason='remeasurement', iteration_no=4,
            measurement_program_id='p0', measurement_ok=True, measurement_score=.2, pop_best=.2))
    rows = [dict(r, run_id='run', segment_id='segment', event_seq=i+1) for i, r in enumerate(rows)]
    (tmp_path/'sciel_events.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    cp = dict(identity={'task':m['task_name'], 'task_hash':m['task_hash']},
        research={'metric':m} if metadata else {}, iteration_no=len(records),
        db=dict(programs=programs, pop_best_id='p0', archive=['p1','p2'],
            islands=[dict(idx=0, members=[p['id'] for p in programs], best_id='p0', grid={'0,0':'p1','1,0':'p2'})]),
        provenance={'run_id':'run','journal_anchor':{'segment_id':'segment','event_seq':len(rows)}})
    (tmp_path/'checkpoint.json').write_text(json.dumps(cp))
    store = RunStore([tmp_path]); ident = store.discover()[0]['id']
    return store, ident, rows, cp


def test_public_routes_keep_raw_history_and_project_all_native_surfaces(tmp_path):
    store, ident, rows, cp = write_run(tmp_path)
    snapshot = store.snapshot(ident)
    trials = {x['id']:x for x in snapshot['trials']}
    assert [(trials[k]['score'], trials[k]['metric_display']['status']) for k in ('r1','r2','r3')] == [
        (0., 'invalid_penalty'), (0., 'measured'), (None, 'failed')]
    assert trials['r1']['display_delta'] is None
    assert trials['r2']['display_delta'] == -2.
    assert trials['r2']['actual_delta'] == -.2
    assert trials['r2']['parent_metric_display']['value'] == 2.
    points = {p['experiment_id']:p for p in snapshot['curves'] if p.get('experiment_id')}
    assert points['r1']['metric_display']['value'] is None
    assert points['r2']['metric_display']['value'] == 0.
    assert snapshot['stats']['seed_metric_display']['value'] == 2.
    assert snapshot['stats']['best_metric_display']['value'] == 2.
    for p in snapshot['curves']: assert p['best_metric_display']['value'] == 2.
    island = snapshot['population']['islands'][0]
    for container, key in [(island['members'],'id'), (island['grid'],'candidate_id'),
                            (snapshot['population']['archive']['members'],'id')]:
        values = {x[key]:x['metric_display'] for x in container}
        assert values['p1']['status'] == 'invalid_penalty'
        assert values['p2']['status'] == 'measured' and values['p2']['value'] == 0.
    assert island['best_metric_display']['value'] == 2.
    detail = store.detail(ident, 'p2')
    assert detail['metric_display']['value'] == 0. and detail['display_delta'] == -2.
    assert detail['code'] == 'zero'
    assert json.loads((tmp_path/'checkpoint.json').read_text()) == cp
    assert [json.loads(l) for l in (tmp_path/'sciel_events.jsonl').read_text().splitlines()] == rows


def test_equal_controller_score_does_not_replace_prior_best_native_value(tmp_path):
    store, ident, _, _ = write_run(tmp_path, tie=True)
    snapshot = store.snapshot(ident)
    point = snapshot['curves'][-1]
    assert point['metric_display']['value'] == 2.0000000000000004
    assert point['best_metric_display']['value'] == 2.


@pytest.mark.parametrize('kind', ['legacy', 'vq'])
@pytest.mark.parametrize('newer_journal', [False, True])
def test_storage_geometry_uses_its_own_recorded_native_measurements(tmp_path, kind, newer_journal):
    _, _, rows, cp = write_run(tmp_path)
    cp['config'] = {'container': {'kind': kind}, 'grid_bins': 10}
    cp['identity']['descriptor'] = {'kind': 'vq_niche'}
    cp['db']['niche'] = {'centroids': [[1., 0.], [0., 1.], [-1., 0.]]}
    cp['db']['islands'][0]['grid']['2,0'] = 'p0'
    if kind == 'vq':
        cp['db']['container'] = dict(config={'kind': 'vq'},
            vectors={'p0': [1., 0.], 'p1': [0., 1.], 'p2': [-1., 0.]},
            geometries={'0': dict(centres=[[1., 0.], [0., 1.], [-1., 0.]], centre_ids=[0, 1, 2])})
    if newer_journal:
        rows.append(dict(event='population', iteration_no=4, run_id='run', segment_id='segment',
            event_seq=len(rows)+1, islands=[dict(idx=0, n=1, cells=1, best=.9,
                members=[['later', .9, 4]], grid=[[1, 9, .9]])]))
    (tmp_path/'checkpoint.json').write_text(json.dumps(cp))
    (tmp_path/'sciel_events.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    store = RunStore([tmp_path])
    snapshot = store.snapshot(store.discover()[0]['id'])
    population = snapshot['population']
    projection = population['storage']['projection']
    assert projection['available'] is True
    assert projection['stale'] is newer_journal
    assert population['source'] == ('journal' if newer_journal else 'checkpoint')
    bound = {p['program_id']: p['metric_display'] for p in projection['assignments']}
    assert bound['p0']['value'] == 2. and bound['p0']['raw_score'] == .2
    assert bound['p1']['status'] == 'invalid_penalty' and bound['p1']['value'] is None
    assert bound['p2']['status'] == 'measured' and bound['p2']['value'] == 0.
    for point in projection['points']:
        if point.get('program_id'):
            assert point['metric_display'] == bound[point['program_id']]
        else:
            assert 'metric_display' not in point, 'Centroids are not measured programs'
    for binding in population['storage']['assignments']:
        if newer_journal:
            assert binding['program_id'] is None
            assert binding['metric_display']['status'] == 'unknown'
        else:
            assert binding['metric_display'] == bound[binding['program_id']]
    assert json.loads((tmp_path/'checkpoint.json').read_text()) == cp
    assert [json.loads(line) for line in (tmp_path/'sciel_events.jsonl').read_text().splitlines()] == rows


def test_legacy_public_routes_preserve_raw_zero_without_inventing_physical_value(tmp_path):
    store, ident, _, _ = write_run(tmp_path, metadata=False)
    snapshot = store.snapshot(ident)
    a, b = snapshot['trials'][:2]
    assert a['score'] == b['score'] == 0.
    assert a['metric_display']['status'] == b['metric_display']['status'] == 'unknown'
    assert a['metric_display']['value'] is b['metric_display']['value'] is None
    assert snapshot['metric_display']['label'] == 'Controller score'


@pytest.mark.parametrize('bad_hash', ['g' * 64, 'f' * 64])
def test_wrong_parent_source_never_gets_native_delta(tmp_path, bad_hash):
    _, _, rows, _ = write_run(tmp_path)
    for row in rows:
        if row.get('event') == 'research':
            row['evidence']['parent_source_sha256'] = bad_hash
    (tmp_path/'sciel_events.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    store = RunStore([tmp_path]); value = store.snapshot(store.discover()[0]['id'])
    for trial in value['trials']:
        assert trial['parent_metric_display']['status'] == 'unknown'
        assert trial['display_delta'] is None


def test_remeasurement_does_not_rewrite_historical_seed_or_parent_native_values(tmp_path):
    store, ident, _, _ = write_run(tmp_path, remeasured_parent=True)
    snapshot = store.snapshot(ident)
    assert snapshot['curves'][0]['metric_display']['status'] == 'unknown'
    assert snapshot['stats']['seed_metric_display']['value'] is None
    assert snapshot['trials'][1]['parent_metric_display']['value'] == 2.
    assert snapshot['stats']['best_metric_display']['value'] == 2.000000000000001


def test_authentic_v18_invalid_penalty_and_valid_zero_records():
    fixture = json.loads((Path(__file__).parent/'fixtures/dashboard_v18_zero_observations.json').read_text())
    a, b = sorted(fixture['records'], key=lambda r:r['id'])
    assert (a['id'], b['id']) == ('r000004a1', 'r000007a1')
    assert a['score'] == b['score'] == 0.
    projection = display(a['metric'])
    assert projection.record(a)['status'] == 'invalid_penalty'
    assert projection.record(a)['value'] is None
    assert projection.record(b)['status'] == 'measured'
    assert projection.record(b)['value'] == 0.


def test_explicitly_unmeasured_seed_cannot_borrow_initialized_scalar_zero(tmp_path):
    m = metric(ratio=False)
    rows = [dict(event='run_start', task=m['task_name'], run_id='run', segment_id='s', event_seq=1),
        dict(event='decision', policy='initialization', action='seed_program',
            schema='sciel-initialization/1', program_id='p0', source='seed', source_sha256=sha('seed'),
            measured=False, score=None, seed_score=0., run_id='run', segment_id='s', event_seq=2)]
    (tmp_path/'sciel_events.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    cp = dict(identity={'task':m['task_name'],'task_hash':m['task_hash']}, research={'metric':m},
        db=dict(pop_best_id='p0', programs=[dict(id='p0',code='seed',score=0.,cases={},origin='seed')]),
        provenance=dict(run_id='run',journal_anchor={'segment_id':'s','event_seq':2}))
    (tmp_path/'checkpoint.json').write_text(json.dumps(cp))
    store = RunStore([tmp_path]); s = store.snapshot(store.discover()[0]['id'])
    assert s['stats']['best_score'] is None
    assert s['stats']['best_metric_display']['status'] == 'unknown'
    assert s['stats']['best_metric_display']['value'] is None
    assert s['programs'][0]['metric_display']['status'] == 'unknown'
