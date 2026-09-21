"""SCiEL durable call identity and partial-ledger projection regressions.

Fixtures follow pinned 0d67f813 engine/parallel_calls.py CallLedger.prepare /
perform. They create inert JSON only and never import or execute SCiEL.
"""
import hashlib
import json
import shutil

import pytest

from arena.results import Evidence, digest, sciel_usage

MODEL = 'gpt-5.6-sol'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def call(root, key, *, kind='llm', state='returned', wave='1'):
    directory = root / 'native/.parallel' / f'wave-{wave}' / 'calls' / hashlib.sha256(key.encode()).hexdigest()
    request = {'prompt': 'Inert fixture', 'model': MODEL} if kind == 'llm' else {'operation': 'inert'}
    request_hash = digest({'kind': kind, 'request': request})
    write(directory / 'intent.json', dict(schema='sciel-parallel-call/1', key=key,
          kind=kind, request=request, request_sha256=request_hash))
    if state == 'prepared':
        return directory
    write(directory / 'dispatched.json', dict(request_sha256=request_hash, timestamp='2026-09-21T00:00:00+00:00', pid=123))
    if state == 'pending':
        return directory
    value = dict(model=MODEL, prompt_tokens=100, completion_tokens=30) if kind == 'llm' else {'status': 'completed'}
    payload = dict(status=state, request_sha256=request_hash, value=value)
    write(directory / 'receipt.json', dict(sha256=digest(payload), payload=payload))
    return directory


def test_prepared_intent_is_not_a_request_but_orphan_receipt_marks_partial(tmp_path):
    call(tmp_path, 'known')
    prepared = call(tmp_path, 'prepared', state='prepared')
    assert sciel_usage(Evidence(tmp_path), MODEL)['complete'] is True
    orphan = call(tmp_path, 'orphan')
    (orphan / 'dispatched.json').unlink()
    evidence = Evidence(tmp_path)
    value = sciel_usage(evidence, MODEL)
    assert (value['requests'], value['total_tokens'], value['complete']) == (1, 130, False)
    assert evidence.issues == {'Provider usage coverage is incomplete.'}
    assert not (prepared / 'dispatched.json').exists()


@pytest.mark.parametrize('mutation', ['request', 'schema', 'key', 'copied_directory', 'changed_kind', 'unknown_kind', 'missing_request'])
def test_intent_binding_rejects_changed_or_copied_calls_without_losing_known_usage(tmp_path, mutation):
    call(tmp_path, 'known')
    directory = call(tmp_path, 'bad')
    path = directory / 'intent.json'
    intent = json.loads(path.read_text())
    if mutation == 'request':
        intent['request']['prompt'] = 'changed after dispatch'
    elif mutation == 'schema':
        intent['schema'] = 'unrecognized/1'
    elif mutation == 'key':
        intent['key'] = 'different-key'
    elif mutation == 'changed_kind':
        intent['kind'] = 'evaluation'  # Cannot hide an LLM call by changing only its kind.
    elif mutation == 'unknown_kind':
        intent['kind'] = 'new-unreviewed-kind'
    elif mutation == 'missing_request':
        del intent['request']
    else:
        shutil.move(directory, directory.with_name('c' * 64))
    if mutation != 'copied_directory':
        write(path, intent)
    evidence = Evidence(tmp_path)
    value = sciel_usage(evidence, MODEL)
    assert value['requests'] == 1
    assert value['total_tokens'] == 130 and value['complete'] is False
    assert evidence.issues


def test_duplicate_directory_does_not_double_count_valid_receipt(tmp_path):
    directory = call(tmp_path, 'known')
    shutil.copytree(directory, directory.with_name('a' * 64))
    value = sciel_usage(Evidence(tmp_path), MODEL)
    assert (value['requests'], value['total_tokens'], value['complete']) == (1, 130, False)


@pytest.mark.parametrize('kind', ['evaluation', 'tool_execution', 'tool_job_submit', 'tool_job_poll', 'tool_job_cancel'])
def test_native_non_provider_operations_are_not_requests_or_unknown_tokens(tmp_path, kind):
    call(tmp_path, 'known')
    call(tmp_path, 'local-operation', kind=kind)
    value = sciel_usage(Evidence(tmp_path), MODEL)
    assert (value['requests'], value['total_tokens'], value['complete']) == (1, 130, True)


@pytest.mark.parametrize('location,value', [
    ('intent.json', []), ('intent.json', None), ('intent.json', {}),
    ('dispatched.json', []), ('receipt.json', []), ('receipt.json', {'payload': None}),
    ('receipt.json', {'payload': {'status': 'returned', 'value': []}}),
])
def test_malformed_sibling_artifact_retains_verified_usage_and_marks_partial(tmp_path, location, value):
    call(tmp_path, 'known')
    directory = call(tmp_path, 'malformed')
    write(directory / location, value)
    evidence = Evidence(tmp_path)
    result = sciel_usage(evidence, MODEL)
    assert result['total_tokens'] == 130 and result['complete'] is False
    assert evidence.issues


def test_invalid_json_and_deep_json_are_bounded_partial_evidence(tmp_path):
    call(tmp_path, 'known')
    directory = call(tmp_path, 'deep')
    (directory / 'intent.json').write_text('{"x":' * 2000 + 'null' + '}' * 2000)
    malformed = call(tmp_path, 'invalid')
    (malformed / 'receipt.json').write_text('{')
    value = sciel_usage(Evidence(tmp_path), MODEL)
    assert value['total_tokens'] == 130 and value['complete'] is False


def test_valid_same_request_at_distinct_native_call_keys_is_not_deduplicated(tmp_path):
    # Separate calls can legitimately share a prompt/request hash.
    call(tmp_path, 'proposal:1')
    call(tmp_path, 'proposal:2')
    value = sciel_usage(Evidence(tmp_path), MODEL)
    assert (value['requests'], value['total_tokens'], value['complete']) == (2, 260, True)


def test_failed_or_pending_call_retains_known_tokens_without_implying_complete_coverage(tmp_path):
    call(tmp_path, 'known')
    call(tmp_path, 'pending', state='pending')
    call(tmp_path, 'failed', state='error')
    value = sciel_usage(Evidence(tmp_path), MODEL)
    assert (value['requests'], value['total_tokens'], value['complete']) == (3, 130, False)


def test_native_named_waves_are_included_not_silently_omitted(tmp_path):
    call(tmp_path, 'numeric', wave='1')
    call(tmp_path, 'named', wave='resume-2')
    result = sciel_usage(Evidence(tmp_path), MODEL)
    assert (result['requests'], result['total_tokens'], result['complete']) == (2, 260, True)


@pytest.mark.parametrize('entry', ['non-hash-directory', 'unexpected-file', 'invalid-wave'])
def test_unrecognized_ledger_entry_does_not_allow_complete_coverage(tmp_path, entry):
    directory = call(tmp_path, 'known')
    if entry == 'non-hash-directory':
        shutil.copytree(directory, directory.with_name('damaged-call'))
    elif entry == 'unexpected-file':
        (directory.parent / 'unrecognized').write_text('inert')
    else:
        (tmp_path / 'native/.parallel/wave-').mkdir()
    result = sciel_usage(Evidence(tmp_path), MODEL)
    assert (result['requests'], result['total_tokens'], result['complete']) == (1, 130, False)
