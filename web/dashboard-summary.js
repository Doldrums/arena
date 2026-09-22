import {
  $,
  badge,
  delta,
  format,
  nameOf,
  numeric,
  plural,
  state,
  taskName,
} from './dashboard-state.js';
import {
  measuredValue,
  metricDifference,
  metricDisplay,
  metricLabel,
  metricStatus,
  metricText,
  referenceComparisonsHTML,
} from './dashboard-metrics.js';

export function renderSummary() {
  const { run, stats, warnings = [] } = state.snapshot;
  $('run-title').textContent = nameOf(run);
  $('run-task').textContent = taskName(run.task).toUpperCase() + ' / EXPERIMENT';
  $('run-status').innerHTML = badge(run.status);
  const start = state.snapshot.events.find((e) => e.event === 'run_start')?.data || {};
  const models = run.models || start.models || [];
  const seed = run.seed ?? start.seed;
  const parts = [
    taskName(run.task),
    ...(seed !== undefined ? ['seed ' + seed] : []),
    ...(models.length ? [models[0].split('/').at(-1)] : []),
  ];
  $('run-subtitle').textContent = parts.join('  ·  ');
  const reference = state.snapshot.benchmark;
  const bestDisplay = metricDisplay(stats, 'best_metric_display', 'best_score'),
    value = measuredValue(bestDisplay);
  $('best-score-label').textContent = metricLabel();
  $('best-score').textContent = numeric(value) ? format(value) : metricStatus(bestDisplay);
  $('best-score').title = numeric(value) ? String(value) : metricText(bestDisplay);
  const comparison = $('best-score-comparison');
  const comparisonHTML = referenceComparisonsHTML(reference, value);
  comparison.hidden = !comparisonHTML;
  document.querySelector('.metrics').classList.toggle('has-reference', !comparison.hidden);
  comparison.innerHTML = comparisonHTML;
  comparison.removeAttribute('title');
  const gain = metricDifference(
    bestDisplay,
    metricDisplay(stats, 'seed_metric_display', 'seed_score'),
  );
  $('score-gain').textContent = numeric(gain)
    ? (gain > 0 ? '↗ ' : '') + delta(gain) + ' from initial program'
    : 'Measured gain unavailable';
  $('score-gain').className = 'metric-foot' + (gain > 0 ? ' positive' : '');
  $('evaluations').textContent = stats.evaluations ?? '—';
  $('evaluations').title =
    'Successful ordinary search evaluations, including successful remeasurements. Excludes seed, bootstrap and failed evaluations.';
  const attempts = stats.attempts ?? stats.iterations ?? 0,
    iterations = stats.iterations ?? 0,
    hypotheses = stats.hypotheses ?? 0,
    reflections = stats.reflections ?? 0;
  $('attempts').textContent =
    attempts +
    ' ' +
    plural(attempts, ['attempt', 'attempts']) +
    ' · ' +
    iterations +
    ' ' +
    plural(iterations, ['iteration', 'iterations']) +
    (numeric(stats.remeasurements)
      ? ' · ' +
        stats.remeasurements +
        ' ' +
        plural(stats.remeasurements, ['remeasurement', 'remeasurements'])
      : '') +
    (numeric(stats.measured_results) ? ' · ' + stats.measured_results + ' measured results' : '') +
    (numeric(stats.repeated_outputs)
      ? ' · ' +
        stats.repeated_outputs +
        (stats.output_resolution ? ' output repeat refusals' : ' exact output repeats')
      : '');
  $('attempts').title =
    'Measured results include seeds, bootstrap, failed evaluations and evaluated retries. Output checks compare saved outputs under a compatible protocol; they do not prove equivalent algorithms.' +
    (stats.output_resolution
      ? ' Near-output refusal requires no canonical score improvement within the task-configured output resolution.'
      : '');
  const memory = state.snapshot.reliability?.memory,
    stored = memory ? memory.stored_active : stats.lessons;
  $('lessons-count').textContent = stored ?? '—';
  $('lessons-unit').textContent = plural(stored, ['lesson', 'lessons']);
  const researchCounts =
    hypotheses +
    ' ' +
    plural(hypotheses, ['hypothesis', 'hypotheses']) +
    ' · ' +
    reflections +
    ' ' +
    plural(reflections, ['reflection attempt', 'reflection attempts']);
  $('hypotheses-count').textContent =
    researchCounts +
    (memory?.latest
      ? ' · ' +
        (numeric(memory.latest.delivered)
          ? memory.latest.delivered + ' delivered in latest prompt'
          : 'Latest delivery not recorded')
      : '');
  renderSpend();
  $('trials-tab-count').textContent = state.snapshot.trials.length;
  $('tools-tab-count').textContent = state.snapshot.research_tools?.summary?.versions ?? 0;
  $('cells-tab-count').textContent = state.snapshot.research_tools?.summary?.cells ?? 0;
  $('hypotheses-tab-count').textContent = state.snapshot.hypotheses.length;
  $('lessons-tab-count').textContent = state.snapshot.lessons.length;
  $('event-count').textContent = state.snapshot.events.length;
  $('run-path').textContent = run.path;
  const notes = [];
  const protocol = state.snapshot.start_protocol;
  if (protocol?.label)
    notes.push(
      protocol.label +
        (protocol.portfolio_seed === true ? ' · portfolio seeding enabled' : '') +
        (protocol.source_candidate ? ' · source ' + protocol.source_candidate : '') +
        '.',
    );
  if (run.stop_detail) notes.push('Stopped: ' + run.stop_detail);
  if (run.engineering_only || run.scope === 'engineering' || (run.path || '').includes('s04_'))
    notes.push(
      'Engineering run: validating the research cycle. These results are not a comparison of method performance.',
    );
  if (warnings.length)
    notes.push(
      warnings.map((w) => (typeof w === 'string' ? w : w.message || JSON.stringify(w))).join(' '),
    );
  $('run-note').hidden = !notes.length;
  $('run-note').textContent = notes.join(' ');
}

