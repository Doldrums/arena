"""Declared tool outcomes remain distinct from host status and legacy evidence."""
import json
import tempfile
import unittest
from pathlib import Path

from arena.observers.sciel.compat.models import content_hash
from arena.observers.sciel.research_tools import EVENT_SCHEMA, research_tools_view, tool_detail


def event(phase, **fields):
    return dict(event='research_tool', schema=EVENT_SCHEMA, phase=phase, **fields)


class DashboardToolResultContractTests(unittest.TestCase):
    def test_semantic_failure_keeps_actual_execution_and_legacy_status(self):
        rows = [event('invocation_result', invocation_id='new', status='ok',
                      dispatch_status='invoked', result_schema='sciel-tool-result/1',
                      tool_result_status='tool_error', tool_result_error='namespace missing'),
                event('invocation_result', invocation_id='legacy', status='ok',
                      dispatch_status='invoked', output={'error': 'historical raw output'})]
        view = research_tools_view({}, {}, rows)
        self.assertEqual(view['summary']['actual_invocations'], 2)
        self.assertEqual(view['summary']['failed_invocations'], 1)
        self.assertEqual(view['summary']['host_failed_invocations'], 0)
        self.assertEqual(view['summary']['tool_failed_invocations'], 1)
        self.assertEqual(view['invocations'][0]['status'], 'ok')
        self.assertEqual(view['invocations'][0]['tool_result_error'], 'namespace missing')
        self.assertNotIn('tool_result_status', view['invocations'][1])

    def test_independent_execution_is_not_measurement_reproduction(self):
        rows = [event('replay_result', tool_id='a'*64, receipt_id='b'*64,
                      matched=True, replay_policy='independent_execution',
                      measurement_reproduced=False)]
        lifecycle = research_tools_view({}, {}, rows)['lifecycle']
        self.assertEqual(lifecycle['counts']['matched_replays'], 1)
        self.assertEqual(lifecycle['counts']['reproduced_measurements'], 0)
        self.assertEqual(lifecycle['counts']['independent_execution_checks'], 1)
        self.assertFalse(lifecycle['events'][0]['measurement_reproduced'])

    def test_failed_input_is_distinct_from_ancestry_in_projection(self):
        binding = dict(candidate_id=None, target_kind='failed_candidate',
                       target_source_sha256='a'*64, ancestry_parent_id='p1',
                       research_targets_sha256='b'*64, population_best_id='p8',
                       population_best_source_sha256='c'*64)
        row = event('invocation_result', invocation_id='new', parent_program_id='p1',
                    target_binding=binding)
        projected = research_tools_view({}, {}, [row])['invocations'][0]
        self.assertEqual(projected['target_binding'], binding)
        self.assertIsNone(projected['target_binding']['candidate_id'])

    def test_new_and_archived_versions_are_readable_but_invalid_contract_is_not(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            objects = root/'research_tools'/'objects'
            objects.mkdir(parents=True)
            for schema, policy, targets in [('sciel-research-tool/1', None, None),
                                   ('sciel-research-tool/2', 'exact_observations', None),
                                   ('sciel-research-tool/2', 'independent_execution', None),
                                   ('sciel-research-tool/2', 'fallback_if_mismatch', None),
                                   ('sciel-research-tool/3', 'exact_observations', 'sciel-research-targets/1'),
                                   ('sciel-research-tool/3', 'independent_execution', 'sciel-research-targets/1'),
                                   ('sciel-research-tool/3', 'exact_observations', 'sciel-research-targets/2'),
                                   ('sciel-research-tool/3', 'exact_observations', None),
                                   ('sciel-research-tool/3', 'exact_observations', 'wrong')]:
                protocol = dict(schema=schema)
                if policy:
                    protocol.update(result_schema='sciel-tool-result/1', replay_policy=policy)
                if targets:
                    protocol['research_targets_schema'] = targets
                body = dict(schema='sciel-method/1', files={'tool.py': 'def run(x): return x\n'},
                            manifest=dict(kind='tool', entrypoint='tool.py:run', protocol=protocol))
                ident = content_hash(body)
                (objects/(ident+'.json')).write_text(json.dumps(body))
                rows = [event('registered', tool_id=ident)]
                if policy == 'fallback_if_mismatch' or (schema=='sciel-research-tool/3' and targets not in ('sciel-research-targets/1','sciel-research-targets/2')):
                    with self.assertRaises(ValueError):
                        tool_detail(root, ident, rows)
                else:
                    detail = tool_detail(root, ident, rows)
                    self.assertTrue(detail['verified'])
                    self.assertEqual(detail['manifest']['protocol'], protocol)


if __name__ == '__main__':
    unittest.main()
