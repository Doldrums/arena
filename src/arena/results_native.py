"""Explicit, hash-checked native metric contracts. Never load participant code.

This module projects known native artifacts, not a common leaderboard score.
Counts describe stored evidence only; model calls/evaluations are not inferred
from iteration limits, population size, machine CPU count or repeated snapshots.
"""
from __future__ import annotations

import hashlib
import csv
import io
import json
import math
from pathlib import PurePosixPath
import re

HASH = re.compile(r'[a-f0-9]{64}')
INTEGER = re.compile(r'0|[1-9][0-9]{0,8}')
NUMBER = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
SUPPORTED = {'adaevolve', 'evox', 'openevolve', 'base', 'eoh', 'meoh',
             'reevo', 'hsevo', 'loongflow', 'codeevolve', 'coevo', 'coevo-observed-v2',
             'darwinian-evolver-gateway', 'aflow-gateway-gsm8k-v1',
             'promptagent-penguins-gateway', 'gepa-gateway-gsm8k', 'miprov2-gateway-gsm8k'}

GSM8K_DATASET = '98abad8a6fc5b24172c329f257815fe0c4c3b6756716a9de980d4ed1be96a974'
GSM8K_METRIC = 'c22b81bccaaebfd1123be296e8b3c3dca3ddc704c46b70bf4a50603bb627e197'
PENGUINS_DATASET = 'f743ab0bd8d500798fc0ab83fdd3547b924e9c1acb15ca11b65ac228c0ab557a'


def _number(value):
    try:
        return value if type(value) in (int, float) and math.isfinite(value) else None
    except OverflowError:
        return None


def _count(value):
    return value if type(value) is int and 0 <= value <= 10**9 else None


def _pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            raise ValueError('Duplicate native evidence key')
        result[key] = value
    return result


class _Artifacts:
    def __init__(self, evidence, native):
        self.evidence, self.files, self.used = evidence, {}, []
        rows = native.get('artifacts')
        if type(rows) is not list or len(rows) > 256:
            raise ValueError('Invalid native artifact inventory')
        for row in rows:
            if type(row) is not dict:
                raise ValueError('Invalid native artifact record')
            name, digest = row.get('path'), row.get('sha256')
            if (type(name) is not str or len(name) > 1024 or '\\' in name or '\x00' in name
                    or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts
                    or str(PurePosixPath(name)) != name or name in self.files
                    or type(digest) is not str or not HASH.fullmatch(digest)):
                raise ValueError('Invalid or duplicate native artifact path/hash')
            self.files[name] = digest

    def matching(self, pattern):
        return sorted(name for name in self.files if re.fullmatch(pattern, name))

    def one(self, pattern):
        paths = self.matching(pattern)
        if len(paths) != 1:
            raise ValueError('Expected one published native result')
        return paths[0]

    def raw(self, name, limit=2 * 1024**2):
        if name not in self.files:
            raise ValueError('Unlisted native evidence')
        raw = self.evidence.raw(name, limit)
        if hashlib.sha256(raw).hexdigest() != self.files[name]:
            raise ValueError('Native evidence hash mismatch')
        self.used.append(self.files[name])
        return raw

    def json(self, name, limit=2 * 1024**2):
        # Upstream may encode invalid scores as NaN/-Infinity. Keep them in
        # decoded input; _number excludes them instead of converting to zero.
        return json.loads(self.raw(name, limit), object_pairs_hook=_pairs)


def _circle(metrics):
    if type(metrics) is not dict or type(metrics.get('validity')) not in (int, float) or metrics['validity'] != 1:
        return None
    ratio = _number(metrics.get('target_ratio'))
    if ratio is None or _number(metrics.get('sum_radii')) is None or metrics['sum_radii'] < 0:
        return None
    if _number(metrics.get('combined_score')) != ratio:
        return None
    return ratio


def _sky(art, framework, result):
    prefix = 'native' if framework == 'openevolve' else 'results'
    best = art.json(prefix + '/best/best_program_info.json')
    score = _circle(best.get('metrics'))
    if score is None:
        raise ValueError('Best circle-packing record lacks valid agreeing metrics')
    result.update(best_score=score, metric='target_ratio', direction='maximize', task='circle-packing')
    metadata = art.matching(prefix + r'/checkpoints/checkpoint_[0-9]{1,9}/metadata\.json')
    iterations = []
    for path in metadata:
        value = art.json(path)
        n = _count(value.get('last_iteration'))
        if n is not None:
            iterations.append(n)
    result['iterations'] = max(iterations) if iterations else None
    records = {}
    for path in art.matching(prefix + r'/checkpoints/checkpoint_[0-9]{1,9}/programs/[a-f0-9-]+\.json'):
        row = art.json(path)
        identity = row.get('id')
        if type(identity) is not str or not re.fullmatch(r'[a-f0-9-]{1,64}', identity):
            raise ValueError('Invalid stored native program identity')
        records[identity] = row
    if records:
        result['candidates'] = len(records)
        result['candidate_count_scope'] = 'Distinct stored native program IDs, not evaluator invocations.'
        roots = [row for row in records.values() if 'parent_id' in row and row['parent_id'] is None]
        if len(roots) == 1:
            result['seed_score'] = _circle(roots[0].get('metrics'))


