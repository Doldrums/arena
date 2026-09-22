export const $ = (id) => document.getElementById(id);

export const esc = (value) =>
  String(value ?? '').replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c],
  );

export const numeric = (value) => typeof value === 'number' && Number.isFinite(value);

export const format = (value, digits = 6) => (numeric(value) ? value.toFixed(digits) : '—');

export const percent = (value) =>
  Math.abs(value).toFixed(Math.abs(value) > 0 && Math.abs(value) < 0.01 ? 6 : 2);

export const toleranceLabel = (value) =>
  numeric(value)
    ? value === 0
      ? 'τ = 0 (strict)'
      : 'τ = ' + value.toExponential().replace('e-0', 'e-')
    : String(value || 'Not specified');

export const sourceLink = (url, label) => {
  try {
    const parsed = new URL(url);
    if (['https:', 'http:'].includes(parsed.protocol))
      return (
        '<a href="' +
        esc(parsed.href) +
        '" target="_blank" rel="noopener noreferrer">' +
        esc(label || 'Source') +
        ' ↗</a>'
      );
  } catch {}
  return esc(label || 'Source unavailable');
};

export const delta = (value) =>
  numeric(value)
    ? (value > 0 ? '+' : '') +
      (Math.abs(value) < 0.00001 && value !== 0 ? value.toExponential(3) : value.toFixed(6))
    : '—';

export const short = (value, n = 12) => String(value ?? '').slice(0, n);

export const plural = (n, forms) => forms[n === 1 ? 0 : 1];

export const MAX_ROWS = 600;

export const state = {
  runs: [],
  runId: null,
  snapshot: null,
  contentVersion: null,
  tab: 'trials',
  axis: 'iteration',
  selected: null,
  follow: true,
  stream: null,
  query: '',
  limit: 60,
  codeMode: 'diff',
  detail: null,
  detailKey: null,
  detailPending: null,
  detailRequest: 0,
  refreshing: false,
  listRequest: 0,
  listUnavailable: false,
  runRequest: 0,
  timingReceivedAt: null,
  timingAdvance: 0,
  timingConnected: false,
};

export const scientificIdentity = (snapshot) =>
  JSON.stringify([snapshot?.run?.id, snapshot?.run?.run_id, snapshot?.run?.task_hash]);

export const sourceIdentity = () =>
  JSON.stringify([scientificIdentity(state.snapshot), state.contentVersion, state.selected]);

export const statuses = {
  running: ['Running', 'success'],
  starting: ['Starting', 'blue'],
  stale: ['Heartbeat stale', 'warning'],
  stalled: ['Heartbeat stale', 'warning'],
  interrupted: ['Interrupted', 'warning'],
  completed: ['Completed', 'neutral'],
  historical: ['Archive · unfinished', 'neutral'],
  observing: ['Waiting for events', 'blue'],
  success: ['Evaluated', 'success'],
  evaluated: ['Evaluated', 'success'],
  pending: ['In progress', 'blue'],
  eval_fail: ['Evaluation failed', 'negative'],
  timeout: ['Timed out', 'warning'],
  nochild: ['No candidate', 'neutral'],
  duplicate: ['Duplicate', 'neutral'],
  failed: ['Failed', 'negative'],
  invalid: ['Rejected', 'negative'],
  SUPPORTED: ['Supported', 'success'],
  CONFIRMED: ['Forecast within interval', 'success'],
  REFUTED: ['Forecast outside interval', 'negative'],
  INCONCLUSIVE: ['Inconclusive', 'neutral'],
  active: ['Active', 'success'],
  retired: ['Retired', 'neutral'],
};

statuses.paused = ['Paused', 'neutral'];

statuses.stopped = ['Stopped', 'neutral'];

statuses.remeasurement = ['Remeasurement', 'blue'];

export const phaseNames = {
  attempt: 'Generation started',
  hypothesis: 'Hypothesis recorded',
  outcome: 'Evaluation received',
  conclusion: 'Conclusion recorded',
  reflection: 'Reflection recorded',
  reflection_context: 'Context prepared',
  aux_start: 'Analysis started',
  aux_result: 'Analysis received',
  run_start: 'Run started',
  run_end: 'Run completed',
  iteration: 'Candidate evaluated',
  checkpoint: 'Checkpoint saved',
  checkpoint_restore: 'Checkpoint restored',
  decision: 'Strategy selected',
  population: 'Population updated',
  sh_cut: 'Islands updated',
  postmortem: 'Failure analyzed',
  repeat_search: 'Repeat evaluation',
};

export const badge = (value) => {
  const [label, kind] = statuses[value] || [value || 'No data', 'neutral'];
  return '<span class="badge ' + kind + '">' + esc(label) + '</span>';
};

export const key = (trial) => String(trial.candidate_id || trial.id);

export const empty = (title, body = '') =>
  '<div class="empty-panel"><strong>' + esc(title) + '</strong>' + esc(body) + '</div>';

export const hypothesisText = (hypothesis) =>
  typeof hypothesis === 'string' ? hypothesis : hypothesis?.text || hypothesis?.hypothesis || '';

export const currentTrial = () => state.snapshot?.trials.find((t) => key(t) === state.selected);

export const taskName = (task) =>
  ({
    'oe/circle_packing': 'Circle packing',
    'oe/heilbronn_triangle': 'Heilbronn triangle',
    'oe/function_minimization_oracle': 'Function minimization',
  })[task] ||
  task ||
  'Experiment';

export const runEffort = (run) => {
  const value = run.committed_effort;
  if (!value) return '<span class="run-effort">Effort not recorded</span>';
  const models = new Set(value.configured_models || []);
  const subscription =
    value.billing_mode === 'subscription_unpriced' || value.cost_status === 'subscription_unpriced';
  const reported = value.provider_reported_llm_usd;
  const estimate = value.estimated_llm_usd;
  const price = subscription
    ? reported > 0 ? '≥ $' + reported.toFixed(2) + ' known + subscription · USD unavailable'
      : 'Subscription · USD unavailable'
    : numeric(reported) ? '$' + reported.toFixed(2) + ' provider-reported'
      : numeric(estimate) ? '$' + estimate.toFixed(2) + ' token-rate estimate'
        : 'USD unverified';
  return (
    '<span class="run-effort" title="' +
    esc(value.note) +
    '">' +
    esc(value.ordinary_iterations ?? '—') +
    ' iterations · ' +
    price +
    ' committed' +
    (value.unknown_cost_present ? ' · charges unknown' : '') +
    ' · ' +
    (models.size || 'unknown') +
    ' configured LLMs</span>'
  );
};

export const nameOf = (run) => {
  const path = run.path || run.name;
  const known = [
    ['s04_r2_cycle', 'Research cycle · S04 r2'],
    ['s04_cycle', 'Research cycle · S04'],
    ['s05_r2_pair', 'Memory · S05 r2'],
    ['s05_pair', 'Memory · S05'],
    ['circle_body_engine_r2', 'Circle body · r2'],
    ['circle_body_engine', 'Circle body'],
  ];
  const found = known.find(([part]) => path.includes(part));
  let name = found ? found[1] : run.name || 'Experiment';
  if (path.includes('cards_off')) name += ' / OFF';
  if (path.includes('cards_on')) name += ' / ON';
  return name;
};

export const mounts = {
  plotProjection: null,
  toolsMount: null,
  toolsIdentity: null,
  cellsMount: null,
  cellsIdentity: null,
  packingsMount: null,
  workflowMount: null,
};
