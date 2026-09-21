"""Inspector visibility for authenticated physical calls after real wave replay."""
from copy import deepcopy
import json
import math
from pathlib import Path
import shutil

import pytest

from arena.observers.sciel.data import RunStore
from arena.observers.sciel.llm_calls import collect_calls

def events(directory):
    return [json.loads(line) for line in (directory / 'sciel_events.jsonl').read_text().splitlines()]


def physical_files(directory):
    return {str(path.relative_to(directory)): path.read_bytes()
            for name in ('intent.json', 'dispatched.json', 'receipt.json')
            for path in (directory / '.parallel').rglob(name)}


@pytest.fixture
def replayed(tmp_path):
    """Recorded fake-provider wave recovery; no engine, model or evaluator runs."""
    directory = tmp_path / 'run'
    shutil.copytree(Path(__file__).with_name('fixtures') / 'replayed_llm', directory)
    authorization = json.loads((directory / 'view.json').read_text())['authorization']
    traces = [json.loads(line) for line in
              (directory / 'artifacts/llm_calls.jsonl').read_text().splitlines()]
    store = RunStore([directory], timing_cache_dir=tmp_path / 'timing')
    run_id = store.discover()[0]['id']
    return directory, store, run_id, traces, authorization


def test_replayed_calls_show_exact_original_physical_evidence_once(replayed):
    directory, store, run_id, traces, authorization = replayed
    before = physical_files(directory)
    calls = store.llm_calls(run_id, limit=100)['calls']
    assert len(calls) == 8 and all(call['source'] == 'trace' for call in calls)
    assert {call['id'] for call in calls} == {row['call_id'] for row in traces}
    assert math.fsum(call['cost'] for call in calls if call['cost'] is not None) == pytest.approx(.15)
    unknown, = [call for call in calls if call['current_call_cost_unknown']]
    assert unknown['status'] == 'failed' and unknown['cost'] is None
    assert unknown['role'] == 'C' and unknown['error']['http_status'] == 429
    terminal = next(row for row in traces if row['event'] == 'error')
    assert unknown['segment_id'] == terminal['segment_id']
    assert unknown['parallel_receipt']['committed_segment_id'] != unknown['segment_id']
    assert unknown['parallel_receipt']['job_call'] == authorization['failed_calls'][0]['key']
    assert unknown['parallel_receipt']['receipt_sha256'] == authorization['failed_calls'][0]['receipt_sha256']
    for call in calls:
        detail = store.llm_call(run_id, call['id'])
        assert detail['prompt']['text'] == (directory / 'artifacts/llm_calls' / (call['id'] + '.prompt.txt')).read_text()
        assert detail['prompt']['source'] == 'trace'
        if call['id'] == unknown['id']:
            assert detail['response']['text'] is None
            assert detail['current_call_cost_unknown'] is True
        else:
            assert detail['response']['source'] == 'trace'
    assert store.llm_calls(run_id, limit=100)['calls'] == calls
    assert physical_files(directory) == before


@pytest.mark.parametrize('damage', ['receipt_hash', 'request_hash', 'dispatch_hash',
    'active_manifest', 'unbound_journal', 'foreign_trace', 'wrong_job', 'wrong_terminal',
    'outside_physical_interval', 'duplicate_trace', 'role', 'reference', 'experiment_id',
    'inflated_elapsed', 'invalid_timestamp', 'non_scalar_parallel_metadata', 'transport_parameters'])