def _base(art, result):
    row = art.json('results/base-result.json')
    if row.get('schema_version') != 'base_online_v1' or row.get('task') != 'cp':
        raise ValueError('Unknown BaSE native result contract')
    arms = row.get('arm_results')
    if type(arms) is not list or not arms:
        raise ValueError('Missing native arms')
    scores = [_circle(arm.get('final_metrics')) for arm in arms if type(arm) is dict]
    scores = [score for score in scores if score is not None]
    best = _number(row.get('final_best_fitness'))
    if not scores or best != max(scores):
        raise ValueError('BaSE best result disagrees with valid arm metrics')
    result.update(best_score=best, seed_score=_number(row.get('init_best')), metric='target_ratio',
                  direction='maximize', task='circle-packing')
    selections = row.get('selections')
    if type(selections) is list and len(selections) <= 10000 and all(type(v) is int and 0 <= v < len(arms) for v in selections):
        result['iterations'] = len(selections)
        result['iteration_count_scope'] = 'Recorded native bandit rounds.'


def _eoh(art, result):
    best = art.json('results/results/samples/samples_best.json')
    value = _number(best.get('objective'))
    if value is None:
        raise ValueError('No finite native EoH objective')
    result.update(best_score=value, metric='mean_relative_bin_excess', direction='minimize', task='online-bin-packing')
    samples = []
    for path in art.matching(r'results/results/samples/samples_[0-9]{1,9}~[0-9]{1,9}\.json'):
        rows = art.json(path, 4 * 1024**2)
        if type(rows) is not list or len(rows) > 10000:
            raise ValueError('Invalid EoH sample array')
        samples += rows
    if samples:
        scores = [_number(row.get('objective')) for row in samples if type(row) is dict]
        scores = [score for score in scores if score is not None]
        if not scores or min(scores) != value:
            raise ValueError('EoH best does not agree with published samples')
        codes = {hashlib.sha256(row['code'].encode()).hexdigest() for row in samples
                 if type(row) is dict and type(row.get('code')) is str}
        result['candidates'] = len(codes) if codes else None
        result['candidate_count_scope'] = 'Distinct source strings in published native samples.'
    generations = art.matching(r'results/results/pops/population_generation_[0-9]{1,9}\.json')
    if generations:
        path = max(generations, key=lambda name: int(re.search(r'([0-9]{1,9})\.json$', name)[1]))
        rows = art.json(path)
        if type(rows) is not list:
            raise ValueError('Invalid native EoH population')
        result['iterations'] = int(re.search(r'([0-9]{1,9})\.json$', path)[1])


def _meoh(art, result):
    paths = art.matching(r'results/[0-9_]+/population/pop_[0-9]{1,9}\.json')
    if not paths or len({p.split('/')[1] for p in paths}) != 1:
        raise ValueError('Missing or ambiguous MEoH native population')
    path = max(paths, key=lambda name: int(re.search(r'pop_([0-9]{1,9})', name)[1]))
    rows = art.json(path, 4 * 1024**2)
    if type(rows) is not list or len(rows) > 1000:
        raise ValueError('Invalid MEoH population')
    points = []
    for row in rows:
        score = row.get('score') if type(row) is dict else None
        if type(score) is list and len(score) == 2 and all(_number(v) is not None for v in score):
            points.append({'negative_mean_bins': score[0], 'negative_mean_evaluation_seconds': score[1]})
    if not points:
        raise ValueError('No finite paired MEoH objectives')
    result.update(metric='native_two_objective_population', task='online-bin-packing',
        objectives=[{'metric':'negative_mean_bins','direction':'maximize'},
                    {'metric':'negative_mean_evaluation_seconds','direction':'maximize'}],
        population_objectives=points, iterations=int(re.search(r'pop_([0-9]{1,9})', path)[1]),
        population_size=len(rows), score_kind='Paired final population objectives; no scalar best is defined.')


