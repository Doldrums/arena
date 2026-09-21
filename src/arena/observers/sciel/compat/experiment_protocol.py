"""Pure SCiEL compatibility projection; source SHA256 17dcdfbe3daa44b6da3eaf261fd430a6b079e5ac3c8bded92c92e476f316a8a1."""
from copy import deepcopy
import json
import math
from .models import require_hash

SCHEMA = 'sciel-experimental-protocol/1'
TEXT_FIELDS = ('question_key', 'new_uncertainty', 'budget_reason', 'saved_state_plan')
KINDS = ('diagnostic', 'controlled_comparison', 'follow_up', 'closure')
BUDGETS = ('initial', 'maintain', 'reallocate', 'escalate', 'none')
CITATION_GUIDANCE = 'prior_receipt_ids: only listed lowercase SHA256 (64 hex) tool receipt_id or canonical_evaluations[].artifact_id; [] if none. Never use/hash ordinary evaluation_id (evaluation:...), program IDs or source hashes. Canonical IDs are evidence, not stage inputs/benefit. '

def parse_protocol(value):
    fields = {*TEXT_FIELDS, 'conditions_json', 'kind', 'budget_action', 'prior_receipt_ids', 'arms', 'matched_seeds', 'cpu_seconds_per_arm'}
    if type(value) is not dict or set(value) != fields:
        raise ValueError('experimental_protocol requires the complete declared experiment design')
    result = deepcopy(value)
    if value['kind'] not in KINDS or value['budget_action'] not in BUDGETS:
        raise ValueError('unsupported experiment kind or budget allocation')
    for key in (*TEXT_FIELDS, 'conditions_json'):
        if type(value[key]) is not str or len(value[key]) > 4000:
            raise ValueError('experimental_protocol.' + key + ' must be a bounded string')
    if not value['question_key'].strip():
        raise ValueError('question_key must identify the persistent testable question')
    refs = value['prior_receipt_ids']
    if type(refs) is not list or len(refs) > 16 or len(set(refs)) != len(refs):
        raise ValueError('prior_receipt_ids must be at most 16 distinct immutable receipts')
    for ident in refs:
        try:
            require_hash(ident, 'prior experiment receipt')
        except ValueError as error:
            raise ValueError(str(error) + '. ' + CITATION_GUIDANCE) from None
    seeds = value['matched_seeds']
    arms = value['arms']
    if type(seeds) is not list or len(seeds) > 64 or any((type(seed) is not int for seed in seeds)) or (len(set(seeds)) != len(seeds)):
        raise ValueError('matched_seeds must be distinct integers, at most 64')
    if type(arms) is not list or len(arms) > 16:
        raise ValueError('experiment arms must be a bounded list')
    for arm in arms:
        if type(arm) is not dict or set(arm) != {'id', 'method'} or any((type(v) is not str or not v.strip() or len(v) > 2000 for v in arm.values())):
            raise ValueError('each arm requires a distinct id and concrete method')
    if len({arm['id'] for arm in arms}) != len(arms):
        raise ValueError('experiment arm ids must be unique')
    cpu = value['cpu_seconds_per_arm']
    if cpu is not None and (type(cpu) not in (int, float) or not math.isfinite(cpu) or cpu <= 0):
        raise ValueError('declared CPU per arm must be finite and positive')

    def finite_float(text):
        value = float(text)
        if not math.isfinite(value):
            raise ValueError('nonfinite condition')
        return value

    def unique_pairs(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('duplicate condition key')
            value[key] = item
        return value
    try:
        conditions = json.loads(value['conditions_json'] or '{}', parse_float=finite_float, object_pairs_hook=unique_pairs, parse_constant=lambda s: (_ for _ in ()).throw(ValueError('nonfinite condition')))
    except (ValueError, TypeError, RecursionError):
        raise ValueError('conditions_json must encode a finite object') from None
    if type(conditions) is not dict:
        raise ValueError('conditions_json must encode an object')
    if value['kind'] == 'controlled_comparison':
        if len(arms) < 2 or len(seeds) < 2 or cpu is None or (not conditions) or (not value['saved_state_plan'].strip()):
            raise ValueError('controlled comparison requires >=2 arms, >=2 matched seeds, one equal positive CPU cap, explicit common conditions and a saved best/state/seed plan')
    return result

def result_assessment(observations, protocol):
    """Check saved report shape only; never upgrade model/tool claims to trust."""
    if protocol is None or protocol.get('kind') != 'controlled_comparison':
        return None
    expected = {(arm['id'], seed) for arm in protocol['arms'] for seed in protocol['matched_seeds']}
    rows = observations.get('comparison_results') if type(observations) is dict else None
    problems = []
    actual = set()
    if type(rows) is not list:
        problems.append('comparison_results missing or not an array')
    else:
        for row in rows:
            if type(row) is not dict or type(row.get('arm_id')) is not str or type(row.get('seed')) is not int:
                problems.append('invalid arm_id/seed')
                continue
            key = (row['arm_id'], row['seed'])
            if key in actual:
                problems.append('duplicate arm/seed result')
            actual.add(key)
            cpu = row.get('cpu_seconds')
            if type(cpu) not in (int, float) or not math.isfinite(cpu) or (not 0 <= cpu <= protocol['cpu_seconds_per_arm']):
                problems.append('reported CPU missing, invalid or above declared cap')
            if not {'best_result', 'saved_state', 'conditions'} <= set(row):
                problems.append('best_result/saved_state/conditions missing')
            elif row['conditions'] != json.loads(protocol['conditions_json'] or '{}'):
                problems.append('reported conditions differ')
        if actual != expected:
            problems.append('arm/seed coverage differs')
    return {'schema': SCHEMA, 'report_shape': 'invalid' if problems else 'complete', 'problems': list(dict.fromkeys(problems)), 'adherence': 'tool_reported_unverified', 'scope': 'Shape validation does not establish equal actual CPU, truthful measurements, or canonical task benefit.'}
