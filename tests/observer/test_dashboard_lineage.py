"""Progress links must follow saved identities, not coincident scores or steps."""
import hashlib
import json

import pytest

from arena.observers.sciel.data import RunStore


def sha(source):
    return hashlib.sha256(source.encode()).hexdigest()


def seed(ident, island=0):
    return dict(event='decision', policy='initialization', action='seed_program',
        schema='sciel-initialization/1', program_id=ident, source='seed source',
        source_sha256=sha('seed source'), score=.25, seed_score=.25, measured=True, island=island)


def outcome(ident, parent, score, source, *, iteration=1, island=0, status='evaluated', operator='diff'):
    return dict(event='research', phase='outcome', experiment_id=ident,
        evidence=dict(id=ident, parent_id=parent, parent_score=.25, iteration=iteration,
            island=island, status=status, score=score, source_sha256=sha(source),
            code_fragment=source, hypothesis={'text':'A recorded hypothesis.'}, operator=operator))


def snapshot(tmp_path, rows, programs=None):
    rows = [dict(event='run_start', task='fixture', counters=dict(cost_total=0,iteration_no=0,B_evals=0)), *rows]
    rows = [dict(row, run_id='run', segment_id='segment', event_seq=index+1) for index,row in enumerate(rows)]
    (tmp_path/'sciel_events.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    if programs is not None:
        (tmp_path/'checkpoint.json').write_text(json.dumps(dict(
            db={'programs':programs}, provenance={'run_id':'run','journal_anchor':{'segment_id':'segment','event_seq':len(rows)}})))
    store = RunStore([tmp_path])
    return store.snapshot(store.discover()[0]['id'])


def test_multiple_seed_copies_share_one_baseline_but_keep_distinct_parent_ids(tmp_path):
    value = snapshot(tmp_path, [seed('p1'),seed('p2',1),
        outcome('r1','p2',.6,'child'),
        dict(event='iteration',iteration_no=1,B_evals=1,child_id='p3',parent_id='p2',
             child_code='child',child_score=.6,model_used='actual-model',island=0,
             meta={'research_id':'r1'},cost=.01,op_used='diff')])
    baseline, child = value['curves']
    assert baseline['candidate_ids'] == ['p1','p2']
    assert baseline['candidate_id'] == 'p1' and baseline['parent_ids'] == []
    assert child['candidate_id'] == 'p3' and child['experiment_id'] == 'r1'
    assert child['parent_ids'] == ['p2'] and child['parent_score'] == .25
    assert child['model'] == 'actual-model' and child['hypothesis'] == 'A recorded hypothesis.'
    assert child['alias_ids'] == ['r1'] and child['code_available'] is True
    programs = {row['candidate_id']:row for row in value['programs']}
    assert programs['p2']['iteration'] == 0
    assert programs['p1']['point_id'] == programs['p2']['point_id'] == baseline['point_id']
    assert 'r1' not in programs
    assert len(value['curves']) == 2


@pytest.mark.parametrize('explicit', [False,True])
def test_crossover_never_invents_extra_parents_or_matches_by_iteration(tmp_path, explicit):
    row = dict(event='iteration',iteration_no=1,B_evals=1,child_id='p3',parent_id='p1',
        child_code='child A',child_score=.6,meta={'research_id':'r1','inspiration_ids':['invented']},op_used='cross')
    if explicit:
        row['parent_ids'] = ['p1','p2']
    value = snapshot(tmp_path, [seed('p1'),seed('p2',1),
        outcome('r1','p1',.6,'child A',operator='cross'),row,
        outcome('r2','p2',.6,'child B',island=1),
        dict(event='iteration',iteration_no=1,B_evals=2,child_id='p4',parent_id='p2',
             child_code='child B',child_score=.6,meta={'research_id':'r2'},island=1)])
    a,b = value['curves'][1:]
    assert (a['candidate_id'],b['candidate_id']) == ('p3','p4')
    assert a['parent_ids'] == (['p1','p2'] if explicit else ['p1'])
    assert b['parent_ids'] == ['p2']
    assert a['point_id'] != b['point_id']


@pytest.mark.parametrize('ambiguous', [False,True])
def test_portfolio_storage_alias_requires_unique_complete_recorded_fingerprint(tmp_path, ambiguous):
    programs=[dict(id='p1',code='seed source',score=.25,parent_id=None,island=0,origin='seed'),
        dict(id='p4',code='portfolio child',score=.8,parent_id='p1',island=0,origin='portfolio'),
        dict(id='p6',code='portfolio child',score=.8,parent_id='p4',island=1,origin='migrant')]
    if ambiguous:
        programs.append(dict(programs[1],id='p5'))
    value = snapshot(tmp_path,[seed('p1'),
        outcome('boot','p1',.8,'portfolio child',iteration=0),
        dict(event='decision',policy='portfolio_seed',action='portfolio',research=True,ok=True,
             island=0,cost=.01,meta={'research_id':'boot'},model_used='bootstrap-model')],programs)
    # Bootstrap admission requires a matching successful returned evaluation.
    # Supply it explicitly rather than deriving success from its finite score.
    # (The second read below exercises the normal public adapter path.)
    path=tmp_path/'sciel_events.jsonl'
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    rows[2]['evidence']['evaluation']={'ok':True,'score':.8}
    path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    store=RunStore([tmp_path]);value=store.snapshot(store.discover()[0]['id'])
    point=value['curves'][-1]
    assert point['kind'] == 'bootstrap' and point['candidate_id'] == 'boot'
    assert point['alias_ids'] == ([] if ambiguous else ['p4'])
    assert point['parent_ids'] == ['p1'] and point['model'] == 'bootstrap-model'
    assert point['iteration'] == 0
    lookup={row['candidate_id']:row for row in value['programs']}
    migrant=lookup['p6']
    assert migrant['parent_ids'] == ['p4']
    assert migrant['iteration'] is None and migrant['cost_total'] is None
    assert migrant['origin'] == 'migrant' and 'no separate evaluation' in migrant['lineage_note']
    assert ('p4' in lookup) is ambiguous


def test_failed_evaluation_has_identity_and_parent_but_no_measured_score(tmp_path):
    value=snapshot(tmp_path,[seed('p1'),outcome('r1','p1',None,'failed',status='eval_failed'),
        dict(event='iteration',iteration_no=1,B_evals=1,parent_id='p1',child_score=0,
             reason='eval_fail',meta={'research_id':'r1'})])
    point=value['curves'][-1]
    assert point['candidate_id'] == 'r1' and point['parent_ids'] == ['p1']
    assert point['score'] is None and point['status'] == 'eval_failed'
