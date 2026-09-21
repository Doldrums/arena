"""Read-only proof that an older physical trace belongs to a committed wave.

The current journal must retain the exact receipt hashes and wave completion.
An orphan trace, active transaction, or merely similar prompt is insufficient.
"""
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re

from .parallel_cost import _read, _directory, _digest, _signature


def _time(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Unbound physical timestamp')
    return parsed


class CommittedTraceBindings:
    def __init__(self, run_dir, rows, waves):
        self.root, self.rows = Path(run_dir), rows
        self.receipts, self.completed, self.cache = {}, {}, {}
        for index, row in enumerate(rows):
            wave = row.get('wave')
            if (row.get('policy') != 'parallel_search' or type(wave) is not int
                    or wave < 0 or row.get('event') != 'decision'):
                continue
            if row.get('action') == 'wave_complete':
                self.completed[wave] = (index, row)
            elif row.get('action') == 'io_receipt' and row.get('kind') == 'llm':
                key = row.get('job_call')
                if isinstance(key, str) and re.fullmatch(r'.+:\d+', key):
                    self.receipts.setdefault((wave, key.rsplit(':', 1)[0]), []).append((index, row))
        self._authenticate(waves)

    def _authenticate(self, waves):
        targets, completions = {}, {}
        for wave in waves:
            self.cache[wave] = None
            try:
                index, complete = self.completed[wave]
                directory = _directory(_directory(self.root / '.parallel') / f'wave-{wave}')
                manifest, _ = _read(directory / 'transaction.json')
                boundary = manifest.get('journal_bytes')
                if (manifest.get('schema') != 'sciel-wave-transaction/2'
                        or manifest.get('phase') != 'committed' or manifest.get('wave_id') != str(wave)
                        or type(boundary) is not int or boundary < 0):
                    continue
                targets.setdefault(boundary, []).append((wave, directory, index, complete,
                                                          manifest.get('journal_sha256')))
                completions[(complete.get('segment_id'), complete.get('event_seq'))] = (wave, complete)
            except (OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError):
                continue
        if not targets:
            return
        # Prefix proof survives later waves and checkpoint compaction. Require
        # the completion row itself inside the committed bytes, not a stale
        # directory with the same wave number beside another journal lineage.
        # All requested boundaries share ONE forward pass, never one full read
        # per historical recovered wave.
        try:
            journal = self.root / 'sciel_events.jsonl'
            signature = _signature(journal)
            offset, digest, found, valid = 0, hashlib.sha256(), set(), {}
            continuing = False
            from .llm_calls import _open_regular
            with _open_regular(journal) as stream:
                for boundary in sorted(targets):
                    while offset < boundary:
                        raw = stream.readline(min(boundary - offset, 8 * 1024 * 1024))
                        if not raw:
                            raise ValueError('Committed journal prefix is incomplete')
                        offset += len(raw)
                        digest.update(raw)
                        if raw.endswith(b'\n') and not continuing:
                            try:
                                row = json.loads(raw)
                                if isinstance(row, dict):
                                    candidate = completions.get((row.get('segment_id'), row.get('event_seq')))
                                    if candidate is not None and row == candidate[1]:
                                        found.add(candidate[0])
                            except (ValueError, UnicodeError, TypeError, RecursionError):
                                pass
                        continuing = not raw.endswith(b'\n')
                    for wave, directory, index, complete, expected in targets[boundary]:
                        if wave in found and digest.hexdigest() == expected:
                            valid[wave] = (directory, index, complete)
            if _signature(journal) == signature:
                self.cache.update(valid)
        except (OSError, ValueError, TypeError, OverflowError):
            return

    def _match(self, request, terminal, index, event):
        directory, complete_index, complete = self.cache[request['parallel_wave']]
        if (index >= complete_index or event.get('segment_id') != complete.get('segment_id')
                or event.get('run_id') != request.get('run_id')
                or complete.get('run_id') != request.get('run_id')):
            return None
        key = event['job_call']
        call = _directory(_directory(directory / 'calls') / hashlib.sha256(key.encode()).hexdigest())
        intent, _ = _read(call / 'intent.json')
        dispatch, _ = _read(call / 'dispatched.json')
        receipt, _ = _read(call / 'receipt.json')
        source, payload = intent.get('request'), receipt.get('payload')
        if not isinstance(source, dict) or not isinstance(payload, dict):
            return None
        request_hash = _digest({'kind': 'llm', 'request': source})
        if (intent.get('schema') != 'sciel-parallel-call/1' or intent.get('kind') != 'llm'
                or intent.get('key') != key or intent.get('request_sha256') != request_hash
                or request_hash != event.get('request_sha256')
                or dispatch.get('request_sha256') != request_hash
                or payload.get('request_sha256') != request_hash
                or receipt.get('sha256') != _digest(payload)
                or receipt['sha256'] != event.get('receipt_sha256')
                or any(payload.get(field) != event.get(field) for field in
                    ('status', 'started_at', 'completed_at', 'elapsed_seconds', 'queue_seconds'))):
            return None
        prompt, options = source.get('prompt'), source.get('options', {})
        context = source.get('trace_context')
        elapsed, outer_elapsed = terminal.get('elapsed_seconds'), payload.get('elapsed_seconds')
        if (not isinstance(prompt, str) or not isinstance(options, dict)
                or not isinstance(context, dict) or set(context) != {'role', 'reference', 'experiment_id'}
                or any(request.get(field) != value for field, value in context.items())
                or set(options) - {'max_tokens', 'response_format'}
                or hashlib.sha256(prompt.encode()).hexdigest() != request.get('prompt_sha256')
                or request.get('model') != source.get('model')
                or request.get('temperature') != source.get('temperature')
                or request.get('transport_parameters') != source.get('transport_parameters')
                or any(request.get(field) != value for field, value in options.items())
                or any(type(value) not in (int, float) or not math.isfinite(value)
                       for value in (elapsed, outer_elapsed))
                or not 0 <= elapsed <= outer_elapsed
                or not _time(payload['started_at']) <= _time(request['timestamp'])
                    <= _time(terminal['timestamp']) <= _time(payload['completed_at'])):
            return None
        if any(terminal.get(field) != request.get(field) for field in
               ('call_id', 'run_id', 'segment_id', 'role', 'reference', 'experiment_id',
                'parallel_wave', 'parallel_job', 'model', 'journal_event_seq')):
            return None
        if payload['status'] == 'returned':
            value = payload.get('value')
            if (not isinstance(value, dict) or not isinstance(value.get('text'), str)
                    or terminal.get('event') != 'response'
                    or terminal.get('generation_returned') is not True
                    or terminal.get('generation_dispatch') != 'returned'
                    or terminal.get('response_sha256') != hashlib.sha256(value['text'].encode()).hexdigest()
                    or any(terminal.get(field) != value.get(field) for field in
                        ('cost', 'prompt_tokens', 'completion_tokens', 'finish_reason',
                         'cost_provenance', 'response_error'))
                    or terminal.get('current_call_cost_unknown') is not (value.get('cost') is None)):
                return None
        elif payload['status'] == 'error':
            undispatched = payload.get('not_dispatched') is True
            if (terminal.get('event') != 'error' or terminal.get('llm_error') != payload.get('error')
                    or terminal.get('generation_returned') is not False
                    or terminal.get('generation_dispatch') != ('not_dispatched' if undispatched else 'unknown')
                    or terminal.get('cost') != (0.0 if undispatched else None)
                    or terminal.get('current_call_cost_unknown') is not (not undispatched)):
                return None
        else:
            return None
        return dict(wave=request['parallel_wave'], job_call=key,
            request_sha256=request_hash, receipt_sha256=receipt['sha256'],
            committed_segment_id=event['segment_id'], committed_event_index=index)

    def match(self, request, terminal):
        wave, job = request.get('parallel_wave'), request.get('parallel_job')
        if type(wave) is not int or not isinstance(job, str) or terminal is None:
            return None
        matches = []
        for index, event in self.receipts.get((wave, job), []):
            try:
                value = self._match(request, terminal, index, event)
                if value is not None:
                    matches.append(value)
            except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError, RecursionError):
                continue
        return matches[0] if len(matches) == 1 else None