export function renderSpend() {
  const { stats, runtime } = state.snapshot;
  const physical = state.snapshot.effort?.total;
  const subscription = physical?.billing_mode === 'subscription_unpriced' ||
    physical?.unpriced_llm_calls > 0 || physical?.cost_status === 'subscription_unpriced' ||
    stats.billing_mode === 'subscription_unpriced' || stats.cost_status === 'subscription_unpriced';
  const unavailable = 'CPU/infrastructure cost unavailable · all-in cost unavailable';
  if (physical) {
    const classified = physical.cost_accounting === 'receipt_provenance';
    const reported = classified ? physical.reported_usd : null;
    const estimated = classified ? physical.estimated_usd : null;
    const unverified = classified ? physical.unattributed_recorded_usd : physical.reported_usd;
    const partial = physical.status !== 'complete';
    $('cost').textContent = subscription
      ? reported > 0 ? '≥ $' + reported.toFixed(4) + ' + subscription' : 'Subscription'
      : numeric(reported) ? (partial ? '≥ ' : '') + '$' + reported.toFixed(4)
        : numeric(estimated) ? '$' + estimated.toFixed(4) + ' estimate' : 'USD unavailable';
    const notes = [String(physical.physical_llm_calls) + ' completed physical LLM calls'];
    if (numeric(reported)) notes.push('Provider-reported LLM charges only');
    if (subscription) notes.push('Subscription · USD unavailable');
    if (numeric(estimated)) notes.push('$' + estimated.toFixed(4) + ' historical token-rate estimate; not billed USD');
    if (numeric(unverified)) notes.push('$' + unverified.toFixed(4) + ' recorded accounting; billing source unverified');
    if (physical.pending_llm_calls) notes.push(physical.pending_llm_calls + ' pending');
    if (physical.unknown_cost_calls) notes.push(physical.unknown_cost_calls + ' charges unknown');
    notes.push(unavailable);
    $('cost-note').textContent = notes.join(' · ');
    $('cost').title = state.snapshot.effort.note;
    return;
  }
  const pending = runtime?.uncommitted_cost;
  const value = pending?.available === true ? pending.known_spend : stats.cost_total;
  const estimated = stats.cost_basis === 'token_estimate' || stats.cost_status === 'estimated';
  const notes = [subscription ? 'Subscription · USD price not supplied'
    : estimated ? 'Historical token-rate estimate; actual billed USD unavailable'
      : 'Recorded accounting; provider billing unverified'];
  if (numeric(value) && (!subscription || value > 0)) notes.push('$' + value.toFixed(4) + (estimated ? ' estimated' : ' recorded'));
  if (pending?.pending_call_count) notes.push(pending.pending_call_count + ' awaiting receipts');
  if (pending?.unknown_call_count) notes.push(pending.unknown_call_count + ' unknown-cost calls');
  else if (stats.unknown_cost_present) notes.push('charges unknown');
  if (pending?.available === false) notes.push('current wave receipts unavailable');
  notes.push(unavailable);
  $('cost').textContent = subscription ? 'Subscription'
    : estimated && numeric(value) ? '$' + value.toFixed(4) + ' estimate' : 'USD unavailable';
  $('cost-note').textContent = notes.join(' · ');
  $('cost').title = 'Journal accounting is preserved as recorded. It does not establish all-in cost or cost savings.';
}
