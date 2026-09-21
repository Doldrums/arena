import { $, key, mounts, numeric, scientificIdentity, state } from './dashboard-state.js';
import { connection, renderRuns, showError } from './dashboard-controller.js';
import { destroyPopulationPreview } from './population-preview.js';
import {
  destroyWorkflow,
  renderCells,
  renderTab,
  renderTools,
  renderWorkflow,
} from './dashboard-tabs.js';
import { suspendPackings } from './packings.js';
import { renderArchitecturePhase, renderMethodsRun } from './dashboard-architecture.js';
import { renderSpend, renderSummary } from './dashboard-summary.js';
import { renderRuntime, renderTiming } from './dashboard-runtime.js';
import { renderBenchmark } from './dashboard-benchmark.js';
import { updatePopulationMap, updatePopulationPreview } from './dashboard-population.js';
import { renderActivity } from './dashboard-activity.js';
import { renderPlot } from './dashboard-chart.js';

export function connectStream() {
  if (state.stream) state.stream.close();
  if (!state.follow || !state.runId) return;
  const runId = state.runId;
  connection('Connecting…', '');
  const source = new EventSource('/api/stream?run=' + encodeURIComponent(runId));
  state.stream = source;
  source.onopen = () => {
    if (state.stream === source) {
      connection('Connected', 'connected');
      showError('');
    }
  };
  source.addEventListener('snapshot', (event) => {
    if (state.stream !== source || state.runId !== runId || !state.follow) return;
    try {
      applySnapshot(JSON.parse(event.data));
      connection('Connected', 'connected');
      showError('');
    } catch (error) {
      showError('Unable to display the update. Previous data is still available.');
      console.error(error);
    }
  });
  source.addEventListener('runtime', (event) => {
    if (state.stream !== source || state.runId !== runId || !state.follow) return;
    try {
      applyRuntime(JSON.parse(event.data));
      connection('Connected', 'connected');
      showError('');
    } catch (error) {
      console.error(error);
    }
  });
  source.addEventListener('unavailable', () => {
    if (state.stream !== source || state.runId !== runId || !state.follow) return;
    connection('Journal unavailable', 'error');
    showError('The run journal is no longer available. Refresh the run list.');
    source.close();
  });
  source.onerror = () => {
    if (state.stream === source && state.follow) {
      connection('Reconnecting…', 'error');
    }
  };
}

export function applySnapshot(snapshot) {
  const previous = state.snapshot;
  // New servers send runtime separately. A bounded signature also accommodates
  // older heartbeat snapshots without serializing the full journal twice.
  const content = (data) =>
    data.content_version ??
    JSON.stringify([
      data.run?.run_id,
      data.stats,
      ...['trials', 'hypotheses', 'lessons', 'events', 'curves'].map((k) => [
        data[k]?.length,
        data[k]?.at(-1),
      ]),
      data.architecture,
      data.research_tools?.summary,
      data.research_tools?.events?.at(-1),
    ]);
  const changed =
    !previous ||
    content(previous) !== content(snapshot) ||
    JSON.stringify(previous.stats) !== JSON.stringify(snapshot.stats) ||
    JSON.stringify(previous.benchmark) !== JSON.stringify(snapshot.benchmark);
  const changedIdentity = previous && scientificIdentity(previous) !== scientificIdentity(snapshot);
  const jobsChanged =
    previous?.research_tools?.jobs?.version !== snapshot.research_tools?.jobs?.version;
  const cellsChanged =
    previous?.research_tools?.pending_cells?.version !==
      snapshot.research_tools?.pending_cells?.version ||
    previous?.research_tools?.pending_cells?.run_status !==
      snapshot.research_tools?.pending_cells?.run_status;
  if (changed || changedIdentity) {
    state.detail = null;
    state.detailKey = null;
    state.detailPending = null;
    state.detailRequest++;
  }
  if (changedIdentity) {
    state.selected = null;
    state.query = '';
  }
  const phaseChanged =
    previous?.runtime?.stage !== snapshot.runtime?.stage ||
    previous?.runtime?.active !== snapshot.runtime?.active;
  state.snapshot = snapshot;
  state.timingReceivedAt = performance.now();
  state.timingAdvance = 0;
  state.contentVersion = content(snapshot);
  const index = state.runs.findIndex((r) => r.id === snapshot.run.id);
  if (index >= 0) {
    state.runs[index] = snapshot.run;
    renderRuns();
  }
  const methods = snapshot.kind === 'methods' || snapshot.run.kind === 'methods';
  $('dashboard').dataset.kind = methods ? 'methods' : 'engine';
  if ($('methods-dashboard')) $('methods-dashboard').hidden = !methods;
  if (methods) {
    destroyPopulationPreview($('population-preview'));
    destroyWorkflow();
    if (mounts.packingsMount) suspendPackings(mounts.packingsMount);
    renderMethodsRun();
    return;
  }
  if (!state.selected) {
    const evaluated = snapshot.trials.filter((t) => numeric(t.score) && t.code_available);
    const best = evaluated.reduce((a, b) => (!a || b.score > a.score ? b : a), null);
    state.selected = best ? key(best) : snapshot.trials[0] ? key(snapshot.trials[0]) : null;
  }
  renderSummary();
  renderRuntime();
  renderTiming();
  renderBenchmark();
  updatePopulationPreview();
  if (changed || changedIdentity) {
    renderActivity();
    renderTab();
  } else if (state.tab === 'workflow') renderWorkflow();
  else if (state.tab === 'tools' && jobsChanged) renderTools();
  else if (state.tab === 'research-cells' && (jobsChanged || cellsChanged)) renderCells();
  else if (state.tab === 'architecture' && phaseChanged) renderArchitecturePhase();
  else if (state.tab === 'population') updatePopulationMap();
  if (changed || changedIdentity) renderPlot();
}

