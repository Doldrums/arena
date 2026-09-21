"""Bounded method-registry readers, record validation and observability."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat

RESOURCES = ('dollars', 'cpu_seconds', 'gpu_seconds', 'wall_seconds', 'storage_bytes', 'steps')
HASH = re.compile(r'[0-9a-f]{64}\Z')
MAX_JOURNAL = 64 * 1024 * 1024
MAX_ARTIFACT = 4 * 1024 * 1024
MAX_ROWS = 100_000
MAX_PROJECTION_BYTES = 32 * 1024 * 1024
MAX_PROJECTION_OBJECTS = 2000
SECRET = re.compile(r'(?i)\b(?:sk-(?:or-v1-)?[a-z0-9_-]{16,}|bearer\s+[^\s,;"\x27]+)')


def obj(value):
    return value if isinstance(value, dict) else {}


def seq(value):
    return value if isinstance(value, list) else []


def registered_artifacts(rows):
    return {r['data']['id']: r['data']['kind'] for r in rows
        if r.get('kind') == 'artifact_registered' and isinstance(r['data'].get('id'), str)
        and HASH.fullmatch(r['data']['id']) and isinstance(r['data'].get('kind'), str)}


def validate_shape(value):
    """Only check fields whose types the projection relies on; never repair."""
    for key in ('id', 'lab_id', 'account_id', 'budget_account', 'context_id', 'call_receipt_id',
                'proposal_id', 'plan_id', 'experiment_id', 'method_id', 'revision_id',
                'request_sha256', 'reservation_id', 'key', 'category', 'status', 'metric',
                'author_lab', 'input_sha256', 'output_sha256', 'at', 'mode', 'kind'):
        if key in value and value[key] is not None and not isinstance(value[key], str):
            raise ValueError('invalid projection identifier')
    for key in ('parents', 'dependencies', 'active_methods', 'active_adapters', 'evidence_refs',
                'invoked_methods', 'invocation_refs', 'treatment', 'control', 'methods'):
        if key in value and (not isinstance(value[key], list) or any(not isinstance(v, str) for v in value[key])):
            raise ValueError('invalid projection reference list')
    for key in ('manifest', 'result', 'criterion'):
        if isinstance(value.get(key), dict):
            validate_shape(value[key])
    return value


def number(value):
    try:
        result = float(value) if type(value) in (int, float, str) else None
        return result if result is not None and math.isfinite(result) else None
    except (ValueError, OverflowError):
        return None


def clean(value, depth=0):
    if depth > 35:
        return '[nested data omitted]'
    if isinstance(value, dict):
        return {str(k): ('[redacted]' if str(k).lower() in
            {'api_key', 'authorization', 'access_token', 'refresh_token', 'password', 'secret'}
            else clean(v, depth + 1)) for k, v in list(value.items())[:4096]}
    if isinstance(value, list):
        return [clean(v, depth + 1) for v in value[:4096]]
    if isinstance(value, str):
        return SECRET.sub('[redacted]', value[:1_000_000])
    if isinstance(value, float):
        return number(value)
    return value if value is None or type(value) in (bool, int) else str(value)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def observability(*, artifacts, registered, metadata, labs, statuses, rows,
                  experiments, proposals, solutions, complete):
    """Map familiar dashboard concepts without inventing legacy engine cards.

    All arguments are the bounded, verified projection. Prompt bodies remain
    lazy-loaded, so receipt references alone never count as delivered knowledge.
    """
    def records(kind):
        return {ident: body for ident, body in artifacts.items() if registered.get(ident) == kind}

    plans = records('experiment_plan')
    experiments_by_plan = {}
    for experiment in experiments:
        experiments_by_plan.setdefault(experiment.get('plan_id'), []).append(experiment)
    questions = []
    for ident, plan in plans.items():
        outcomes = experiments_by_plan.get(ident, [])
        questions.append(dict(id=ident, record_kind='precommitted_experiment_plan',
            at=obj(metadata.get(ident)).get('at'), lab_id=plan.get('lab_id'),
            question=plan.get('question') if isinstance(plan.get('question'), str) else None,
            purpose=plan.get('purpose'), criterion=plan.get('criterion'), scope=plan.get('scope'),
            treatment=seq(plan.get('treatment')), control=seq(plan.get('control')),
            proposal_id=plan.get('proposal_id') if registered.get(plan.get('proposal_id')) == 'proposal_receipt' else None,
            experiment_ids=[e['id'] for e in outcomes],
            status=outcomes[-1].get('status') or 'outcome_recorded' if outcomes else 'planned'))

    submitted = [p for p in proposals if p.get('kind') == 'solution']
    solution_plans = {ident for ident, plan in plans.items() if plan.get('purpose') == 'solution'}
    trials = [e for e in experiments if e.get('plan_id') in solution_plans]
    calls = records('call_receipt')
    invoked_trials = [e for e in trials if any(
        obj(calls.get(ref)).get('category') == 'execution'
        and obj(obj(calls.get(ref)).get('result')).get('dispatch_status') == 'invoked'
        and obj(obj(calls.get(ref)).get('result')).get('plan_id') == e.get('plan_id')
        for ref in seq(e.get('invocation_refs')))]
    not_dispatched = sum(p.get('dispatch_status') == 'not_dispatched' for p in proposals)
    unclassified = sum(p.get('dispatch_status') != 'not_dispatched'
        and p.get('kind') not in ('method', 'experiment', 'solution', 'stop') for p in proposals)
    refused = sum(p.get('status') == 'refused' for p in submitted)
    failed = sum(e.get('status') == 'failed' for e in trials)
    invalid = sum(e.get('status') == 'completed' and e.get('valid_treatment') is False for e in trials)
    unverified = len(records('solution')) - len(solutions)
    nonaccepted = len(records('solution_evaluation'))
    if solutions:
        program_status = 'evaluated'
        reason = f'{len(solutions)} valid Program/evaluation records are bound to actual solution executions.'
    elif submitted or solution_plans or unverified or nonaccepted:
        program_status = 'requested_no_accepted_program'
        reason = ('Solution work is recorded, but no valid Program/evaluation record has been admitted: '
            f'{len(submitted)} parsed solution actions, {refused} refused actions, '
            f'{len(invoked_trials)} solution trials invoked, {failed} failed experiments, '
            f'{invalid} completed experiments with invalid treatment, '
            f'{unverified} unverifiable Program records, {nonaccepted} nonaccepted solution-evaluation records.')
    elif not complete:
        program_status = 'history_incomplete'
        reason = 'No accepted Program is visible in this partial history. Earlier solution submissions cannot be ruled out.'
    elif unclassified:
        program_status = 'submission_unavailable'
        reason = (f'No parsed solution action is recorded, but {unclassified} proposal responses have no classifiable action. '
            'Their intended action is unknown; this does not establish that solutions were never requested.')
    elif not_dispatched:
        program_status = 'proposal_not_dispatched'
        reason = (f'{not_dispatched} proposal requests were refused before dispatch. '
            'They produced no model response; no solution action was submitted.')
    else:
        program_status = 'no_recorded_solution_actions'
        reason = ('No solution action or solution experiment has been recorded. '
            'Recorded method and tool experiments do not create a Program evaluation.')
    if not complete:
        reason += ' Counts cover loaded verified records only; history is incomplete.'
    programs = dict(submitted_solution_actions=len(submitted), accepted_programs=len(solutions),
        solution_experiments=len(trials), invoked_solution_experiments=len(invoked_trials),
        refused_solution_actions=refused, failed_solution_experiments=failed,
        invalid_solution_experiments=invalid, unclassified_proposals=unclassified,
        not_dispatched_proposals=not_dispatched,
        unverified_solution_records=unverified, nonaccepted_solution_evaluations=nonaccepted,
        status=program_status, reason=reason, history_complete=complete,
        scope='Accepted Programs are bound valid Program/evaluation records. A solution trial invocation is container dispatch, not proof that evaluation succeeded. Counts cover loaded verified artifacts.')

    evidence_kinds = ('knowledge_claim', 'experiment', 'proposal_receipt', 'adoption_basis', 'funding_grant')
    knowledge_ids = {ident for ident in artifacts if registered.get(ident) in evidence_kinds}
    claim_ids = set(records('knowledge_claim'))
    active_refs = set()
    for lab in labs.values():
        if lab.get('status') == 'archived':
            continue
        active_refs.update(seq(lab.get('evidence_refs')))
        for method in seq(lab.get('active_methods')) + seq(lab.get('active_adapters')):
            active_refs.update(seq(obj(statuses.get(method)).get('evidence_refs')))
    active_ids = active_refs & knowledge_ids
    latest_claims = {}
    for row in rows:
        data = obj(row.get('data'))
        if (row.get('kind') == 'claim_revision' and isinstance(data.get('key'), str)
                and isinstance(data.get('id'), str)):
            latest_claims[data['key']] = data['id']
    knowledge = dict(record_kind='claim_and_evidence', stored_records=len(knowledge_ids),
        active_referenced_records=len(active_ids), stored_claims=len(claim_ids),
        current_claims=len(set(latest_claims.values()) & claim_ids),
        active_referenced_claims=len(active_ids & claim_ids), active_referenced_ids=sorted(active_ids)[:200],
        omitted_active_referenced_ids=max(0, len(active_ids) - 200),
        record_counts={kind:sum(registered[ident] == kind for ident in knowledge_ids) for kind in evidence_kinds},
        prompt_delivery=dict(count=None, status='unavailable',
            reason='Saved proposal contexts are fetched only when opened. Receipt references and active evidence do not prove that a record reached the model.'),
        legacy_lessons=dict(count=None, status='not_implemented',
            reason='This methods runner stores claim revisions and experiment evidence; it does not emit legacy Lesson cards.'),
        history_complete=complete,
        scope='Stored records include claim revisions, experiments, proposal feedback, adoption bases and funding grants. Active means explicitly referenced by a current non-archived lab revision or an active method; it does not mean delivered to a prompt. Current claims require a latest claim_revision journal selection.')
    features = [dict(id=ident, label=label, enabled=False, status=status, reason=reason) for ident, label, status, reason in (
        ('legacy_evolution', 'Legacy evolution engine', 'not_used', 'The methods coordinator runs laboratory proposals and versioned tool experiments, not the legacy island evolution loop.'),
        ('bandits', 'Bandit controller', 'not_implemented', 'No learned bandit controller selects actions in the methods runner.'),
        ('rl', 'RL controller', 'not_implemented', 'No RL policy update or trained action policy is implemented in the methods runner.'),
        ('legacy_hcl', 'Legacy H / C / L cards', 'not_implemented', 'Precommitted experiment plans and claim revisions are different record types; legacy Hypothesis, Conclusion and Lesson cards are not emitted.'),
        ('islands', 'Evolution islands', 'not_used', 'Laboratories have explicit tool revisions and evidence; they are not legacy evolution islands.'),
        ('map_elites', 'MAP-Elites storage', 'not_used', 'Methods use an immutable content-addressed registry; no MAP-Elites grid is maintained.'),
        ('vq_niches', 'VQ / embedding niches', 'not_used', 'No VQ or embedding niche population selects methods in this runner.'),
    )]
    return dict(schema='sciel-method-observability/1', programs=programs,
        hypotheses=dict(record_kind='precommitted_experiment_plan', count=len(questions),
            with_questions=sum(bool(q['question']) for q in questions), items=questions[-200:],
            omitted_items=max(0, len(questions) - 200), history_complete=complete,
            scope='Saved experiment questions and precommitted criteria, including plans without results. These are not accepted causal hypotheses or legacy H cards.'),
        knowledge=knowledge, features=features,
        feature_scope='Methods host controller capabilities; this does not infer which algorithms a generated tool implements.')


def signature(path):
    try:
        value = path.lstat()
        return value.st_ino, value.st_size, value.st_mtime_ns
    except OSError:
        return None


def _read(root, path, limit):
    # Reject both leaf and ancestor symlinks, including links into the same run.
    path.relative_to(root)
    if any(p.is_symlink() for p in (path, *path.parents) if p == root or p.is_relative_to(root)):
        raise ValueError('linked artifact refused')
    if not path.resolve().is_relative_to(root):
        raise ValueError('artifact outside run')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError('oversized or nonregular artifact')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ValueError('artifact grew beyond read bound')
        return raw
    finally:
        os.close(fd)


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
