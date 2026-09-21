import { $, esc, numeric, state } from './dashboard-state.js';
import { updateMethodsTiming } from './methods.js';

export function elapsed(seconds) {
  if (!numeric(seconds)) return 'Not recorded';
  const value = Math.max(0, Math.floor(seconds));
  return value < 60
    ? value + 's'
    : value < 3600
      ? Math.floor(value / 60) + 'm ' + (value % 60) + 's'
      : Math.floor(value / 3600) + 'h ' + Math.floor((value % 3600) / 60) + 'm';
}

export function clockDuration(seconds) {
  if (!numeric(seconds)) return '—';
  const total = Math.max(0, Math.floor(seconds)),
    h = Math.floor(total / 3600),
    m = Math.floor((total % 3600) / 60),
    s = total % 60;
  return [h, m, s].map((value) => String(value).padStart(2, '0')).join(':');
}

export function renderTiming() {
  if (state.snapshot?.kind === 'methods' || state.snapshot?.run.kind === 'methods') {
    updateMethodsTiming($('methods-dashboard'), {
      follow: state.follow,
      connected: state.timingConnected,
    });
    return;
  }
  const timing = state.snapshot?.timing,
    bar = $('timing-bar');
  bar.hidden = !timing;
  if (!timing) return;
  const runtime = state.snapshot.runtime;
  if (
    timing.live === true &&
    runtime?.active === true &&
    state.follow &&
    state.timingConnected &&
    numeric(state.timingReceivedAt)
  ) {
    // Interpolate between small SSE frames using the browser's monotonic clock,
    // and stop at the heartbeat freshness boundary if updates disappear.
    const freshness =
      numeric(runtime.stale_after_seconds) && numeric(runtime.heartbeat_age_seconds)
        ? Math.max(0, runtime.stale_after_seconds - runtime.heartbeat_age_seconds)
        : 0;
    state.timingAdvance = Math.max(
      state.timingAdvance,
      Math.min(freshness, Math.max(0, (performance.now() - state.timingReceivedAt) / 1000)),
    );
  }
  const advance = timing.live === true ? state.timingAdvance : 0;
  $('run-elapsed').textContent = clockDuration(
    numeric(timing.session?.elapsed_seconds) ? timing.session.elapsed_seconds + advance : null,
  );
  $('hypothesis-age').textContent = clockDuration(
    numeric(timing.last_hypothesis_age_seconds)
      ? timing.last_hypothesis_age_seconds + advance
      : null,
  );
  $('hypothesis-interval').textContent = clockDuration(timing.intervals?.last_seconds);
  $('hypothesis-median').textContent = clockDuration(timing.intervals?.median_seconds);
  $('hypothesis-interval-count').textContent =
    (timing.intervals?.count || 0) + ' measured intervals';
  const last = timing.hypotheses?.at(-1);
  $('last-hypothesis-id').textContent =
    ('last_hypothesis_id' in timing ? timing.last_hypothesis_id : last?.experiment_id) ||
    'Not recorded in this session';
  const observed =
    !String(timing.intervals?.source || '').startsWith('recorded') && last?.source !== 'recorded';
  const start = timing.observed_since ? new Date(timing.observed_since).toLocaleTimeString() : null;
  $('timing-note').textContent =
    (observed
      ? 'Hypothesis arrival times observed by the monitor' +
        (start ? ' since ' + start : '') +
        '. Polling resolution: about 2 seconds.'
      : 'Hypothesis intervals use recorded engine timestamps.') +
    ' Intervals exclude pauses between sessions.' +
    (timing.live === false ? ' Timers are frozen at the last recorded boundary.' : '') +
    ((timing.coverage?.untimed_hypotheses || 0) > 0
      ? ' Earlier hypothesis timings were not recorded.'
      : '') +
    ((timing.coverage?.gaps?.length || 0) > 0 ? ' Gaps in monitoring are excluded.' : '');
}

