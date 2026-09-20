"""Bounded, read-only projection of research-practice registries.

This module deliberately does not import the method runtime: opening a dashboard
must never construct a writable registry, acquire its locks, or execute a tool.
Only committed hash-chain prefixes and content-addressed JSON are displayed.
"""
from __future__ import annotations

from collections import Counter, OrderedDict
from datetime import datetime, timezone
import difflib
import hashlib
import json
import math
import os
from pathlib import Path
import re
import socket
import stat
import time

from .compat.runtime import process_matches

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


class MethodsView:
    def __init__(self, journal):
        journal = Path(journal)
        self.root = journal.parent.parent.resolve()
        self.registry = self.root / journal.parent.name
        self.journal = self.registry / journal.name
        self._cache = OrderedDict()

    def signature(self):
        return tuple(signature(p) for p in (self.journal, self.root / 'resources.jsonl',
            self.root / 'acceptance.json', self.root / 'run-report.json', self.root / 'checkpoint.json', self.root / 'run-config.json'))

    def _json(self, path, limit=MAX_ARTIFACT):
        return decode(_read(self.root, path, limit))

    def rows(self, *, ledger=False):
        path = self.root / 'resources.jsonl' if ledger else self.journal
        warnings, rows = [], []
        try:
            raw = _read(self.root, path, MAX_JOURNAL)
        except (OSError, ValueError):
            return [], ['Resource ledger unavailable.' if ledger else 'Registry journal unavailable.']
        previous = '0' * 64
        for index, line in enumerate(raw.splitlines(keepends=True)):
            if index >= MAX_ROWS:
                warnings.append('Journal display limit reached; later records are not projected.')
                break
            if not line.endswith(b'\n'):
                warnings.append('Incomplete trailing record; waiting for its writer.')
                break
            try:
                row = decode(line)
                hash_key, prev_key = ('sha256', 'prev_sha256') if ledger else ('id', 'prev')
                expected_schema = 'sciel-resource-ledger/1' if ledger else 'sciel-method-event/1'
                if (not isinstance(row, dict) or row.get('schema') != expected_schema
                        or type(row.get('seq')) is not int or row.get('seq') != index + 1 or row.get(prev_key) != previous
                        or row.get(hash_key) != digest({k: v for k, v in row.items() if k != hash_key})
                        or not isinstance(row.get('data'), dict)
                        or not isinstance(row.get('op' if ledger else 'kind'), str)):
                    raise ValueError('unverified journal record')
                previous = row[hash_key]
                rows.append(row)
            except (ValueError, UnicodeError, RecursionError, TypeError):
                warnings.append(f'Journal integrity unavailable at record {index + 1}; showing verified prefix only.')
                break
        return rows, warnings

    def _object(self, directory, ident):
        if not isinstance(ident, str) or not HASH.fullmatch(ident):
            raise KeyError('Invalid artifact ID')
        key = (directory, ident)
        path = self.registry / directory / (ident + '.json')
        stamp = signature(path)
        cached = self._cache.get(key)
        if cached and cached[0] == stamp:
            self._cache.move_to_end(key)
            return cached[1]
        value = self._json(path)
        if not isinstance(value, dict) or digest(value) != ident:
            raise ValueError('Artifact integrity mismatch')
        self._cache[key] = (stamp, value)
        while len(self._cache) > 256 or sum(v[0][1] for v in self._cache.values() if v[0]) > 16 * 1024 * 1024:
            self._cache.popitem(last=False)
        return value

    def artifact(self, kind, ident, registered=None):
        if registered is None:
            rows, _ = self.rows()
            registered = registered_artifacts(rows)
        if registered.get(ident) != kind:
            raise KeyError('Artifact is not committed in this run')
        value = self._object('artifacts', ident)
        if value.get('schema') != 'sciel-method-artifact/1' or value.get('kind') != kind:
            raise ValueError('Artifact kind mismatch')
        return validate_shape(obj(value.get('body')))

    def budget(self):
        rows, warnings = self.rows(ledger=True)
        accounts, reservations, limits = {}, {}, {}
        for row in rows:
            data = row['data']
            try:
                validate_shape(data)
            except ValueError:
                warnings.append('Malformed resource metadata; showing its prior prefix.')
                break
            if row.get('op') == 'init':
                limits = obj(data.get('limits'))
            elif row.get('op') == 'account' and isinstance(data.get('account_id'), str):
                accounts[data['account_id']] = obj(data.get('limits'))
            elif row.get('op') == 'reserve' and isinstance(data.get('id'), str):
                reservations[data['id']] = dict(data, status='reserved', actual={})
            elif row.get('op') in ('settle', 'resolve') and data.get('id') in reservations:
                reservations[data['id']].update(data)
        def balance(selected, ceiling):
            spent, held = dict.fromkeys(RESOURCES, 0.), dict.fromkeys(RESOURCES, 0.)
            for r in selected:
                for key in RESOURCES:
                    actual = number(obj(r.get('actual')).get(key)) or 0
                    spent[key] += actual
                    if r.get('status') in ('reserved', 'unknown'):
                        held[key] += max(0, (number(obj(r.get('bounds')).get(key)) or 0) - actual)
            remaining = {}
            for key in RESOURCES:
                if key not in ceiling:
                    continue  # Missing metadata is unknown, never an unlimited grant.
                if ceiling[key] is None:
                    remaining[key] = None
                elif number(ceiling[key]) is not None:
                    remaining[key] = max(0, number(ceiling[key]) - spent[key] - held[key])
            return dict(limits=ceiling, spent=spent, reserved=held,
                remaining=remaining,
                unknown_reservations=[r['id'] for r in selected if r.get('status') == 'unknown'],
                pending_reservations=[r['id'] for r in selected if r.get('status') == 'reserved'])
        values = list(reservations.values())
        result = balance(values, limits)
        result['accounts'] = {a: balance([r for r in values if r.get('account_id') == a], cap)
            for a, cap in accounts.items()}
        result['by_category'] = {category: balance([r for r in values if r.get('category') == category], limits)['spent']
            for category in sorted({str(r.get('category')) for r in values})}
        result['measurement_scope'] = 'Charged operation resources. Summed wall time is not elapsed time; storage is cumulative charged bytes.'
        result['current_operations'] = [{k:r.get(k) for k in ('id', 'account_id', 'category', 'status')}
            for r in values if r.get('status') in ('reserved', 'unknown')]
        result['complete'] = not warnings
        return result, warnings

    def runtime(self, identity, registry_started_at=None):
        return clean(self._runtime(identity, registry_started_at))

    def terminal_report(self, rows, identity, registered):
        """Only a terminal report bound to the exact current journal checkpoint."""
        try:
            checkpoint = self._json(self.root / 'checkpoint.json')
            anchor = obj(checkpoint.get('journal'))
            if (not rows or anchor.get('count') != len(rows) or anchor.get('head') != rows[-1]['id']
                    or checkpoint.get('id') != digest({k:v for k,v in checkpoint.items() if k != 'id'})):
                return None
            for filename in ('run-report.json', 'acceptance.json'):
                try:
                    report = self._json(self.root / filename)
                except FileNotFoundError:
                    continue
                if report.get('checkpoint_id') != checkpoint['id']:
                    continue
                if filename == 'run-report.json':
                    if (report.get('schema') != 'sciel-method-run-report/1'
                            or report.get('coordinator_identity') != identity):
                        continue
                    status = {'completed':'completed', 'budget_exhausted':'stopped',
                        'accounting_stopped':'unknown', 'failed':'failed', 'stopped':'stopped'}.get(report.get('status'))
                    if status:
                        return dict(status=status, source=filename, reason=report.get('reason'), classification=report.get('classification'),
                            accounting_coverage=report.get('accounting_coverage'), accounting_note=report.get('accounting_note'),
                            quality=report.get('quality'))
                elif (report.get('schema') == 'sciel-method-technical-acceptance/1'
                        and report.get('status') == 'passed' and report.get('technical_only') is True
                        and obj(identity.get('generator')).get('kind') == 'scripted_fixture'
                        and registered.get(report.get('adoption_id')) == 'adoption'
                        and registered.get(report.get('release_id')) == 'method_evidence'
                        and all(registered.get(i) == 'experiment' for i in obj(report.get('experiments')).values())):
                    return dict(status='completed', source=filename, reason='Technical acceptance completed; no scientific benefit claim.',
                        technical_only=True, limitations=report.get('limitations'))
        except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
            pass
        return None

    def _runtime(self, identity, registry_started_at):
        result = dict(available=False, active=None, status='unknown', stage=None,
            verification='unavailable', heartbeat_age_seconds=None, elapsed_seconds=None,
            reason='No process-bound runtime heartbeat is available.')
        try:
            value = self._json(self.root / 'runtime.json', 65536)
            if not isinstance(value, dict) or value.get('schema') != 'sciel-method-runtime/1':
                return result
        except (OSError, ValueError, UnicodeError, RecursionError):
            return result
        result['available'] = True
        binding = value.get('registry_identity_sha256')
        if (not binding or binding != digest(identity) or registry_started_at is None
                or value.get('registry_started_at') != registry_started_at):
            result.update(verification='different_run', reason='Runtime telemetry is not bound to this registry identity.')
            return result
        result.update({k: value.get(k) for k in ('stage', 'heartbeat_at', 'started_at', 'finished_at',
            'pid', 'stale_after_seconds', 'overhead', 'runtime_id', 'reason', 'run_name')})
        def timestamp(v):
            parsed = datetime.fromisoformat(v.replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                raise ValueError('timezone required')
            return parsed.timestamp()
        try:
            started = timestamp(value['started_at'])
            heartbeat = timestamp(value['heartbeat_at'])
            end = timestamp(value['finished_at']) if value.get('finished_at') else heartbeat
            result['heartbeat_age_seconds'] = max(0, time.time() - heartbeat)
            result['elapsed_seconds'] = max(0, end - started)
        except (KeyError, ValueError, TypeError, AttributeError, OverflowError):
            result.update(verification='invalid_timestamp', reason='Runtime timestamp is unavailable.')
            return result
        if value.get('status') in ('completed', 'failed', 'stopped', 'interrupted', 'unknown'):
            result.update(status=value['status'], active=False, verification='terminal_recorded')
            return result
        if value.get('status') != 'running' or value.get('hostname') != socket.gethostname():
            result.update(verification='unverified_host')
            return result
        matches = process_matches(value)
        if matches is False:
            result.update(status='interrupted', active=False, verification='process_not_running',
                reason='Recorded controller process is no longer running.')
        elif matches is None:
            result.update(verification='process_unverified')
        elif (number(value.get('stale_after_seconds')) or 0) <= 0 or heartbeat > time.time() + 2:
            result.update(verification='invalid_timestamp')
        elif time.time() - heartbeat > float(value['stale_after_seconds']):
            result.update(status='stalled', active=False, verification='stale_heartbeat',
                reason='Controller exists but runtime heartbeat is stale.')
        else:
            result.update(status='running', active=True, verification='live_process', reason=None)
        return result

    def project(self, run_id):
        rows, warnings = self.rows()
        registered = registered_artifacts(rows)
        artifacts, methods, revisions, labs, statuses, events = {}, {}, {}, {}, {}, []
        identity, started_at, registry_started_at = {}, None, None
        artifact_meta, method_meta = {}, {}
        # Preselect from the newest records, so an old, large request history
        # cannot consume unbounded memory or hide the newest visible activity.
        allowed_objects, projection_bytes, omitted_objects = set(), 0, 0
        for row in reversed(rows):
            data, kind = row['data'], row.get('kind')
            directory = ('methods' if kind == 'method_registered' else 'revisions'
                if kind in ('lab_created', 'lab_revised') else 'artifacts'
                if kind == 'artifact_registered' and data.get('kind') not in
                    ('proposal_context', 'solution_source', 'budget_checkpoint') else None)
            ident = data.get('revision_id') if directory == 'revisions' else data.get('id')
            if directory is None or not isinstance(ident, str) or not HASH.fullmatch(ident):
                continue
            key = (directory, ident)
            if key in allowed_objects:
                continue
            stamp = signature(self.registry / directory / (ident + '.json'))
            size = stamp[1] if stamp else 0
            if (len(allowed_objects) >= MAX_PROJECTION_OBJECTS or size > MAX_ARTIFACT
                    or projection_bytes + size > MAX_PROJECTION_BYTES):
                omitted_objects += 1
                continue
            projection_bytes += size
            allowed_objects.add(key)
        if omitted_objects:
            warnings.append(f'Display scan bound reached: {omitted_objects} older/oversized objects omitted. Counts describe loaded records, not complete history.')

        def revision_unavailable(data, row):
            # New events identify the lab independently of their artifact. For
            # legacy events that omit it, any existing lab could be affected;
            # do not present last-known membership as verified current state.
            named = data.get('lab_id')
            affected = [named] if isinstance(named, str) else list(labs)
            for lab_id in affected:
                old = labs.get(lab_id, {})
                last = old.get('last_verified_revision')
                if old.get('revision_available', True) and old.get('revision_id'):
                    last = dict(id=old['revision_id'], number=old.get('revision_number'),
                        active_methods=old.get('active_methods', []),
                        active_adapters=old.get('active_adapters', []))
                labs[lab_id] = dict(old, id=lab_id, status=old.get('status', 'trial'),
                    mode=old.get('mode', data.get('mode')), agenda=old.get('agenda', data.get('agenda')),
                    budget_account=old.get('budget_account'), revision_available=False,
                    revision_id=data.get('revision_id') if named else None,
                    announced_revision_id=data.get('revision_id'),
                    revision_number=(old.get('revision_number', 0) + 1
                        if named and type(old.get('revision_number', 0)) is int else None),
                    revision=None, last_verified_revision=last, revision_at=row.get('at'),
                    active_methods=[], active_adapters=[], evidence_refs=[], capabilities={},
                    current_stage='revision_unavailable', last_activity_at=row.get('at'))
        for row in rows:
            kind, data = row.get('kind'), row['data']
            ident = data.get('id')
            try:
                validate_shape(data)
                if kind == 'coordinator_identity':
                    identity, started_at = obj(data.get('identity')), row.get('at')
                    registry_started_at = data.get('started_at')
                elif kind == 'method_registered':
                    if ('methods', ident) not in allowed_objects:
                        continue
                    methods[ident] = validate_shape(self._object('methods', ident))
                    method_meta[ident] = row
                    statuses[ident] = dict(status='draft', evidence_refs=[])
                elif kind == 'method_status' and ident in methods:
                    statuses[ident] = dict(status=data.get('status'), evidence_refs=list(dict.fromkeys(
                        statuses[ident]['evidence_refs'] + seq(data.get('evidence_refs')))))
                elif kind in ('lab_created', 'lab_revised'):
                    revision_id = data.get('revision_id')
                    if ('revisions', revision_id) not in allowed_objects:
                        revision_unavailable(data, row)
                        continue
                    revision = validate_shape(self._object('revisions', revision_id))
                    revisions[revision_id] = revision
                    lab_id = revision.get('lab_id')
                    if not isinstance(lab_id, str):
                        raise ValueError('revision has no lab identity')
                    if data.get('lab_id', lab_id) != lab_id:
                        raise ValueError('announced lab differs from revision')
                    old = labs.get(lab_id, {})
                    labs[lab_id] = dict(old, id=lab_id, mode=data.get('mode', old.get('mode')),
                        agenda=data.get('agenda', old.get('agenda')), status=old.get('status', 'trial'),
                        created_at=row.get('at') if kind == 'lab_created' else old.get('created_at'),
                        revision_at=row.get('at'),
                        revision_id=revision_id,
                        # A named announcement still advances the version even
                        # when its artifact was unavailable. An unidentified
                        # legacy gap leaves the ordinal unknown, not reset to 1.
                        revision_number=(old.get('revision_number', 0) + 1
                            if type(old.get('revision_number', 0)) is int else None),
                        revision_available=True, announced_revision_id=revision_id,
                        last_verified_revision=None,
                        active_methods=seq(revision.get('active_methods')), active_adapters=seq(revision.get('active_adapters')),
                        budget_account=revision.get('budget_account'), capabilities=obj(revision.get('capabilities')),
                        evidence_refs=seq(revision.get('evidence_refs')), last_activity_at=row.get('at'),
                        current_stage=revision.get('reason'), revision=revision)
                elif kind == 'lab_lifecycle' and data.get('lab_id') in labs:
                    labs[data['lab_id']].update(status=data.get('status'), current_stage=data.get('reason'))
                elif kind == 'artifact_registered':
                    artifact_meta[ident] = row
                    # Large saved prompts are fetched only when opened.
                    if data.get('kind') not in ('proposal_context', 'solution_source', 'budget_checkpoint'):
                        if ('artifacts', ident) not in allowed_objects:
                            continue
                        artifacts[ident] = self.artifact(data.get('kind'), ident, registered)
            except (KeyError, ValueError, OSError, UnicodeError, RecursionError, TypeError):
                if kind in ('lab_created', 'lab_revised'):
                    revision_unavailable(data, row)
                warnings.append(f'Unavailable {kind} artifact at registry record {row.get("seq")}.')
            if kind not in ('artifact_registered', 'funding_state'):
                events.append(dict(id=row.get('id'), seq=row.get('seq'), at=row.get('at'), kind=kind, data=data))
        by_kind = lambda k: [(i, b) for i, b in artifacts.items() if registered.get(i) == k]
        calls = dict(by_kind('call_receipt'))
        invoked = [(i, b) for i, b in calls.items() if obj(b.get('result')).get('dispatch_status') == 'invoked']
        invocation_counts = Counter(obj(b.get('result')).get('method_id') for _, b in invoked)
        experiments = []
        for ident, body in by_kind('experiment'):
            plan = artifacts.get(body.get('plan_id'), {})
            metric = obj(plan.get('criterion')).get('metric')
            def score(arm):
                values = [number(obj(obj(r.get('measurement')).get('metrics')).get(metric))
                    for r in seq(obj(body.get('results')).get(arm)) if isinstance(r, dict)]
                return sum(values) / len(values) if values and all(v is not None for v in values) else None
            def native_score(arm):
                values = [number(obj(obj(r.get('measurement')).get('observables')).get('sum_radii',
                    obj(obj(r.get('measurement')).get('metrics')).get('sum_radii')))
                    for r in seq(obj(body.get('results')).get(arm)) if isinstance(r, dict)]
                return sum(values) / len(values) if values and all(v is not None for v in values) else None
            control_score, treatment_score = score('control'), score('treatment')
            native_control, native_treatment = native_score('control'), native_score('treatment')
            task_schema = obj(plan.get('task')).get('schema') or obj(identity.get('task')).get('schema')
            native_metric = ('sum_radii' if metric == 'combined_score'
                and task_schema == 'sciel-method-circle26-task/1'
                and (native_control is not None or native_treatment is not None) else None)
            experiments.append(dict(body, id=ident, at=artifact_meta[ident].get('at'),
                created_at=artifact_meta[ident].get('at'), registration_seq=artifact_meta[ident].get('seq'),
                proposal_id=plan.get('proposal_id') if registered.get(plan.get('proposal_id')) == 'proposal_receipt' else None,
                lab_id=plan.get('lab_id'), purpose=plan.get('purpose'), question=plan.get('question'),
                scope=plan.get('scope'), treatment=seq(plan.get('treatment')), control=seq(plan.get('control')),
                criterion=plan.get('criterion'), metric=metric, control_score=control_score, treatment_score=treatment_score,
                native_metric=native_metric,
                native_control_score=native_control, native_treatment_score=native_treatment,
                display_metric=native_metric or metric,
                display_control_score=native_control if native_metric else control_score,
                display_treatment_score=native_treatment if native_metric else treatment_score,
                effect=body.get('mean_effect'), passed=body.get('rule_passed'), source_plan=plan.get('source_plan')))
        proposals = []
        steps = [dict(r['data'], at=r.get('at')) for r in rows if r.get('kind') == 'episode_step'
            and isinstance(r['data'].get('lab_id'), str) and isinstance(r['data'].get('proposal_id'), str)]
        for ident, body in by_kind('proposal_receipt'):
            if not body.get('context_id'):
                continue
            call = calls.get(body.get('call_receipt_id'), {})
            step = next((s for s in steps if s.get('proposal_id') == ident), {})
            refusal = artifacts.get(step.get('refusal_id'), {})
            proposals.append(dict(id=ident, lab_id=body.get('lab_id'), at=artifact_meta[ident].get('at'),
                index=step.get('index'), status='refused' if refusal else ('invalid' if body.get('error') else step.get('status') or call.get('status')),
                kind=obj(body.get('draft')).get('kind'), error=body.get('error') or refusal.get('error'),
                diagnostic=refusal.get('diagnostic') or body.get('diagnostic'), novelty=refusal.get('novelty'),
                method_id=step.get('method_id'), experiment_id=step.get('experiment_id'), cost=obj(call.get('actual')).get('dollars'),
                actual=call.get('actual'), call_receipt_id=body.get('call_receipt_id'),
                dispatch_status=(obj(call.get('result')).get('dispatch_status') or
                    obj(body.get('diagnostic')).get('dispatch_status') or
                    ('not_dispatched' if body.get('error') == 'proposal_not_dispatched' else None)),
                source_read=body.get('source_read'), evidence_refs=body.get('evidence_refs')))
        transfers = []
        for ident, body in by_kind('adoption'):
            at = artifact_meta[ident].get('at')
            next_use = next((e for e in experiments if e.get('lab_id') == body.get('lab_id')
                and e.get('at', '') > at and body.get('method_id') in seq(e.get('invoked_methods'))), {})
            transfers.append(dict(body, id=ident, kind='adoption', at=at, revision_id=body.get('new_revision'),
                next_use_experiment_id=next_use.get('id'), next_use_at=next_use.get('at')))
        for ident, body in by_kind('solution_transfer'):
            transfers.append(dict(body, id=ident, kind='solution_transfer', at=artifact_meta[ident].get('at')))
        tools = []
        for ident, body in methods.items():
            manifest = obj(body.get('manifest'))
            is_solution_bundle = obj(manifest.get('protocol')).get('permanent_toolbox_method') is False
            evidence = [artifacts.get(ref, {}) for ref in statuses[ident]['evidence_refs']]
            tools.append(dict(id=ident, **{k: manifest.get(k) for k in
                ('name', 'kind', 'author_lab', 'parents', 'dependencies', 'scope', 'protocol', 'entrypoint', 'resources')},
                created_at=method_meta[ident].get('at'), registration_seq=method_meta[ident].get('seq'),
                **statuses[ident], source_sha256=digest(obj(body.get('files'))),
                record_kind='solution_execution_bundle' if is_solution_bundle else 'reusable_method',
                provenance='solution_execution_adapter' if is_solution_bundle else
                    'common_toolbox' if ident in seq(identity.get('common_methods')) else 'lab_created',
                invocations=invocation_counts[ident], evidence=evidence,
                adopted_by=[t.get('lab_id') for t in transfers if t.get('kind') == 'adoption' and t.get('method_id') == ident],
                active_in=[l['id'] for l in labs.values() if ident in l['active_methods'] or ident in l['active_adapters']],
                replayed=any(e.get('level') == 'replayed' for e in evidence)))
        execution_bundles = [t for t in tools if t['record_kind'] == 'solution_execution_bundle']
        tools = [t for t in tools if t['record_kind'] == 'reusable_method']
        solutions = []
        experiments_by_id = {e['id']:e for e in experiments}
        for ident, body in by_kind('solution'):
            program, evaluation = obj(body.get('program')), obj(body.get('evaluation'))
            call = calls.get(body.get('call_receipt_id'), {})
            execution = obj(call.get('result'))
            bundle = methods.get(execution.get('method_id'), {})
            experiment = experiments_by_id.get(body.get('experiment_id'), {})
            code = program.get('code')
            # Quality comes from an admitted Program and its actual bound
            # evaluation, never from arbitrary method-state trial measurements.
            if (not isinstance(program.get('id'), str) or not isinstance(code, str)
                    or number(program.get('score')) is None or program.get('score') != evaluation.get('score')
                    or evaluation.get('ok') is not True or experiment.get('valid_treatment') is not True
                    or execution.get('dispatch_status') != 'invoked' or execution.get('status') != 'ok'
                    or execution.get('plan_id') != experiment.get('plan_id')
                    or body.get('call_receipt_id') not in seq(experiment.get('invocation_refs'))
                    or execution.get('source_sha256') != digest(obj(bundle.get('files')))
                    or obj(bundle.get('files')).get('candidate.py') != code):
                warnings.append('A solution record is missing its bound valid Program/evaluation; omitted from task quality.')
                continue
            cases = obj(evaluation.get('cases'))
            native = number(cases.get('sum_radii'))
            # Link only explicit saved bindings, never program-name conventions
            # or whichever proposal happened nearest in wall-clock time.
            proposal_ids = {s['proposal_id'] for s in steps if s.get('solution_id') == ident
                and s.get('lab_id') == body.get('lab_id')
                and registered.get(s['proposal_id']) == 'proposal_receipt'}
            if experiment.get('lab_id') == body.get('lab_id') and experiment.get('proposal_id'):
                proposal_ids.add(experiment['proposal_id'])
            solutions.append(dict(id=ident, record_kind='solution', program_id=program['id'],
                lab_id=body.get('lab_id'), at=artifact_meta[ident].get('at'),
                created_at=artifact_meta[ident].get('at'), registration_seq=artifact_meta[ident].get('seq'),
                proposal_id=next(iter(proposal_ids)) if len(proposal_ids) == 1 else None,
                experiment_id=body.get('experiment_id'), call_receipt_id=body.get('call_receipt_id'),
                method_id=execution.get('method_id'), score=program['score'], cases=cases,
                native_metric='sum_radii' if native is not None else None, native_score=native,
                valid=True, source_sha256=hashlib.sha256(code.encode()).hexdigest(),
                confirmed=obj(body.get('cascade')).get('confirmed'), evaluation_protocol=body.get('evaluation_protocol')))
        direction = obj(identity.get('task')).get('direction', 'max')
        best_solution = (min if direction == 'min' else max)(solutions,
            key=lambda s:s['score'], default=None)
        quality = dict(best_solution_id=best_solution.get('id') if best_solution else None,
            best_score=best_solution.get('score') if best_solution else None,
            best_native_metric=best_solution.get('native_metric') if best_solution else None,
            best_native_score=best_solution.get('native_score') if best_solution else None,
            metric=obj(identity.get('solution_task')).get('metric') or obj(identity.get('task')).get('metric'),
            direction=direction, valid_solutions=len(solutions),
            scope='Observed valid Program evaluations only. Method-state trials are separate; no independent-repeat or held-out benefit claim.')
        budget, budget_warnings = self.budget()
        warnings.extend(budget_warnings)
        claims = [dict(b, id=i, at=artifact_meta[i].get('at')) for i, b in by_kind('knowledge_claim')]
        for lab in labs.values():
            local_steps = [s for s in steps if s.get('lab_id') == lab['id']]
            lab.update(steps=len(local_steps), experiments=sum(e.get('lab_id') == lab['id'] for e in experiments),
                tools=sum(t.get('author_lab') == lab['id'] for t in tools),
                solutions=sum(s.get('lab_id') == lab['id'] for s in solutions),
                claims=sum(any(m in lab['active_methods'] for m in seq(c.get('methods'))) for c in claims),
                budget=budget['accounts'].get(lab['budget_account'], {}))
            if local_steps:
                lab.update(last_activity_at=local_steps[-1].get('at'), current_stage=local_steps[-1].get('status'))
            local_experiments = [e for e in experiments if e.get('lab_id') == lab['id']]
            if local_experiments:
                latest = local_experiments[-1]
                lab['last_outcome'] = dict(experiment_id=latest['id'], passed=latest.get('passed'),
                    effect=latest.get('effect'), at=latest.get('at'), purpose=latest.get('purpose'))
                if latest.get('at', '') >= (lab.get('last_activity_at') or '') or not local_steps:
                    lab.update(last_activity_at=latest.get('at'), current_stage=(
                        'Replay completed' if latest.get('purpose') == 'replay' else 'Evaluation completed'))
            pending = [r for r in budget['current_operations'] if r.get('account_id') == lab['budget_account']]
            if pending:
                lab['current_stage'] = pending[-1]['category'] + (' · outcome unknown' if pending[-1]['status'] == 'unknown' else '')
            lab['current_operations'] = pending
            if lab.get('revision_available') is False:
                lab['current_stage'] = 'revision_unavailable'
        runtime = self.runtime(identity, registry_started_at)
        report = self.terminal_report(rows, identity, registered)
        modified = self.journal.stat().st_mtime
        status = runtime['status'] if runtime['available'] else 'historical'
        if report and not runtime['available']:
            status = report['status']
        summary = dict(labs=len(labs), methods=len(tools), released=sum(t['status'] == 'released' for t in tools),
            solutions=len(solutions), execution_bundles=len(execution_bundles),
            experiments=len(experiments), proposals=len(proposals), invocations=len(invoked), claims=len(claims),
            adoptions=sum(t['kind'] == 'adoption' for t in transfers),
            unknown=len(budget['unknown_reservations']), failed_calls=sum(c.get('status') == 'failed' for c in calls.values()),
            history_complete=not omitted_objects and not warnings)
        observation = observability(artifacts=artifacts, registered=registered, metadata=artifact_meta,
            labs=labs, statuses=statuses, rows=rows, experiments=experiments, proposals=proposals,
            solutions=solutions, complete=summary['history_complete'])
        classification = report.get('classification') if report else None
        if classification is None:
            try:
                classification = obj(self._json(self.root / 'run-config.json')).get('claim')
            except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
                pass
        if classification not in ('local_episode', 'bounded_arm', 'continuous_run'):
            classification = None
        run_policy = dict(classification=classification, **{key:identity[key] for key in
            ('max_steps', 'calendar_seconds', 'storage_bytes', 'capacity_wait_seconds', 'resources') if key in identity})
        run_name = self.root.name
        if run_name == 'run' and self.root.parent.parent.name == 'units':
            run_name = self.root.parent.parent.parent.name + ' · ' + self.root.parent.name
        run = dict(id=run_id, kind='methods', name=run_name, label=run_name, status=status, classification=classification,
            status_reason=report.get('reason') if report and not runtime['available'] else runtime.get('reason'),
            terminal_source=report.get('source') if report else None, started_at=started_at,
            last_modified=datetime.fromtimestamp(modified, timezone.utc).isoformat(),
            task=obj(identity.get('task')).get('schema', 'Research practices'), iteration=len(steps),
            cost_total=budget['spent']['dollars'], best_score=quality['best_score'])
        visible_versions = tools[-500:] + execution_bundles[-200:]
        edge_limit = 2000
        parent_edges, dependency_edges = [], []
        edge_counts = dict(parents=0, dependencies=0)
        for version in visible_versions:
            for key, edges in (('parents', parent_edges), ('dependencies', dependency_edges)):
                refs = seq(version.get(key))
                edge_counts[key] += len(refs)
                edges.extend(dict(source=ref, target=version['id']) for ref in refs[:max(0, edge_limit-len(edges))])
        storage = dict(kind='content_addressed_registry', label='Immutable method registry',
            history_scope='One append-only run journal across all labs; inactive and superseded versions remain in history.',
            selection='Lab revisions explicitly select active method and adapter versions.',
            coordinates=None,
            active_versions=[dict(lab_id=lab['id'], revision_id=lab['revision_id'],
                membership_known=lab.get('revision_available', True),
                last_verified_revision=lab.get('last_verified_revision'),
                method_ids=lab['active_methods'][:500], adapter_ids=lab['active_adapters'][:500],
                omitted_methods=max(0, len(lab['active_methods'])-500),
                omitted_adapters=max(0, len(lab['active_adapters'])-500)) for lab in labs.values()],
            parent_edges=parent_edges, dependency_edges=dependency_edges,
            omitted_parent_edges=edge_counts['parents']-len(parent_edges),
            omitted_dependency_edges=edge_counts['dependencies']-len(dependency_edges),
            edge_scope='Edges of displayed versions; source versions may be outside the displayed window. Dependencies declare source inclusion, not invocation.',
            history_complete=summary['history_complete'],
            display_scope='Active lists and counts reflect the loaded journal projection; display bounds do not remove registry history.')
        data = dict(schema='sciel-method-dashboard/1', identity=identity, registry_started_at=registry_started_at, summary=summary, report=report, run_policy=run_policy,
            storage=storage, observability=observation,
            labs=list(labs.values()), tools=tools[-500:], experiments=experiments[-200:], claims=claims[-200:],
            execution_bundles=execution_bundles[-200:], solutions=solutions[-200:], quality=quality,
            proposals=proposals[-200:], transfers=transfers[-200:], events=events[-200:], budget=budget,
            steps=steps[-200:], receipts=[dict(id=i, category=b.get('category'), status=b.get('status'),
                actual=b.get('actual'), method_id=obj(b.get('result')).get('method_id'),
                plan_id=obj(b.get('result')).get('plan_id'), dispatch_status=obj(b.get('result')).get('dispatch_status'),
                dependency_use_attested=obj(b.get('result')).get('dependency_use_attested')) for i,b in list(calls.items())[-200:]],
            display_limits=dict(tools=500, execution_bundles=200, solutions=200, experiments=200, claims=200, proposals=200, transfers=200, events=200),
            projection=dict(loaded_objects=len(allowed_objects),loaded_bytes=projection_bytes,omitted_objects=omitted_objects,
                max_bytes=MAX_PROJECTION_BYTES,max_objects=MAX_PROJECTION_OBJECTS,newest_first=True,history_complete=not omitted_objects and not warnings),
            interpretation='Read-only saved records. Source inclusion and dependencies are not evidence of invocation; release is not evidence of general benefit.')
        return clean(dict(schema='sciel-dashboard/1', kind='methods', run=run, runtime=runtime,
            timing=dict(elapsed_seconds=runtime.get('elapsed_seconds'), session=dict(elapsed_seconds=runtime.get('elapsed_seconds'))), methods=data, warnings=warnings[:50]))

    def method_detail(self, ident):
        rows, warnings = self.rows()
        registered = {r['data']['id'] for r in rows if r.get('kind') == 'method_registered' and isinstance(r['data'].get('id'), str)}
        if ident not in registered:
            raise KeyError('Unknown method')
        body = self._object('methods', ident)
        manifest = obj(body.get('manifest'))
        parents = []
        for parent in seq(manifest.get('parents'))[:16]:
            if parent not in registered:
                continue
            old = self._object('methods', parent)
            diffs = []
            for name in sorted(set(obj(old.get('files'))) | set(obj(body.get('files')))):
                before, after = obj(old.get('files')).get(name, ''), obj(body.get('files')).get(name, '')
                if isinstance(before, str) and isinstance(after, str):
                    diffs.append(''.join(difflib.unified_diff(before[:100_000].splitlines(True), after[:100_000].splitlines(True),
                        fromfile=parent[:12] + '/' + name, tofile=ident[:12] + '/' + name)))
            parents.append(dict(id=parent, name=obj(old.get('manifest')).get('name'), diff=''.join(diffs)[:500_000]))
        return clean(dict(id=ident, manifest=manifest, files=body.get('files'), parents=parents,
            diff=parents[0]['diff'] if parents else None, source_sha256=digest(obj(body.get('files'))), warnings=warnings))

    def proposal_detail(self, ident):
        rows, warnings = self.rows()
        registered = registered_artifacts(rows)
        body = self.artifact('proposal_receipt', ident, registered)
        context = self.artifact('proposal_context', body.get('context_id'), registered)
        call = self.artifact('call_receipt', body.get('call_receipt_id'), registered)
        # A dispatch intent is saved before the request. Never reconstruct a
        # missing historical prompt from today's procedure implementation.
        request = None
        if isinstance(call.get('key'), str) and isinstance(call.get('account'), str):
            directory = digest(dict(key=call['key'], account=call['account']))
            try:
                intent = self._json(self.registry / 'dispatch' / directory / 'intent.json')
                if (intent.get('sha256') == digest({k:v for k,v in intent.items() if k != 'sha256'})
                        and intent.get('reservation_id') == call.get('reservation_id')
                        and intent.get('request_sha256') == call.get('request_sha256')):
                    request = intent.get('request')
            except (ValueError, OSError, UnicodeError, RecursionError):
                warnings.append('Saved generation request is unavailable.')
        return clean(dict(id=ident, receipt=body, context=context, request=request,
            response=obj(call.get('result')).get('text'), call_receipt=call, warnings=warnings,
            note='Exact saved request/response only; no historical text reconstructed.'))
