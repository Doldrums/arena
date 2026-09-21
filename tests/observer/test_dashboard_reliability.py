"""Recorded delivery/validation telemetry, without renderers or providers."""
import json
from pathlib import Path
import tempfile
import unittest

from arena.observers.sciel.data import RunStore
from arena.observers.sciel.reliability import reliability_view


def event(phase, **fields):
    return dict(event='research', phase=phase, **fields)


def attempt(ident, *, shown=(), ranked=2, omitted=(), **metadata):
    return event('attempt', experiment_id=ident,
        evidence=dict(id=ident, iteration=1, injected_ids=list(shown)),
        lesson_presentation=dict(ranked_count=ranked, presented=[dict(id=ident) for ident in shown],
                                 omitted=list(omitted), **metadata))


class ReliabilityTests(unittest.TestCase):
    def view(self, rows, checkpoint=None, lessons=None):
        return reliability_view({}, checkpoint or {}, rows, lessons or [])

    def test_stored_ranked_selected_and_delivered_are_not_interchangeable(self):
        rows = [attempt('r1', shown=['l1'], ranked=3, stored_active_count=5, selected_count=2,
                        omitted=[dict(id='l2', reason='card_char_limit')]),
                attempt('r2', ranked=3, omitted=[dict(id='l1', reason='memory_char_limit')])]
        view = self.view(rows, dict(research=dict(knowledge=dict(lessons=[dict(id='l1')]))),
                         [dict(id='l1', status='active'), dict(id='l2', status='retired')])['memory']
        self.assertEqual(view['stored_active'], 1)
        first, last = view['history']
        self.assertEqual([first[key] for key in ('stored_active', 'ranked', 'selected', 'delivered', 'dropped_by_size')],
                         [5, 3, 2, 1, 1])
        self.assertIsNone(last['stored_active']);self.assertIsNone(last['selected'])
        self.assertEqual(view['zero_delivered_due_size'], 1)
        self.assertEqual(view['metadata_known'], 2)

    def test_missing_ambiguous_and_inconsistent_metadata_stays_unknown(self):
        missing = event('attempt', experiment_id='old', evidence=dict(injected_ids=[]))
        bad = attempt('bad', shown=['l1']);bad['evidence']['injected_ids'] = []
        guarded = attempt('guarded', ranked=3, omitted=[dict(id='l1', reason='ablation')])
        guarded['lesson_presentation']['selection'] = dict(candidate=dict(ids=['l1', 'l2']))
        guarded['lesson_presentation']['selected_count'] = True
        view = self.view([missing, bad, guarded])['memory']
        self.assertIsNone(view['stored_active'])
        self.assertEqual(view['metadata_unknown'], 2)
        self.assertIsNone(view['history'][0]['delivered'])
        self.assertIsNone(view['history'][1]['delivered'])
        self.assertFalse(view['history'][1]['delivery_consistent'])
        self.assertEqual(view['latest']['delivered'], 0)
        self.assertIsNone(view['latest']['selected'])
        self.assertEqual(view['zero_delivered_due_size'], 0)
        self.assertIsNone(self.view([missing])['memory']['zero_delivered_due_size'])

    def test_terminal_conclusions_override_intermediate_rejection_without_double_count(self):
        rows = [event('aux_start', kind='conclusion', reference='r1'),
                event('conclusion_rejected', experiment_id='r1', reason='invalid_structure',
                      diagnostic=dict(code='text_too_long', path='quote', actual=800, maximum=512)),
                event('conclusion_repair', experiment_id='r1'),
                event('aux_start', kind='conclusion', reference='r1'),
                event('conclusion', experiment_id='r1', status='parsed'),
                event('conclusion', experiment_id='r2', status='invalid'),
                event('conclusion', experiment_id='r3', status='skipped', reason='response_length'),
                event('aux_start', kind='conclusion', reference='r4')]
        view = self.view(rows)['conclusions']
        self.assertEqual([view[key] for key in ('parsed', 'rejected', 'skipped', 'pending', 'repairs')], [1,1,1,1,1])
        self.assertEqual(view['history'][0]['status'], 'parsed')
        self.assertEqual(view['history'][0]['diagnostic']['actual'], 800)

    def test_idea_repair_is_not_terminal_failure_and_exhaustion_is_precode(self):
        rows = []
        for ident, status, code in [('i1','evaluated',True), ('i2','idea_card_repair_exhausted',False),
                                   ('i3','idea_card_duplicate',False)]:
            rows.append(event('idea', idea_id=ident, action='request_start', stage='card', iteration=5))
            rows.append(event('idea', idea_id=ident, action='card_rejected', retry_scheduled=True,
                              diagnostics=[dict(kind='too_long', field='mechanism', length=1030, maximum=1024)]))
            if code:
                rows.append(event('idea', idea_id=ident, action='request_start', stage='code'))
            rows.append(event('idea', idea_id=ident, action='finish', status=status))
        view = self.view(rows)['ideas']
        self.assertEqual(view['attempts'], 3)
        self.assertEqual(view['finished'], 3)
        self.assertEqual(view['rejected_before_code'], 2)
        self.assertEqual(view['invalid_cards'], 0)
        self.assertEqual(view['repair_exhausted'], 1)
        self.assertEqual(view['evaluated'], 1)
        self.assertEqual(view['history'][0]['diagnostic']['field'], 'mechanism')

    def test_histories_bounded_without_truncating_totals(self):
        rows = [attempt('r'+str(i), ranked=1, omitted=[dict(id='l1', reason='card_char_limit')]) for i in range(150)]
        rows += [event('conclusion', experiment_id='r'+str(i), status='invalid') for i in range(150)]
        view = self.view(rows)
        self.assertEqual(view['memory']['attempts'], 150)
        self.assertEqual(view['memory']['zero_delivered_due_size'], 150)
        self.assertEqual(view['conclusions']['rejected'], 150)
        self.assertEqual(len(view['memory']['history']), 120)
        self.assertEqual(view['memory']['history'][0]['experiment_id'], 'r30')
        self.assertTrue(view['memory']['history_truncated'])

    def test_snapshot_integration_updates_after_complete_appended_record(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'sciel_events.jsonl'
            path.write_text(json.dumps(dict(event='run_start',task='test/fixture'))+'\n')
            store = RunStore([Path(directory)]);ident = store.discover()[0]['id']
            self.assertIsNone(store.snapshot(ident)['reliability']['memory']['stored_active'])
            with path.open('a') as journal:
                journal.write(json.dumps(attempt('r1', shown=['l1'], ranked=1))+'\n')
            view = store.snapshot(ident)['reliability']
            self.assertEqual(view['memory']['latest']['delivered'], 1)
            self.assertFalse(view['conclusions']['recorded'])


if __name__ == '__main__':
    unittest.main()
