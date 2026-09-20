"""Read-only native Engine tool projection; no scientific code is executed."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from arena.observers.sciel.research_tools import EVENT_SCHEMA, research_tools_view, tool_detail, artifact_detail, cell_detail, job_detail, BackgroundJobView
from arena.observers.sciel.compat.models import content_hash
from arena.observers.sciel.architecture_graph import architecture_graph
from arena.observers.sciel.data import RunStore
from arena.observers.sciel.parallel import runtime_parallel, parallel_view


def event(phase, **fields):
    return dict(event='research_tool', schema=EVENT_SCHEMA, phase=phase, **fields)


def canonical(body):
    return json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


class ResearchToolDashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        for folder in ('objects', 'artifacts'):
            (self.path / 'research_tools' / folder).mkdir(parents=True)

    def write(self, folder, body):
        ident = hashlib.sha256(canonical(body)).hexdigest()
        (self.path / 'research_tools' / folder).mkdir(parents=True,exist_ok=True)
        (self.path / 'research_tools' / folder / (ident + '.json')).write_bytes(canonical(body))
        return ident

    def bundle(self, code='def run(inputs):\n    return {"x": 0}\n', parents=()):
        return dict(schema='sciel-method/1', files={'tool.py': code}, manifest=dict(
            kind='tool', name='fixture', entrypoint='tool.py:run', parents=list(parents),
            protocol=dict(schema='sciel-research-tool/1', author_island=0)))

    def job(self, *, completed=False, key='one', parent_job_id=None):
        schema='sciel-research-tool-job/1'
        ident=content_hash(dict(schema=schema,job_key=key))
        owner=dict(action_id='c'*64,cell_id='d'*64,island_id=0,parent_program_id='p1')
        request=dict(tool_id='a'*64,owner=owner,inputs={'query':'<script>exact</script>'},
            limits=dict(cpu_seconds=60,wall_seconds=120),parent_job_id=parent_job_id,library_identity='e'*64,
            source_sha256='f'*64,runtime_sha256='1'*64,dependency_ids=[])
        spec=dict(schema=schema,job_id=ident,job_key=key,request_hash=content_hash(request),request=request)
        state=dict(schema=schema,job_id=ident,request_hash=spec['request_hash'],status='queued',
            created_at='2026-09-19T00:00:00Z',updated_at='2026-09-19T00:00:00Z',
            started_at=None,finished_at=None,resources=None,dispatch_status='not_dispatched',receipt_id=None,error=None)
        directory=self.path/'research_tools/jobs'/ident;directory.mkdir(parents=True)
        if completed:
            receipt=dict(schema='sciel-method-execution/1',method_id=request['tool_id'],invocation_id=ident,
                plan_id=owner['action_id'],reservation_id=ident,input_sha256=content_hash(request['inputs']),
                source_sha256=request['source_sha256'],runtime_sha256=request['runtime_sha256'],dependency_ids=[],
                status='ok',dispatch_status='invoked',limits=request['limits'],output={'answer':0},
                output_sha256=content_hash({'answer':0}),resources=dict(cpu_seconds=0,wall_seconds=2))
            receipt['receipt_sha256']=content_hash(receipt)
            (directory/'receipt.json').write_bytes(canonical(receipt))
            state.update(status='completed',receipt_id=content_hash(receipt),resources=receipt['resources'],dispatch_status='invoked')
        (directory/'spec.json').write_bytes(canonical(spec));(directory/'status.json').write_bytes(canonical(state))
        binding=dict(tool_id=request['tool_id'],owner=owner,request_hash=spec['request_hash'])
        return ident,binding,directory,state

    def test_jobs_only_committed_checkpoint_ids_grant_visibility_and_lazy_access(self):
        ident,binding,_,_=self.job()
        rows=[event('job_submitted',job_id=ident,tool_id='a'*64)]
        view=research_tools_view({}, {}, rows)
        self.assertEqual(view['jobs']['summary']['total'],0)
        with self.assertRaises(KeyError):job_detail(self.path,ident,{})
        checkpoint={'research_tools':{'jobs':{ident:binding}}}
        data=BackgroundJobView(self.path).project(research_tools_view({},checkpoint,rows)['jobs'])
        self.assertEqual(data['items'][0]['requested']['cpu_seconds'],60)
        self.assertIsNone(data['items'][0]['actual']['cpu_seconds'])
        self.assertIsNone(data['summary']['observed_cpu_seconds'])
        self.assertEqual(data['summary']['unknown_cpu_jobs'],1)
        detail=job_detail(self.path,ident,checkpoint)
        self.assertTrue(detail['verified']);self.assertEqual(detail['request']['inputs'],{'query':'<script>exact</script>'})
        self.assertIsNone(detail['receipt'])
        binding['owner']=dict(binding['owner'],island_id=9)
        with self.assertRaises(ValueError):job_detail(self.path,ident,checkpoint)

    def test_job_zero_resources_and_full_output_are_verified_but_tampered_accounting_is_not(self):
        ident,binding,directory,state=self.job(completed=True)
        checkpoint={'research_tools':{'jobs':{ident:binding}}}
        view=BackgroundJobView(self.path);base=research_tools_view({},checkpoint,[])['jobs']
        self.assertEqual(view.project(base)['summary']['observed_cpu_seconds'],0)
        detail=job_detail(self.path,ident,checkpoint)
        self.assertEqual(detail['receipt']['output'],{'answer':0})
        state['resources']={'cpu_seconds':999,'wall_seconds':2};(directory/'status.json').write_bytes(canonical(state))
        shown=view.project(base)
        self.assertEqual(shown['items'][0]['status'],'unknown');self.assertIsNone(shown['summary']['observed_cpu_seconds'])
        with self.assertRaises(ValueError):job_detail(self.path,ident,checkpoint)

    def test_job_refresh_and_cancellation_do_not_replay_search_or_invent_known_cpu(self):
        ident,binding,directory,state=self.job()
        rows=[dict(event='run_start',run_id='run',segment_id='segment',event_seq=1,task='fixture',
            config={'research_tools':{'enabled':True,'jobs':{'enabled':True}}},counters={'cost_total':.4})]
        (self.path/'sciel_events.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
        (self.path/'checkpoint.json').write_text(json.dumps({'research_tools':{'jobs':{ident:binding}},'provenance':{'run_id':'run'}}))
        store=RunStore([self.path]);run=store.discover()[0]['id'];version,kind,first=store.stream_update(run)
        self.assertEqual(kind,'snapshot');self.assertEqual(first['research_tools']['jobs']['summary']['queued'],1)
        state.update(status='running',updated_at='2026-09-19T00:01:00Z');(directory/'status.json').write_bytes(canonical(state))
        (directory/'cancel.request').write_bytes(canonical(dict(job_id=ident,request_hash=state['request_hash'],cancel_requested=True)))
        with patch.object(store,'_project',side_effect=AssertionError('job status must not rebuild Engine history')):
            next_version,kind,update=store.stream_update(run,version)
            self.assertEqual(next_version,version);self.assertEqual(kind,'runtime')
            job=update['research_tool_jobs']['items'][0]
            self.assertEqual(job['status'],'running');self.assertTrue(job['cancel_requested']);self.assertIsNone(job['actual']['cpu_seconds'])
            self.assertEqual(store.snapshot(run)['stats']['cost_total'],.4)
        self.assertEqual(store.research_tool_job(run,ident)['status'],'running')

    def test_job_projection_is_bounded_and_never_discovers_orphan_files(self):
        bindings={f'{n:064x}':dict(tool_id='a'*64,owner={}) for n in range(250)}
        base=research_tools_view({}, {'research_tools':{'jobs':bindings}}, [])['jobs']
        self.assertEqual(base['summary'],dict(total=250,visible=200,omitted=50))
        self.assertEqual(len(base['items']),200)
        with patch('arena.observers.sciel.research_tools._job_row',return_value=dict(status='unknown',actual={})) as read:
            view=BackgroundJobView(self.path);view.project(base);view.project(base)
            self.assertEqual(read.call_count,200)

    def test_cached_job_rejects_replacement_with_a_directory_symlink(self):
        ident,binding,directory,_=self.job(completed=True)
        base=research_tools_view({}, {'research_tools':{'jobs':{ident:binding}}}, [])['jobs']
        view=BackgroundJobView(self.path)
        self.assertEqual(view.project(base)['items'][0]['status'],'completed')
        target=self.path/'relocated-job';directory.rename(target);directory.symlink_to(target,target_is_directory=True)
        self.assertEqual(view.project(base)['items'][0]['status'],'unknown')

    def test_deferred_background_cell_is_not_a_submitted_job_or_execution(self):
        rows=[event('cell_created',cell_id='a'*64,cell_revision_id='b'*64,question='Probe a bottleneck',island_id=0),
            event('cell_revision',cell_id='a'*64,cell_revision_id='c'*64,stage='background_deferred',evidence=[])]
        view=research_tools_view({}, {}, rows)
        self.assertEqual(view['cells'][0]['stage'],'background_deferred')
        self.assertFalse(view['cells'][0]['scheduled'])
        self.assertEqual(view['jobs']['summary']['total'],0)
        self.assertEqual(view['summary']['actual_invocations'],0)

    def test_projection_counts_actual_foreign_execution_once_and_keeps_zero(self):
        ident = 'a'*64
        result = event('invocation_result', tool_id=ident, invocation_id='one', receipt_id='b'*64,
            island_id=1, dispatch_status='invoked', status='ok', resources=dict(cpu_seconds=0, wall_seconds=0))
        rows = [event('registered',tool_id=ident,author_island_id=0,name='tool'),
            event('published',tool_id=ident,availability='shared'),
            event('invocation_started',tool_id=ident,invocation_id='one',island_id=1),result,result,
            event('invocation_started',tool_id=ident,invocation_id='one',island_id=1),
            event('invocation_result',tool_id=ident,invocation_id='two',island_id=0,dispatch_status='invoked',status='failed'),
            event('invocation_result',tool_id=ident,invocation_id='three',island_id=2,dispatch_status='not_dispatched',status='failed'),
            event('invocation_result',tool_id=ident,invocation_id='four',island_id=2,dispatch_status='unknown',status='unknown'),
            event('context_prepared',action_id='episode',receipt_ids=['b'*64]),
            event('child_link',child_program_id='p3',island_id=1,tool_ids=[ident],receipt_ids=['b'*64])]
        view = research_tools_view({}, {}, rows)
        self.assertEqual(view['summary']['actual_invocations'], 2)
        self.assertEqual(view['summary']['foreign_invocations'], 1)
        self.assertEqual(view['summary']['failed_invocations'], 1)
        self.assertEqual(view['summary']['unknown_invocations'], 1)
        self.assertEqual(view['invocations'][0]['resources']['cpu_seconds'], 0)
        self.assertEqual(view['versions'][0]['author_island_id'], 0)
        self.assertEqual(view['versions'][0]['availability'], 'shared')
        self.assertEqual(view['versions'][0]['children'][0]['program_id'], 'p3')
        self.assertIn('not proven delivery', ' '.join(view['notes']))

    def test_metadata_windows_are_bounded_and_totals_retain_history(self):
        rows=[event('registered',tool_id=f'{n:064x}',author_island_id=0) for n in range(250)]
        view=research_tools_view({}, {}, rows)
        self.assertEqual(view['summary']['versions'],250)
        self.assertEqual(len(view['versions']),200)
        self.assertEqual(view['coverage']['omitted_versions'],50)
        self.assertEqual(len(view['events']),200)
        self.assertFalse(research_tools_view({}, {}, [])['available'])
        self.assertEqual(research_tools_view({}, {}, [dict(event='research_tool',phase='published')])['summary']['versions'],0)

    def test_returned_and_rejected_tool_proposals_do_not_remain_pending(self):
        rows=[event('llm_start',action_id='ep',attempt=0),
              event('llm_result',action_id='ep',attempt=0,receipt_id='a'*64,known_cost=0)]
        self.assertEqual(research_tools_view({}, {}, rows)['llm_calls'][0]['status'],'returned')
        rows.append(event('rejected',action_id='ep',attempt=0,status='proposal_invalid',error='invalid JSON'))
        call=research_tools_view({}, {}, rows)['llm_calls'][0]
        self.assertEqual(call['status'],'proposal_invalid')
        self.assertEqual(call['error'],'invalid JSON')
        self.assertEqual(call['known_cost'],0)

    def test_source_and_parent_diff_verify_immutable_ids_without_execution(self):
        parent=self.write('objects',self.bundle())
        code='raise RuntimeError("this source must never execute")\n# café\n'
        child=self.write('objects',self.bundle(code,[parent]))
        rows=[event('registered',tool_id=child)]
        detail=tool_detail(self.path,child,rows)
        self.assertTrue(detail['verified'])
        self.assertEqual(detail['files']['tool.py'],code)
        self.assertEqual(detail['source_sha256'],hashlib.sha256(code.encode()).hexdigest())
        self.assertIn('+raise RuntimeError',detail['parents'][0]['diff'])
        self.assertTrue(detail['parents'][0]['verified'])
        with self.assertRaises(KeyError):tool_detail(self.path,child,[])
        path=self.path/'research_tools'/'objects'/(parent+'.json')
        path.write_text('{}')
        self.assertFalse(tool_detail(self.path,child,rows)['parents'][0]['verified'])
        path=self.path/'research_tools'/'objects'/(child+'.json')
        path.write_text('{}')
        with self.assertRaises(ValueError):tool_detail(self.path,child,rows)

    def test_artifacts_require_hash_kind_and_episode_binding(self):
        proposal=dict(schema='sciel-research-tool-artifact/1',kind='proposal',payload=dict(
            action_id='ep',attempt=0,prompt='<script>raw</script>',response=dict(text='reply',cost=0)))
        ident=self.write('artifacts',proposal)
        rows=[event('llm_result',receipt_id=ident,action_id='ep',attempt=0,island_id=0,parent_program_id='p1')]
        result=artifact_detail(self.path,ident,rows)
        self.assertEqual(result['payload']['response']['cost'],0)
        self.assertEqual(result['payload']['prompt'],'<script>raw</script>')
        with self.assertRaises(ValueError):artifact_detail(self.path,ident,[event('llm_result',receipt_id=ident,action_id='other')])
        with self.assertRaises(ValueError):artifact_detail(self.path,ident,[event('invocation_result',receipt_id=ident,action_id='ep')])
        with self.assertRaises(KeyError):artifact_detail(self.path,ident,[])
        invocation=dict(schema='sciel-research-tool-artifact/1',kind='invocation',payload=dict(
            action_id='ep',island_id=0,parent_program_id='p1',tool_id='a'*64,inputs={'x':0},receipt={'output':{'answer':0}}))
        inv=self.write('artifacts',invocation)
        detail=artifact_detail(self.path,inv,[event('invocation_result',receipt_id=inv,action_id='ep',island_id=0,parent_program_id='p1',tool_id='a'*64)])
        self.assertEqual(detail['payload']['receipt']['output']['answer'],0)

    def test_traversal_symlink_and_read_bound_are_rejected(self):
        ident=self.write('objects',self.bundle())
        rows=[event('registered',tool_id=ident),event('registered',tool_id='../outside')]
        with self.assertRaises(ValueError):tool_detail(self.path,'../outside',rows)
        path=self.path/'research_tools'/'objects'/(ident+'.json')
        target=self.path/'outside.json';path.rename(target);path.symlink_to(target)
        with self.assertRaises(ValueError):tool_detail(self.path,ident,rows)
        path.unlink();path.write_bytes(b' '*(1600*1024+1))
        with self.assertRaises(ValueError):tool_detail(self.path,ident,rows)

    def test_input_attribution_requires_saved_source_and_journal_binding(self):
        from copy import deepcopy
        from types import SimpleNamespace
        from arena.observers.sciel.compat.research_targets import input_binding
        inputs = json.loads((Path(__file__).with_name('fixtures') / 'research_input.json').read_text())
        target = input_binding(inputs)
        payload = dict(action_id='ep',island_id=0,parent_program_id='p1',tool_id='a'*64,
            inputs=inputs,input_program_id='p1',target_binding=target,receipt={})
        body = dict(schema='sciel-research-tool-artifact/1',kind='invocation',payload=payload)
        ident = self.write('artifacts', body)
        row = event('invocation_result',receipt_id=ident,action_id='ep',target_binding=target)
        self.assertTrue(artifact_detail(self.path,ident,[row])['verified'])
        for binding in (None, dict(target,candidate_id='p2')):
            with self.assertRaises(ValueError):
                artifact_detail(self.path,ident,[dict(row,target_binding=binding)])
        altered = deepcopy(body);altered['payload']['inputs']['parent_source'] = 'different source'
        altered_id = self.write('artifacts',altered)
        with self.assertRaises(ValueError):
            artifact_detail(self.path,altered_id,[dict(row,receipt_id=altered_id)])

    def test_native_projection_does_not_create_programs_lessons_or_duplicate_costs(self):
        ident=self.write('objects',self.bundle())
        rows=[dict(event='run_start',run_id='run',segment_id='segment',event_seq=1,task='fixture',
            config={'research_tools':{'enabled':True,'share_between_islands':True}},counters={'cost_total':.4,'B_evals':0,'iteration_no':0}),
            dict(event('registered',tool_id=ident,author_island_id=0),run_id='run',segment_id='segment',event_seq=2),
            dict(event('llm_result',action_id='ep',attempt=0,known_cost=.2),run_id='run',segment_id='segment',event_seq=3)]
        (self.path/'sciel_events.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
        store=RunStore([self.path]);run=store.discover()[0]['id'];snap=store.snapshot(run)
        self.assertEqual(snap['research_tools']['summary']['versions'],1)
        self.assertEqual(snap['stats']['evaluations'],0)
        self.assertEqual(snap['stats']['lessons'],0)
        self.assertEqual(snap['stats']['cost_total'],.4)
        self.assertEqual(snap['trials'],[])
        self.assertTrue(store.research_tool(run,ident)['verified'])
        self.assertIn('tool_library',[node['id'] for node in snap['architecture']['graph']['nodes']])

    def test_architecture_is_recorded_and_does_not_add_tool_reward_path(self):
        graph=architecture_graph({'config':{'research_tools':{'enabled':True,'share_between_islands':False}}},{},[])
        library=next(node for node in graph['nodes'] if node['id']=='tool_library')
        self.assertEqual(library['label'],'Island tool library')
        self.assertIn('sharing is explicitly disabled',library['detail'])
        self.assertFalse(any(edge['from']=='tool_execution' and edge['to']=='reward' for edge in graph['edges']))
        self.assertFalse(any(node['id']=='tool_library' for node in architecture_graph({}, {}, [])['nodes']))

    def test_parallel_tools_remain_distinct_from_task_evaluations(self):
        value=dict(schema='sciel-parallel-runtime/1',pending_evaluations=1,pending_tool_calls=2)
        self.assertEqual(runtime_parallel(value)['pending_tool_calls'],2)
        value.pop('pending_tool_calls');self.assertNotIn('pending_tool_calls',runtime_parallel(value))
        wave=parallel_view({}, {}, [dict(event='decision',policy='parallel_search',action='wave_complete',wave=1,evaluations=1,tool_executions=2)])['waves'][0]
        self.assertEqual(wave['evaluations'],1);self.assertEqual(wave['tool_executions'],2)

    def test_same_program_remeasurement_keeps_distinct_receipt_links(self):
        common=dict(child_program_id='p1',island_id=0,tool_ids=['a'*64])
        rows=[event('child_link',action_id='first',link_kind='mutation',**common),
              event('child_link',action_id='repeat',link_kind='remeasurement',**common)]
        view=research_tools_view({}, {}, rows+rows)
        self.assertEqual(view['summary']['linked_programs'],1)
        self.assertEqual(view['summary']['linked_records'],2)
        self.assertEqual([row['link_kind'] for row in view['child_links']],['mutation','remeasurement'])

    def test_restore_excludes_abandoned_tool_and_receipt_from_lazy_endpoints(self):
        tool=self.write('objects',self.bundle())
        receipt=self.write('artifacts',dict(schema='sciel-research-tool-artifact/1',kind='proposal',
            payload=dict(action_id='abandoned',attempt=0,prompt='obsolete',response={'text':'obsolete'})))
        rows=[dict(event='run_start',run_id='run',segment_id='old',event_seq=1,task='fixture'),
              dict(event('registered',tool_id=tool),run_id='run',segment_id='old',event_seq=2),
              dict(event('llm_result',receipt_id=receipt,action_id='abandoned',attempt=0),run_id='run',segment_id='old',event_seq=3),
              dict(event='run_start',run_id='run',segment_id='new',event_seq=1,task='fixture',resumed=True),
              dict(event='checkpoint_restore',run_id='run',segment_id='new',event_seq=2,
                   provenance=dict(run_id='run',journal_anchor=dict(segment_id='old',event_seq=1)))]
        (self.path/'sciel_events.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
        store=RunStore([self.path]);run=store.discover()[0]['id']
        self.assertEqual(store.snapshot(run)['research_tools']['summary']['versions'],0)
        with self.assertRaises(KeyError):store.research_tool(run,tool)
        with self.assertRaises(KeyError):store.research_tool_artifact(run,receipt)

    def cell(self):
        genesis=dict(schema='sciel-research-cell/1',origin_island=0,question='Which search decision is limiting progress?',trigger={'kind':'stagnation','record_B_evals':0})
        ident=self.write('cells/genesis',genesis)
        first=dict(schema='sciel-research-cell-revision/1',cell_id=ident,previous_revision=None,ordinal=1,phase='propose',tool_ids=[],evidence=[],roles={'creator':0},summary='Question opened',decision={})
        revision=self.write('cells/revisions',first)
        return ident,revision,first

    def test_cells_are_separate_durable_records_and_transition_counts_are_not_a_success_funnel(self):
        cell,revision,_=self.cell();tool='a'*64
        rows=[event('cell_created',cell_id=cell,cell_revision_id=revision,origin_island_id=0,island_id=0,question='Why plateau?'),
            event('cell_activated',cell_id=cell,cell_revision_id=revision,stage='research'),
            event('invocation_result',cell_id=cell,stage='research',tool_id=tool,receipt_id='b'*64,invocation_id='local',dispatch_status='invoked',status='failed'),
            event('cell_revision',cell_id=cell,cell_revision_id=revision,stage='research',tool_ids=[]),
            event('replay_result',cell_id=cell,tool_id=tool,receipt_id='c'*64,matched=False,status='not_reproduced'),
            event('adopted',cell_id=cell,cell_revision_id=revision,tool_id=tool,receipt_id='d'*64,status='adopted_for_trials',benefit='not_established'),
            event('post_adoption_use',cell_id=cell,tool_id=tool,receipt_id='e'*64,status='failed')]
        view=research_tools_view({}, {}, rows)
        self.assertEqual(view['summary']['cells'],1)
        self.assertEqual(view['cells'][0]['origin_island_id'],0)
        self.assertFalse(view['cells'][0]['scheduled'])
        self.assertEqual(view['lifecycle']['counts'],dict(proposed_cells=1,local_trials=1,independent_replays=1,matched_replays=0,reproduced_measurements=0,independent_execution_checks=0,adoptions=1,post_adoption_uses=0))
        rows.append(event('invocation_result',cell_id=cell,stage='use_again',tool_id=tool,receipt_id='e'*64,invocation_id='later',dispatch_status='invoked',status='failed'))
        self.assertEqual(research_tools_view({}, {}, rows)['lifecycle']['counts']['post_adoption_uses'],1)

    def test_cell_history_verifies_lineage_and_excludes_orphan_artifacts(self):
        cell,first,body=self.cell()
        second=self.write('cells/revisions',dict(body,previous_revision=first,ordinal=2,phase='adopt',decision={'benefit':'not_established'},tool_ids=['a'*64],evidence=[dict(kind='tool_invocation',id='b'*64,tool_id='a'*64)]))
        rows=[event('cell_created',cell_id=cell,cell_revision_id=first),event('cell_revision',cell_id=cell,cell_revision_id=second,stage='adopt_trial')]
        detail=cell_detail(self.path,cell,{},rows)
        self.assertEqual([item['id'] for item in detail['revision_history']],[second,first])
        self.assertEqual(detail['genesis']['trigger']['record_B_evals'],0)
        self.assertFalse(detail['history_truncated'])
        with self.assertRaises(KeyError):cell_detail(self.path,cell,{},[])
        checkpoint={'research_tools':{'lifecycle':{'cells':{'schema':'sciel-research-cells/1','cells':{cell:{'head_revision':first,'active':False,'affinities':[0]}}}}}}
        self.assertEqual(cell_detail(self.path,cell,checkpoint,[])['head_revision'],first)
        # A newer on-disk revision does not advance a committed head.
        self.assertEqual(len(cell_detail(self.path,cell,checkpoint,[])['revision_history']),1)
        (self.path/'research_tools/cells/revisions'/(first+'.json')).write_text('{}')
        with self.assertRaises(ValueError):cell_detail(self.path,cell,{},rows)

    def test_cell_revision_cannot_reference_another_cell_or_symlinked_ancestry(self):
        cell,first,body=self.cell()
        bad=self.write('cells/revisions',dict(body,cell_id='f'*64))
        with self.assertRaises(ValueError):cell_detail(self.path,cell,{},[event('cell_revision',cell_id=cell,cell_revision_id=bad)])
        directory=self.path/'research_tools/cells';outside=self.path/'foreign-cells';directory.rename(outside);directory.symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ValueError):cell_detail(self.path,cell,{},[event('cell_revision',cell_id=cell,cell_revision_id=first)])

    def test_cells_architecture_has_no_tool_reward_or_fake_population_edge(self):
        graph=architecture_graph({'config':{'research_tools':{'enabled':True,'trigger_sources':['population_stall']}}},{},[])
        ids={node['id'] for node in graph['nodes']}
        self.assertTrue({'research_cells','research_checks'} <= ids)
        self.assertTrue(any(edge['from']=='research_checks' and edge['to']=='generation' for edge in graph['edges']))
        self.assertFalse(any(edge['from']=='research_cells' and edge['to'] in ('reward','population','mode_policy') for edge in graph['edges']))
