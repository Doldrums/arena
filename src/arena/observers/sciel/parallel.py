"""Recorded execution limits and wave receipts, never inferred concurrency."""
from __future__ import annotations

import math


LIMITS = ('workers', 'host_llm_slots', 'provider_slots', 'host_evaluator_slots',
          'max_inflight_per_island', 'max_inflight_per_parent')
MAX_WAVES = 30


def _int(value):
    return value if type(value) is int and value >= 0 else None


def _number(value):
    try:
        return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None
    except OverflowError:
        return None


def portfolio_progress(value, *, workers=None):
    """Only recorded interleaved scheduling grants this progress presentation."""
    if not isinstance(value, dict) or value.get('portfolio_schedule') != 'interleaved':
        return None
    attempted, total = _int(value.get('portfolio_attempted')), _int(value.get('portfolio_total'))
    if attempted is None or total is None or attempted > total:
        return None
    kind = value.get('wave_kind')
    eligible = value.get('eligible_islands')
    allocation = value.get('allocation')
    next_kind = allocation.get('next_kind') if isinstance(allocation, dict) and allocation.get('schema') == 'sciel-portfolio-allocation/1' else None
    batch = min(workers, total) if type(workers) is int and workers > 0 else None
    return dict(policy='interleaved', attempted=attempted, total=total, remaining=total-attempted,
        initial_batch_total=batch, initial_batch_attempted=min(attempted, batch) if batch is not None else None,
        wave_kind=kind if kind in ('canonical_seed', 'portfolio', 'evolution') else None,
        next_kind=next_kind if next_kind in ('portfolio', 'evolution') else None,
        eligible_islands=len(set(eligible)) if isinstance(eligible, list) and len(eligible) <= 10000
            and all(_int(item) is not None for item in eligible) else None,
        scope='Committed attempted fresh starts, including failures; not successful candidates or measured diversity.')


def runtime_parallel(value):
    """Called only after the enclosing runtime's run/segment identity matches."""
    if not isinstance(value, dict) or value.get('schema') != 'sciel-parallel-runtime/1':
        return None
    phase = value.get('phase')
    return dict(schema=value['schema'], phase=phase if phase in {
        'bootstrap', 'generation', 'conclusion', 'reflection', 'commit', 'paused'} else None,
        **{key: _int(value.get(key)) for key in ('wave', 'workers', 'jobs',
            'pending_calls', 'pending_llm_calls', 'pending_evaluations')},
        **({'pending_tool_calls': _int(value.get('pending_tool_calls'))} if 'pending_tool_calls' in value else {}),
        **({'portfolio': portfolio_progress(value, workers=_int(value.get('workers')))}
           if value.get('portfolio_schedule') == 'interleaved' else {}),
        pending_semantics='Submitted calls, including host-queued work; not active execution slots.')


def parallel_view(start, checkpoint, rows):
    config, source = start.get('config'), 'run_start.config'
    if not isinstance(config, dict):
        config, source = checkpoint.get('config'), 'checkpoint.config'
    config = config if isinstance(config, dict) else {}
    policy = config.get('parallel_search')
    policy = policy if isinstance(policy, dict) else {}
    status = 'enabled' if policy.get('enabled') is True else 'disabled' if policy.get('enabled') is False else 'unknown'
    limits = {key: _int(policy.get(key)) for key in LIMITS}
    waves = {}
    for row in rows:
        if not isinstance(row, dict) or row.get('event') != 'decision' or row.get('policy') != 'parallel_search':
            continue
        wave = _int(row.get('wave'))
        if wave is None:
            continue
        action = row.get('action')
        if action not in {'wave_dispatch', 'io_receipt', 'wave_complete'}:
            continue
        item = waves.setdefault(wave, dict(wave=wave, jobs=None, workers=None,
            status='recorded', bootstrap=None, calls=None, evaluations=None,
            elapsed_seconds=None, cost_total=None, recorded_llm_receipts=0,
            recorded_evaluation_receipts=0, recorded_error_receipts=0))
        if action == 'wave_dispatch':
            item.update(jobs=_int(row.get('jobs')), workers=_int(row.get('workers')),
                status='dispatched', bootstrap=row.get('bootstrap') if type(row.get('bootstrap')) is bool else None)
        elif action == 'wave_complete':
            item.update(status='committed', calls=_int(row.get('calls')), evaluations=_int(row.get('evaluations')),
                elapsed_seconds=_number(row.get('elapsed_seconds')), cost_total=_number(row.get('cost_total')))
            if 'tool_executions' in row:
                item['tool_executions'] = _int(row.get('tool_executions'))
        elif action == 'io_receipt':
            item['recorded_llm_receipts'] += int(row.get('kind') == 'llm')
            item['recorded_evaluation_receipts'] += int(row.get('kind') == 'evaluation')
            item['recorded_error_receipts'] += int(row.get('status') == 'error')
            if row.get('kind') == 'tool_execution':
                item['recorded_tool_receipts'] = item.get('recorded_tool_receipts', 0) + 1
        if row.get('portfolio_schedule') == 'interleaved':
            item['portfolio'] = portfolio_progress(row, workers=limits['workers'])
    history = list(waves.values())
    cursor = checkpoint.get('portfolio_bootstrap')
    cursor = cursor if isinstance(cursor, dict) else {}
    saved_parallel = checkpoint.get('parallel_search')
    saved_parallel = saved_parallel if isinstance(saved_parallel, dict) else {}
    portfolio = portfolio_progress(dict(portfolio_schedule=policy.get('portfolio_schedule'),
        portfolio_attempted=cursor.get('next_island'), portfolio_total=cursor.get('islands'),
        allocation=saved_parallel.get('allocation')), workers=limits['workers'])
    return dict(schema='sciel-parallel-view/1', status=status,
        source=source + '.parallel_search' if policy else None, limits=limits,
        observed_waves=len(history), waves=history[-MAX_WAVES:], history_limit=MAX_WAVES,
        history_limited=len(history) > MAX_WAVES,
        **({'portfolio': portfolio} if policy.get('portfolio_schedule') == 'interleaved' else {}),
        feedback=('When research is enabled, conclusions follow the completed generation wave; due reflection follows ordered conclusion admission before the next wave.'
                  if status == 'enabled' else None),
        notes=['Configured slots are limits, not measured simultaneous execution.',
               'Scientific journal state is published at wave commit; pending runtime work may be newer.',
               'Wave cost_total is cumulative run spend, not the price of that wave.'] if status == 'enabled' else
              ['No parallel execution configuration was recorded; current defaults are not substituted.'] if status == 'unknown' else [])
