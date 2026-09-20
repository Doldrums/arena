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


class MethodsDashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = self.root / 'live'
        self.registry = self.run / 'registry'
        for name in ('methods', 'revisions', 'artifacts', 'dispatch'):
            (self.registry / name).mkdir(parents=True, exist_ok=True)
        self.journal = self.registry / 'journal.jsonl'
        self.rows = []
        self.identity = dict(task=dict(schema='fixture/1'), common_methods=[])
        self.append('coordinator_identity', dict(identity=self.identity, started_at=1))
        self.tool = self.object('methods', dict(schema='sciel-method/1', files={'tool.py': 'x = 1\n'},
            manifest=dict(name='Fixture', kind='tool', author_lab='lab', parents=[], dependencies=[])))
        self.append('method_registered', dict(id=self.tool))
        revision = self.object('revisions', dict(schema='sciel-lab-revision/1', lab_id='lab',
            budget_account='lab', active_methods=[self.tool], active_adapters=[], capabilities={}, evidence_refs=[]))
        self.append('lab_created', dict(revision_id=revision, agenda='Research', mode='C'))
        self.resource_rows = []
        cap = dict(dollars='5',cpu_seconds='100',gpu_seconds='0',wall_seconds='500',storage_bytes=100000,steps=12)
        self.ledger('init', dict(limits=cap))
        self.ledger('account', dict(account_id='lab', limits=cap))
        self.store = RunStore([self.root])

    def object(self, directory, body):
        ident = digest(body)
        (self.registry / directory / (ident + '.json')).write_text(json.dumps(body))
        return ident

    def artifact(self, kind, body):
        ident = self.object('artifacts', dict(schema='sciel-method-artifact/1',kind=kind,body=body))
        self.append('artifact_registered',dict(kind=kind,id=ident))
        return ident

    def append(self, kind, data):
        body = dict(schema='sciel-method-event/1',seq=len(self.rows)+1,
            prev=self.rows[-1]['id'] if self.rows else '0'*64,
            at=(datetime(2026,9,19,tzinfo=timezone.utc)+timedelta(seconds=len(self.rows))).isoformat(),kind=kind,data=data)
        row = dict(body,id=digest(body))
        self.rows.append(row)
        with self.journal.open('a') as f:
            f.write(json.dumps(row)+'\n')

    def ledger(self, op, data):
        body = dict(schema='sciel-resource-ledger/1',seq=len(self.resource_rows)+1,
            prev_sha256=self.resource_rows[-1]['sha256'] if self.resource_rows else '0'*64,
            at='2026-09-19T00:00:00+00:00',op=op,data=data)
        row=dict(body,sha256=digest(body));self.resource_rows.append(row)
        with (self.run/'resources.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')

    def snapshot(self):
        ident=self.store.discover()[0]['id']
        return self.store.snapshot(ident)

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

    def _solution_fixture(self, *, valid=True, invoked=True, proposal_id=None):
        code='def solve():\n    return 1\n'
        files={'candidate.py':code,'adapter.py':'def run(x): return x\n'}
        bundle=self.object('methods',dict(schema='sciel-method/1',files=files,
            manifest=dict(name='Execution adapter',kind='adapter',author_lab='lab',parents=[],dependencies=[],
                protocol=dict(permanent_toolbox_method=False,purpose='solution_execution_adapter'))))
        self.append('method_registered',dict(id=bundle))
        plan=self.artifact('experiment_plan',dict(lab_id='lab',purpose='solution',treatment=[bundle],control=[],
            proposal_id=proposal_id,criterion=dict(metric='combined_score',direction='max')))
        call=self.artifact('call_receipt',dict(category='execution',status='completed',result=dict(
            method_id=bundle,plan_id=plan,dispatch_status='invoked' if invoked else 'not_dispatched',
            status='ok',source_sha256=digest(files)),actual={}))
        experiment=self.artifact('experiment',dict(plan_id=plan,valid_treatment=valid,rule_passed=valid,
            status='completed',invocation_refs=[call],invoked_methods=[bundle],results={}))
        solution=self.artifact('solution',dict(lab_id='lab',experiment_id=experiment,call_receipt_id=call,
            program=dict(id='program-1',code=code,score=.8),evaluation=dict(ok=valid,score=.8,cases=dict(sum_radii=2.1)),
            cascade=dict(confirmed=False),evaluation_protocol='cascade'))
        return bundle,solution

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

    def test_stored_claims_explicit_active_evidence_and_prompt_delivery_are_different(self):
        claim = self.artifact('knowledge_claim', dict(methods=[self.tool], supporting=[],
            contradicting=[], inconclusive=[]))
        self.append('claim_revision', dict(key='claim-key', id=claim))
        evidence = self.artifact('experiment', dict(status='completed', valid_treatment=True, results={}))
        context = self.artifact('proposal_context', dict(lab_id='lab', evidence=[]))
        # Merely listing a source/claim in the receipt does not prove its delivery.
        feedback = self.artifact('proposal_receipt', dict(lab_id='lab', context_id=context,
            evidence_refs=[claim], source_read=[dict(id=self.tool, source_included=True)], draft=dict(kind='method')))
        revision = self.object('revisions', dict(schema='sciel-lab-revision/1', lab_id='lab',
            budget_account='lab', active_methods=[self.tool], active_adapters=[], capabilities={},
            evidence_refs=[evidence, feedback]))
        self.append('lab_revised', dict(revision_id=revision))
        knowledge = self.snapshot()['methods']['observability']['knowledge']
        self.assertEqual(knowledge['stored_records'], 3)
        self.assertEqual(knowledge['stored_claims'], 1)
        self.assertEqual(knowledge['current_claims'], 1)
        self.assertEqual(knowledge['active_referenced_records'], 2)
        self.assertEqual(knowledge['active_referenced_claims'], 0)
        self.assertEqual(set(knowledge['active_referenced_ids']), {evidence, feedback})
        self.assertIsNone(knowledge['prompt_delivery']['count'])
        self.append('method_status', dict(id=self.tool, status='released', evidence_refs=[claim]))
        knowledge = self.snapshot()['methods']['observability']['knowledge']
        self.assertEqual(knowledge['active_referenced_records'], 3)
        self.assertEqual(knowledge['active_referenced_claims'], 1)
        self.append('lab_lifecycle', dict(lab_id='lab', status='archived'))
        archived = self.snapshot()['methods']['observability']['knowledge']
        self.assertEqual(archived['stored_records'], 3)
        self.assertEqual(archived['active_referenced_records'], 0)

    def test_failed_treatment_preserves_native_control_metric_without_mixing_units(self):
        plan=self.artifact('experiment_plan',dict(lab_id='lab',purpose='local',treatment=[self.tool],control=[self.tool],
            task=dict(schema='sciel-method-circle26-task/1'),criterion=dict(metric='combined_score',direction='max')))
        control=dict(status='ok',measurement=dict(valid=True,metrics=dict(combined_score=.96),
            observables=dict(sum_radii=2.53)))
        self.artifact('experiment',dict(plan_id=plan,valid_treatment=False,status='failed',
            results=dict(control=[control],treatment=[dict(status='failed',measurement=None)])))
        failed=self.snapshot()['methods']['experiments'][0]
        self.assertEqual(failed['native_metric'],'sum_radii')
        self.assertEqual(failed['display_metric'],'sum_radii')
        self.assertEqual(failed['display_control_score'],2.53)
        self.assertIsNone(failed['display_treatment_score'])
        # A recorded normalized-only treatment must not appear under a native label.
        self.artifact('experiment',dict(plan_id=plan,valid_treatment=True,status='completed',
            results=dict(control=[control],treatment=[dict(status='ok',measurement=dict(valid=True,
                metrics=dict(combined_score=.7),observables={}))])))
        partial=self.snapshot()['methods']['experiments'][-1]
        self.assertEqual(partial['treatment_score'],.7)
        self.assertIsNone(partial['display_treatment_score'])

    def test_unrelated_task_cannot_relabel_metric_from_sum_radii_observable(self):
        plan=self.artifact('experiment_plan',dict(lab_id='lab',purpose='local',treatment=[self.tool],control=[],
            task=dict(schema='another-task/1'),criterion=dict(metric='correct',direction='max')))
        self.artifact('experiment',dict(plan_id=plan,status='completed',results=dict(control=[],treatment=[
            dict(status='ok',measurement=dict(valid=True,metrics=dict(correct=1),observables=dict(sum_radii=2.5)))])))
        record=self.snapshot()['methods']['experiments'][0]
        self.assertIsNone(record['native_metric'])
        self.assertEqual(record['display_metric'],'correct')
        self.assertEqual(record['display_treatment_score'],1)

    def test_unlimited_resource_caps_preserve_null_and_unknown_reservations(self):
        (self.run/'resources.jsonl').unlink()
        self.resource_rows=[]
        resources=('dollars','cpu_seconds','gpu_seconds','wall_seconds','storage_bytes','steps')
        cap=dict.fromkeys(resources,None)
        account=dict(cap,dollars='5',gpu_seconds='0')
        self.ledger('init',dict(limits=cap))
        self.ledger('account',dict(account_id='lab',limits=account))
        self.ledger('reserve',dict(id='r-1',account_id='lab',request_id='req',category='generation',
            bounds=dict(dollars='2',cpu_seconds='10',gpu_seconds='0',wall_seconds='20',storage_bytes=100,steps=1)))
        self.ledger('settle',dict(id='r-1',status='unknown',actual=dict(dollars='0.5'),resolution=None))
        budget=self.snapshot()['methods']['budget']
        self.assertEqual(budget['limits'],cap)
        self.assertEqual(budget['remaining'],cap)
        self.assertEqual(budget['spent']['dollars'],.5)
        self.assertEqual(budget['reserved']['dollars'],1.5)
        self.assertEqual(budget['accounts']['lab']['remaining']['dollars'],3)
        self.assertEqual(budget['accounts']['lab']['remaining']['gpu_seconds'],0)
        self.assertIsNone(budget['accounts']['lab']['remaining']['cpu_seconds'])
        self.assertEqual(budget['unknown_reservations'],['r-1'])
        json.dumps(budget,allow_nan=False)

    def test_missing_budget_cap_stays_unknown_instead_of_becoming_unlimited_or_zero(self):
        (self.run/'resources.jsonl').unlink()
        self.resource_rows=[]
        self.ledger('init',dict(limits=dict(dollars=None)))
        budget=self.snapshot()['methods']['budget']
        self.assertIsNone(budget['remaining']['dollars'])
        self.assertNotIn('cpu_seconds',budget['remaining'])

    def test_continuous_classification_comes_from_saved_config_and_invalidates_cached_view(self):
        before=self.snapshot()
        self.assertIsNone(before['run']['classification'])
        (self.run/'run-config.json').write_text(json.dumps(dict(claim='continuous_run')))
        after=self.snapshot()
        self.assertEqual(after['run']['classification'],'continuous_run')
        self.assertEqual(after['methods']['run_policy']['classification'],'continuous_run')
        self.assertNotEqual(before['content_version'],after['content_version'])
        self.assertEqual(after['run']['status'],'historical')

    def test_methods_heartbeat_and_discovery_do_not_copy_full_history(self):
        from arena.observers.sciel.data import _safe
        ident=self.store.discover()[0]['id']
        version,event,full=self.store.stream_update(ident)
        self.assertEqual(event,'snapshot')
        cached=self.store._projections[self.journal.resolve()][2]
        full['run']['name']='modified response'
        full['methods']['tools'].clear()
        def small_only(value,*args,**kwargs):
            self.assertIsNot(value,cached)
            self.assertIsNot(value,cached['methods'])
            return _safe(value,*args,**kwargs)
        with patch('arena.observers.sciel.data._safe',side_effect=small_only):
            same,kind,small=self.store.stream_update(ident,version)
            self.assertEqual((same,kind),(version,'runtime'))
            self.assertNotIn('methods',small)
            self.assertEqual(len(self.store.discover()),1)
        current=self.store.snapshot(ident)
        self.assertNotEqual(current['run']['name'],'modified response')
        self.assertEqual(len(current['methods']['tools']),1)

    def test_unknown_budget_holds_remaining_and_labels_lab_stage(self):
        bounds=dict(dollars='2',cpu_seconds='10',gpu_seconds='0',wall_seconds='20',storage_bytes=100,steps=1)
        self.ledger('reserve',dict(id='r-1',account_id='lab',request_id='req',bounds=bounds,category='generation'))
        self.ledger('settle',dict(id='r-1',status='unknown',actual=dict(dollars='0.5'),resolution=None))
        view=self.snapshot()['methods']
        self.assertEqual(view['budget']['spent']['dollars'],.5)
        self.assertEqual(view['budget']['reserved']['dollars'],1.5)
        self.assertEqual(view['budget']['remaining']['dollars'],3)
        self.assertEqual(view['summary']['unknown'],1)
        self.assertIn('unknown',view['labs'][0]['current_stage'])

    def test_corrupt_or_incomplete_journal_shows_only_verified_prefix(self):
        with self.journal.open('a') as f:f.write('{"seq":')
        view=self.snapshot()
        self.assertEqual(view['methods']['summary']['methods'],1)
        self.assertIn('Incomplete',view['warnings'][0])
        with self.journal.open('a') as f:f.write('8}\n')
        view=self.snapshot()
        self.assertIn('integrity',view['warnings'][0])

    def test_malformed_committed_metadata_is_inert(self):
        self.append('artifact_registered',dict(id=['../../secret'],kind='experiment'))
        self.append('lab_revised',dict(revision_id=['bad']))
        view=self.snapshot()
        self.assertEqual(view['methods']['summary']['methods'],1)
        self.assertTrue(view['warnings'])

    def test_format_failure_diagnostic_is_projected_without_refusal_artifact(self):
        context=self.artifact('proposal_context',dict(lab_id='lab'))
        diagnostic=dict(code='missing_action_kind',message='Set top-level kind.',field='kind')
        self.artifact('proposal_receipt',dict(lab_id='lab',context_id=context,
            error='invalid_proposal_format',diagnostic=diagnostic,draft=None))
        proposal=self.snapshot()['methods']['proposals'][0]
        self.assertEqual(proposal['status'],'invalid')
        self.assertEqual(proposal['diagnostic'],diagnostic)

    def test_projection_bound_preserves_latest_and_discloses_partial_counts(self):
        for index in range(5):
            self.artifact('knowledge_claim',dict(scope='scope-'+str(index),methods=[]))
        with patch('arena.observers.sciel.methods.MAX_PROJECTION_OBJECTS',2):
            view=self.snapshot()
        self.assertEqual([c['scope'] for c in view['methods']['claims']],['scope-3','scope-4'])
        self.assertFalse(view['methods']['summary']['history_complete'])
        self.assertFalse(view['methods']['storage']['history_complete'])
        self.assertGreater(view['methods']['projection']['omitted_objects'],0)
        self.assertIn('complete history',view['warnings'][0])

    def test_unregistered_linked_and_tampered_sources_are_refused(self):
        view=MethodsView(self.journal)
        unregistered=self.object('methods',dict(files={'x.py':'private'},manifest={}))
        with self.assertRaises(KeyError):view.method_detail(unregistered)
        with self.assertRaises(KeyError):view.method_detail('../../secret')
        path=self.registry/'methods'/(self.tool+'.json')
        original=path.read_bytes();outside=self.root/'outside.json';outside.write_bytes(original)
        path.unlink();path.symlink_to(outside)
        with self.assertRaises(ValueError):view.method_detail(self.tool)
        path.unlink();path.write_text('{}')
        with self.assertRaises(ValueError):view.method_detail(self.tool)

    def test_source_detail_diff_redacts_secrets_and_never_executes(self):
        sentinel=self.root/'executed'
        code=f'from pathlib import Path\nPath({str(sentinel)!r}).touch()\nx = 2\n# sk-or-v1-'+'a'*64+'\n'
        child=self.object('methods',dict(schema='sciel-method/1',files={'tool.py':code},
            manifest=dict(name='Child',parents=[self.tool],dependencies=[])))
        self.append('method_registered',dict(id=child))
        detail=MethodsView(self.journal).method_detail(child)
        self.assertIn('-x = 1',detail['diff']);self.assertIn('+x = 2',detail['diff'])
        self.assertNotIn('sk-or-v1-',json.dumps(detail));self.assertFalse(sentinel.exists())

    def test_live_heartbeat_bound_to_registry_and_frozen_on_stale_or_dead(self):
        now=datetime.now(timezone.utc)
        runtime=dict(schema='sciel-method-runtime/1',registry_identity_sha256=digest(self.identity),registry_started_at=1,
            started_at=(now-timedelta(seconds=30)).isoformat(),heartbeat_at=now.isoformat(),
            status='running',hostname=socket.gethostname(),pid=os.getpid(),process_identity={'kind':'test','value':'1'},
            stale_after_seconds=10,overhead={'controller_cpu_seconds':2})
        path=self.run/'runtime.json';path.write_text(json.dumps(runtime))
        with patch('arena.observers.sciel.methods.process_matches',return_value=True):
            live=self.snapshot();self.assertTrue(live['runtime']['active'])
            self.assertEqual(live['timing']['session']['elapsed_seconds'],30)
        with patch('arena.observers.sciel.methods.process_matches',return_value=False):
            self.assertEqual(self.snapshot()['run']['status'],'interrupted')
        runtime['heartbeat_at']=(now-timedelta(seconds=20)).isoformat();path.write_text(json.dumps(runtime))
        with patch('arena.observers.sciel.methods.process_matches',return_value=True):
            self.assertEqual(self.snapshot()['run']['status'],'stalled')
        runtime['registry_identity_sha256']='b'*64;path.write_text(json.dumps(runtime))
        self.assertEqual(self.snapshot()['runtime']['verification'],'different_run')
        self.assertNotIn('overhead',self.snapshot()['runtime'])
        runtime['registry_identity_sha256']=digest(self.identity)
        runtime['registry_started_at']=2
        path.write_text(json.dumps(runtime))
        self.assertEqual(self.snapshot()['runtime']['verification'],'different_run')

    def test_http_method_route_and_static_allowlist(self):
        server=DashboardServer(('127.0.0.1',0),[self.root])
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            run_id=server.store.discover()[0]['id']
            c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
            c.request('GET',f'/api/runs/{run_id}/method/{self.tool}')
            response=c.getresponse();self.assertEqual(response.status,200)
            self.assertEqual(json.loads(response.read())['files']['tool.py'],'x = 1\n')
            c.close()
        finally:
            server.shutdown();server.server_close();thread.join(3)

    def test_actual_technical_acceptance_projection_and_exact_proposal(self):
        root=Path(__file__).resolve().parents[2]/'outputs/methods_technical_20260919_v2'
        if not root.exists():self.skipTest('Local technical acceptance artifacts unavailable')
        store=RunStore([root]);run=store.discover()[0];view=store.snapshot(run['id'])
        self.assertEqual(view['methods']['summary']['invocations'],16)
        self.assertEqual(view['methods']['summary']['labs'],3)
        self.assertEqual(view['methods']['summary']['released'],1)
        self.assertEqual(view['methods']['summary']['adoptions'],1)
        self.assertIsNotNone(view['methods']['transfers'][0]['next_use_experiment_id'])
        self.assertEqual(view['warnings'],[])
        self.assertEqual(view['run']['status'],'completed')
        self.assertEqual(store.snapshot(run['id'])['run']['status'],'completed')
        reviewer=next(l for l in view['methods']['labs'] if l['id']=='reviewer')
        self.assertEqual(reviewer['current_stage'],'Replay completed')
        detail=MethodsView(root/'registry/journal.jsonl').proposal_detail(view['methods']['proposals'][0]['id'])
        self.assertIsInstance(detail['request'],dict)
        self.assertIn('known_defect_sort_fixture',detail['response'])
        self.assertEqual(view['methods']['tools'][0]['provenance'],'common_toolbox')


    def test_predispatch_refusal_is_not_an_unclassifiable_model_reply(self):
        context = self.artifact('proposal_context', {'lab_id':'lab'})
        call = self.artifact('call_receipt', dict(category='generation', status='failed',
            result=dict(status='failed', dispatch_status='not_dispatched'), actual=dict(dollars=0)))
        self.artifact('proposal_receipt', dict(lab_id='lab',context_id=context,
            call_receipt_id=call,draft=None,error='proposal_not_dispatched'))
        view = self.snapshot()['methods']
        programs = view['observability']['programs']
        self.assertEqual(programs['unclassified_proposals'],0)
        self.assertEqual(programs['not_dispatched_proposals'],1)
        self.assertEqual(programs['status'],'proposal_not_dispatched')
        self.assertIn('no model response',programs['reason'])
        self.assertEqual(view['proposals'][0]['dispatch_status'],'not_dispatched')
        self.assertEqual(view['proposals'][0]['cost'],0)

    def test_missing_latest_revision_never_exposes_old_tools_as_current(self):
        for declared_lab in (False, True):
            with self.subTest(declared_lab=declared_lab):
                revision = self.object('revisions',dict(schema='sciel-lab-revision/1',lab_id='lab',
                    budget_account='lab',active_methods=[],active_adapters=[],capabilities={},evidence_refs=[]))
                self.append('lab_revised',dict(revision_id=revision,**({'lab_id':'lab'} if declared_lab else {})))
                (self.registry/'revisions'/(revision+'.json')).unlink()
                view = self.snapshot()['methods']
                lab = view['labs'][0]
                self.assertIs(lab['revision_available'],False)
                self.assertEqual(lab['active_methods'],[])
                self.assertEqual(lab['last_verified_revision']['active_methods'],[self.tool])
                self.assertEqual(lab['current_stage'],'revision_unavailable')
                self.assertEqual(view['tools'][0]['active_in'],[])
                self.assertIs(view['storage']['active_versions'][0]['membership_known'],False)
                self.assertFalse(view['summary']['history_complete'])


    def test_identified_unavailable_revision_only_marks_its_own_lab_unknown(self):
        second = self.object('revisions',dict(schema='sciel-lab-revision/1',lab_id='second',
            budget_account='second',active_methods=[self.tool],active_adapters=[],capabilities={},evidence_refs=[]))
        self.append('lab_created',dict(revision_id=second,lab_id='second',agenda='Second',mode='C'))
        self.append('lab_revised',dict(revision_id='d'*64,lab_id='lab'))
        view = self.snapshot()['methods']
        labs = {lab['id']:lab for lab in view['labs']}
        self.assertIs(labs['lab']['revision_available'],False)
        self.assertIs(labs['second']['revision_available'],True)
        self.assertEqual(view['tools'][0]['active_in'],['second'])

    def test_identified_revision_gap_advances_ordinal_without_guessing_membership(self):
        missing = 'd' * 64
        self.append('lab_revised',dict(revision_id=missing,lab_id='lab'))
        lab = self.snapshot()['methods']['labs'][0]
        self.assertEqual(lab['revision_number'],2)
        self.assertIs(lab['revision_available'],False)
        self.assertEqual(lab['active_methods'],[])
        revision = self.object('revisions',dict(schema='sciel-lab-revision/1',lab_id='lab',
            previous_revision=missing,budget_account='lab',active_methods=[],active_adapters=[],
            capabilities={},evidence_refs=[]))
        self.append('lab_revised',dict(revision_id=revision,lab_id='lab'))
        lab = self.snapshot()['methods']['labs'][0]
        self.assertEqual(lab['revision_number'],3)
        self.assertIs(lab['revision_available'],True)
        self.assertEqual(lab['active_methods'],[])

    def test_unidentified_legacy_revision_gap_does_not_restart_numbering(self):
        self.append('lab_revised',dict(revision_id='d'*64))
        self.assertIsNone(self.snapshot()['methods']['labs'][0]['revision_number'])
        revision = self.object('revisions',dict(schema='sciel-lab-revision/1',lab_id='lab',
            budget_account='lab',active_methods=[],active_adapters=[],capabilities={},evidence_refs=[]))
        self.append('lab_revised',dict(revision_id=revision,lab_id='lab'))
        lab = self.snapshot()['methods']['labs'][0]
        self.assertIs(lab['revision_available'],True)
        # Its current content is known; the missing event's lab identity is not.
        self.assertIsNone(lab['revision_number'])


if __name__=='__main__':unittest.main()