def _validation(art, framework, result):
    path = art.one(r'workspace/' + framework + r'/outputs/[A-Za-z0-9_./-]+/best_code_overall_val_stdout\.txt')
    text = art.raw(path, 65536).decode('utf-8')
    pattern = (r'\[\*\] Running \.\.\.\nweibull_5k_val\.pickle\n\s*Average number of bins: (' + NUMBER
               + r')\n\s*Lower bound on optimum: (' + NUMBER + r')\n\s*Excess: (' + NUMBER
               + r')%\n\[\*\] Average:\n(' + NUMBER + r')\n?')
    match = re.fullmatch(pattern, text)
    if not match:
        raise ValueError('Unknown native validation stdout contract')
    bins, lower, rounded, excess = map(float, match.groups())
    if (any(_number(v) is None for v in (bins, lower, rounded, excess)) or lower <= 0 or bins < 0
            or not math.isclose((bins-lower)/lower*100, excess, rel_tol=1e-8, abs_tol=1e-8)
            or abs(rounded-excess) > 0.0051):
        raise ValueError('Inconsistent native validation metrics')
    result.update(best_score=excess, metric='validation_excess_percent', direction='minimize',
        task='online-bin-packing', score_kind='Held-out validation of the native-selected program; not training best.',
        named_metrics={'validation_mean_bins':bins, 'validation_lower_bound':lower})


def _loongflow(art, result):
    paths = art.matching(r'workspace/loongflow/results/[a-f0-9-]+/[0-9]{1,9}/executor/best_evaluation\.json')
    if not paths or len({p.split('/')[3] for p in paths}) != 1:
        raise ValueError('Missing or ambiguous native LoongFlow run')
    scores = []
    for path in paths:
        row = art.json(path)
        metrics = row.get('metrics', {})
        if (row.get('status') == 'success' and type(metrics) is dict
                and type(metrics.get('validity')) in (int,float) and metrics['validity'] == 1
                and _number(row.get('score')) is not None
                and _number(metrics.get('target_ratio')) == row['score']):
            scores.append(row['score'])
    if not scores:
        raise ValueError('No successful valid LoongFlow native score')
    result.update(best_score=max(scores), metric='target_ratio', direction='maximize', task='circle-packing',
                  iterations=max(int(path.split('/')[4]) for path in paths))


def _codeevolve(art, result):
    data = art.json('results/run_metadata.json')
    if type(data) is not dict or not data or any(not INTEGER.fullmatch(key) for key in data):
        raise ValueError('Invalid CodeEvolve iteration metadata')
    scores = []
    for row in data.values():
        best = row.get('best_sol', {})
        metrics = best.get('eval_metrics', {})
        score = _number(best.get('fitness'))
        if (score is not None and score > 0 and _number(metrics.get('benchmark_ratio')) == score
                and _number(metrics.get('radii_sum')) is not None and metrics['radii_sum'] > 0):
            scores.append(score)
    result.update(metric='benchmark_ratio', direction='maximize', task='circle-packing', iterations=max(map(int,data)))
    if not scores:
        raise ValueError('CodeEvolve zero penalties lack explicit validity; no positive agreeing result')
    result['best_score'] = max(scores)
    result['score_kind'] = 'Positive native fitness with agreeing radius/ratio metrics; no canonical validity claim.'


def _coevo(art, framework, result):
    paths = art.matching(r'workspace/' + framework + r'/results/oscillation_1_coevo/history/gen_[0-9]{1,9}\.json')
    scores, identities, generations = [], set(), []
    for path in paths:
        data = art.json(path, 4 * 1024**2)
        rows = data.get('solutions')
        if type(rows) is not list or len(rows) > 10000 or _count(data.get('generation')) is None:
            raise ValueError('Invalid native CoEvo history')
        generations.append(data['generation'])
        for row in rows:
            evaluation = row.get('evaluation_res', {})
            score = _number(evaluation.get('score'))
            if evaluation.get('valid') is True and score is not None:
                scores.append(score)
            if type(row.get('sol_string')) is str:
                identities.add(hashlib.sha256(row['sol_string'].encode()).hexdigest())
    if not scores:
        raise ValueError('No explicitly valid CoEvo native evaluations')
    result.update(best_score=max(scores), metric='negative_mse', direction='maximize', task='oscillation_1',
        candidates=len(identities), native_generation=max(generations),
        candidate_count_scope='Distinct stored solution strings; overwritten saves do not prove total evaluations or iterations.')


