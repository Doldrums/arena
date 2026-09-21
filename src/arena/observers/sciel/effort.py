"""Observed effort, separate from candidate cost and scientific counters.

Only checksum-bound cooperative-I/O receipts are counted. Old runs without the
physical ledger remain unknown. This module neither imports nor recovers Engine.
"""
from collections import OrderedDict
from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path
import re

from .parallel_cost import WaveSpendMonitor, IO_KINDS, _read, _digest, _directory, _signature, _number
from .parallel_llm import CommittedTraceBindings
from .cost_accounting import subscription_unpriced, token_count


def _dict(value):
    return value if isinstance(value, dict) else {}


def _score(value):
    try:
        return value if type(value) in (int, float) and math.isfinite(value) else None
    except OverflowError:
        return None


def _at(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed if parsed.tzinfo else None
    except (AttributeError, ValueError, TypeError, OverflowError):
        return None


def effort_basis(rows, sources, program_id, score, task_hash, iterations):
    program = _dict(sources.get(program_id))
    code = program.get('code')
    source = hashlib.sha256(code.encode('utf-8', errors='surrogatepass')).hexdigest() if isinstance(code, str) else None
    ids, target_iteration = [], None
    for row in rows:
        if row.get('child_id') != program_id or row.get('child_score') != score:
            continue
        target_iteration = row.get('iteration_no')
        for evaluation in _dict(row.get('meta')).get('evaluations', []):
            if isinstance(evaluation, dict) and evaluation.get('source_sha256') == source and evaluation.get('score') == score and evaluation.get('ok') is True:
                ids.append(evaluation.get('evaluation_id'))
    return dict(program_id=program_id, source_sha256=source, score=score,
        cases=program.get('cases'), task_hash=task_hash,
        evaluation_ids=list(dict.fromkeys(x for x in ids if isinstance(x, str))), ordinary_iterations=iterations,
        target_iteration=target_iteration)


class EffortMonitor:
    """Memoize compact receipt facts; never retain prompts or generated code."""
    def __init__(self):
        self.calls = OrderedDict()
        self.spend = WaveSpendMonitor()

    def _call(self, directory, wave, run_id, task_hash, event=None):
        paths = [directory / name for name in ('intent.json', 'dispatched.json', 'receipt.json')]
        signature = tuple(_signature(p) if p.exists() or p.is_symlink() else None for p in paths)
        cache_key = (str(directory), signature, run_id, task_hash)
        if cache_key in self.calls:
            self.calls.move_to_end(cache_key)
            fact = self.calls[cache_key]
        else:
            intent, _ = _read(paths[0]); request = intent.get('request'); kind = intent.get('kind'); key = intent.get('key')
            if (intent.get('schema') != 'sciel-parallel-call/1' or not isinstance(request, dict)
                    or kind not in IO_KINDS or not isinstance(key, str)
                    or hashlib.sha256(key.encode()).hexdigest() != directory.name):
                raise ValueError('Invalid physical request')
            expected = _digest(dict(kind=kind, request=request))
            if intent.get('request_sha256') != expected:
                raise ValueError('Invalid request checksum')
            if signature[1] is None:
                if signature[2] is not None:
                    raise ValueError('Receipt without dispatch')
                return None
            dispatch, _ = _read(paths[1]); dispatched = dispatch.get('timestamp')
            if dispatch.get('request_sha256') != expected or _at(dispatched) is None:
                raise ValueError('Invalid dispatch')
            fact = dict(kind=kind, key=key, wave=wave, dispatched_at=dispatched,
                completed_at=None, status='pending', request_sha256=expected, receipt_sha256=None,
                model=request.get('model') if isinstance(request.get('model'), str) else None,
                reported_usd=None, cost_source=None, unpriced=False, prompt_tokens=None, completion_tokens=None,
                source_sha256=None, score=None, cases=None,
                evaluation_id=f'evaluation:{run_id}:wave:{wave}:{key}' if kind == 'evaluation' else None)
            if kind == 'evaluation':
                source = request.get('source')
                if not isinstance(source, str) or request.get('task_hash') != task_hash:
                    raise ValueError('Evaluation task/source mismatch')
                fact['source_sha256'] = hashlib.sha256(source.encode('utf-8', errors='surrogatepass')).hexdigest()
            if signature[2] is not None:
                envelope, _ = _read(paths[2]); payload = envelope.get('payload')
                if (not isinstance(payload, dict) or envelope.get('sha256') != _digest(payload)
                        or payload.get('request_sha256') != expected or payload.get('status') not in {'returned', 'error'}
                        or _at(payload.get('completed_at')) is None
                        or _at(payload['completed_at']) < _at(dispatched)):
                    raise ValueError('Invalid physical receipt')
                value = _dict(payload.get('value'))
                fact.update(completed_at=payload['completed_at'], status=payload['status'],
                    receipt_sha256=envelope['sha256'], not_dispatched=payload.get('not_dispatched') is True)
                if kind == 'llm' and payload['status'] == 'returned':
                    provenance = _dict(value.get('cost_provenance'))
                    fact.update(reported_usd=_number(value.get('cost')),
                        model=value.get('model') if isinstance(value.get('model'), str) else fact['model'],
                        cost_source=provenance.get('source') or 'unspecified_recorded_cost',
                        unpriced=subscription_unpriced(value), prompt_tokens=token_count(value.get('prompt_tokens')),
                        completion_tokens=token_count(value.get('completion_tokens')))
                if kind == 'evaluation':
                    result = _dict(value.get('result'))
                    fact.update(score=_score(result.get('score')), cases=result.get('cases'), ok=result.get('ok'))
            if signature != tuple(_signature(p) if p.exists() or p.is_symlink() else None for p in paths):
                raise ValueError('Physical receipt changed during read')
            self.calls[cache_key] = fact
            while len(self.calls) > 16384:
                self.calls.popitem(last=False)
        if event is not None and any(event.get(field) != fact.get(field) for field in
                ('kind', 'request_sha256', 'receipt_sha256', 'completed_at', 'status')):
            raise ValueError('Receipt does not match its committed journal owner')
        return fact

    def observe(self, run_dir, start, rows, basis):
        checked = datetime.now(timezone.utc).isoformat()
        result = dict(schema='arena-run-effort/1', observed_at=checked, total=None, to_best=None,
            best_program_id=basis.get('program_id'), source='Checksum-bound physical I/O receipts',
            note='All branches, retries and research calls in this run; a read-only, non-atomic receipt snapshot. Subscription calls have no provider-reported USD price; known USD is a subtotal. USD covers recorded LLM charges only; CPU, local models and infrastructure are not priced. Evaluation cascades include seed, bootstrap, failures and remeasurements; smoke/full stages are not separate cascades.')
        root = Path(run_dir) / '.parallel'
        if not root.exists():
            result['reason'] = 'Physical receipt history not recorded.'
            return result
        try:
            _directory(root)
            waves = {r['wave'] for r in rows if r.get('policy') == 'parallel_search'
                and r.get('action') == 'wave_complete' and type(r.get('wave')) is int and r['wave'] >= 0
                and r.get('run_id') == start.get('run_id')}
            if len(waves) > 4096:
                raise ValueError('Receipt projection limit reached')
            proofs = CommittedTraceBindings(run_dir, rows, waves)
            events = {(r.get('wave'), r.get('job_call')): (index, r) for index, r in enumerate(rows) if r.get('policy') == 'parallel_search'
                and r.get('action') == 'io_receipt' and r.get('run_id') == start.get('run_id')}
            facts, complete, reasons = [], True, []
            directories = {}
            for wave in waves:
                proof = proofs.cache.get(wave)
                if proof is None:
                    complete = False
                    continue
                directories[wave] = (proof[0], True)
            pending = self.spend.observe(run_dir, start)
            if pending is not None:
                if pending.get('available'):
                    wave = int(pending['wave'])
                    directories[wave] = (_directory(root / f'wave-{wave}'), False)
                else:
                    complete = False
                    reasons.append('Current wave is not yet authenticated.')
            expected = set(range(len(directories)))
            if set(directories) != expected or not directories:
                complete = False
            inspected = 0
            for wave, (directory, committed) in sorted(directories.items()):
                calls = _directory(directory / 'calls')
                observed_keys = set()
                for child in calls.iterdir():
                    inspected += 1
                    if inspected > 100000:
                        raise ValueError('Receipt projection limit reached')
                    _directory(child)
                    if not re.fullmatch('[a-f0-9]{64}', child.name):
                        raise ValueError('Invalid receipt directory')
                    try:
                        fact = self._call(child, wave, start.get('run_id'), basis.get('task_hash'))
                        if fact is None:
                            continue
                        if committed:
                            owner = events.get((wave, fact['key']))
                            proof = proofs.cache[wave]
                            if (owner is None or owner[0] >= proof[1]
                                    or owner[1].get('segment_id') != proof[2].get('segment_id')):
                                raise ValueError('No journal receipt owner')
                            fact = self._call(child, wave, start.get('run_id'), basis.get('task_hash'), owner[1])
                        facts.append(fact)
                        observed_keys.add(fact['key'])
                    except (OSError, ValueError, TypeError, OverflowError, RecursionError):
                        complete = False
                if committed and observed_keys != {key for (number, key) in events if number == wave}:
                    complete = False
            if not complete:
                reasons.append('Physical history has missing or unauthenticated receipts; counts and cost are lower bounds.')
            result['total'] = self._scope(facts, checked, complete, rows, basis.get('ordinary_iterations'), subscription=_dict(_dict(start.get('config')).get('llm')).get('provider') == 'codex_responses')
            result['total']['reason'] = ' '.join(reasons) or None
            # A full source + saved measurement binding is required. Same-score
            # programs and repeated measurements cannot choose a cutoff by score.
            candidates = [f for f in facts if f['kind'] == 'evaluation' and f.get('ok') is True
                and f['source_sha256'] == basis.get('source_sha256') and f['score'] == basis.get('score')
                and isinstance(basis.get('cases'), dict) and f.get('cases') == basis['cases']
                and (not basis.get('evaluation_ids') or f['evaluation_id'] in basis['evaluation_ids'])]
            if len(candidates) == 1:
                best = candidates[0]
                result['to_best'] = self._scope(facts, best['completed_at'], complete, rows, subscription=_dict(_dict(start.get('config')).get('llm')).get('provider') == 'codex_responses')
                result['to_best'].update(program_id=basis.get('program_id'), evaluation_id=best['evaluation_id'],
                    source_sha256=best['source_sha256'], cutoff_kind='evaluation_completed',
                    target_iteration=basis.get('target_iteration'))
            else:
                result['best_reason'] = 'Best measurement has no unique authenticated physical receipt.'
        except (OSError, ValueError, TypeError, OverflowError, RecursionError, KeyError):
            result['reason'] = 'Physical receipt history cannot currently be authenticated.'
        return result

    @staticmethod
    def _scope(facts, cutoff, complete, rows, iterations=None, *, subscription=False):
        boundary = _at(cutoff)
        started = [f for f in facts if _at(f['dispatched_at']) <= boundary and not f.get('not_dispatched')]
        ended = [f for f in started if _at(f['completed_at']) is not None and _at(f['completed_at']) <= boundary]
        ended_keys = {(f['wave'], f['key']) for f in ended}
        llm = [f for f in ended if f['kind'] == 'llm']
        waiting = [f for f in started if f['kind'] == 'llm' and (f['wave'],f['key']) not in ended_keys]
        known = [f['reported_usd'] for f in llm if f['reported_usd'] is not None]
        unpriced = sum(f['unpriced'] for f in llm)
        unknown = sum(f['reported_usd'] is None and not f['unpriced'] for f in llm)
        tokens = {field: [f[field] for f in llm if f.get(field) is not None]
                  for field in ('prompt_tokens', 'completion_tokens')}
        models = sorted({f['model'] for f in started if f['kind'] == 'llm' and f.get('model')})
        model_missing = any(f['kind'] == 'llm' and not f.get('model') for f in started)
        starts = [_at(r.get('timestamp')) for r in rows if r.get('event') == 'run_start' and _at(r.get('timestamp'))]
        elapsed = (boundary-min(starts)).total_seconds() if starts and min(starts) <= boundary else None
        if iterations is None:
            recorded = [r.get('iteration_no') for r in rows if r.get('event') == 'iteration'
                and _at(r.get('timestamp')) is not None and _at(r['timestamp']) <= boundary and type(r.get('iteration_no')) is int]
            iterations = max(recorded, default=0)
        return dict(status='complete' if complete and not unknown and not waiting else 'partial',
            history_complete=complete, cutoff_at=cutoff, ordinary_iterations=iterations,
            evaluator_cascades=sum(f['kind'] == 'evaluation' for f in ended),
            pending_evaluator_cascades=sum(f['kind'] == 'evaluation' for f in started if (f['wave'],f['key']) not in ended_keys),
            physical_llm_calls=len(llm), dispatched_llm_calls=len(llm)+len(waiting),
            pending_llm_calls=len(waiting), unknown_cost_calls=unknown, unpriced_llm_calls=unpriced,
            billing_mode='subscription_unpriced' if subscription or unpriced else None,
            prompt_tokens=sum(tokens['prompt_tokens']) if tokens['prompt_tokens'] else None,
            completion_tokens=sum(tokens['completion_tokens']) if tokens['completion_tokens'] else None,
            token_usage_complete=complete and not waiting and all(len(v) == len(llm) for v in tokens.values()),
            reported_usd=math.fsum(known) if known or not llm and complete and not subscription else None,
            cost_status='subscription_unpriced' if unpriced or subscription else 'reported' if complete and not waiting and not unknown and all(f['cost_source'] == 'provider_reported' for f in llm) else 'partial_or_estimated',
            models=models, model_count=len(models) if not model_missing and complete else None,
            wall_seconds=elapsed, wall_scope='Elapsed since first recorded run start, including pauses',
            cpu_seconds=None, cpu_usd=None,
            tool_calls=sum(f['kind'] in {'tool_execution','tool_job_submit','tool_job_poll','tool_job_cancel'} for f in ended))
