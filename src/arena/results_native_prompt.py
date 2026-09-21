"""Native held-out prompt and workflow evaluation contracts."""
from __future__ import annotations

import csv
import io
import math
import re
from .results_native_evidence import (
    HASH,
    _count,
    _number,
)


GSM8K_DATASET = '98abad8a6fc5b24172c329f257815fe0c4c3b6756716a9de980d4ed1be96a974'


GSM8K_METRIC = 'c22b81bccaaebfd1123be296e8b3c3dca3ddc704c46b70bf4a50603bb627e197'


PENGUINS_DATASET = 'f743ab0bd8d500798fc0ab83fdd3547b924e9c1acb15ca11b65ac228c0ab557a'


def _accuracy(value):
    value = _number(value)
    if value is None or not 0 <= value <= 1:
        raise ValueError('Invalid native accuracy')
    return value


def _heldout(result, *, task, seed, selected, correct, total, selection_score, selection_split, definition):
    result.update(best_score=selected, seed_score=seed, metric='heldout_accuracy', direction='maximize',
        task=task, evaluation_split='heldout', selection_split=selection_split,
        heldout_correct=correct, heldout_total=total, named_metrics={'selection_accuracy': selection_score},
        metric_definition=definition,
        score_kind='Held-out accuracy of the native-selected candidate, selected before held-out evaluation; not the maximum held-out score. Small integration pilot, not canonical evaluation.')


def _gsm8k_report(report):
    total, correct = _count(report.get('total')), _count(report.get('correct'))
    records = report.get('records')
    if total != 8 or correct is None or correct > total or type(records) is not list or len(records) != total:
        raise ValueError('Incomplete held-out GSM8K observations')
    ids, hashes = set(), set()
    for row in records:
        index, digest = _count(row.get('source_index_zero_based')), row.get('question_sha256')
        if (row.get('source_split') != 'test' or index is None or index in ids
                or type(digest) is not str or not HASH.fullmatch(digest) or digest in hashes
                or type(row.get('correct')) is not bool):
            raise ValueError('Invalid or duplicate held-out GSM8K observation')
        # This is the pinned dataset.py string-extraction contract, not a new
        # judge. Recheck its stored outcome without running participant code.
        prediction, extracted, gold = row.get('prediction'), row.get('extracted_prediction'), row.get('gold')
        if not all(type(v) is str for v in (prediction, extracted, gold)):
            raise ValueError('Missing GSM8K native metric inputs')
        match = re.search(r'#### (\-?[0-9\.\,]+)', prediction)
        expected = match.group(1).strip().replace(',', '') if match else '[invalid]'
        if extracted != expected or gold == '[invalid]' or row['correct'] != (expected == gold):
            raise ValueError('GSM8K correctness differs from pinned metric')
        ids.add(index)
        hashes.add(digest)
    score = _accuracy(report.get('accuracy'))
    if correct != sum(row['correct'] for row in records) or score != correct / total:
        raise ValueError('Held-out accuracy disagrees with observations')
    return score, correct, {(row['source_index_zero_based'], row['question_sha256']) for row in records}


def _prompt_gsm8k(art, framework, result):
    protocol = art.json('results/protocol.json')
    metric = protocol.get('metric', {})
    if (protocol.get('schema') != 'arena.prompt-pilot-protocol/1' or protocol.get('framework') != framework
            or protocol.get('canonical_evaluation') is not False or protocol.get('dataset_sha256') != GSM8K_DATASET
            or protocol.get('split_sizes') != {'train': 8, 'validation': 8, 'heldout': 8}
            or metric.get('source_sha256') != GSM8K_METRIC
            or metric.get('functions') != ['extract_answer', 'is_correct']):
        raise ValueError('Unknown prompt pilot dataset/metric contract')
    heldout = art.json('results/heldout.json')
    if (heldout.get('schema') != 'arena.prompt-pilot-heldout/1' or heldout.get('canonical_evaluation') is not False
            or heldout.get('selection_split') != 'validation' or set(heldout.get('reports', {})) != {'seed', 'selected'}):
        raise ValueError('Held-out report does not preserve validation selection')
    scores, identities = {}, {}
    for label in ('seed', 'selected'):
        report = art.json('results/heldout-' + label + '.json')
        if (report.get('status') != 'completed'
                or {k: v for k, v in report.items() if k != 'status'} != heldout['reports'][label]):
            raise ValueError('Partial or inconsistent held-out report')
        scores[label], correct, identities[label] = _gsm8k_report(report)
    if identities['seed'] != identities['selected']:
        raise ValueError('Seed and selected candidate use different held-out observations')
    if framework == 'gepa-gateway-gsm8k':
        native = art.json('results/gepa-result.json')
        values, index = native.get('val_aggregate_scores'), _count(native.get('best_idx'))
        if type(values) is not list or not values or len(values) > 1024 or index is None or index >= len(values):
            raise ValueError('Missing GEPA validation selection')
        values = [_accuracy(v) for v in values]
        if values[index] != max(values):
            raise ValueError('GEPA selected candidate disagrees with validation ranking')
        selection_score = values[index]
    else:
        native = art.json('results/native-summary.json')
        value = _number(native.get('validation_score_percent'))
        if native.get('native_optimizer') != 'MIPROv2' or value is None:
            raise ValueError('Missing MIPROv2 validation selection')
        selection_score = _accuracy(value / 100)
    _heldout(result, task='gsm8k', seed=scores['seed'], selected=scores['selected'], correct=correct, total=8,
        selection_score=selection_score, selection_split='validation',
        definition='Pinned official GSM8K extract_answer/is_correct: first #### numeric capture, comma removal and exact string equality.')
    result['metric_source_sha256'] = GSM8K_METRIC


