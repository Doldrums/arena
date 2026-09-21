"""Read-only methods dashboards, including evidence/liveness boundary checks."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

from arena.observers.sciel.data import RunStore
from arena.observers.sciel.methods import MethodsView, digest
from arena.server import DashboardServer

from _dashboard_methods_helpers import MethodsDashboardFixture


class MethodsDashboardTests(MethodsDashboardFixture):
    def test_discovery_keeps_ordinary_runs_and_never_writes(self):
        ordinary=self.root/'ordinary';ordinary.mkdir()
        (ordinary/'sciel_events.jsonl').write_text(json.dumps(dict(event='run_start',task='fixture',run_id='r'))+'\n')
        before={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        runs=self.store.discover()
        self.assertEqual(len(runs),2)
        for run in runs:self.store.snapshot(run['id'])
        after={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before,after)
        methods=next(r for r in runs if r.get('kind')=='methods')
        self.assertEqual(methods['status'],'historical')

    def test_dependencies_and_source_inclusion_do_not_count_as_invocation(self):
        self.artifact('call_receipt',dict(category='retrieval',status='completed',
            result=dict(method_id=self.tool,dependency_ids=[self.tool]),actual={}))
        self.artifact('call_receipt',dict(category='execution',status='failed',
            result=dict(method_id=self.tool,dispatch_status='not_dispatched'),actual={}))
        view=self.snapshot()
        self.assertEqual(view['methods']['tools'][0]['invocations'],0)
        self.assertEqual(view['methods']['summary']['failed_calls'],1)
        self.artifact('call_receipt',dict(category='execution',status='failed',
            result=dict(method_id=self.tool,dispatch_status='invoked',dependency_ids=['a'*64]),actual={}))
        self.assertEqual(self.snapshot()['methods']['tools'][0]['invocations'],1)

    def test_registry_storage_preserves_version_history_and_explicit_active_adapters(self):
        original_registration=next(r for r in self.rows if r['kind']=='method_registered')
        replay=self.artifact('knowledge_claim',dict(level='replayed',methods=[self.tool]))
        self.append('method_status',dict(id=self.tool,status='released',evidence_refs=[replay]))
        self.append('method_status',dict(id=self.tool,status='superseded',evidence_refs=[]))
        child=self.object('methods',dict(schema='sciel-method/1',files={'adapter.py':'x = 2\n'},
            manifest=dict(name='Adapter',kind='adapter',author_lab='lab',parents=[self.tool],dependencies=[self.tool])))
        self.append('method_registered',dict(id=child))
        child_registration=self.rows[-1]
        revision=self.object('revisions',dict(schema='sciel-lab-revision/1',lab_id='lab',budget_account='lab',
            active_methods=[],active_adapters=[child],capabilities=dict(network=False,executor='docker'),evidence_refs=[]))
        self.append('lab_revised',dict(revision_id=revision))
        view=self.snapshot()['methods']
        tools={tool['id']:tool for tool in view['tools']}
        self.assertEqual(tools[self.tool]['created_at'],original_registration['at'])
        self.assertEqual(tools[self.tool]['registration_seq'],original_registration['seq'])
        self.assertEqual(tools[self.tool]['status'],'superseded')
        self.assertEqual(tools[self.tool]['evidence_refs'],[replay])
        self.assertTrue(tools[self.tool]['replayed'])
        self.assertEqual(tools[self.tool]['active_in'],[])
        self.assertEqual(tools[child]['active_in'],['lab'])
        self.assertEqual(tools[child]['created_at'],child_registration['at'])
        storage=view['storage']
        self.assertEqual(storage['kind'],'content_addressed_registry')
        self.assertIsNone(storage['coordinates'])
        self.assertEqual(storage['parent_edges'],[dict(source=self.tool,target=child)])
        self.assertEqual(storage['dependency_edges'],[dict(source=self.tool,target=child)])
        self.assertEqual(storage['active_versions'][0]['adapter_ids'],[child])
        self.assertEqual(storage['active_versions'][0]['revision_id'],revision)
        self.assertTrue(storage['history_complete'])
        self.assertEqual(view['labs'][0]['created_at'],self.rows[2]['at'])
        self.assertEqual(view['labs'][0]['revision_at'],self.rows[-1]['at'])
        self.assertEqual(view['labs'][0]['capabilities'],dict(network=False,executor='docker'))

    def test_solution_timestamps_and_proposal_links_use_explicit_saved_binding(self):
        context=self.artifact('proposal_context',dict(lab_id='lab'))
        proposal=self.artifact('proposal_receipt',dict(lab_id='lab',context_id=context,draft=dict(kind='solution')))
        _,solution=self._solution_fixture(proposal_id=proposal)
        registration=self.rows[-1]
        view=self.snapshot()['methods']
        value=next(s for s in view['solutions'] if s['id']==solution)
        self.assertEqual(value['proposal_id'],proposal)
        self.assertEqual(value['created_at'],registration['at'])
        self.assertEqual(value['registration_seq'],registration['seq'])
        experiment=next(e for e in view['experiments'] if e['id']==value['experiment_id'])
        self.assertEqual(experiment['proposal_id'],proposal)
        self.assertEqual(experiment['at'],experiment['created_at'])
        # Merely being the latest proposal is not an association.
        _,unbound=self._solution_fixture()
        other=next(s for s in self.snapshot()['methods']['solutions'] if s['id']==unbound)
        self.assertIsNone(other['proposal_id'])

    def test_solution_bundles_are_separate_from_reusable_tools_and_quality(self):
        bundle,solution=self._solution_fixture()
        # A method-state experiment with a larger score is not a task solution.
        plan=self.artifact('experiment_plan',dict(lab_id='lab',purpose='local',treatment=[self.tool],control=[],
            criterion=dict(metric='combined_score',direction='max')))
        self.artifact('experiment',dict(plan_id=plan,valid_treatment=True,rule_passed=True,status='completed',
            invocation_refs=[],invoked_methods=[],results=dict(treatment=[dict(measurement=dict(valid=True,
                metrics=dict(combined_score=1),observables=dict(sum_radii=2.9)))])))
        view=self.snapshot()['methods']
        self.assertEqual(view['summary']['methods'],1)
        self.assertEqual(view['summary']['execution_bundles'],1)
        self.assertEqual(view['summary']['solutions'],1)
        self.assertEqual(view['execution_bundles'][0]['id'],bundle)
        self.assertEqual(view['execution_bundles'][0]['provenance'],'solution_execution_adapter')
        self.assertEqual(view['quality']['best_solution_id'],solution)
        self.assertEqual(view['quality']['best_native_score'],2.1)
        self.assertEqual(view['quality']['best_score'],.8)
        self.assertEqual(view['labs'][0]['tools'],1)

    def test_uninvoked_or_invalid_program_is_not_quality(self):
        self._solution_fixture(invoked=False)
        self._solution_fixture(valid=False)
        view=self.snapshot()
        self.assertEqual(view['methods']['solutions'],[])
        self.assertIsNone(view['methods']['quality']['best_native_score'])
        self.assertTrue(view['warnings'])

    def test_observability_preserves_recorded_zero_and_unavailable_legacy_metrics(self):
        view = self.snapshot()['methods']['observability']
        self.assertEqual(view['programs']['accepted_programs'], 0)
        self.assertEqual(view['programs']['submitted_solution_actions'], 0)
        self.assertEqual(view['programs']['status'], 'no_recorded_solution_actions')
        self.assertEqual(view['hypotheses']['count'], 0)
        knowledge = view['knowledge']
        self.assertEqual(knowledge['stored_records'], 0)
        self.assertEqual(knowledge['active_referenced_records'], 0)
        self.assertEqual(knowledge['record_counts']['knowledge_claim'], 0)
        self.assertIsNone(knowledge['prompt_delivery']['count'])
        self.assertEqual(knowledge['prompt_delivery']['status'], 'unavailable')
        self.assertIsNone(knowledge['legacy_lessons']['count'])
        self.assertEqual(knowledge['legacy_lessons']['status'], 'not_implemented')
        features = {feature['id']:feature for feature in view['features']}
        self.assertFalse(features['rl']['enabled'])
        self.assertEqual(features['rl']['status'], 'not_implemented')
        self.assertFalse(features['bandits']['enabled'])
        self.assertFalse(features['map_elites']['enabled'])
        self.assertFalse(features['vq_niches']['enabled'])

    def test_unclassifiable_proposal_does_not_prove_solutions_were_never_requested(self):
        context = self.artifact('proposal_context', dict(lab_id='lab'))
        self.artifact('proposal_receipt', dict(lab_id='lab', context_id=context,
            draft=None, error='invalid_proposal_format'))
        programs = self.snapshot()['methods']['observability']['programs']
        self.assertEqual(programs['submitted_solution_actions'], 0)
        self.assertEqual(programs['unclassified_proposals'], 1)
        self.assertEqual(programs['status'], 'submission_unavailable')
        self.assertIn('intended action is unknown', programs['reason'])

    def test_failed_refused_solution_is_distinct_from_no_solution_action(self):
        context = self.artifact('proposal_context', dict(lab_id='lab'))
        proposal = self.artifact('proposal_receipt', dict(lab_id='lab', context_id=context,
            draft=dict(kind='solution')))
        plan = self.artifact('experiment_plan', dict(lab_id='lab', proposal_id=proposal,
            purpose='solution', question='Does the submitted solution improve the target?',
            treatment=[self.tool], control=[], criterion=dict(metric='combined_score', direction='max')))
        call = self.artifact('call_receipt', dict(category='execution', status='failed',
            result=dict(dispatch_status='invoked', status='failed', plan_id=plan, method_id=self.tool)))
        experiment = self.artifact('experiment', dict(plan_id=plan, status='failed', valid_treatment=False,
            invocation_refs=[call], results=dict(treatment=[dict(status='failed', measurement=None)])))
        self.artifact('solution_evaluation', dict(lab_id='lab', experiment_id=experiment,
            call_receipt_id=call, program=None, evaluation=dict(ok=False)))
        refusal = self.artifact('proposal_receipt', dict(lab_id='lab', proposal_id=proposal,
            error='proposal_refused', diagnostic='Evaluation failed.'))
        self.append('episode_step', dict(lab_id='lab', proposal_id=proposal, refusal_id=refusal,
            index=0, status='continued', plan_id=plan, experiment_id=experiment))
        view = self.snapshot()['methods']['observability']
        programs = view['programs']
        self.assertEqual(programs['submitted_solution_actions'], 1)
        self.assertEqual(programs['accepted_programs'], 0)
        self.assertEqual(programs['refused_solution_actions'], 1)
        self.assertEqual(programs['solution_experiments'], 1)
        self.assertEqual(programs['invoked_solution_experiments'], 1)
        self.assertEqual(programs['failed_solution_experiments'], 1)
        self.assertEqual(programs['invalid_solution_experiments'], 0)
        self.assertEqual(programs['nonaccepted_solution_evaluations'], 1)
        self.assertEqual(programs['status'], 'requested_no_accepted_program')
        self.assertIn('1 failed experiments', programs['reason'])
        self.assertEqual(view['hypotheses']['count'], 1)
        question = view['hypotheses']['items'][0]
        self.assertEqual(question['record_kind'], 'precommitted_experiment_plan')
        self.assertEqual(question['experiment_ids'], [experiment])
        self.assertEqual(question['status'], 'failed')
        self.assertEqual(question['proposal_id'], proposal)

    def test_actual_program_counts_do_not_include_tool_trials_or_unexecuted_plans(self):
        self._solution_fixture()
        tool_plan = self.artifact('experiment_plan', dict(lab_id='lab', purpose='local',
            question='A precommitted tool comparison?', treatment=[self.tool], control=[],
            criterion=dict(metric='combined_score', direction='max')))
        self.artifact('experiment', dict(plan_id=tool_plan, status='completed', valid_treatment=True,
            invocation_refs=[], results={}))
        pending = self.artifact('experiment_plan', dict(lab_id='lab', purpose='local',
            question='Not evaluated yet?', treatment=[self.tool], control=[]))
        observation = self.snapshot()['methods']['observability']
        self.assertEqual(observation['programs']['accepted_programs'], 1)
        self.assertEqual(observation['programs']['solution_experiments'], 1)
        self.assertEqual(observation['programs']['status'], 'evaluated')
        self.assertEqual(observation['hypotheses']['count'], 3)
        self.assertEqual(next(q for q in observation['hypotheses']['items'] if q['id'] == pending)['status'], 'planned')

    def test_partial_history_cannot_assert_no_solution_was_requested(self):
        with self.journal.open('a') as stream:
            stream.write('{"incomplete":')
        programs = self.snapshot()['methods']['observability']['programs']
        self.assertEqual(programs['accepted_programs'], 0)
        self.assertEqual(programs['submitted_solution_actions'], 0)
        self.assertFalse(programs['history_complete'])
        self.assertEqual(programs['status'], 'history_incomplete')
        self.assertIn('cannot be ruled out', programs['reason'])


if __name__ == "__main__":
    unittest.main()