def test_unbound_old_trace_never_bypasses_original_journal_boundary(replayed, damage):
    directory, store, run_id, traces, authorization = replayed
    failed = authorization['failed_calls'][0]
    call_dir = directory / '.parallel/wave-1/calls' / failed['directory']
    unknown = next(row for row in traces if row['event'] == 'error')['call_id']
    target = [row for row in traces if row['call_id'] == unknown]
    if damage in ('receipt_hash', 'request_hash', 'dispatch_hash'):
        name, field = {'receipt_hash': ('receipt.json', 'sha256'),
            'request_hash': ('intent.json', 'request_sha256'),
            'dispatch_hash': ('dispatched.json', 'request_sha256')}[damage]
        value = json.loads((call_dir / name).read_text())
        value[field] = '0' * 64
        (call_dir / name).write_text(json.dumps(value))
    elif damage == 'active_manifest':
        path = directory / '.parallel/wave-1/transaction.json'
        value = json.loads(path.read_text()); value['phase'] = 'active'
        path.write_text(json.dumps(value))
    elif damage == 'unbound_journal':
        path = directory / 'sciel_events.jsonl'
        path.write_bytes(path.read_bytes().replace(b'wave_complete', b'wave_inert___', 1))
    elif damage == 'foreign_trace':
        for row in target: row['run_id'] = 'foreign'
    elif damage == 'wrong_job':
        for row in target: row['parallel_job'] = 'C:r999999a1'
    elif damage == 'wrong_terminal':
        target[-1]['llm_error']['http_status'] = 503
    elif damage == 'outside_physical_interval':
        target[0]['timestamp'] = '2020-01-01T00:00:00+00:00'
    elif damage == 'duplicate_trace':
        copies = deepcopy(target)
        for row in copies: row['call_id'] = 'f' * 32
        traces += copies
    elif damage in ('role', 'reference', 'experiment_id'):
        for row in target: row[damage] = 'forged'
    elif damage == 'inflated_elapsed':
        target[-1]['elapsed_seconds'] = 1000000
    elif damage == 'invalid_timestamp':
        target[0]['timestamp'] = 123
    elif damage == 'non_scalar_parallel_metadata':
        for row in target: row['parallel_wave'] = {}
    elif damage == 'transport_parameters':
        target[0]['transport_parameters'] = {'schema': 'sciel-llm-transport-parameters/1',
            'temperature': {'enabled': False, 'sent': False, 'value': None}}
    if damage not in ('receipt_hash', 'request_hash', 'dispatch_hash', 'active_manifest', 'unbound_journal'):
        (directory / 'artifacts/llm_calls.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in traces))
    calls = store.llm_calls(run_id, limit=100)['calls']
    assert unknown not in {call['id'] for call in calls}
    assert 'f' * 32 not in {call['id'] for call in calls}
    # The committed semantic abandonment still records unknown, without an
    # authenticated exact physical transcript being invented by the viewer.
    failures = [call for call in calls if call['current_call_cost_unknown']]
    assert len(failures) == 1 and failures[0]['cost'] is None


def test_authoritative_receipt_hash_is_required_for_cross_segment_visibility(replayed):
    directory, _, _, traces, _ = replayed
    rows = events(directory)
    for row in rows:
        if row.get('action') == 'io_receipt':
            row.pop('request_sha256', None)
            row.pop('receipt_sha256', None)
    calls = collect_calls(directory, rows)
    assert not any(call['source'] == 'trace' for call in calls)
    unknown, = [call for call in calls if call['current_call_cost_unknown']]
    assert unknown['role'] == 'C' and unknown['cost'] is None


def test_outside_boundary_clone_cannot_duplicate_an_already_visible_physical_call(replayed):
    directory, _, _, traces, _ = replayed
    ident = next(row for row in traces if row['event'] == 'error')['call_id']
    copies = []
    for row in traces:
        if row['call_id'] == ident:
            row['journal_event_seq'] = 1
            clone = deepcopy(row)
            clone.update(call_id='e' * 32, journal_event_seq=999999)
            copies.append(clone)
    (directory / 'artifacts/llm_calls.jsonl').write_text(
        ''.join(json.dumps(row) + '\n' for row in traces + copies))
    calls = collect_calls(directory, events(directory))
    assert 'e' * 32 not in {call['id'] for call in calls}
    assert len([call for call in calls if call['id'] == ident]) == 1


def test_multiple_recovered_wave_prefixes_share_one_forward_read(tmp_path, monkeypatch):
    import hashlib
    from arena.observers.sciel import llm_calls
    from arena.observers.sciel.parallel_llm import CommittedTraceBindings
    rows, data = [], b''
    for wave in range(3):
        row = dict(event='decision', policy='parallel_search', action='wave_complete',
                   wave=wave, segment_id='segment', run_id='run', event_seq=wave + 1)
        rows.append(row)
        data += (json.dumps(row) + '\n').encode()
        folder = tmp_path / f'.parallel/wave-{wave}'
        folder.mkdir(parents=True)
        (folder / 'transaction.json').write_text(json.dumps(dict(
            schema='sciel-wave-transaction/2', phase='committed', wave_id=str(wave),
            journal_bytes=len(data), journal_sha256=hashlib.sha256(data).hexdigest())))
    (tmp_path / 'sciel_events.jsonl').write_bytes(data)
    original, opened, read_bytes = llm_calls._open_regular, [], []
    class Counted:
        def __init__(self, stream): self.stream = stream
        def __enter__(self): return self
        def __exit__(self, *args): self.stream.close()
        def readline(self, limit):
            value = self.stream.readline(limit)
            read_bytes.append(len(value))
            return value
    def counted(path):
        opened.append(path)
        return Counted(original(path))
    monkeypatch.setattr(llm_calls, '_open_regular', counted)
    proof = CommittedTraceBindings(tmp_path, rows, {0, 1, 2})
    assert all(proof.cache.values())
    assert opened == [tmp_path / 'sciel_events.jsonl'] and sum(read_bytes) == len(data)