def _aflow_csv(art, path):
    rows = list(csv.DictReader(io.StringIO(art.raw(path).decode('utf-8'))))
    if len(rows) != 8:
        raise ValueError('Incomplete AFlow observations')
    questions, scores = set(), []
    for row in rows:
        if set(row) != {'question', 'prediction', 'expected_output', 'score', 'cost'}:
            raise ValueError('Unknown AFlow native CSV contract')
        question, score = row['question'], row['score']
        if type(question) is not str or not question or question in questions or score not in {'0.0', '1.0', '0', '1'}:
            raise ValueError('Invalid or duplicate AFlow observation')
        questions.add(question)
        scores.append(float(score))
    return sum(scores) / 8, int(sum(scores)), questions


def _aflow(art, result):
    pilot, selection = art.json('results/pilot.json'), art.json('results/selection.json')
    selected = _count(selection.get('round'))
    if (pilot.get('schema') != 'arena.aflow-gsm8k-pilot/1' or pilot.get('canonical_evaluation') is not False
            or pilot.get('source_commit') != '3f457218fc716093fe53f6df8a5d5e6379d66346'
            or pilot.get('dataset_sha256') != GSM8K_DATASET or pilot.get('native_completed') is not True
            or pilot.get('heldout_completed') is not True or selection.get('heldout_seen') is not False
            or selected not in {1, 2, 3} or pilot.get('selected_round') != selected):
        raise ValueError('AFlow selection/held-out receipt is incomplete')
    data = {name: pilot.get(name + '_data', {}) for name in ('validation', 'heldout')}
    for item in data.values():
        digest = item.get('sha256')
        if item.get('count') != 8 or type(digest) is not str or not HASH.fullmatch(digest):
            raise ValueError('Unknown AFlow split manifest')
    if data['validation']['sha256'] == data['heldout']['sha256']:
        raise ValueError('AFlow selection and held-out data overlap')
    prefix = 'workspace/aflow-gateway-gsm8k-v1/workspace/GSM8K/workflows/'
    ranking = art.json(prefix + 'results.json')
    if type(ranking) is not list or len(ranking) != 3 or {r.get('round') for r in ranking} != {1, 2, 3}:
        raise ValueError('Incomplete native AFlow validation ranking')
    validation = {}
    validation_questions = None
    for row in ranking:
        number = row['round']
        path = art.one(re.escape(prefix) + 'round_' + str(number) + r'/[0-9.]+_[0-9_]+\.csv')
        score, _, questions = _aflow_csv(art, path)
        if _accuracy(row.get('score')) != score or (validation_questions is not None and questions != validation_questions):
            raise ValueError('AFlow validation scores or observations disagree')
        validation[number], validation_questions = score, questions
    if _accuracy(selection.get('validation_score')) != validation[selected] or validation[selected] != max(validation.values()):
        raise ValueError('AFlow candidate was not selected by native validation ranking')
    scores, identities = {}, {}
    for number in dict.fromkeys((1, selected)):
        path = art.one('results/heldout-round-' + str(number) + r'/[0-9.]+_[0-9_]+\.csv')
        score, correct, questions = _aflow_csv(art, path)
        if _accuracy(pilot.get('heldout', {}).get(str(number), {}).get('score')) != score or questions & validation_questions:
            raise ValueError('AFlow held-out score or split disagrees')
        scores[number], identities[number] = (score, correct), questions
    if identities[1] != identities[selected]:
        raise ValueError('AFlow seed and selected held-out observations differ')
    _heldout(result, task='gsm8k', seed=scores[1][0], selected=scores[selected][0], correct=scores[selected][1], total=8,
        selection_score=validation[selected], selection_split='validation',
        definition='Pinned native AFlow GSM8KBenchmark: last-number float extraction with absolute tolerance 1e-6. Distinct from official GSM8K string matching.')


