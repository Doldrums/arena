"""Read-only, bounded results projections. Never import participant code.

Scores share a comparison cohort only when task, evaluator, source revision,
metric, direction and execution environment agree. Native price estimates are
not bills. Failed runs keep their usable evaluation evidence.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import time

MAX_RUNS = 500
MAX_BYTES = 24 * 1024 * 1024
MAX_FILES = 512
HASH = re.compile(r"[a-f0-9]{64}")
IDENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/ -]{0,127}")


def number(value):
    try:
        return value if type(value) in (int, float) and math.isfinite(value) else None
    except OverflowError:
        return None


def count(value):
    return value if type(value) is int and 0 <= value <= 10**12 else None


def text(value):
    from .control import SECRET_VALUE
    return value if type(value) is str and IDENT.fullmatch(value) and not SECRET_VALUE.search(value) else None


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


class Evidence:
    def __init__(self, root):
        self.root = Path(root)
        self.bytes = self.files = 0
        self.issues = set()

    def raw(self, relative, limit=1024 * 1024):
        from .control import _read_regular
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts or self.files >= MAX_FILES:
            raise ValueError('Evidence boundary')
        data = _read_regular(self.root / path, maximum=min(limit, MAX_BYTES - self.bytes))
        self.bytes += len(data)
        self.files += 1
        return data

    def read(self, relative, limit=1024 * 1024):
        from .control import _decode
        raw = self.raw(relative, limit)
        try:
            value = _decode(raw)
        except RecursionError as exc:
            raise ValueError('Evidence nesting limit') from exc
        if type(value) is not dict:
            raise ValueError('Expected an evidence object')
        return value, hashlib.sha256(raw).hexdigest()

    def children(self, relative, pattern, maximum):
        """Only enumerate real directories; leaf reads also use no-follow FDs."""
        directory = self.root / relative
        if directory.is_symlink() or any(p.is_symlink() for p in directory.parents):
            raise ValueError('Linked evidence directory')
        if not directory.exists():
            return []
        names = []
        for index, path in enumerate(directory.iterdir()):
            if index >= maximum * 4:
                raise ValueError('Evidence directory entry limit')
            if pattern.fullmatch(path.name):
                if len(names) >= maximum:
                    raise ValueError('Evidence listing limit')
                if path.is_symlink() or not path.is_dir():
                    raise ValueError('Invalid evidence directory')
                names.append(path.relative_to(self.root))
        return sorted(names)


def empty_canonical():
    return dict(evaluations=0, valid=0, invalid=0, unknown=0, unique_valid_candidates=0,
                best_score=None, seed_score=None, score_gain=None, metric=None,
                direction=None, task_id=None, task_name=None, cohort=None,
                receipt_hashes=[], valid_candidate_hashes=[], status='missing')


def evaluator_source_identity(source):
    """Retain old Git receipts and bind bundled receipts to complete file hashes."""
    if source.get('kind') == 'bundled':
        required = {'kind', 'id', 'manifest_sha256', 'file_count'}
        if (not required <= source.keys() or source.keys() - required - {'external_files_sha256'}
                or not text(source.get('id')) or not HASH.fullmatch(source.get('manifest_sha256', ''))
                or type(source.get('file_count')) is not int or source['file_count'] < 1):
            raise ValueError('Missing bundled evaluator source identity')
        identity = {'source_manifest_sha256': source['manifest_sha256'], 'source_id': source['id']}
        if 'external_files_sha256' in source:
            if not HASH.fullmatch(source['external_files_sha256']):
                raise ValueError('Invalid native source asset identity')
            identity['source_assets_sha256'] = source['external_files_sha256']
        return identity
    if not re.fullmatch(r'[a-f0-9]{40}', source.get('commit', '')):
        raise ValueError('Missing pinned evaluator source')
    return {'source_commit': source['commit']}


def canonical(evidence, run_id):
    result, receipts = empty_canonical(), []
    folders = evidence.children('canonical-evaluations', re.compile(r'[a-f0-9]{32}'), 128)
    for folder in folders:
        try:
            row, receipt_hash = evidence.read(folder / 'receipt.json', 65536)
            if any(type(row.get(key)) is not dict for key in ('control', 'task_source', 'execution')):
                raise ValueError('Malformed receipt metadata')
            if (row.get('schema') != 'arena.evaluation/1'
                    or row.get('control', {}).get('run_id') != run_id
                    or row.get('direction') not in ('maximize', 'minimize')
                    or not text(row.get('task_id')) or not text(row.get('metric'))):
                raise ValueError('Invalid receipt binding')
            for key in ('candidate_sha256', 'problem_sha256', 'evaluator_sha256'):
                if not HASH.fullmatch(row.get(key, '')):
                    raise ValueError('Invalid evidence digest')
            source = row.get('task_source', {})
            source_identity = evaluator_source_identity(source)
            candidate = evidence.raw(folder / 'input/program.py')
            if hashlib.sha256(candidate).hexdigest() != row['candidate_sha256']:
                raise ValueError('Candidate evidence changed')
            if row.get('native_result_sha256'):
                native, native_hash = evidence.read(folder / 'native-output/native.json')
                if (native_hash != row['native_result_sha256']
                        or native.get('task_id') != row['task_id']
                        or native.get('candidate_sha256') != row['candidate_sha256']
                        or native.get('evaluator_sha256') != row['evaluator_sha256']):
                    raise ValueError('Native evidence changed')
            else:
                native = {}
            # Validity is explicit. Completion without finite, agreeing native
            # evidence cannot turn into a valid solution or a zero score.
            valid = (row.get('status') == 'completed' and row.get('validity') is True
                     and native.get('status') == 'completed' and native.get('valid') is True
                     and number(row.get('raw_score')) is not None
                     and number(native.get('score')) == row['raw_score'])
            invalid = row.get('validity') is False
            execution = row.get('execution', {})
            environment = execution.get('image') if execution.get('kind') == 'docker' else None
            cohort_fields = {k: row.get(k) for k in ('task_id', 'problem_sha256', 'evaluator_sha256', 'metric', 'direction', 'protocol')}
            cohort_fields.update(source_identity, environment=environment)
            # Unpinned local evaluation is inspectable, but not a comparison cohort.
            comparable = isinstance(environment, str) and bool(re.search(r'sha256:[a-f0-9]{64}$', environment))
            receipts.append(dict(row=row, hash=receipt_hash, valid=valid, invalid=invalid,
                                 identity=digest(cohort_fields),
                                 cohort=digest(cohort_fields) if comparable else None))
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            evidence.issues.add('Some canonical evidence is incomplete or failed integrity checks.')
    if not receipts:
        if folders:
            result['status'] = 'partial'
        return result
    receipts.sort(key=lambda item: (number(item['row'].get('started_at')) or 0, item['hash']))
    result.update(evaluations=len(receipts), valid=sum(item['valid'] for item in receipts),
                  invalid=sum(item['invalid'] for item in receipts),
                  unique_valid_candidates=len({item['row']['candidate_sha256'] for item in receipts if item['valid']}),
                  valid_candidate_hashes=sorted({item['row']['candidate_sha256'] for item in receipts if item['valid']}),
                  receipt_hashes=[item['hash'] for item in receipts],
                  status='recorded' if len(receipts) == len(folders) else 'partial')
    result['unknown'] = result['evaluations'] - result['valid'] - result['invalid']
    identities = {item['identity'] for item in receipts}
    if len(identities) != 1:
        evidence.issues.add('Multiple evaluator cohorts: scores are not aggregated.')
        result['status'] = 'partial'
        return result
    first = receipts[0]
    row = first['row']
    result.update(task_id=row['task_id'], task_name=row['task_id'].replace('-', ' ').title(),
                  metric=row['metric'], direction=row['direction'], cohort=first['cohort'])
    scores = [item['row']['raw_score'] for item in receipts if item['valid']]
    if scores:
        result['best_score'] = (max if row['direction'] == 'maximize' else min)(scores)
    # Initial receipt is a reference observation, never the first *successful*
    # one after discarding earlier failures.
    result['seed_score'] = row['raw_score'] if (first['valid'] and len(receipts) == len(folders)
                                               and all(number(item['row'].get('started_at')) is not None for item in receipts)) else None
    if result['best_score'] is not None and result['seed_score'] is not None:
        result['score_gain'] = ((result['best_score'] - result['seed_score'])
                                * (1 if row['direction'] == 'maximize' else -1))
    return result


def sciel_usage(evidence, model):
    usage = dict(input_tokens=None, output_tokens=None, total_tokens=None, requests=None,
                 complete=False, usd=None, scope='Recorded durable provider receipts; not a billing record.')
    successful, dispatched, missing = [], 0, False
    # SCiEL 0d67f813: engine/parallel_calls.py CallLedger.prepare binds the
    # directory to key, and the intent/dispatch/receipt to {kind, request}.
    # JSON_CONTROL_KINDS and tool_execution carry local operation receipts,
    # not provider usage. Do not count them as LLM requests.
    non_llm = {'evaluation', 'tool_execution', 'tool_job_submit', 'tool_job_poll', 'tool_job_cancel'}
    errors = (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError)
    try:
        # Match parallel_store._wave_id, which accepts both numbered and named
        # waves. An unfamiliar wave/call directory cannot silently disappear
        # while the remaining projection declares complete coverage.
        waves = evidence.children('native/.parallel', re.compile(r'wave-[A-Za-z0-9][A-Za-z0-9_-]{0,95}'), 100)
    except errors:
        waves, missing = [], True
    try:
        if set(evidence.children('native/.parallel', re.compile(r'wave-.*'), 100)) != set(waves):
            missing = True
    except errors:
        missing = True
    for wave in waves:
        try:
            calls = evidence.children(wave / 'calls', HASH, 100)
        except errors:
            missing = True
            continue
        try:
            if set(evidence.children(wave / 'calls', re.compile(r'.+'), 100)) != set(calls):
                missing = True
        except errors:
            missing = True
        for call in calls:
            try:
                intent, _ = evidence.read(call / 'intent.json')
                kind, key = intent.get('kind'), intent.get('key')
                if (intent.get('schema') != 'sciel-parallel-call/1'
                        or not isinstance(key, str)
                        or hashlib.sha256(key.encode()).hexdigest() != call.name
                        or not isinstance(kind, str) or kind not in {'llm', *non_llm}
                        or 'request' not in intent):
                    raise ValueError('Provider intent identity mismatch')
                request_hash = digest({'kind': kind, 'request': intent['request']})
                if intent.get('request_sha256') != request_hash:
                    raise ValueError('Provider intent request digest mismatch')
                if kind in non_llm:
                    continue
                try:
                    dispatch, _ = evidence.read(call / 'dispatched.json', 65536)
                except FileNotFoundError:
                    # A prepared intent alone is genuinely undispatched. A
                    # terminal receipt without its marker is damaged evidence,
                    # not an absent/free request that can be silently omitted.
                    try:
                        evidence.raw(call / 'receipt.json')
                    except FileNotFoundError:
                        continue
                    missing = True
                    continue
                dispatched += 1
                if dispatch.get('request_sha256') != request_hash:
                    raise ValueError('Provider dispatch request digest mismatch')
                receipt, _ = evidence.read(call / 'receipt.json')
                payload = receipt.get('payload')
                if (not isinstance(payload, dict)
                        or receipt.get('sha256') != digest(payload)
                        or payload.get('request_sha256') != request_hash):
                    raise ValueError('Provider receipt digest mismatch')
                value = payload.get('value')
                if (payload.get('status') != 'returned' or not isinstance(value, dict)
                        or value.get('model') != model
                        or count(value.get('prompt_tokens')) is None or count(value.get('completion_tokens')) is None):
                    missing = True
                    continue
                successful.append(value)
            except errors:
                missing = True
    if dispatched:
        usage['requests'] = dispatched
    if successful:
        usage.update(input_tokens=sum(row['prompt_tokens'] for row in successful),
                     output_tokens=sum(row['completion_tokens'] for row in successful))
        usage['total_tokens'] = usage['input_tokens'] + usage['output_tokens']
    # This indicates complete coverage of the inspected durable ledger only;
    # it does not assert that every possible external request uses that ledger.
    usage['complete'] = bool(dispatched and not missing and len(successful) == dispatched)
    if missing:
        evidence.issues.add('Provider usage coverage is incomplete.')
    return usage


def project_run(service, row):
    result = service._public(row)
    evidence = Evidence(service.runs_dir / row['id'] / 'artifacts')
    metrics = dict(wall_seconds=None, canonical=empty_canonical(),
        native=dict(best_score=None, metric=None, direction=None, task=None, scope='native'),
        usage=dict(input_tokens=None, output_tokens=None, total_tokens=None, requests=None, complete=False, usd=None),
        budget=dict(generation_calls=None, evaluations=None, label=None),
        evidence=dict(artifact_count=0, issues=[]))
    result['metrics'] = metrics
    if number(row['started']) is not None and number(row['ended']) is not None:
        metrics['wall_seconds'] = max(0, row['ended'] - row['started'])
    if row['state'] not in {'completed', 'failed', 'cancelled'}:
        return result
    try:
        metrics['canonical'] = canonical(evidence, row['id'])
    except (OSError, ValueError, TypeError, KeyError):
        evidence.issues.add('Canonical evidence is unavailable within the inspection bounds.')
    try:
        native, _ = evidence.read('.arena/native-result.json', 2 * 1024 * 1024)
        if native.get('schema') != 'arena.native-result/1' or native.get('framework') != row['framework']:
            raise ValueError('Native result identity mismatch')
        artifacts = native.get('artifacts', [])
        metrics['evidence']['artifact_count'] = len(artifacts) if isinstance(artifacts, list) else 0
        best, details = native.get('best_candidate', {}), native.get('native', {})
        metrics['native'].update(best_score=number(best.get('score', details.get('pop_best'))),
                                 metric=text(best.get('score_space', details.get('metric'))),
                                 direction=best.get('direction', details.get('direction')) if best.get('direction', details.get('direction')) in ('maximize', 'minimize') else None,
                                 task=text(details.get('task')))
        from .results_native import SUPPORTED, project_native
        if row['framework'] in SUPPORTED:
            metrics['native'] = project_native(evidence, row['framework'], native)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        evidence.issues.add('Native summary is not yet available.')
    if row['framework'] in ('sciel', 'sciel-release'):
        try:
            checkpoint, _ = evidence.read('native/checkpoint.json', 8 * 1024 * 1024)
            metrics['budget'].update(evaluations=count(checkpoint.get('budget')), label='Native search budget (B_evals)')
            metrics['usage'] = sciel_usage(evidence, row['model'])
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            evidence.issues.add('Provider usage coverage is incomplete.')
    metrics['evidence']['issues'] = sorted(evidence.issues)
    return result


def results(service, principal):
    service._scope(principal, 'read')
    is_admin = 'admin' in principal['scopes']
    where, args = ('', ()) if is_admin else (' WHERE owner=?', (principal['owner'],))
    with service._db() as db:
        total = db.execute('SELECT COUNT(*) FROM runs' + where, args).fetchone()[0]
        rows = db.execute('SELECT * FROM runs' + where + ' ORDER BY created DESC,id DESC LIMIT ?', (*args, MAX_RUNS)).fetchall()
    return {'schema': 'arena.results/1', 'generated_at': time.time(), 'scope': 'all' if is_admin else 'owner',
            'runs': [project_run(service, row) for row in rows], 'total': total, 'truncated': total > len(rows),
            'notes': ['Canonical scores use integrity-checked worker-published evaluator receipts; authoritative execution journals remain private.',
                      'The first evaluation is the initial reference; repeated evaluations are not distinct solutions.',
                      'Same-evaluator cohorts still differ in search budgets and protocols. Compare the same model before interpreting efficiency.',
                      'Token totals cover recorded provider receipts. Native price estimates are not billed costs; USD remains unknown.',
                      'Failed runs retain evidence; no failure is replaced with zero fitness. Small pilots are not paper reproductions.']}
