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


class MethodsRuntimeTests(MethodsDashboardFixture):
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
        with patch('arena.observers.sciel.methods_projection.MAX_PROJECTION_OBJECTS',2):
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


if __name__ == "__main__":
    unittest.main()