def _promptagent(art, result):
    prefix = 'promptagent-pilot/'
    receipt = art.json(prefix + 'pilot-receipt.json')
    splits = art.json(prefix + 'native-splits.json')
    frozen = art.json(prefix + 'frozen-search-state.json')
    native = art.json(prefix + 'native-result.json')
    if (receipt.get('schema') != 'arena.promptagent-pilot/1' or receipt.get('framework') != 'promptagent-penguins-gateway'
            or receipt.get('source_commit') != '2edfc9e4462a6af97dc973442d074de9b3e876b2'
            or receipt.get('canonical_evaluation') is not False or receipt.get('heldout_frozen') is not True
            or receipt.get('splits_sha256') != art.files[prefix + 'native-splits.json']
            or receipt.get('frozen_state_sha256') != art.files[prefix + 'frozen-search-state.json']
            or splits.get('schema') != 'arena.promptagent-native-splits/1' or splits.get('dataset_sha256') != PENGUINS_DATASET
            or splits.get('disjoint') is not True):
        raise ValueError('PromptAgent held-out freeze/split evidence disagrees')
    hashes, records = set(), splits.get('record_hashes', {})
    if set(records) != {'train', 'eval', 'test'}:
        raise ValueError('Unknown PromptAgent split names')
    for name, count in (('train', 8), ('eval', 4), ('test', 4)):
        values = records[name]
        if (type(values) is not list or len(values) != count
                or any(type(v) is not str or not HASH.fullmatch(v) for v in values)
                or len(set(values)) != count or hashes & set(values)):
            raise ValueError('PromptAgent split overlaps or contains missing observations')
        hashes.update(values)
    nodes = native.get('all_nodes')
    if (type(nodes) is not list or not nodes or len(nodes) > 1024 or type(frozen) is not list
            or len(frozen) != len(nodes) or receipt.get('native_nodes') != len(nodes)):
        raise ValueError('Incomplete PromptAgent frozen search state')
    frozen_by_id = {row['id']: row for row in frozen}
    by_id = {}
    for row in nodes:
        identity = _count(row.get('id'))
        if identity is None or identity in by_id or identity not in frozen_by_id:
            raise ValueError('Invalid PromptAgent native node identity')
        before = {k: v for k, v in frozen_by_id[identity].items() if k != 'cum_rewards'}
        if before != {k: v for k, v in row.items() if k != 'test_metric'}:
            raise ValueError('PromptAgent search changed after held-out evaluation began')
        by_id[identity] = row
    selected = native.get('best_reward_path_selected_node')
    path = native.get('best_reward_path')
    if (type(selected) is not list or len(selected) != 1 or type(path) is not list or not path
            or len(path) > len(nodes) or any(row != by_id.get(row.get('id')) for row in path)
            or selected[0] not in path):
        raise ValueError('Unknown PromptAgent native reward-selected path')
    row = selected[0]
    reward = _accuracy(row.get('reward'))
    heldout = _accuracy(row.get('test_metric'))
    if (reward != max(_accuracy(node.get('reward')) for node in path)
            or receipt.get('selected_node') != {'id': row['id'], 'reward': reward, 'heldout_accuracy': heldout}
            or not math.isclose(heldout * 4, round(heldout * 4), abs_tol=1e-9)):
        raise ValueError('PromptAgent selected metric disagrees with frozen native selection')
    roots = [node for node in nodes if node.get('parent') == -1 and node.get('depth') == 0]
    seed = _accuracy(roots[0]['test_metric']) if len(roots) == 1 and roots[0].get('test_metric') is not None else None
    if seed is not None and not math.isclose(seed * 4, round(seed * 4), abs_tol=1e-9):
        raise ValueError('PromptAgent seed accuracy disagrees with test denominator')
    _heldout(result, task='penguins-in-a-table', seed=seed, selected=heldout, correct=round(heldout * 4), total=4,
        selection_score=reward, selection_split='reward',
        definition='Native PromptAgent penguins accuracy on the four frozen test examples; MCTS reward uses four separate evaluation examples.')
    result.update(candidates=len(nodes), iterations=_count(receipt.get('iterations_completed')),
        candidate_count_scope='Distinct stored native MCTS node IDs, not model calls or evaluator invocations.')
