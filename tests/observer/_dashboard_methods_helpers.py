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


class MethodsDashboardFixture(unittest.TestCase):
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
