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


class MethodsEvidenceTests(MethodsDashboardFixture):
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


if __name__ == "__main__":
    unittest.main()