def _darwinian(art, result):
    seam = art.json('native/provider-seam.json', 65536)
    if (seam.get('schema') != 'arena.native-provider-seam/1'
            or seam.get('recipe') != 'darwinian-evolver-gateway'
            or seam.get('source_commit') != '7f12365d2059c47e29068a5a6f498a293148d2a9'
            or type(seam.get('native_argv')) is not list
            or seam['native_argv'][:1] != ['circle_packing']
            or seam.get('native_evaluator_modified') is not False):
        raise ValueError('Unknown Darwinian native evaluator binding')
    lines = art.raw('native/results.jsonl', 4 * 1024**2).splitlines()
    if not lines or len(lines) > 1000:
        raise ValueError('Invalid native iteration log')
    scores, identities = [], set()
    for index, line in enumerate(lines):
        row = json.loads(line, object_pairs_hook=_pairs)
        if type(row) is not dict or _count(row.get('iteration')) != index:
            raise ValueError('Noncontiguous native iteration log')
        organisms = row.get('population', {}).get('organisms')
        if type(organisms) is not list or len(organisms) > 10000:
            raise ValueError('Invalid Darwinian population')
        for entry in organisms:
            organism, evaluation = entry['organism'], entry['evaluation_result']
            identity = organism.get('id')
            if type(identity) is not str or not re.fullmatch(r'[a-f0-9-]{1,64}', identity):
                raise ValueError('Invalid Darwinian organism identity')
            identities.add(identity)
            value = _number(evaluation.get('score'))
            cases = evaluation.get('trainable_failure_cases')
            # The native evaluator uses score=0 for errors, and is_viable alone
            # is not packing validity. Its explicit successful-validation
            # marker and matching radius sum distinguish a measured result.
            valid = (value is not None and value >= 0 and type(cases) is list and len(cases) == 1
                     and cases[0].get('error_message') == 'Valid but suboptimal configuration.'
                     and _number(cases[0].get('sum_of_radii')) == value)
            if valid:
                scores.append(value)
                if index == 0 and len(organisms) == 1 and organism.get('parent_id') is None:
                    result['seed_score'] = value
    if not scores:
        raise ValueError('No explicitly valid Darwinian circle-packing score')
    result.update(best_score=max(scores), metric='sum_radii', direction='maximize', task='circle-packing',
                  iterations=len(lines)-1, candidates=len(identities),
                  candidate_count_scope='Distinct stored evaluated native organism IDs; not evaluator invocations.')


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


def project_native(evidence, framework, native_result):
    """Read only listed, hash-matching files through the caller's bounded reader."""
    result = dict(best_score=None, seed_score=None, metric=None, direction=None, task=None,
                  scope='native', evaluations=None, candidates=None, iterations=None, status='unsupported')
    if framework not in SUPPORTED:
        return result
    result['status'] = 'missing'
    try:
        if (type(native_result) is not dict or native_result.get('schema') != 'arena.native-result/1'
                or native_result.get('framework') != framework or native_result.get('canonical_evaluation') is not False):
            raise ValueError('Native identity/scope mismatch')
        art = _Artifacts(evidence, native_result)
        if framework in {'adaevolve','evox','openevolve'}:
            _sky(art,framework,result)
        elif framework == 'base': _base(art,result)
        elif framework == 'eoh': _eoh(art,result)
        elif framework == 'meoh': _meoh(art,result)
        elif framework in {'reevo','hsevo'}: _validation(art,framework,result)
        elif framework == 'loongflow': _loongflow(art,result)
        elif framework == 'codeevolve': _codeevolve(art,result)
        elif framework == 'darwinian-evolver-gateway': _darwinian(art,result)
        elif framework in {'gepa-gateway-gsm8k', 'miprov2-gateway-gsm8k'}: _prompt_gsm8k(art,framework,result)
        elif framework == 'aflow-gateway-gsm8k-v1': _aflow(art,result)
        elif framework == 'promptagent-penguins-gateway': _promptagent(art,result)
        else: _coevo(art,framework,result)
        result.update(status='partial' if native_result.get('status') != 'recorded' else 'recorded',
                      evidence_hashes=sorted(set(art.used)))
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError, OverflowError, RecursionError, csv.Error):
        # A failed required integrity/contract check must not leave a previously
        # read best score behind as if the overall projection had succeeded.
        result.update(best_score=None, seed_score=None, status='partial', candidates=None, iterations=None)
        result.pop('population_objectives',None)
        result.pop('named_metrics',None)
        evidence.issues.add('Native metric evidence is missing, incompatible, or failed integrity checks.')
    return result
