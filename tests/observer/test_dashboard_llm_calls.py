"""Inspector evidence, fixed-path reads and unknown-cost recovery; inert files only."""
import hashlib
import json
import os
from pathlib import Path
import signal
from contextlib import contextmanager

import pytest

from arena.observers.sciel.data import RunStore
from arena.observers.sciel.llm_calls import collect_calls, detail, metadata
from arena.observers.sciel import llm_calls


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def record(event='research', **fields):
    return dict(event=event, run_id='run', segment_id='segment', **fields)


def legacy_rows():
    return [record('run_start', event_seq=1, task='fixture'),
        record(phase='attempt', event_seq=2, experiment_id='r1', prompt_sha256=sha('actual request'),
               timestamp='2026-09-19T00:00:00Z', segment_elapsed_seconds=1, evidence={'iteration':1}),
        record(phase='hypothesis', event_seq=3, experiment_id='r1', response='prefix',
               response_sha256=sha('prefix and remainder'), response_truncated=True,
               timestamp='2026-09-19T00:00:03Z', segment_elapsed_seconds=4),
        record(phase='outcome', event_seq=4, experiment_id='r1', evidence={'status':'no_child','generation_cost':.1}),
        record(phase='aux_start', event_seq=5, kind='conclusion', reference='r1', call_index=1,
               model='recorded-model', prompt_sha256=sha('unavailable request'),
               timestamp='2026-09-19T00:00:05Z'),
        record(phase='aux_stopped', event_seq=6, kind='conclusion', reference='r1', call_index=1,
               timestamp='2026-09-19T00:00:08Z', cost=None, current_call_cost_unknown=True,
               llm_error={'reason':'connection_error','cause_type':'APIConnectionError'})]


def test_legacy_missing_prompts_failed_response_and_truncation_are_explicit(tmp_path):
    calls = collect_calls(tmp_path, legacy_rows())
    assert len(calls) == 2
    conclusion, generation = calls
    failed = detail(tmp_path, conclusion)
    assert failed['role'] == 'C' and failed['status'] == 'failed'
    assert failed['model'] == 'recorded-model'
    assert failed['prompt']['text'] is None and failed['response']['text'] is None
    assert failed['elapsed_seconds'] == 3 and failed['latency_source'] == 'journal_event_interval'
    assert failed['current_call_cost_unknown'] is True
    assert failed['error']['reason'] == 'connection_error'
    child = detail(tmp_path, generation)
    assert child['prompt']['available'] is False
    assert child['response']['text'] == 'prefix' and child['response']['truncated'] is True
    assert child['outcome_status'] == 'no_child'
    assert child['elapsed_seconds'] == 3


def test_iteration_full_text_is_used_only_when_hash_and_segment_match(tmp_path):
    rows = legacy_rows()[:4]
    rows += [record('iteration', iteration_no=1, meta={'research_id':'r1'},
        prompt='actual request', response='prefix and remainder', model_used='precise-model')]
    call, = collect_calls(tmp_path, rows)
    full = detail(tmp_path, call)
    assert full['prompt']['text'] == 'actual request'
    assert full['response']['text'] == 'prefix and remainder'
    assert full['response']['truncated'] is False and full['model'] == 'precise-model'
    rows[-1]['prompt'] = 'fabricated request'
    rows[-1]['response'] = 'fabricated response'
    refused = detail(tmp_path, collect_calls(tmp_path, rows)[0])
    assert refused['prompt']['text'] is None
    assert refused['response']['text'] == 'prefix'
    rows[-1]['segment_id'] = 'another segment'
    assert len(collect_calls(tmp_path, rows)) == 2


