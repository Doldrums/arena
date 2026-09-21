"""Saved evidence only. Inert candidate text must never be imported or executed."""
from copy import deepcopy
import hashlib
import http.client
import json
import os
from pathlib import Path
import signal
import threading

import pytest

from arena.observers.sciel.compat.repeat_support import BODY_TASK_HASH
from arena.observers.sciel.packings import PackingsView, _digest
from arena.observers.sciel.data import RunStore
from arena.server import DashboardServer
from fixture_geometry import fixture, observation, canonical


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + '\n')


def append(root, row):
    with (root / 'sciel_events.jsonl').open('a') as stream:
        stream.write(json.dumps(row) + '\n')


def run(tmp_path, task_hash=BODY_TASK_HASH):
    root = tmp_path / 'run'
    root.mkdir()
    append(root, {'event': 'run_start', 'task': 'oe/circle_packing',
                  'task_hash': task_hash, 'run_id': 'saved-run'})
    write(root / 'checkpoint.json', {'identity': {'task_hash': task_hash},
                                     'provenance': {'run_id': 'saved-run'}, 'db': {'programs': []}})
    return root


def saved(root, number=1, *, radius=.01, valid=True, physical=True, journal=True,
          missing=False, pending=False, source=None, invocation=None, aliases=()):
    code = source or "raise AssertionError('candidate must never execute')\n"
    source_sha = hashlib.sha256(code.encode()).hexdigest()
    numeric = {'centers': [[(i % 6 + .5)/6, (i//6 + .5)/5] for i in range(26)],
               'radii': [float(radius)] * 26}
    if not valid:
        numeric['centers'][1] = list(numeric['centers'][0])
    g = fixture(numeric=numeric, validity=valid)
    g.update(source_sha256=source_sha, invocation_id=invocation or f'{number:032x}')
    obs = observation(g)
    result = {k: obs[k] for k in ('ok', 'score', 'cases')}
    result['artifacts'] = {} if missing else {'native_geometry': canonical(g)}
    key = f'portfolio:{number}:1'
    evaluation = f'evaluation:saved-run:wave:1:{key}'
    stamp = f'2026-09-20T10:00:{number:02d}+00:00'
    row = {'event': 'decision', 'policy': 'evaluation', 'action': 'result',
           'schema': 'sciel-evaluation-result/1', 'evaluation_id': evaluation,
           'source_sha256': source_sha, 'timestamp': stamp, 'iteration_no_before': number,
           **result, 'reached': 'full', 'confirmed': False}
    directory = root / '.parallel/wave-1/calls' / hashlib.sha256(key.encode()).hexdigest()
    if physical:
        request = {'source': code, 'task_hash': BODY_TASK_HASH, 'confirm_records': False}
        request_sha = _digest({'kind': 'evaluation', 'request': request})
        write(directory / 'intent.json', {'schema': 'sciel-parallel-call/1', 'key': key,
            'kind': 'evaluation', 'request': request, 'request_sha256': request_sha})
        if not pending:
            write(directory / 'dispatched.json', {'pid': 1, 'timestamp': stamp, 'request_sha256': request_sha})
            payload = {'request_sha256': request_sha, 'status': 'returned', 'completed_at': stamp,
                'value': {'result': result, 'reached': 'full', 'confirmed': False, 'raw_first_score': obs['score']}}
            write(directory / 'receipt.json', {'payload': payload, 'sha256': _digest(payload)})
    if journal and not pending:
        append(root, row)
    if aliases:
        state = json.loads((Path(__file__).with_name('fixtures') / 'novelty_alias_template.json').read_text())
        assert state['sources'][0]['code'] == code and state['records'][0]['id'] == evaluation
        state['records'][0]['aliases'] = [ident for ident, _ in aliases]
        state['records'][0]['islands'] = list(dict.fromkeys(island for _, island in aliases))
        state['sha256'] = _digest({key:value for key,value in state.items() if key != 'sha256'}, ascii=True)
        cp = json.loads((root / 'checkpoint.json').read_text())
        cp['candidate_novelty'] = state
        write(root / 'checkpoint.json', cp)
    return {'directory': directory, 'row': row, 'geometry': g, 'source': code,
            'evaluation': evaluation, 'source_sha256': source_sha}


def test_physical_and_journal_are_one_invocation_and_evicted_aliases_survive(tmp_path):
    root = run(tmp_path)
    evidence = saved(root, aliases=[(f'p{i+1}', i) for i in range(24)])
    result = PackingsView(root).page(island='17')
    assert result['supported'] and result['available'] == result['total'] == 1
    assert result['unavailable'] == result['pending'] == 0
    item, = result['items']
    assert item['evaluation_id'] == evidence['evaluation']
    assert item['program_ids'] == [f'p{i+1}' for i in range(24)]
    assert item['island_ids'] == list(range(24))
    assert item['provenance']['kind'] == 'physical_receipt'
    assert item['centers'] == evidence['geometry']['numeric']['centers']
    assert item['score'] == evidence['geometry']['native_sum_radii']
    assert item['source_sha256'] == evidence['source_sha256']
    assert json.loads((root/'checkpoint.json').read_text())['db']['programs'] == []


def test_equal_output_separate_invocations_and_valid_zero_not_invalid_penalty(tmp_path):
    root = run(tmp_path)
    saved(root, 1); saved(root, 2)  # Same arrays, source and score; different executions.
    saved(root, 3, radius=0.); saved(root, 4, valid=False)
    page = PackingsView(root).page()
    assert page['available'] == 4 and len({x['id'] for x in page['items']}) == 4
    zero = next(x for x in page['items'] if x['invocation_id'] == f'{3:032x}')
    invalid = next(x for x in page['items'] if not x['valid'])
    assert zero['score'] == 0. and zero['valid'] is True
    assert invalid['score'] is None and invalid['raw_score'] == 0.
    assert invalid['radii'] == [.01] * 26
    assert page['items'][-1]['id'] == invalid['id']


def test_serial_journal_history_and_no_parent_geometry_fallback(tmp_path):
    root = run(tmp_path)
    a = saved(root, physical=False)
    saved(root, 2, physical=False, missing=True)
    page = PackingsView(root).page()
    assert page['available'] == 1 and page['unavailable'] == 1
    assert page['unavailable_reasons'] == {'missing_geometry': 1}
    assert page['items'][0]['provenance']['kind'] == 'journal'
    assert page['items'][0]['evaluation_id'] == a['evaluation']
    assert page['items'][0]['program_id'] is None


def test_pagination_sort_filters_detachment_and_pending_are_explicit(tmp_path):
    root = run(tmp_path)
    for n in range(1, 5):
        saved(root, n, radius=.01 * n)
    saved(root, 5, pending=True)
    view = PackingsView(root)
    page = view.page(limit=2)
    assert page['total'] == page['available'] == 4 and page['pending'] == 1
    assert page['has_more'] and [x['island_id'] for x in page['items']] == [4, 3]
    page['items'][0]['centers'][0][0] = 999
    assert view.page(limit=2)['items'][0]['centers'][0][0] != 999
    assert [x['island_id'] for x in view.page(offset=2, limit=2)['items']] == [2, 1]
    assert [x['island_id'] for x in view.page(sort='oldest')['items']] == [1, 2, 3, 4]
    assert [x['island_id'] for x in view.page(sort='newest')['items']] == [4, 3, 2, 1]
    assert view.page(island='3')['total'] == 1
    assert view.page(query='portfolio:2:1')['total'] == 1
    assert view.page(query='<script>')['total'] == 0
    assert view.page(offset=100)['items'] == []


@pytest.mark.parametrize('damage', ['receipt_hash', 'source', 'task', 'evaluator', 'numeric',
                                    'score', 'dispatch', 'intent_hash'])
def test_tampered_physical_evidence_withheld_without_journal_fallback(tmp_path, damage):
    root = run(tmp_path); e = saved(root)
    path = e['directory']/'receipt.json'; receipt = json.loads(path.read_text())
    if damage == 'receipt_hash': receipt['sha256'] = 'f'*64
    elif damage in ('source', 'evaluator', 'numeric'):
        g = json.loads(receipt['payload']['value']['result']['artifacts']['native_geometry'])
        if damage == 'numeric': g['numeric']['radii'][0] = .02
        else: g['source_sha256' if damage == 'source' else 'evaluator_sha256'] = 'f'*64
        receipt['payload']['value']['result']['artifacts']['native_geometry'] = canonical(g)
    elif damage == 'score': receipt['payload']['value']['result']['score'] = .99
    elif damage == 'dispatch':
        write(e['directory']/'dispatched.json', {'request_sha256':'f'*64})
    else:
        ip = e['directory']/'intent.json';intent = json.loads(ip.read_text())
        if damage == 'task':intent['request']['task_hash'] = 'f'*64
        else:intent['request_sha256'] = 'f'*64
        write(ip,intent)
    if damage != 'receipt_hash':receipt['sha256'] = _digest(receipt['payload'])
    write(path,receipt)
    page = PackingsView(root).page()
    assert page['available'] == 0 and page['unavailable'] == 1
    assert page['unavailable_reasons'] == {'unverifiable_evidence':1}


def test_unsupported_task_and_serial_binding_failure_explicit(tmp_path):
    root = run(tmp_path, task_hash='f'*64)
    saved(root, physical=False)
    result = PackingsView(root).page()
    assert not result['supported'] and result['supported_reason']
    assert result['available'] == 0 and result['unavailable'] == 1


def test_receipt_symlink_never_reads_outside_root(tmp_path):
    root = run(tmp_path); e = saved(root)
    receipt = e['directory']/'receipt.json';outside = tmp_path/'private.json'
    receipt.rename(outside); receipt.symlink_to(outside)
    result = PackingsView(root).page()
    assert result['available'] == 0 and result['unavailable'] == 1
    assert str(outside) not in json.dumps(result)


def test_cached_evidence_no_reread_or_revalidation_and_changed_receipt_invalidates(tmp_path, monkeypatch):
    root = run(tmp_path);e = saved(root);clock=[0]
    view = PackingsView(root, clock=lambda:clock[0])
    initial=view.page();calls=[]; original=view._read
    def tracked(path, *args, **kwargs):
        calls.append(path)
        return original(path,*args,**kwargs)
    monkeypatch.setattr(view,'_read',tracked)
    clock[0]=4
    assert view.page()==initial and calls==[]
    receipt=e['directory']/'receipt.json';obj=json.loads(receipt.read_text());obj['sha256']='f'*64;write(receipt,obj)
    clock[0]=8;changed=view.page()
    assert changed['available']==0 and changed['unavailable']==1
    assert changed['content_version']!=initial['content_version']
    assert receipt in calls


def test_journal_append_partial_line_and_truncation_do_not_replay_whole_history(tmp_path, monkeypatch):
    root=run(tmp_path);saved(root,physical=False);clock=[0];view=PackingsView(root,clock=lambda:clock[0])
    assert view.page()['available']==1
    calls=[];original=view._consume
    def consume(row,offset):calls.append(row);return original(row,offset)
    monkeypatch.setattr(view,'_consume',consume)
    e=saved(root,2,physical=False);clock[0]=4
    assert view.page()['available']==2 and len(calls)==1
    journal=root/'sciel_events.jsonl'
    with journal.open('a') as f:f.write('{"event":')
    clock[0]=8;assert view.page()['available']==2 and view.page()['journal_read_errors']==0
    journal.write_text(json.dumps({'event':'run_start','task_hash':BODY_TASK_HASH,'run_id':'saved-run'})+'\n')
    clock[0]=12;assert view.page()['available']==0


@pytest.mark.parametrize('kwargs',[{'offset':-1},{'limit':0},{'limit':121},{'limit':True},
                                    {'sort':'__dict__'},{'query':'x'*257}])
def test_invalid_queries_rejected(tmp_path,kwargs):
    with pytest.raises(ValueError):PackingsView(run(tmp_path)).page(**kwargs)


def test_runstore_and_http_route_keep_paths_opaque_and_runtime_read_only(tmp_path):
    root=run(tmp_path);saved(root)
    before={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}
    server=DashboardServer(('127.0.0.1',0),[root]);thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        store=RunStore([root]);store._scan();ident=next(iter(store._runs))
        assert store.packings(ident)['available']==1
        def get(suffix):
            c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
            try:
                c.request('GET',suffix);r=c.getresponse();return r.status,json.loads(r.read())
            finally:c.close()
        status,page=get(f'/api/runs/{ident}/packings?limit=1&sort=newest')
        assert status==200 and page['available']==1
        assert get(f'/api/runs/{ident}/packings?limit=999')[0]==400
        assert get('/api/runs/../../packings')[0]==404
        assert get('/api/runs/not-a-run/packings')[0]==404
    finally:
        server.shutdown();server.server_close();thread.join(timeout=3)
    after={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
           for p in root.rglob('*') if p.is_file()}
    assert after==before


def test_wrong_run_checkpoint_cannot_assign_another_runs_program_ids(tmp_path):
    root=run(tmp_path);saved(root,aliases=[('foreign-program',1)])
    path=root/'checkpoint.json';cp=json.loads(path.read_text());cp['provenance']['run_id']='other-run';write(path,cp)
    page=PackingsView(root).page()
    assert page['available']==1 and page['items'][0]['program_id'] is None
    assert page['warnings']==['Checkpoint belongs to another run; its program aliases are unavailable.']


def test_wrong_run_serial_event_and_duplicate_json_are_withheld(tmp_path):
    root=run(tmp_path);e=saved(root,physical=False)
    path=root/'sciel_events.jsonl';lines=path.read_text().splitlines();row=json.loads(lines[-1]);row['run_id']='other-run'
    path.write_text(lines[0]+'\n'+json.dumps(row)+'\n')
    page=PackingsView(root).page()
    assert page['available']==0 and page['unavailable_reasons']=={'wrong_run_journal_evidence':1}
    path.write_text(lines[0]+'\n'+json.dumps(e['row'])[:-1]+',"score":99}\n')
    page=PackingsView(root).page()
    assert page['available']==0 and page['journal_read_errors']==1


def test_conflicting_copies_of_one_invocation_never_choose_a_winning_layout(tmp_path):
    root=run(tmp_path)
    saved(root,1,invocation='a'*32);saved(root,2,radius=.02,invocation='a'*32)
    page=PackingsView(root).page()
    assert page['available']==0 and page['unavailable_reasons']=={'conflicting_invocation_evidence':1}


def test_serial_program_link_needs_exact_child_source_binding(tmp_path):
    root=run(tmp_path);e=saved(root,physical=False)
    append(root,{'event':'iteration','iteration_no':7,'island':2,'child_id':'wrong-child',
                 'child_code':'different source','meta':{'evaluation_ids':[e['evaluation']]}})
    page=PackingsView(root).page()
    assert page['items'][0]['program_id'] is None
    assert page['items'][0]['iteration']==7


@pytest.mark.skipif(not hasattr(os, 'mkfifo') or not hasattr(signal, 'setitimer'), reason='POSIX fixture')
@pytest.mark.parametrize('side', ['receipt', 'journal', 'checkpoint'])
def test_fifo_evidence_is_refused_without_waiting_for_a_writer(tmp_path, side):
    root = run(tmp_path)
    evidence = saved(root, physical=side != 'journal')
    path = {'receipt': evidence['directory'] / 'receipt.json',
            'journal': root / 'sciel_events.jsonl',
            'checkpoint': root / 'checkpoint.json'}[side]
    path.unlink()
    os.mkfifo(path)

    def timed_out(*_):
        raise AssertionError('Packing gallery blocked on a nonregular evidence file')

    previous = signal.signal(signal.SIGALRM, timed_out)
    timer = signal.setitimer(signal.ITIMER_REAL, 1)
    try:
        page = PackingsView(root).page()
        if side == 'receipt':
            assert page['available'] == 0
            assert page['unavailable_reasons'] == {'unverifiable_evidence': 1}
        elif side == 'journal':
            assert page['available'] == 0 and page['journal_read_errors'] == 1
        else:
            assert page['available'] == 1 and page['items'][0]['program_id'] is None
    finally:
        signal.setitimer(signal.ITIMER_REAL, *timer)
        signal.signal(signal.SIGALRM, previous)