export function renderRuntime() {
  if (!state.snapshot) return;
  if (state.snapshot.kind === 'methods' || state.snapshot.run.kind === 'methods') return;
  const runtime = state.snapshot.runtime,
    bar = $('runtime-bar');
  bar.hidden = false;
  if (!runtime?.available) {
    bar.innerHTML =
      '<span class="runtime-indicator"></span><span class="runtime-label">Runtime not recorded</span><span class="runtime-detail">This journal has no verified engine heartbeat.</span>';
    return;
  }
  const stages = {
    starting: 'Starting engine',
    seeding: 'Evaluating seed programs',
    generating: 'Generating a candidate',
    evaluating: 'Evaluating a candidate',
    research: 'Updating research knowledge',
    checkpointing: 'Saving checkpoint',
    finished: 'Run finished',
  };
  const fresh = runtime.active === true;
  const parallelStages = {
    bootstrap: 'Initializing portfolio wave',
    generation: 'Generating candidate wave',
    conclusion: 'Writing conclusions',
    reflection: 'Reflecting on wave evidence',
    commit: 'Committing wave',
    paused: 'Parallel wave paused',
  };
  const portfolio = runtime.parallel?.portfolio;
  const interleavedPhase =
    portfolio?.policy === 'interleaved' &&
    ['bootstrap', 'generation'].includes(runtime.parallel?.phase)
      ? {
          canonical_seed: 'Evaluating seed programs',
          portfolio:
            portfolio.attempted === 0 ? 'Creating the initial search batch' : 'Adding fresh starts',
          evolution: 'Evolving initialized islands',
        }[portfolio.wave_kind]
      : null;
  const phase =
    interleavedPhase ||
    parallelStages[runtime.parallel?.phase] ||
    stages[runtime.stage] ||
    runtime.stage ||
    'Stage not recorded';
  const heartbeat = runtime.heartbeat_at
    ? new Date(runtime.heartbeat_at).toLocaleString()
    : 'Not recorded';
  const observed = state.follow ? '' : '<span class="badge warning">View paused</span>';
  bar.innerHTML =
    '<span class="runtime-indicator ' +
    (fresh ? 'live' : '') +
    '"></span><span class="runtime-label">' +
    esc(phase) +
    '</span>' +
    observed +
    '<span class="runtime-detail" title="' +
    esc(heartbeat) +
    '">Heartbeat ' +
    (numeric(runtime.heartbeat_age_seconds)
      ? esc(elapsed(runtime.heartbeat_age_seconds)) + ' ago'
      : esc(heartbeat)) +
    '</span>' +
    (runtime.pid ? '<span class="runtime-detail mono">PID ' + esc(runtime.pid) + '</span>' : '') +
    '<span class="runtime-reason">' +
    esc(runtime.reason || '') +
    '</span>';
  const parallel = runtime.parallel;
  if (parallel?.schema === 'sciel-parallel-runtime/1') {
    const count = (value) => (numeric(value) ? String(value) : 'unknown');
    const detail = document.createElement('span');
    detail.className = 'runtime-detail runtime-parallel';
    detail.title =
      'Submitted calls include host-queued work; these are not measured executing slots.';
    detail.textContent =
      (fresh ? '' : 'Recorded · ') +
      'Wave ' +
      count(parallel.wave) +
      ' · ' +
      (parallel.phase || 'phase unknown') +
      ' · ' +
      count(parallel.workers) +
      ' workers · pending LLM ' +
      count(parallel.pending_llm_calls) +
      ' / evaluation ' +
      count(parallel.pending_evaluations) +
      (Object.hasOwn(parallel, 'pending_tool_calls')
        ? ' / tool ' + count(parallel.pending_tool_calls)
        : '');
    bar.append(detail);
    if (portfolio?.policy === 'interleaved') {
      const progress = document.createElement('span');
      progress.className = 'runtime-detail runtime-portfolio';
      progress.title =
        portfolio.scope ||
        'Committed attempts include failed fresh starts; they are not successful candidates.';
      progress.textContent =
        (fresh ? '' : 'Recorded · ') +
        ({
          canonical_seed: 'Seed evaluation · ',
          portfolio: 'Fresh-start wave · ',
          evolution: 'Evolution wave · ',
        }[portfolio.wave_kind] || '') +
        'Initial batch ' +
        count(portfolio.initial_batch_attempted) +
        '/' +
        count(portfolio.initial_batch_total) +
        ' attempted · Fresh starts ' +
        count(portfolio.attempted) +
        '/' +
        count(portfolio.total) +
        ' · ' +
        count(portfolio.remaining) +
        ' remaining' +
        (numeric(portfolio.eligible_islands)
          ? ' · ' + count(portfolio.eligible_islands) + ' islands eligible for evolution'
          : '') +
        (parallel.phase === 'commit' && portfolio.next_kind
          ? ' · Next ' + (portfolio.next_kind === 'portfolio' ? 'fresh starts' : 'evolution')
          : '');
      bar.append(progress);
    }
  }
}
