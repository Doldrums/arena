import {
  $,
  badge,
  empty,
  esc,
  format,
  mounts,
  nameOf,
  numeric,
  runEffort,
  state,
  statuses,
} from './dashboard-state.js';
import {
  destroyPopulation,
  updatePopulationMap,
  updatePopulationPreview,
} from './dashboard-population.js';
import { destroyWorkflow, renderWorkflow } from './dashboard-tabs.js';
import { destroyPackings } from './packings.js';
import { destroyMethodsDashboard } from './methods.js';
import { applySnapshot, connectStream } from './dashboard-stream.js';
import { destroyPopulationPreview } from './population-preview.js';

export async function getJSON(url, options = {}) {
  const response = await fetch(url, { ...options, cache: 'no-store' });
  if (!response.ok) throw new Error('Data is currently unavailable (' + response.status + ').');
  return response.json();
}

export function connection(text, kind) {
  state.timingConnected = kind === 'connected';
  $('connection').textContent = text;
  $('connection-dot').className = 'connection-dot ' + (kind || '');
  updatePopulationPreview();
  if (state.tab === 'population') updatePopulationMap();
  if (
    state.tab === 'workflow' &&
    state.snapshot?.kind !== 'methods' &&
    state.snapshot?.run.kind !== 'methods'
  )
    renderWorkflow();
}

export function showError(message) {
  $('error-banner').hidden = !message;
  $('error-banner').textContent = message || '';
}

export function preferredRun(runs) {
  const rank = (run) =>
    ['running', 'starting', 'active'].includes(run.status)
      ? 2
      : /(^|\/)outputs\//.test(run.path || '')
        ? 1
        : 0;
  return runs
    .slice()
    .sort(
      (a, b) =>
        rank(b) - rank(a) ||
        String(b.last_modified || '').localeCompare(String(a.last_modified || '')),
    )[0];
}

export function renderRuns() {
  if (state.listUnavailable && !state.runs.length) {
    $('run-list').innerHTML =
      '<div class="sidebar-empty">Run list unavailable. Retrying automatically.</div>';
    return;
  }
  const query = $('run-search').value.toLowerCase();
  const runs = state.runs.filter((run) =>
    (nameOf(run) + ' ' + run.task + ' ' + run.path).toLowerCase().includes(query),
  );
  $('run-count').textContent = state.runs.length;
  $('run-list').innerHTML =
    runs
      .map(
        (run) =>
          '<button class="run-item' +
          (run.id === state.runId ? ' selected' : '') +
          '" data-run="' +
          esc(run.id) +
          '" ' +
          (run.id === state.runId ? 'aria-current="true"' : '') +
          '><span class="run-icon" aria-hidden="true">↗</span><span class="run-info"><span class="run-name">' +
          esc(nameOf(run)) +
          '</span><span class="run-meta"><span class="run-state-dot ' +
          (['running', 'starting'].includes(run.status) ? 'live' : '') +
          '"></span>' +
          esc(statuses[run.status]?.[0] || 'Archive') +
          ' · ' +
          (run.kind === 'methods'
            ? 'Research labs'
            : numeric(run.best_score)
              ? format(run.best_score, 4)
              : '—') +
          '</span>' +
          runEffort(run) +
          '</span></button>',
      )
      .join('') ||
    '<div class="sidebar-empty">' + (query ? 'No matching runs' : 'No runs yet') + '</div>';
}

export function renderEmptyState(unavailable = false) {
  $('empty-title').textContent = unavailable
    ? 'Experiments are temporarily unavailable'
    : 'Watch your search unfold';
  $('empty-message').textContent = unavailable
    ? 'We could not reach the run monitor. We will keep trying, or you can retry now.'
    : 'Waiting for the first experiment log. New runs appear automatically.';
  $('empty-help').hidden = unavailable;
  $('empty-retry').hidden = !unavailable;
}

