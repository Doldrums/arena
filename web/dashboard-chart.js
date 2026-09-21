import { $, currentTrial, esc, key, mounts, state } from './dashboard-state.js';
import {
  measuredValue,
  metricDifference,
  metricDisplay,
  metricHTML,
  metricLabel,
  metricText,
} from './dashboard-metrics.js';
import { renderChart } from './chart.js';
import { renderTab, switchTab } from './dashboard-tabs.js';

export function renderPlot() {
  if (state.snapshot?.kind === 'methods' || state.snapshot?.run.kind === 'methods') return;
  if (!state.snapshot) return;
  const trial = currentTrial();
  $('selected-point-label').textContent = trial ? 'Iteration ' + trial.iteration : '';
  const displayPoint = (point) => {
    const view = metricDisplay(point),
      parent = metricDisplay(point, 'parent_metric_display', 'parent_score');
    return {
      ...point,
      score: measuredValue(view),
      best_score: measuredValue(metricDisplay(point, 'best_metric_display', 'best_score')),
      parent_score: measuredValue(parent),
      display_delta: metricDifference(view, parent),
      metric_display: view,
      metric_text: view.status === 'measured' ? null : metricText(view, 9),
      metric_note: view.status === 'measured' ? null : view.reason,
      display_status:
        view.status === 'invalid_penalty'
          ? 'Invalid result · penalty'
          : view.status === 'failed'
            ? 'Evaluation failed'
            : view.status === 'unknown'
              ? 'Measurement unavailable'
              : point.status,
    };
  };
  if (mounts.plotProjection?.snapshot !== state.snapshot)
    mounts.plotProjection = {
      snapshot: state.snapshot,
      points: state.snapshot.curves.map(displayPoint),
      programs: (state.snapshot.programs || state.snapshot.curves).map(displayPoint),
    };
  const { points, programs } = mounts.plotProjection;
  const pointIdentity = (point) => point.candidate_id || point.experiment_id || null;
  const selectPoint = (point) => {
    const id = pointIdentity(point);
    if (!id) return;
    state.selected = id;
    state.detail = null;
  };
  const shown = renderChart(
    $('score-chart'),
    points,
    state.axis,
    trial?.iteration,
    (point) => {
      if (pointIdentity(point)) {
        selectPoint(point);
        renderPlot();
        renderTab();
      }
    },
    metricLabel(),
    {
      runKey: state.runId + ':' + (state.snapshot.run.run_id || ''),
      dataVersion: state.snapshot.content_version,
      live: state.snapshot.runtime?.active === true,
      selectedCandidateId: state.selected,
      programs,
      onInspect: (point) => {
        if (point.code_available === false || !pointIdentity(point)) return;
        selectPoint(point);
        switchTab('code');
        renderPlot();
      },
      onLLM: (point) => {
        if (point.llm_available === false) return;
        const query = point.experiment_id || point.candidate_id;
        if (query) switchTab('llm', query);
      },
    },
  );
  $('chart-subtitle').textContent = metricLabel() + ' · measured outcomes only';
  $('chart-metric-label').textContent = 'Best ' + metricLabel().toLowerCase();
  $('chart-start').textContent =
    'Initial ' +
    metricText(metricDisplay(state.snapshot.stats, 'seed_metric_display', 'seed_score'), 4);
  $('chart-end').title =
    'Successful ordinary search evaluations. Excludes seed, bootstrap and failed evaluations.';
  $('chart-end').textContent =
    (state.snapshot.stats.iterations ?? 0) +
    ' iterations · ' +
    (state.snapshot.stats.evaluations ?? 0) +
    ' search evaluations' +
    (shown.total > shown.displayed
      ? ' · ' + shown.displayed + ' of ' + shown.total + ' chart samples'
      : '');
  renderUnmeasuredOutcomes();
}

export function renderUnmeasuredOutcomes() {
  let mount = $('chart-outcomes');
  if (!mount) {
    mount = document.createElement('div');
    mount.id = 'chart-outcomes';
    mount.className = 'chart-outcomes';
    $('score-chart').after(mount);
    mount.addEventListener('click', (event) => {
      const llm = event.target.closest('[data-llm-experiment]');
      if (llm) {
        switchTab('llm', llm.dataset.llmExperiment);
        return;
      }
      const code = event.target.closest('[data-candidate]');
      if (code) {
        state.selected = code.dataset.candidate;
        state.detail = null;
        renderPlot();
        switchTab('code');
      }
    });
  }
  const open = mount.querySelector('details')?.open === true;
  const rows = state.snapshot.trials.filter((row) => measuredValue(metricDisplay(row)) === null);
  const counts = { invalid_penalty: 0, failed: 0, unknown: 0 };
  for (const row of rows) {
    const status = metricDisplay(row).status;
    counts[status in counts ? status : 'unknown']++;
  }
  mount.hidden = !rows.length;
  mount.innerHTML = rows.length
    ? '<details' +
      (open ? ' open' : '') +
      '><summary>Not on the measured-value axis · ' +
      counts.invalid_penalty +
      ' invalid · ' +
      counts.failed +
      ' failed · ' +
      counts.unknown +
      ' unavailable or pending</summary><p>Penalty scores are not physical measurements. Valid zero measurements remain on the chart. All attempts remain in Programs.</p><div class="chart-outcome-list">' +
      rows
        .slice(-60)
        .reverse()
        .map(
          (row) =>
            '<div data-outcome-id="' +
            esc(row.candidate_id || row.id) +
            '" data-metric-status="' +
            esc(metricDisplay(row).status) +
            '"><span class="mono">' +
            esc(row.candidate_id || row.id) +
            '</span><span>' +
            metricHTML(metricDisplay(row)) +
            '</span><span class="card-actions">' +
            (row.code_available
              ? '<button class="inline-link" data-candidate="' +
                esc(key(row)) +
                '">Code &amp; diff ↗</button>'
              : '') +
            '<button class="inline-link" data-llm-experiment="' +
            esc(row.id) +
            '">LLM ↗</button></span></div>',
        )
        .join('') +
      '</div>' +
      (rows.length > 60
        ? '<p>Latest 60 of ' +
          rows.length +
          ' outcomes shown; use Programs to inspect the complete history.</p>'
        : '') +
      '</details>'
    : '';
}
