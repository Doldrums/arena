"""Results-board provenance, score semantics and confidentiality regressions."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from arena.results import Evidence, canonical, sciel_usage, project_run

RUN = 'a' * 32
MODEL = 'gpt-5.6-sol'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, sort_keys=True) + '\n').encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def receipt(root, index, *, score=1.0, valid=True, source='1' * 40, model=None):
    folder = root / 'canonical-evaluations' / f'{index:032x}'
    code = b'# inert candidate, never execute\n'
    (folder / 'input').mkdir(parents=True)
    (folder / 'input/program.py').write_bytes(code)
    candidate = hashlib.sha256(code).hexdigest()
    native = dict(task_id='reference-sat', candidate_sha256=candidate,
                  evaluator_sha256='2' * 64, status='completed', valid=valid, score=score)
    native_hash = write(folder / 'native-output/native.json', native)
    value = dict(schema='arena.evaluation/1', task_id='reference-sat', task_source={'commit': source},
        protocol='recreated', problem_sha256='3' * 64, evaluator_sha256='2' * 64,
        candidate_sha256=candidate, execution={'kind': 'docker', 'image': 'sha256:' + '4' * 64},
        raw_score=score, fitness=score, validity=valid, direction='maximize', metric='score', status='completed',
        started_at=index, native_result_sha256=native_hash, control={'run_id': RUN})
    write(folder / 'receipt.json', value)
    return folder, value


def test_perfect_seed_is_not_an_improvement_and_repeats_are_not_unique(tmp_path):
    receipt(tmp_path, 1)
    receipt(tmp_path, 2, score=.8)
    result = canonical(Evidence(tmp_path), RUN)
    assert result['evaluations'] == result['valid'] == 2
    assert result['unique_valid_candidates'] == 1
    assert result['seed_score'] == result['best_score'] == 1.0
    assert result['score_gain'] == 0 and result['cohort']


def test_best_score_is_an_individual_observation_not_a_confirmation_mean(tmp_path):
    for index, score in enumerate([1, 2, 9], 1):
        receipt(tmp_path, index, score=score)
    result = canonical(Evidence(tmp_path), RUN)
    assert result['valid'] == 3 and result['unique_valid_candidates'] == 1
    assert result['best_score'] == 9  # Three trials of one program; mean would be 4.
    assert result['best_score_basis'] == 'best_single_evaluation'
    assert result['seed_score'] == 1 and result['score_gain'] == 8
    assert result['protocol'] == 'recreated'
    assert 'confirmed_score' not in result


def test_protocol_is_exposed_without_merging_distinct_evaluator_cohorts(tmp_path):
    first, value = receipt(tmp_path, 1)
    value['protocol'] = 'recreated_verified'
    write(first / 'receipt.json', value)
    assert canonical(Evidence(tmp_path), RUN)['protocol'] == 'recreated_verified'
    receipt(tmp_path, 2)
    mixed = canonical(Evidence(tmp_path), RUN)
    assert mixed['protocol'] is mixed['best_score'] is mixed['cohort'] is None


def test_bundled_evaluator_results_are_visible_and_grouped_by_manifest(tmp_path):
    folder, value = receipt(tmp_path, 1)
    value['task_source'] = dict(kind='bundled', id='arena-tasks',
        manifest_sha256='5' * 64, external_files_sha256='6' * 64, file_count=6000)
    write(folder / 'receipt.json', value)
    result = canonical(Evidence(tmp_path), RUN)
    assert result['status'] == 'recorded' and result['valid'] == 1
    assert result['best_score'] == 1.0 and result['cohort']
    folder2, value2 = receipt(tmp_path, 2)
    value2['task_source'] = {**value['task_source'], 'manifest_sha256': '7' * 64}
    write(folder2 / 'receipt.json', value2)
    result = canonical(Evidence(tmp_path), RUN)
    assert result['evaluations'] == 2 and result['cohort'] is None
    assert result['best_score'] is None and result['status'] == 'partial'


def test_bundled_results_with_changed_native_assets_are_separate(tmp_path):
    for index in (1, 2):
        folder, value = receipt(tmp_path, index)
        value['task_source'] = dict(kind='bundled', id='arena-tasks',
            manifest_sha256='5' * 64, external_files_sha256=str(index) * 64, file_count=6000)
        write(folder / 'receipt.json', value)
    result = canonical(Evidence(tmp_path), RUN)
    assert result['evaluations'] == 2 and result['cohort'] is None


def test_invalid_initial_reference_is_not_replaced_with_later_success(tmp_path):
    receipt(tmp_path, 1, score=None, valid=False)
    receipt(tmp_path, 2, score=0.0)
    result = canonical(Evidence(tmp_path), RUN)
    assert result['seed_score'] is None and result['score_gain'] is None
    assert result['best_score'] == 0.0
    assert (result['valid'], result['invalid']) == (1, 1)


def test_unknown_validity_is_not_counted_as_invalid_or_success(tmp_path):
    receipt(tmp_path, 1, score=1.0, valid=None)
    result = canonical(Evidence(tmp_path), RUN)
    assert result['unknown'] == 1 and result['valid'] == result['invalid'] == 0
    assert result['best_score'] is None


def test_rejected_earlier_receipt_cannot_make_later_success_the_seed(tmp_path):
    folder, value = receipt(tmp_path, 1)
    value['control'] = []
    write(folder / 'receipt.json', value)
    receipt(tmp_path, 2, score=.8)
    result = canonical(Evidence(tmp_path), RUN)
    assert result['status'] == 'partial' and result['best_score'] == .8
    assert result['seed_score'] is result['score_gain'] is None


def test_oversized_numeric_score_does_not_break_results(tmp_path):
    receipt(tmp_path, 1, score=10**400)
    result = canonical(Evidence(tmp_path), RUN)
    assert result['valid'] == 0 and result['unknown'] == 1
    assert result['best_score'] is None


def test_mixed_evaluator_revisions_do_not_share_a_score_or_cohort(tmp_path):
    receipt(tmp_path, 1)
    receipt(tmp_path, 2, source='9' * 40)
    result = canonical(Evidence(tmp_path), RUN)
    assert result['valid'] == 2
    assert result['cohort'] is result['best_score'] is None
    assert result['status'] == 'partial'


def test_unpinned_local_evaluators_still_require_one_identity_for_aggregation(tmp_path):
    for index, source in [(1, '1' * 40), (2, '9' * 40)]:
        folder, value = receipt(tmp_path, index, source=source, score=index)
        value['execution'] = {'kind': 'local_trusted'}
        write(folder / 'receipt.json', value)
    result = canonical(Evidence(tmp_path), RUN)
    assert result['status'] == 'partial' and result['valid'] == 2
    assert result['best_score'] is result['seed_score'] is result['score_gain'] is None


@pytest.mark.parametrize('tamper', ['candidate', 'native', 'owner', 'symlink'])
def test_changed_or_cross_run_evidence_is_not_published_as_valid(tmp_path, tamper):
    folder, value = receipt(tmp_path, 1)
    if tamper == 'candidate':
        (folder / 'input/program.py').write_text('changed')
    elif tamper == 'native':
        (folder / 'native-output/native.json').write_text('{}')
    elif tamper == 'owner':
        value['control']['run_id'] = 'b' * 32
        write(folder / 'receipt.json', value)
    else:
        path = folder / 'input'
        path.rename(folder / 'original-input')
        path.symlink_to(folder / 'original-input', target_is_directory=True)
    result = canonical(Evidence(tmp_path), RUN)
    assert result['status'] == 'partial' and result['valid'] == 0
    assert result['best_score'] is None


def test_minimization_gain_and_environment_identity(tmp_path):
    for index, score in [(1, 10), (2, 7)]:
        folder, value = receipt(tmp_path, index, score=score)
        value['direction'] = 'minimize'
        write(folder / 'receipt.json', value)
    result = canonical(Evidence(tmp_path), RUN)
    assert (result['seed_score'], result['best_score'], result['score_gain']) == (10, 7, 3)
    for path in tmp_path.glob('canonical-evaluations/*/receipt.json'):
        value = json.loads(path.read_text())
        value['execution'] = {'kind': 'local_trusted'}
        write(path, value)
    assert canonical(Evidence(tmp_path), RUN)['cohort'] is None


def call(root, index, *, failed=False, kind='llm', model=MODEL):
    from arena.results import digest
    key = f'fixture-call-{index}'
    request = {'index': index, 'model': model}
    request_hash = digest({'kind': kind, 'request': request})
    folder = root / 'native/.parallel/wave-1/calls' / hashlib.sha256(key.encode()).hexdigest()
    write(folder / 'intent.json', {'schema': 'sciel-parallel-call/1', 'key': key,
                                 'kind': kind, 'request': request, 'request_sha256': request_hash})
    write(folder / 'dispatched.json', {'request_sha256': request_hash})
    payload = {'status': 'error' if failed else 'returned', 'request_sha256': request_hash,
               'value': {'model': model, 'prompt_tokens': 100, 'completion_tokens': 30,
                         'cost': 9999, 'text': 'private model output must never leave'}}
    write(folder / 'receipt.json', {'payload': payload, 'sha256': digest(payload)})
    return folder


def test_token_ledger_retains_unknown_failed_cost_and_never_prices_native_estimate(tmp_path):
    call(tmp_path, 1)
    call(tmp_path, 2, kind='evaluation')
    call(tmp_path, 3, failed=True)
    value = sciel_usage(Evidence(tmp_path), MODEL)
    assert value['requests'] == 2 and value['total_tokens'] == 130
    assert value['complete'] is False and value['usd'] is None
    assert 'private model output' not in json.dumps(value)


def test_token_receipts_require_matching_hash_and_model(tmp_path):
    folder = call(tmp_path, 1)
    path = folder / 'receipt.json'
    value = json.loads(path.read_text())
    value['payload']['value']['prompt_tokens'] = 0
    write(path, value)
    call(tmp_path, 2, model='different-model')
    usage = sciel_usage(Evidence(tmp_path), MODEL)
    assert usage['total_tokens'] is None and usage['complete'] is False


def test_token_receipt_requires_matching_dispatch(tmp_path):
    folder = call(tmp_path, 1)
    write(folder / 'dispatched.json', {'request_sha256': 'e' * 64})
    usage = sciel_usage(Evidence(tmp_path), MODEL)
    assert usage['total_tokens'] is None and usage['complete'] is False


def test_failed_process_keeps_canonical_evidence_without_exposing_native_code(tmp_path):
    root = tmp_path / RUN / 'artifacts'
    receipt(root, 1)
    write(root / '.arena/native-result.json', {'schema': 'arena.native-result/1', 'framework': 'fixture',
          'native': {}, 'artifacts': [], 'secret': 'private-engine-code'})
    service = SimpleNamespace(runs_dir=tmp_path, _public=lambda row: {k: row[k] for k in ('id', 'framework', 'state')})
    value = project_run(service, {'id': RUN, 'framework': 'fixture', 'state': 'failed', 'model': MODEL,
                                 'started': 10.0, 'ended': 20.0})
    assert value['state'] == 'failed' and value['metrics']['canonical']['valid'] == 1
    assert value['metrics']['wall_seconds'] == 10
    assert 'private-engine-code' not in json.dumps(value)


def test_native_label_cannot_publish_credential_shaped_text(tmp_path):
    root = tmp_path / RUN / 'artifacts'
    write(root / '.arena/native-result.json', {'schema': 'arena.native-result/1', 'framework': 'fixture',
          'native': {'task': 'sk-REVIEWONLY0123456789', 'metric': 'Bearer fixture-key'}, 'artifacts': []})
    service = SimpleNamespace(runs_dir=tmp_path, _public=lambda row: {'id': row['id']})
    value = project_run(service, {'id': RUN, 'framework': 'fixture', 'state': 'completed', 'model': MODEL,
                                 'started': 10, 'ended': 20})
    assert value['metrics']['native']['task'] is value['metrics']['native']['metric'] is None
    assert 'REVIEWONLY' not in json.dumps(value) and 'fixture-key' not in json.dumps(value)


def test_reading_cannot_follow_parent_links_or_execute_candidate(tmp_path):
    external = tmp_path / 'private'
    external.mkdir()
    (external / 'secret.json').write_text('{"secret":"never publish"}')
    root = tmp_path / 'root'
    root.mkdir()
    (root / 'linked').symlink_to(external, target_is_directory=True)
    with pytest.raises((OSError, ValueError)):
        Evidence(root).read('linked/secret.json')
    with pytest.raises(ValueError):
        Evidence(root).read('../private/secret.json')


def test_deeply_nested_evidence_is_bounded(tmp_path):
    (tmp_path / 'deep.json').write_text('{"value":' + '[' * 2000 + '0' + ']' * 2000 + '}')
    with pytest.raises(ValueError, match='nesting limit'):
        Evidence(tmp_path).read('deep.json')