export function applyRuntime(update) {
  if (!state.snapshot || update.run?.id !== state.runId) return;
  if (state.snapshot.kind === 'methods' || state.snapshot.run.kind === 'methods') {
    Object.assign(state.snapshot.run, update.run);
    state.snapshot.runtime = update.runtime;
    if (update.timing) state.snapshot.timing = update.timing;
    renderMethodsRun();
    return;
  }
  const changed =
    state.snapshot.run.status !== update.run.status ||
    state.snapshot.run.status_reason !== update.run.status_reason ||
    state.snapshot.run.stop_detail !== update.run.stop_detail;
  Object.assign(state.snapshot.run, {
    status: update.run.status,
    status_reason: update.run.status_reason,
    stop_detail: update.run.stop_detail,
  });
  state.snapshot.runtime = update.runtime;
  if (update.effort) {
    state.snapshot.effort = update.effort;
    renderBenchmark();
  }
  if (update.research_tool_jobs && state.snapshot.research_tools) {
    const changed =
      state.snapshot.research_tools.jobs?.version !== update.research_tool_jobs.version;
    state.snapshot.research_tools.jobs = update.research_tool_jobs;
    if (changed && state.tab === 'tools') renderTools();
    if (changed && state.tab === 'research-cells') renderCells();
  }
  if (update.research_pending_cells && state.snapshot.research_tools) {
    const prior = state.snapshot.research_tools.pending_cells,
      next = update.research_pending_cells;
    state.snapshot.research_tools.pending_cells = next;
    if (
      (prior?.version !== next.version || prior?.run_status !== next.run_status) &&
      state.tab === 'research-cells'
    )
      renderCells();
  }
  if (update.timing) {
    state.snapshot.timing = { ...state.snapshot.timing, ...update.timing };
    state.timingReceivedAt = performance.now();
    state.timingAdvance = 0;
  }
  if (changed) {
    const run = state.runs.find((r) => r.id === state.runId);
    if (run)
      Object.assign(run, { status: update.run.status, status_reason: update.run.status_reason });
    renderSummary();
    renderRuns();
  } else renderSpend();
  renderRuntime();
  renderTiming();
  // Runtime-only status changes can end the live pulse without rebuilding the
  // graph, its pinned program card, or the source inspector.
  $('score-chart')
    .querySelector('svg')
    ?.classList.toggle('is-live', update.runtime?.active === true);
  if (state.tab === 'architecture') renderArchitecturePhase();
  if (state.tab === 'population') updatePopulationMap();
  if (state.tab === 'workflow') renderWorkflow();
}
