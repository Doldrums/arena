"""Whole-run dashboard facts without importing or executing candidate programs."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from arena.observers.sciel.result_history import MATCH_LIMIT, result_history_view
from arena.observers.sciel.data import RunStore


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False))


def seal(value, field):
    value.pop(field, None)
    value[field] = digest(value)
    return value


def observation(ident, code, numeric='shared', *, parent=None, evaluator='evaluator', dtype='float64', score=.8):
    return seal(dict(schema='sciel-observed-change/1', id='program:' + ident,
        scope='unpaired', child_program_id=ident, child_source_sha256=sha(code),
        parent_program_id=parent, status='different_geometry_unpaired',
        child_observation=dict(ok=True, validity=True, confirmed=False, reached='full', score=score,
            status='valid', reason='observed', geometry_status='validated',
            geometry=dict(numeric_sha256=sha(numeric), evaluator_sha256=sha(evaluator),
                centers_dtype=dtype, radii_dtype=dtype))), 'record_sha256')


def checkpoint(specs):
    """Specs: (program ID, code, output key, evaluation ID, origin, parent)."""
    programs, sources, evaluations, observations = [], {}, {}, []
    for ident, code, output, evaluation, origin, parent in specs:
        programs.append(dict(id=ident, code=code, score=.8, origin=origin, parent_id=parent,
                             cases={'validity': 1.0}, island=len(programs)))
        sources[sha(code)] = dict(source_sha256=sha(code), ast_sha256=sha('AST:' + code), code=code)
        evaluations.setdefault(evaluation, dict(id=evaluation, source_sha256=sha(code),
            aliases=[], islands=[], evaluation_ok=True))['aliases'].append(ident)
        observations.append(observation(ident, code, output, parent=parent))
    cp = dict(iteration_no=5, B_evals=5, db=dict(programs=programs, islands=[]),
        identity=dict(task_hash='task'),
        provenance=dict(journal_anchor=dict(segment_id='seg', event_seq=1)),
        candidate_novelty=dict(schema='sciel-candidate-novelty/1', identity=dict(ast_version='python-ast-fields-constants/1'),
            sources=list(sources.values()), records=list(evaluations.values())),
        observed_changes=dict(schema='sciel-observed-changes/1', identity=dict(metric=dict(task_hash='task'),
            geometry_policy='validated_native_numeric_sha256_same_evaluator_and_dtypes'), records=observations, aliases=[]))
    return reseal(cp)


def reseal(cp):
    seal(cp['candidate_novelty'], 'sha256')
    seal(cp['observed_changes'], 'state_sha256')
    return cp


class ResultHistoryTests(unittest.TestCase):
    def test_whole_run_nonparent_match_and_aliases_are_distinct(self):
        cp = checkpoint([('p1', 'seed', 'seed', 'e1', 'seed', None),
                         ('p2', 'seed', 'seed', 'e1', 'seed', None),
                         ('p3', 'different source A', 'output', 'e2', 'gen', 'p1'),
                         ('p4', 'different source B', 'output', 'e3', 'gen', 'p2')])
        original = copy.deepcopy(cp)
        view = result_history_view(cp, [])
        self.assertEqual(view['counts']['evaluations'], 3)
        self.assertEqual(view['counts']['unique_sources'], 3)
        self.assertEqual(view['counts']['source_aliases'], 1)
        self.assertEqual(view['counts']['repeated_outputs'], 1)
        self.assertEqual(view['by_program']['p4']['output_matches'], ['p3'])
        self.assertEqual(view['by_program']['p4']['earliest_output_match'], 'p3')
        self.assertEqual(view['by_program']['p4']['first_output_program_id'], 'p3')
        self.assertEqual(view['by_program']['p1']['output_match_count'], 0)
        self.assertEqual(view['by_program']['p1']['output_alias_matches'], ['p2'])
        self.assertEqual(view['by_program']['p2']['alias_kind'], 'seed_copy')
        self.assertEqual(cp, original)

    def test_same_score_and_even_source_do_not_establish_matching_output(self):
        cp = checkpoint([('p1', 'x=1', 'A', 'e1', 'gen', None),
                         ('p2', 'x=1', 'B', 'e2', 'gen', 'p1')])
        view = result_history_view(cp, [])
        self.assertEqual(view['counts']['repeated_outputs'], 0)
        self.assertEqual(view['by_program']['p2']['source_matches'], ['p1'])
        self.assertEqual(view['by_program']['p2']['ast_matches'], ['p1'])
        self.assertEqual(view['by_program']['p2']['output_matches'], [])

    def test_same_numeric_hash_requires_evaluator_and_dtype_compatibility(self):
        for field, value in [('evaluator_sha256', sha('other evaluator')), ('radii_dtype', 'float32')]:
            with self.subTest(field=field):
                cp = checkpoint([('p1', 'A', 'same', 'e1', 'gen', None), ('p2', 'B', 'same', 'e2', 'gen', None)])
                record = cp['observed_changes']['records'][1]
                record['child_observation']['geometry'][field] = value
                seal(record, 'record_sha256'); reseal(cp)
                self.assertEqual(result_history_view(cp, [])['counts']['repeated_outputs'], 0)

    def test_source_mismatch_invalid_record_and_failed_output_are_excluded(self):
        for mutation in ['source', 'checksum', 'invalid', 'task']:
            with self.subTest(mutation=mutation):
                cp = checkpoint([('p1', 'A', 'same', 'e1', 'gen', None), ('p2', 'B', 'same', 'e2', 'gen', None)])
                record = cp['observed_changes']['records'][1]
                if mutation == 'source': record['child_source_sha256'] = sha('not source')
                if mutation == 'checksum': record['record_sha256'] = '0' * 64
                if mutation == 'invalid': record['child_observation']['validity'] = False
                if mutation == 'task': cp['observed_changes']['identity']['metric']['task_hash'] = 'other'
                if mutation != 'checksum': seal(record, 'record_sha256')
                reseal(cp)
                view = result_history_view(cp, [])
                self.assertEqual(view['by_program']['p2']['output_status'], 'unavailable')
                self.assertIn(view['counts']['repeated_outputs'], [None, 0])

    def test_missing_state_is_unknown_not_zero_and_future_ast_is_unknown(self):
        view = result_history_view({}, [])
        self.assertIsNone(view['counts']['repeated_outputs'])
        self.assertIsNone(view['counts']['evaluations'])
        cp = checkpoint([('p1', 'A', 'same', 'e1', 'gen', None)])
        cp['candidate_novelty']['identity']['ast_version'] = 'future'
        reseal(cp)
        view = result_history_view(cp, [])
        self.assertIsNone(view['counts']['unique_asts'])
        self.assertIsNone(view['by_program']['p1']['ast_match_count'])

    def test_tampered_registry_does_not_turn_seed_copies_into_measurements(self):
        cp = checkpoint([('p1', 'A', 'same', 'e1', 'seed', None), ('p2', 'A', 'same', 'e1', 'seed', None)])
        cp['candidate_novelty']['records'][0]['evaluation_ok'] = False
        view = result_history_view(cp, [])
        self.assertFalse(view['coverage']['registry_available'])
        self.assertIsNone(view['counts']['repeated_outputs'])
        self.assertIsNone(view['by_program']['p2']['output_match_count'])
        self.assertFalse(view['by_program']['p2']['output_comparison_available'])

    def test_explicit_migrant_alias_preserves_measurement_identity(self):
        cp = checkpoint([('p1', 'A', 'same', 'e1', 'gen', None), ('p2', 'A', 'same', 'e1', 'migrant', 'p1')])
        cp['candidate_novelty']['records'][0]['aliases'] = ['p1']
        record = cp['observed_changes']['records'].pop()
        cp['observed_changes']['aliases'] = [dict(program_id='p2', reference_program_id='p1',
            source_sha256=sha('A'), reference_record_sha256=cp['observed_changes']['records'][0]['record_sha256'],
            score=.8, cases_sha256=digest({'validity': 1.0}))]
        reseal(cp)
        view = result_history_view(cp, [])
        self.assertEqual(view['by_program']['p2']['evaluation_id'], 'e1')
        self.assertEqual(view['by_program']['p2']['alias_kind'], 'migration_copy')
        self.assertEqual(view['by_program']['p2']['output_alias_matches'], ['p1'])
        self.assertEqual(view['counts']['repeated_outputs'], 0)
        self.assertEqual(view['counts']['source_aliases'], 1)

    def test_caps_matches_not_history_and_marks_newer_journal_stale(self):
        cp = checkpoint([('p'+str(i), str(i), 'same', 'e'+str(i), 'gen', None) for i in range(30)])
        rows = [dict(event='checkpoint', segment_id='seg', event_seq=1, iteration_no=5),
                dict(event='decision', policy='observed_change', segment_id='seg', event_seq=2, iteration_no=5)]
        view = result_history_view(cp, rows)
        self.assertEqual(view['by_program']['p29']['output_match_count'], 29)
        self.assertEqual(len(view['by_program']['p29']['output_matches']), MATCH_LIMIT)
        self.assertEqual(view['counts']['repeated_outputs'], 29)
        self.assertTrue(view['coverage']['stale'])
        self.assertFalse(view['coverage']['journal_outputs_included'])

    def test_malformed_sealed_ids_do_not_crash_projection(self):
        for mutation in ['observed_id', 'registry_sha', 'alias_id']:
            with self.subTest(mutation=mutation):
                cp = checkpoint([('p1', 'A', 'same', 'e1', 'gen', None)])
                if mutation == 'observed_id':
                    cp['observed_changes']['records'][0]['child_program_id'] = []
                elif mutation == 'registry_sha':
                    cp['candidate_novelty']['records'][0]['source_sha256'] = []
                else:
                    cp['observed_changes']['aliases'] = [{'program_id': [], 'reference_program_id': 'p1'}]
                reseal(cp)
                view = result_history_view(cp, [])
                self.assertIn('p1', view['by_program'])
                if mutation == 'registry_sha':
                    self.assertFalse(view['coverage']['registry_available'])
                elif mutation == 'observed_id':
                    self.assertFalse(view['by_program']['p1']['output_comparison_available'])

    def test_pending_or_failed_measurement_cannot_supply_an_output_match(self):
        for status in [None, False]:
            with self.subTest(status=status):
                cp = checkpoint([('p1', 'A', 'same', 'e1', 'gen', None), ('p2', 'B', 'same', 'e2', 'gen', None)])
                cp['candidate_novelty']['records'][1]['evaluation_ok'] = status
                reseal(cp)
                view = result_history_view(cp, [])
                self.assertEqual(view['coverage']['output_evaluations'], 1)
                self.assertEqual(view['by_program']['p1']['output_match_count'], 0)
                self.assertFalse(view['by_program']['p2']['output_comparison_available'])

    def test_actual_evaluator_decision_marks_same_iteration_coverage_stale(self):
        cp = checkpoint([('p1', 'A', 'same', 'e1', 'gen', None)])
        for policy in ['evaluation', 'candidate_measurement']:
            with self.subTest(policy=policy):
                rows = [dict(event='checkpoint', segment_id='seg', event_seq=1, iteration_no=5),
                        dict(event='decision', policy=policy, action='result', segment_id='seg',
                             event_seq=2, iteration_no_before=5)]
                self.assertTrue(result_history_view(cp, rows)['coverage']['stale'])

    def test_three_thousand_copies_and_repeated_outputs_keep_bounded_links(self):
        # Both large seed-alias and output-match groups are realistic long-run
        # shapes. Only the per-group count is full; each member gets <=12 links.
        for separate_evaluations in [False, True]:
            with self.subTest(separate_evaluations=separate_evaluations):
                cp = checkpoint([('p'+str(i), str(i) if separate_evaluations else 'seed', 'same',
                    'e'+str(i) if separate_evaluations else 'e1', 'gen' if separate_evaluations else 'seed', None)
                    for i in range(3000)])
                view = result_history_view(cp, [])
                last = view['by_program']['p2999']
                self.assertEqual(len(view['by_program']), 3000)
                self.assertEqual(last['output_match_count'], 2999 if separate_evaluations else 0)
                self.assertEqual(last['output_alias_count'], 0 if separate_evaluations else 2999)
                self.assertEqual(view['counts']['repeated_outputs'], 2999 if separate_evaluations else 0)
                self.assertLessEqual(len(last['output_matches']), MATCH_LIMIT)
                self.assertLessEqual(len(last['source_matches']), MATCH_LIMIT)
                self.assertLessEqual(len(last['output_alias_matches']), MATCH_LIMIT)

    def test_run_store_snapshot_and_research_alias_detail(self):
        cp = checkpoint([('p1', 'A', 'same', 'e1', 'gen', None), ('p2', 'B', 'same', 'e2', 'gen', 'p1')])
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            cp['provenance'] = dict(run_id='run', journal_anchor=dict(segment_id='seg', event_seq=2))
            (directory / 'checkpoint.json').write_text(json.dumps(cp))
            rows = [dict(event='run_start', run_id='run', segment_id='seg', event_seq=1),
                    dict(event='iteration', run_id='run', segment_id='seg', event_seq=2,
                        iteration_no=5, child_id='p2', child_score=.8, parent_id='p1', meta=dict(research_id='r2'))]
            (directory / 'sciel_events.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            store = RunStore([directory])
            ident = store.discover()[0]['id']
            snapshot = store.snapshot(ident)
            self.assertEqual(snapshot['result_history']['counts']['repeated_outputs'], 1)
            self.assertEqual(store.detail(ident, 'p2')['result_history']['output_matches'], ['p1'])
            self.assertEqual(store.detail(ident, 'r2')['result_history']['output_matches'], ['p1'])


if __name__ == '__main__':
    unittest.main()