def trace_fixture(tmp_path, *, failed=False):
    ident = 'a' * 32
    directory = tmp_path / 'artifacts' / 'llm_calls'
    directory.mkdir(parents=True)
    prompt, response = 'actual request', '<script>inert raw response</script>\r\n' * 3000
    (directory / (ident + '.prompt.txt')).write_text(prompt)
    (directory / (ident + '.response.txt')).write_text(response)
    common = dict(call_id=ident, run_id='run', segment_id='segment', role='G',
                  experiment_id='r1', reference='r1', model='trace-model', journal_event_seq=2)
    rows = [dict(common, event='request', prompt_sha256=sha(prompt), prompt_chars=len(prompt),
                 temperature=.7, timestamp='2026-09-19T00:00:00Z'),
            dict(common, event='error' if failed else 'response', response_sha256=sha(response),
                 response_chars=len(response), cost=None if failed else .12,
                 current_call_cost_unknown=failed, elapsed_seconds=2.5,
                 timestamp='2026-09-19T00:00:02.500Z', llm_error={'reason':'timeout'})]
    (tmp_path / 'artifacts' / 'llm_calls.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    return ident, directory, prompt, response


def test_trace_merges_generation_and_loads_exact_text_only_on_detail(tmp_path):
    ident, directory, prompt, response = trace_fixture(tmp_path)
    rows = legacy_rows()
    rows[2]['response_sha256'] = sha(response)
    rows[2]['response'] = response[:6]
    calls = collect_calls(tmp_path, rows)
    assert len(calls) == 2
    call = next(call for call in calls if call['id'] == ident)
    index = metadata(call)
    assert 'prompt' not in index and 'response' not in index
    assert index['source'] == 'trace' and index['outcome_status'] == 'no_child'
    actual = detail(tmp_path, call)
    assert actual['prompt']['text'] == prompt and actual['response']['text'] == response
    assert actual['elapsed_seconds'] == 2.5 and actual['latency_source'] == 'recorded_call'
    assert actual['request_options'] == {'temperature': .7}
    (directory / (ident + '.response.txt')).write_text('changed')
    fallback = detail(tmp_path, call)['response']
    assert fallback['text'] == response[:6] and fallback['source'] == 'journal'


def test_request_only_trace_preserves_returned_journal_response_and_cost(tmp_path):
    ident, _, _, _ = trace_fixture(tmp_path)
    manifest = tmp_path/'artifacts/llm_calls.jsonl'
    manifest.write_text(manifest.read_text().splitlines()[0]+'\n')
    call = next(call for call in collect_calls(tmp_path, legacy_rows()) if call['id'] == ident)
    actual = detail(tmp_path, call)
    assert actual['status'] == 'returned' and actual['cost'] == .1
    assert actual['response']['text'] == 'prefix'
    assert actual['response']['source'] == 'journal' and actual['response']['truncated'] is True
    assert actual['elapsed_seconds'] == 3 and actual['latency_source'] == 'journal_event_interval'


def test_request_detail_distinguishes_requested_temperature_from_omitted_transport(tmp_path):
    ident, _, _, _ = trace_fixture(tmp_path)
    path = tmp_path / 'artifacts/llm_calls.jsonl'
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    projection = {'schema': 'sciel-llm-transport-parameters/1',
        'temperature': {'enabled': False, 'sent': False, 'value': None}}
    rows[0]['temperature'] = .2
    rows[0]['transport_parameters'] = projection
    path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
    call = next(row for row in collect_calls(tmp_path, legacy_rows()) if row['id'] == ident)
    options = detail(tmp_path, call)['request_options']
    assert options['temperature'] == .2
    assert options['transport_parameters'] == projection
    assert options['transport_parameters']['temperature']['value'] is None


@pytest.mark.parametrize('provenance, expected', [
    (None, None),
    ({'schema':'sciel-llm-cost-provenance/1', 'source':'provider_reported', 'reported_cost':0}, 'provider_reported'),
    ({'schema':'sciel-llm-cost-provenance/1', 'source':'token_estimate', 'pricing_key':'default',
      'prompt_usd_per_1k':.001, 'completion_usd_per_1k':.002}, 'token_estimate'),
    ({'schema':'sciel-llm-cost-provenance/1', 'source':'provider_reported', 'reported_cost':1}, None),
    ({'schema':'sciel-llm-cost-provenance/1', 'source':'provider_reported', 'reported_cost':0,
      'arbitrary':'must not propagate'}, None),
])
def test_inspector_preserves_verified_zero_cost_source_without_inventing_legacy_provenance(tmp_path, provenance, expected):
    ident, _, _, _ = trace_fixture(tmp_path)
    manifest = tmp_path/'artifacts/llm_calls.jsonl'
    rows = [json.loads(line) for line in manifest.read_text().splitlines()]
    rows[-1].update(cost=0, prompt_tokens=0, completion_tokens=0, cost_provenance=provenance)
    manifest.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    call = next(call for call in collect_calls(tmp_path, legacy_rows()) if call['id'] == ident)
    for result in (metadata(call), detail(tmp_path, call)):
        assert result['cost'] == 0
        actual = result['cost_provenance']
        assert (actual['source'] if actual else None) == expected
        if expected:
            assert actual == provenance


@pytest.mark.parametrize('field', ['prompt_sha256', 'response_sha256'])
def test_conflicting_hashes_do_not_attach_scientific_outcome_to_trace(tmp_path, field):
    ident, _, _, response = trace_fixture(tmp_path)
    rows = legacy_rows()
    rows[2]['response_sha256'] = sha(response)
    rows[1 if field == 'prompt_sha256' else 2][field] = sha('different original text')
    calls = collect_calls(tmp_path, rows)
    assert len(calls) == 3
    call = next(call for call in calls if call['id'] == ident)
    assert call['outcome_status'] is None
    assert '_legacy' not in call


def test_missing_trace_response_file_uses_compatible_journal_prefix(tmp_path):
    ident, directory, _, response = trace_fixture(tmp_path)
    rows = legacy_rows()
    rows[2]['response_sha256'] = sha(response)
    rows[2]['response'] = response[:30]
    (directory/(ident+'.response.txt')).unlink()
    call = next(call for call in collect_calls(tmp_path, rows) if call['id'] == ident)
    actual = detail(tmp_path, call)
    assert actual['response']['text'] == response[:30]
    assert actual['response']['source'] == 'journal'
    assert actual['response']['truncated'] is True


def test_unknown_trace_role_uses_hash_bound_idea_metadata(tmp_path):
    ident, _, _, _ = trace_fixture(tmp_path)
    manifest = tmp_path/'artifacts/llm_calls.jsonl'
    request = json.loads(manifest.read_text().splitlines()[0])
    request.update(role='unknown', reference=None, experiment_id=None)
    manifest.write_text(json.dumps(request)+'\n')
    rows = [legacy_rows()[0], record(phase='idea', action='request_start', stage='card',
        event_seq=2, idea_id='idea-1', prompt='actual request', prompt_sha256=sha('actual request'))]
    call, = collect_calls(tmp_path, rows)
    assert call['id'] == ident and call['role'] == 'idea' and call['reference'] == 'idea-1'


def test_failed_trace_never_uses_uncommitted_response_file(tmp_path):
    ident, _, _, _ = trace_fixture(tmp_path, failed=True)
    call = next(call for call in collect_calls(tmp_path, legacy_rows()) if call['id'] == ident)
    actual = detail(tmp_path, call)
    assert actual['status'] == 'failed'
    assert actual['response']['text'] is None


def test_trace_rejects_symlink_text_and_foreign_run(tmp_path):
    ident, directory, _, _ = trace_fixture(tmp_path)
    call = next(call for call in collect_calls(tmp_path, legacy_rows()) if call['id'] == ident)
    target = tmp_path / 'private.txt'
    target.write_text('private')
    prompt = directory / (ident + '.prompt.txt')
    prompt.unlink()
    prompt.symlink_to(target)
    assert detail(tmp_path, call)['prompt']['text'] is None
    foreign = [dict(row, run_id='foreign') for row in legacy_rows()]
    assert all(call['source'] == 'journal' for call in collect_calls(tmp_path, foreign))
    manifest = tmp_path / 'artifacts' / 'llm_calls.jsonl'
    content = manifest.read_text().replace('"journal_event_seq": 2', '"journal_event_seq": 999')
    manifest.write_text(content)
    assert all(call['source'] == 'journal' for call in collect_calls(tmp_path, legacy_rows()))


def test_pagination_paths_and_unknown_recovery_cost_are_read_only(tmp_path):
    rows = legacy_rows()
    journal = tmp_path / 'sciel_events.jsonl'
    journal.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    checkpoint = dict(cost_total=3., iteration_no=2, B_evals=2,
        provider_recoveries=[{'unknown_cost':True}],
        provenance={'run_id':'run','journal_anchor':{'segment_id':'segment','event_seq':6}})
    (tmp_path / 'checkpoint.json').write_text(json.dumps(checkpoint))
    before = {str(path):path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}
    store = RunStore([tmp_path])
    run_id = store.discover()[0]['id']
    index = store.llm_calls(run_id, limit=1)
    assert index['total'] == 2 and index['next_offset'] == 1 and len(index['calls']) == 1
    assert len(store.llm_calls(run_id, query='recorded-model')['calls']) == 1
    with pytest.raises(KeyError):
        store.llm_call(run_id, '../../private.txt')
    with pytest.raises(ValueError):
        store.llm_calls(run_id, limit=1000)
    assert store.snapshot(run_id)['stats']['cost_status'] == 'known_logged_lower_bound'
    assert before == {str(path):path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}


def test_unknown_recovery_receipt_keeps_resumed_reported_spend_a_lower_bound(tmp_path):
    rows = [record('run_start', event_seq=1, counters={'cost_total':3.,'B_evals':2,'iteration_no':2}),
            record('run_end', event_seq=2, cost_total=4., B_evals=3, iteration_no=3, reason='paused')]
    (tmp_path/'sciel_events.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    checkpoint = dict(cost_total=4., iteration_no=3, B_evals=3,
        provider_recoveries=[{'unknown_cost':True}],
        provenance={'run_id':'run','journal_anchor':{'segment_id':'segment','event_seq':2}})
    (tmp_path/'checkpoint.json').write_text(json.dumps(checkpoint))
    store = RunStore([tmp_path])
    snapshot = store.snapshot(store.discover()[0]['id'])
    assert snapshot['stats']['cost_total'] == 4.
    assert snapshot['stats']['cost_status'] == 'known_logged_lower_bound'


def test_generation_error_metadata_survives_later_outcome_summary(tmp_path):
    rows = legacy_rows()[:2] + [
        record(phase='generation_error', experiment_id='r1', timestamp='2026-09-19T00:00:02Z',
               segment_elapsed_seconds=3, cost=None, current_call_cost_unknown=True,
               llm_error={'stage':'request', 'reason':'http_error', 'http_status':429,
                          'cause_type':'RateLimitError', 'unsafe_message':'not exposed'}),
        record(phase='outcome', experiment_id='r1', timestamp='2026-09-19T00:00:05Z',
               evidence={'status':'generation_stopped', 'generation_cost':None, 'generation_dispatch':'unknown'})]
    call, = collect_calls(tmp_path, rows)
    result = detail(tmp_path, call)
    assert result['status'] == 'failed'
    assert result['outcome_status'] == 'generation_stopped'
    assert result['error'] == dict(stage='request', reason='http_error', http_status=429, cause_type='RateLimitError')
    assert result['elapsed_seconds'] == 2
    assert result['cost'] is None and result['current_call_cost_unknown'] is True


@pytest.mark.parametrize('stage', ['card', 'code'])
@pytest.mark.parametrize('dispatch', ['unknown', 'not_dispatched'])
def test_idea_stop_is_terminal_without_charging_earlier_calls(tmp_path, stage, dispatch):
    rows = legacy_rows()[:1]
    if stage == 'code':
        rows += [legacy_rows()[1]]
    rows += [record(phase='idea', action='request_start', stage=stage, idea_id='idea-1',
                    experiment_id='r1' if stage == 'code' else None,
                    prompt='saved idea request', prompt_sha256=sha('saved idea request')),
             record(phase='idea', action='stopped', stage=stage, idea_id='idea-1',
                    generation_dispatch=dispatch, generation_returned=False,
                    current_call_cost_unknown=dispatch == 'unknown', known_cost=.25,
                    error_type='LLMError', llm_error={'reason':'connection_error'})]
    if stage == 'code':
        rows += [record(phase='outcome', experiment_id='r1', evidence={
            'status':'generation_stopped', 'generation_cost':None, 'generation_dispatch':dispatch})]
    call, = collect_calls(tmp_path, rows)
    result = detail(tmp_path, call)
    assert result['status'] == 'failed'
    assert result['error']['reason'] == 'connection_error'
    assert result['error']['type'] == 'LLMError'
    assert result['current_call_cost_unknown'] is (dispatch == 'unknown')
    assert result['cost'] == (None if dispatch == 'unknown' else 0.)


@pytest.mark.parametrize('cost', [None, .12])
def test_idea_stop_after_response_does_not_turn_returned_call_into_provider_failure(tmp_path, cost):
    rows = legacy_rows()[:2] + [
        record(phase='idea', action='request_start', stage='code', idea_id='idea-1', experiment_id='r1'),
        record(phase='idea', action='request_result', stage='code', idea_id='idea-1',
               cost=cost, response='returned', response_sha256=sha('returned')),
        record(phase='idea', action='stopped', stage='code', idea_id='idea-1',
               generation_returned=True, generation_dispatch='returned',
               current_call_cost_unknown=cost is None, known_cost=.25,
               error_type='CampaignStopped', llm_error={}),
        record(phase='outcome', experiment_id='r1', evidence={
            'status':'generation_stopped', 'generation_cost':None, 'generation_dispatch':'returned'})]
    call, = collect_calls(tmp_path, rows)
    assert call['status'] == 'returned' and call['cost'] == cost
    assert call['current_call_cost_unknown'] is (cost is None)
    assert detail(tmp_path, call)['response']['text'] == 'returned'


@pytest.mark.skipif(not hasattr(os, 'mkfifo') or not hasattr(signal, 'setitimer'), reason='POSIX fixture')
@pytest.mark.parametrize('side', ['prompt', 'response'])
def test_fifo_trace_text_is_refused_without_waiting_for_a_writer(tmp_path, side):
    ident, directory, _, _ = trace_fixture(tmp_path)
    call, = collect_calls(tmp_path, legacy_rows()[:1] + [record('fixture', event_seq=2)])
    path = directory / (ident + '.' + side + '.txt')
    path.unlink()
    os.mkfifo(path)

    def timed_out(*_):
        raise AssertionError('Inspector blocked reading a nonregular transcript')

    previous = signal.signal(signal.SIGALRM, timed_out)
    timer = signal.setitimer(signal.ITIMER_REAL, 1)
    try:
        text, note = llm_calls._trace_text(tmp_path, call, side)
        assert text is None and 'unavailable' in note
    finally:
        signal.setitimer(signal.ITIMER_REAL, *timer)
        signal.signal(signal.SIGALRM, previous)


def test_trace_read_is_bounded_even_if_file_grows_after_size_check(tmp_path, monkeypatch):
    ident, directory, _, _ = trace_fixture(tmp_path)
    call, = collect_calls(tmp_path, legacy_rows()[:1] + [record('fixture', event_seq=2)])
    monkeypatch.setattr(llm_calls, 'MAX_TEXT_BYTES', 32)
    original_open = llm_calls._open_regular
    requested = []

    @contextmanager
    def growing_file(path):
        with original_open(path) as stream:
            class Reader:
                def fileno(self):
                    return stream.fileno()

                def read(self, size):
                    requested.append(size)
                    with open(path, 'ab') as writer:
                        writer.write(b'x' * 100)
                    return stream.read(size)
            yield Reader()

    monkeypatch.setattr(llm_calls, '_open_regular', growing_file)
    text, note = llm_calls._trace_text(tmp_path, call, 'prompt')
    assert requested == [33]
    assert text is None and 'limit' in note
    # Already oversized files are rejected before even issuing a read.
    requested.clear()
    text, note = llm_calls._trace_text(tmp_path, call, 'prompt')
    assert requested == []
    assert text is None and 'limit' in note
