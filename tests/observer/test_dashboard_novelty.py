"""Recorded novelty/remeasurement projection; no engine or source execution."""
import json
from pathlib import Path
import tempfile
import unittest

from arena.observers.sciel.data import RunStore


class NoveltyDashboardTests(unittest.TestCase):
    def test_receipt_ast_diff_and_remeasurement_are_distinct_from_mutation_quality(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = dict(id='r2', status='no_child', iteration=2, parent_id='p1',
                            score=None, actual_delta=None, hypothesis=None)
            rows = [
                dict(event='run_start', task='test/fixture', resumed=False,
                     counters=dict(iteration_no=0, B_evals=0, n_remeasurements=0, cost_total=0)),
                dict(event='research', phase='outcome', experiment_id='r2', evidence=evidence),
                dict(event='decision', policy='candidate_novelty', accept=True, remeasurement=True,
                     match_kind='sha256', matched_program_id='evaluation:old', reason='previous_evaluation_failed',
                     neighbors=[dict(program_id='evaluation:old', similarity=1., ast_diff='', ast_diff_truncated=False)]),
                dict(event='decision', policy='candidate_measurement', action='start', remeasurement=True),
                dict(event='iteration', iteration_no=2, B_evals=1, reason='remeasurement', child_id=None,
                     measurement_program_id='p2', measurement_ok=True, measurement_score=.8, pop_best=.8,
                     meta=dict(research_id='r2', remeasurement=True), cost=.04),
            ]
            journal = root/'sciel_events.jsonl'
            journal.write_text(''.join(json.dumps(dict(row, run_id='run', segment_id='seg', event_seq=i+1))+'\n'
                                       for i, row in enumerate(rows)))
            store = RunStore([root]);view = store.snapshot(store.discover()[0]['id'])
            self.assertEqual(view['stats']['remeasurements'], 1)
            self.assertEqual(view['stats']['best_score'], .8)
            self.assertEqual(view['stats']['cost_total'], .04)
            self.assertEqual(view['best_candidate_id'], 'p2')
            trial = next(t for t in view['trials'] if t['id']=='r2')
            self.assertEqual(trial['status'], 'remeasurement')
            self.assertEqual(trial['measurement_score'], .8)
            self.assertIsNone(trial['score']);self.assertIsNone(trial['actual_delta'])
            self.assertTrue(all(point['score'] is None for point in view['curves']))
            receipt = next(e['data'] for e in view['events'] if e['data'].get('policy')=='candidate_novelty')
            self.assertEqual(receipt['neighbors'][0]['ast_diff'], '')

    def test_historical_missing_counter_stays_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'sciel_events.jsonl').write_text('{"event":"run_start","task":"test/fixture"}\n')
            store = RunStore([root])
            self.assertIsNone(store.snapshot(store.discover()[0]['id'])['stats']['remeasurements'])

    def test_output_repeat_cost_and_measurements_do_not_inflate_admission_clock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [
                dict(event='run_start', task='test/fixture'),
                dict(event='decision', policy='output_novelty', status='exact_recorded_repeat',
                     n_evaluation_results=4, n_output_repeats=3, evaluation_id='e4',
                     match=dict(evaluation_id='e1', program_id='p1'), accept=False),
                dict(event='iteration', iteration_no=1, B_evals=0, child=None,
                     reason='output_repeat_cap', cost=.09),
            ]
            (root/'sciel_events.jsonl').write_text(''.join(json.dumps(dict(row,
                run_id='run', segment_id='seg', event_seq=i+1))+'\n' for i,row in enumerate(rows)))
            store=RunStore([root]);view=store.snapshot(store.discover()[0]['id'])
            self.assertEqual(view['stats']['evaluations'], 0)
            self.assertEqual(view['stats']['measured_results'], 4)
            self.assertEqual(view['stats']['repeated_outputs'], 3)
            self.assertAlmostEqual(view['stats']['cost_total'], .09)
            receipt=next(e['data'] for e in view['events'] if e['data'].get('policy')=='output_novelty')
            self.assertEqual(receipt['match']['program_id'], 'p1')


if __name__ == '__main__':
    unittest.main()