export async function refreshRuns(initial = false) {
  const request = ++state.listRequest;
  try {
    const result = await getJSON('/api/runs');
    if (request !== state.listRequest) return;
    if (state.listUnavailable) {
      showError('');
      if (state.snapshot && !state.follow) connection('Updates paused', '');
    }
    state.listUnavailable = false;
    renderEmptyState();
    state.runs = result.runs;
    renderRuns();
    if (!state.runId && state.runs.length) {
      const requested = new URL(location.href).searchParams.get('run');
      const selected = state.runs.find((r) => r.id === requested) || preferredRun(state.runs);
      await selectRun(selected.id);
    }
    $('empty-state').hidden = !!state.runs.length;
    if (!state.runs.length) {
      $('dashboard').hidden = true;
      connection('Waiting for a run', 'connected');
    }
  } catch (error) {
    if (request !== state.listRequest) return;
    state.listUnavailable = true;
    if (!state.runs.length && !state.snapshot) {
      renderRuns();
      renderEmptyState(true);
      $('dashboard').hidden = true;
      $('empty-state').hidden = false;
    }
    connection('Disconnected', 'error');
    showError('Unable to connect to the monitor. Reconnecting automatically.');
  }
}

export async function selectRun(id) {
  const request = ++state.runRequest;
  if (state.stream) state.stream.close();
  state.stream = null;
  state.detailRequest++;
  state.runId = id;
  state.snapshot = null;
  state.selected = null;
  state.detail = null;
  state.query = '';
  state.limit = 60;
  const url = new URL(location.href);
  url.searchParams.set('run', id);
  history.replaceState(null, '', url);
  renderRuns();
  showError('');
  $('dashboard').hidden = false;
  $('empty-state').hidden = true;
  destroyPopulation();
  destroyWorkflow();
  if (mounts.packingsMount) {
    destroyPackings(mounts.packingsMount);
    mounts.packingsMount = null;
  }
  if ($('methods-dashboard')) destroyMethodsDashboard($('methods-dashboard'));
  resetRunDisplay();
  $('run-title').textContent = nameOf(
    state.runs.find((r) => r.id === id) || { name: id, path: '' },
  );
  $('tab-content').innerHTML = '<div class="loading">Loading run events…</div>';
  try {
    const snapshot = await getJSON('/api/runs/' + encodeURIComponent(id));
    if (state.runId !== id || state.runRequest !== request) return;
    applySnapshot(snapshot);
    showError('');
    if (state.follow) connectStream();
    else connection('Updates paused', '');
  } catch (error) {
    if (state.runId === id && state.runRequest === request) {
      showError(error.message);
      $('tab-content').innerHTML = empty('Unable to load this run', 'Refresh to try again.');
      $('score-chart').innerHTML = empty('Run data unavailable');
      connection('No data', 'error');
    }
  }
}

export function resetRunDisplay() {
  destroyPopulationPreview($('population-preview'));
  $('dashboard').dataset.kind = 'engine';
  if ($('methods-dashboard')) $('methods-dashboard').hidden = true;
  for (const id of [
    'best-score',
    'evaluations',
    'lessons-count',
    'cost',
    'trials-tab-count',
    'hypotheses-tab-count',
    'lessons-tab-count',
    'tools-tab-count',
    'cells-tab-count',
    'event-count',
  ]) {
    $(id).textContent = '—';
    $(id).removeAttribute('title');
  }
  for (const id of [
    'run-subtitle',
    'score-gain',
    'attempts',
    'hypotheses-count',
    'cost-note',
    'run-path',
    'selected-point-label',
    'chart-start',
    'chart-end',
  ])
    $(id).textContent = '';
  $('run-task').textContent = 'EXPERIMENT';
  $('run-status').innerHTML = badge('pending');
  $('best-score-label').textContent = 'Best score';
  $('best-score-comparison').hidden = true;
  $('best-score-comparison').textContent = '';
  document.querySelector('.metrics').classList.remove('has-reference');
  $('run-note').hidden = true;
  $('runtime-bar').hidden = true;
  $('timing-bar').hidden = true;
  if ($('benchmark-comparison')) $('benchmark-comparison').hidden = true;
  $('score-chart').innerHTML = empty('Loading run data…');
  if ($('chart-outcomes')) {
    $('chart-outcomes').replaceChildren();
    $('chart-outcomes').hidden = true;
  }
  $('activity-feed').innerHTML = empty('Loading events…');
  $('chart-subtitle').textContent = 'Score by iteration';
}

export async function refreshAll() {
  if (state.refreshing) return;
  state.refreshing = true;
  $('refresh-button').disabled = true;
  try {
    await refreshRuns(true);
    if (state.runId) {
      const runId = state.runId,
        snapshot = await getJSON('/api/runs/' + encodeURIComponent(runId));
      if (state.runId === runId) applySnapshot(snapshot);
      if (state.follow) connectStream();
    }
  } catch (error) {
    showError(error.message);
  } finally {
    state.refreshing = false;
    $('refresh-button').disabled = false;
  }
}
