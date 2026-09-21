"""Read-only LLM exchanges, with exact text loaded only on explicit inspection.

Legacy journal hashes are never treated as recoverable prompts. Trace paths are
derived from a validated ID, never taken from a journal field.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
from types import SimpleNamespace

from .compat.llm_cost import response_cost_provenance

MAX_TEXT_BYTES = 16 * 1024 * 1024
CALL_ID = re.compile(r"[0-9a-f]{32}\Z")


def _dict(value):
    return value if isinstance(value, dict) else {}


def _number(value):
    try:
        return value if type(value) in (int, float) and math.isfinite(value) else None
    except OverflowError:
        return None


def _hash(text):
    return hashlib.sha256(text.encode('utf-8', errors='surrogatepass')).hexdigest()


def _iteration(row):
    for value in (row.get('iteration_no'), row.get('iteration'), _dict(row.get('evidence')).get('iteration')):
        if type(value) is int:
            return value
    return None


def _legacy_id(row, role, reference, index):
    key = [row.get('segment_id'), row.get('event_seq', index), role, reference]
    return 'legacy-' + _hash(json.dumps(key, sort_keys=True))[:24]


def _duration(start, end):
    a, b = _number(start.get('segment_elapsed_seconds')), _number(end.get('segment_elapsed_seconds'))
    if a is not None and b is not None and start.get('segment_id') == end.get('segment_id') and b >= a:
        return b - a
    try:
        a = datetime.fromisoformat(start['timestamp'].replace('Z', '+00:00'))
        b = datetime.fromisoformat(end['timestamp'].replace('Z', '+00:00'))
        value = (b - a).total_seconds()
        return value if a.tzinfo and b.tzinfo and value >= 0 else None
    except (ValueError, TypeError, KeyError, OverflowError):
        return None


def _new(row, role, reference, index):
    return dict(id=_legacy_id(row, role, reference, index), source='journal',
        role=role, reference=reference, experiment_id=row.get('experiment_id'),
        segment_id=row.get('segment_id'), iteration=_iteration(row),
        model=row.get('model'), status='response_not_recorded', outcome_status=None,
        started_at=row.get('timestamp'), ended_at=None, elapsed_seconds=None,
        latency_source=None, cost=None, current_call_cost_unknown=None, cost_provenance=None,
        prompt_sha256=row.get('prompt_sha256'), response_sha256=None,
        error=None, _request=row, _response={}, _terminal={}, _order=index)


def _terminal(call, row, *, response=False, error=False):
    call['_terminal'] = row
    call['ended_at'] = row.get('timestamp')
    call['elapsed_seconds'] = _duration(call['_request'], row)
    call['latency_source'] = 'journal_event_interval' if call['elapsed_seconds'] is not None else None
    if response:
        call['_response'] = row
        call['status'] = 'returned'
        call['response_sha256'] = row.get('response_sha256')
    if error:
        call['status'] = 'failed'
        safe = _dict(row.get('llm_error'))
        saved_error = call.get('error') or {}
        call['error'] = {**saved_error, **{key: safe.get(key)
            for key in ('stage', 'reason', 'cause_type', 'http_status') if key in safe}}
        if row.get('error_type'):
            call['error']['type'] = str(row['error_type'])[:100]
        if not call['error']:
            call['error'] = {'reason': 'Generation stopped; the journal does not record the provider error.'}
    for key in ('cost', 'current_call_cost_unknown'):
        if key in row:
            call[key] = row[key]
    if response:
        call['cost_provenance'] = response_cost_provenance(SimpleNamespace(
            cost=call['cost'], cost_provenance=row.get('cost_provenance'),
            prompt_tokens=row.get('prompt_tokens'), completion_tokens=row.get('completion_tokens')))
    call['model'] = row.get('model') or row.get('returned_model') or call['model']


def legacy_calls(rows):
    calls, generation, auxiliary, ideas = [], {}, {}, {}
    for index, row in enumerate(rows):
        segment, phase = row.get('segment_id'), row.get('phase')
        experiment = row.get('experiment_id')
        if row.get('event') == 'research' and phase == 'attempt':
            call = _new(row, 'G', experiment, index)
            calls.append(call)
            generation[segment, experiment] = call
        elif row.get('event') == 'research' and phase in ('hypothesis', 'structured_response', 'generation_error', 'outcome'):
            call = generation.get((segment, experiment))
            if call is None:
                continue
            evidence = _dict(row.get('evidence'))
            if phase in ('hypothesis', 'structured_response'):
                _terminal(call, row, response=True)
            elif phase == 'generation_error':
                _terminal(call, row, error=True)
            if phase == 'outcome':
                call['outcome_status'] = evidence.get('status')
                # A two-stage idea logs each response's cost separately. Its
                # stopped outcome may lack that receipt; never erase it or
                # substitute the accumulated cost of earlier requests.
                if ('cost' not in call['_response'] and call['cost'] is None
                        and call['current_call_cost_unknown'] is not True):
                    call['cost'] = _number(evidence.get('generation_cost'))
                if evidence.get('status') == 'generation_stopped':
                    if call['status'] not in ('failed', 'returned'):
                        _terminal(call, row, error=True)
                    if call['current_call_cost_unknown'] is None:
                        call['current_call_cost_unknown'] = (call['cost'] is None and evidence.get('generation_dispatch') != 'not_dispatched')
        elif row.get('event') == 'research' and phase in ('aux_start', 'aux_result', 'aux_stopped', 'aux_abandoned'):
            kind, reference = row.get('kind'), row.get('reference')
            key = (segment, kind, reference, row.get('call_index'))
            if phase == 'aux_start':
                call = _new(row, {'conclusion': 'C', 'reflection': 'R'}.get(kind, 'unknown'), reference, index)
                call['experiment_id'] = reference if kind == 'conclusion' else None
                if kind == 'conclusion' and (segment, reference) in generation:
                    call['iteration'] = generation[segment, reference]['iteration']
                calls.append(call)
                auxiliary[key] = call
            else:
                call = auxiliary.get(key)
                if call is not None:
                    _terminal(call, row, response=phase == 'aux_result',
                              error=phase in ('aux_stopped', 'aux_abandoned'))
        elif row.get('event') == 'research' and phase == 'idea':
            key = (segment, row.get('idea_id'), row.get('stage'))
            if row.get('action') == 'request_start':
                call = generation.get((segment, experiment)) if row.get('stage') == 'code' else None
                if call is None:
                    call = _new(row, 'idea', row.get('idea_id'), index)
                    calls.append(call)
                else:
                    call['_request'] = row
                    call['model'] = row.get('model') or call['model']
                ideas[key] = call
            elif row.get('action') == 'request_result' and key in ideas:
                call = ideas[key]
                _terminal(call, row, response=True)
            elif row.get('action') == 'stopped' and key in ideas:
                call = ideas[key]
                if call['status'] != 'returned':
                    _terminal(call, row, error=True)
                    if row.get('generation_dispatch') == 'not_dispatched':
                        call['cost'] = 0.0
                elif 'current_call_cost_unknown' in row:
                    # A parsing/evaluation/accounting stop after a recorded
                    # response is not evidence that the provider call failed.
                    call['current_call_cost_unknown'] = row['current_call_cost_unknown']
        elif row.get('event') == 'iteration' and isinstance(row.get('prompt'), str):
            experiment = _dict(row.get('meta')).get('research_id')
            call = generation.get((segment, experiment)) if experiment else None
            if call is None:
                call = _new(row, 'G', experiment or row.get('child_id'), index)
                # An iteration is a terminal record, not a request timestamp.
                call['started_at'] = None
                calls.append(call)
            prompt = row['prompt']
            if not call['prompt_sha256'] or _hash(prompt) == call['prompt_sha256']:
                call['_full_prompt'] = prompt
                call['prompt_sha256'] = _hash(prompt)
            response = row.get('response')
            if isinstance(response, str) and (not call['response_sha256'] or _hash(response) == call['response_sha256']):
                call['_full_response'] = response
                call['response_sha256'] = _hash(response)
                call['status'] = 'returned'
            call['model'] = row.get('model_used') or call['model']
            call['iteration'] = _iteration(row)
    return calls


def trace_manifest(run_dir):
    path = Path(run_dir) / 'artifacts' / 'llm_calls.jsonl'
    return path if not path.parent.is_symlink() and not path.is_symlink() else None


def _bounded_lines(stream):
    while True:
        line = stream.readline(131073)
        if not line:
            return
        if len(line) > 131072:
            while line and not line.endswith(b'\n'):
                line = stream.readline(131073)
            continue
        if line.endswith(b'\n'):
            yield line


def _open_regular(path):
    # Nonblocking open is essential: a FIFO has size zero and would otherwise
    # wait forever before fstat can reject it. NOFOLLOW also closes the final
    # component symlink race between the path check and open.
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_NOFOLLOW', 0))
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError('Transcript is not a regular file')
        return os.fdopen(fd, 'rb')
    except BaseException:
        os.close(fd)
        raise


def _trace_calls(run_dir, rows):
    path = trace_manifest(run_dir)
    if path is None or not path.is_file():
        return []
    starts = [row for row in rows if row.get('event') == 'run_start']
    run_ids = {row.get('run_id') for row in starts if isinstance(row.get('run_id'), str)}
    segments = {row.get('segment_id') for row in starts if isinstance(row.get('segment_id'), str)}
    sequences = {}
    for row in rows:
        if type(row.get('event_seq')) is int:
            sequences[row.get('segment_id')] = max(sequences.get(row.get('segment_id'), 0), row['event_seq'])
    calls = {}
    try:
        with _open_regular(path) as stream:
            for line in _bounded_lines(stream):
                try:
                    row = json.loads(line)
                except (ValueError, UnicodeError, RecursionError):
                    continue
                if (type(row) is not dict or not CALL_ID.fullmatch(str(row.get('call_id', '')))
                        or type(row.get('run_id')) is not str or row['run_id'] not in run_ids
                        or type(row.get('segment_id')) is not str or row['segment_id'] not in segments):
                    continue
                visible = not (type(row.get('journal_event_seq')) is int
                    and row['journal_event_seq'] > sequences.get(row['segment_id'], 0))
                ident = row['call_id']
                if row.get('event') == 'request':
                    call = _new(row, row.get('role', 'unknown'), row.get('reference') or row.get('experiment_id'), len(rows) + len(calls))
                    call.update(id=ident, source='trace', _trace_request=row,
                                _journal_visible=visible)
                    calls[ident] = call
                elif row.get('event') in ('response', 'error') and ident in calls:
                    call = calls[ident]
                    if not visible:
                        call['_unpublished_terminal'] = row
                        continue
                    _terminal(call, row, response=row['event'] == 'response', error=row['event'] == 'error')
                    call['elapsed_seconds'] = _number(row.get('elapsed_seconds'))
                    call['latency_source'] = 'recorded_call' if call['elapsed_seconds'] is not None else None
                    call['_trace_terminal'] = row
    except OSError:
        return []
    from .parallel_llm import CommittedTraceBindings
    def parallel_key(call):
        request = call['_trace_request']
        wave, job = request.get('parallel_wave'), request.get('parallel_job')
        return (wave, job) if type(wave) is int and wave >= 0 and isinstance(job, str) else None
    affected = {parallel_key(call)
        for call in calls.values() if not call['_journal_visible'] or '_unpublished_terminal' in call}
    affected.discard(None)
    bindings = CommittedTraceBindings(run_dir, rows, {wave for wave, _ in affected})
    proven = {}
    for ident, call in calls.items():
        request = call['_trace_request']
        if parallel_key(call) not in affected:
            continue
        terminal = call.get('_unpublished_terminal', call.get('_trace_terminal'))
        proof = bindings.match(request, terminal)
        if proof is not None:
            call['_parallel_binding'] = proof
            proven.setdefault((proof['wave'], proof['job_call']), []).append(ident)
    # Multiple trace IDs claiming the same physical request are ambiguous, not
    # extra model calls. Do not relax the original journal boundary for them.
    for identities in proven.values():
        if len(identities) != 1:
            for ident in identities:
                calls[ident].pop('_parallel_binding', None)
    accepted = []
    for call in calls.values():
        proof = call.get('_parallel_binding')
        if proof is not None:
            terminal = call.get('_unpublished_terminal', call.get('_trace_terminal'))
            _terminal(call, terminal, response=terminal['event'] == 'response', error=terminal['event'] == 'error')
            call['_trace_terminal'] = terminal
            call['elapsed_seconds'] = _number(terminal.get('elapsed_seconds'))
            call['latency_source'] = 'recorded_call' if call['elapsed_seconds'] is not None else None
            call['parallel_receipt'] = {k: v for k, v in proof.items() if k != 'committed_event_index'}
        if call['_journal_visible'] or proof is not None:
            accepted.append(call)
    return accepted


def collect_calls(run_dir, rows):
    calls = legacy_calls(rows)
    by_hash, by_reference = {}, {}
    for index, call in enumerate(calls):
        if isinstance(call['prompt_sha256'], str):
            by_hash.setdefault((call['segment_id'], call['prompt_sha256']), []).append(index)
        if type(call['reference']) in (str, int):
            by_reference.setdefault((call['segment_id'], call['role'], call['reference']), []).append(index)
    removed, traced = set(), []
    for trace in _trace_calls(run_dir, rows):
        proof = trace.get('_parallel_binding')
        segment = proof['committed_segment_id'] if proof else trace['segment_id']
        candidates = (set(by_hash.get((segment, trace['prompt_sha256']), []))
                      if isinstance(trace['prompt_sha256'], str) else set())
        if type(trace['reference']) in (str, int):
            candidates.update(by_reference.get((segment, trace['role'], trace['reference']), []))
        matches = [index for index in candidates - removed
            if not any(trace[key] and calls[index][key] and trace[key] != calls[index][key]
                       for key in ('prompt_sha256', 'response_sha256'))
            and (proof is None or (calls[index]['prompt_sha256'] == trace['prompt_sha256']
                 and calls[index]['role'] == trace['role']
                 and calls[index]['reference'] == trace['reference']
                 and calls[index]['_order'] < proof['committed_event_index']))]
        if proof is not None and matches:
            # The nearest preceding logical start owns this exact physical
            # receipt. A repeated prompt in a later retry is a separate call.
            matches = [max(matches, key=lambda index: calls[index]['_order'])]
        if len(matches) == 1:
            matched, = matches
            old = calls[matched]
            trace['_legacy'] = old
            trace['_order'] = old['_order']
            trace['outcome_status'] = old['outcome_status']
            trace['iteration'] = trace['iteration'] if trace['iteration'] is not None else old['iteration']
            trace['experiment_id'] = trace['experiment_id'] or old['experiment_id']
            trace['reference'] = trace['reference'] if trace['reference'] is not None else old['reference']
            trace['model'] = trace['model'] or old['model']
            if trace['role'] == 'unknown':
                trace['role'] = old['role']
            if '_trace_terminal' not in trace:
                # The provider response can reach its ordinary journal owner
                # even if transcript persistence failed. Keep that paid result.
                for key in ('status', 'cost', 'current_call_cost_unknown', 'cost_provenance', 'ended_at',
                            'elapsed_seconds', 'latency_source', 'response_sha256', 'error'):
                    trace[key] = old[key]
            removed.add(matched)
        traced.append(trace)
    return sorted([call for index, call in enumerate(calls) if index not in removed] + traced,
                  key=lambda call: (call.get('started_at') or '', call['_order']), reverse=True)


def metadata(call):
    result = {key: value for key, value in call.items() if not key.startswith('_')}
    for side in ('prompt', 'response'):
        base = call.get('_legacy', call) if call['source'] == 'trace' else call
        row = base['_request'] if side == 'prompt' else base['_response']
        text = base.get('_full_' + side, row.get(side))
        traced = call['source'] == 'trace' and (side == 'prompt' or call.get('_trace_terminal', {}).get('event') == 'response')
        result[side + '_available'] = isinstance(text, str) or traced
        result[side + '_truncated'] = False if '_full_' + side in base or traced else bool(row.get(side + '_truncated'))
        trace_row = call['_request'] if side == 'prompt' else call.get('_trace_terminal', {})
        result[side + '_chars'] = (trace_row.get(side + '_chars') if traced
            else len(text) if isinstance(text, str) else row.get(side + '_chars'))
    return result


def _trace_text(run_dir, call, side):
    if side == 'response' and call.get('_trace_terminal', {}).get('event') != 'response':
        return None, 'No response text was recorded for this call.'
    base = Path(run_dir) / 'artifacts' / 'llm_calls'
    path = base / (call['id'] + '.' + side + '.txt')
    if (not CALL_ID.fullmatch(call['id']) or base.parent.is_symlink()
            or base.is_symlink() or path.is_symlink()):
        return None, 'Trace text path is unavailable.'
    try:
        with _open_regular(path) as stream:
            if os.fstat(stream.fileno()).st_size > MAX_TEXT_BYTES:
                return None, 'Recorded text exceeds the 16 MiB inspector limit.'
            # Bound the read itself as the file may grow after fstat.
            raw = stream.read(MAX_TEXT_BYTES + 1)
        if len(raw) > MAX_TEXT_BYTES:
            return None, 'Recorded text exceeds the 16 MiB inspector limit.'
        # Preserve CRLF literally; text-mode universal-newline conversion would
        # change the exact prompt and make its recorded digest appear invalid.
        text = raw.decode('utf-8')
    except (OSError, UnicodeError):
        return None, 'Text file was not recorded or is unavailable.'
    expected = call.get(side + '_sha256')
    if not isinstance(expected, str) or _hash(text) != expected:
        return None, 'Text does not match its recorded SHA-256; display refused.'
    return text, None


def detail(run_dir, call):
    result = metadata(call)
    result['request_options'] = {key: call['_request'][key]
        for key in ('temperature', 'max_tokens', 'response_format', 'transport_parameters')
        if key in call['_request']}
    for side in ('prompt', 'response'):
        row = call['_request'] if side == 'prompt' else call['_response']
        if call['source'] == 'trace':
            text, note = _trace_text(run_dir, call, side)
            text_source = 'trace' if text is not None else None
            if (text is None and '_legacy' in call
                    and call.get('_trace_terminal', {}).get('event') != 'error'):
                saved = detail(run_dir, call['_legacy'])[side]
                expected = call.get(side + '_sha256')
                if (saved['available'] and (not expected or saved['sha256'] == expected
                        or not saved['truncated'] and _hash(saved['text']) == expected)):
                    text, text_source = saved['text'], 'journal'
                    result[side + '_truncated'] = saved['truncated']
                    note = 'Transcript text unavailable; showing the saved journal ' + ('prefix.' if saved['truncated'] else 'text.')
        else:
            text = call.get('_full_' + side, row.get(side))
            text = text if isinstance(text, str) else None
            note = None if text is not None else 'Only a hash was recorded; the original text cannot be reconstructed.' if call.get(side + '_sha256') else 'No text was recorded for this call.'
            text_source = 'journal' if text is not None else None
        result[side] = dict(text=text, available=text is not None,
            truncated=result[side + '_truncated'], sha256=call.get(side + '_sha256'),
            source=text_source,
            note=note or ('The journal stores only a prefix of the original text.' if result[side + '_truncated'] else None))
    return result
