import {
  measuredValue,
  metricDisplay,
  metricHTML,
  metricLabel,
  metricStatus,
  referenceGapText,
} from './dashboard-metrics.js';
import {
  $,
  delta,
  esc,
  format,
  numeric,
  sourceLink,
  state,
  toleranceLabel,
} from './dashboard-state.js';
import { effortDetailsHTML, publishedEffortHTML, renderEffort } from './effort.js';
import { renderPlot } from './dashboard-chart.js';
import { switchTab } from './dashboard-tabs.js';

export function benchmarkTableHTML(reference) {
  const view = metricDisplay(state.snapshot.stats, 'best_metric_display', 'best_score'),
    current = measuredValue(view);
  const tolerance = reference.run_tolerance,
    knownTolerance = numeric(tolerance) && tolerance >= 0;
  const bound = numeric(current) && reference.current_value === current;
  const references = Array.isArray(reference.references) ? reference.references : [];
  const matched = references.filter((row) => knownTolerance && row.tolerance === tolerance);
  const other = references.filter((row) => !knownTolerance || row.tolerance !== tolerance);
  const id =
    typeof state.snapshot.best_candidate_id === 'string' ? state.snapshot.best_candidate_id : null;
  const currentRow = { current: true, value: current };
  const renderRow = (row, comparable) => {
    if (row.current)
      return (
        '<tr class="benchmark-current" data-current-solution data-comparable="' +
        comparable +
        '"><td><strong>This run · best</strong><small>' +
        (id
          ? '<button class="inline-link mono" data-benchmark-candidate="' +
            esc(id) +
            '" aria-label="Open best program ' +
            esc(id) +
            '">' +
            esc(id) +
            ' ↗</button>'
          : 'Program ID not recorded') +
        '</small></td><td class="number published-value" title="' +
        esc(numeric(current) ? String(current) : view.reason || '') +
        '">' +
        (numeric(current) ? esc(String(current)) : metricHTML(view)) +
        '</td><td>' +
        esc(knownTolerance ? toleranceLabel(tolerance) : 'Not recorded') +
        '</td><td>' +
        (comparable ? 'This solution' : 'Not ranked') +
        '</td><td>' +
        effortDetailsHTML(state.snapshot.effort?.to_best) +
        '</td><td>Saved evaluator result<small>' +
        (numeric(current)
          ? comparable
            ? 'Position among the selected references at the same tolerance.'
            : 'Comparable measurement contract not available.'
          : esc(metricStatus(view))) +
        '</small></td></tr>'
      );
    const gap =
      bound && comparable && numeric(row.value) && row.value > 0
        ? ((row.value - current) / row.value) * 100
        : null;
    const method =
      {
        ai_search_framework: 'AI search',
        ai_assisted: 'AI-assisted',
        human: 'Human method',
        unknown: 'Method not classified',
      }[row.method_classification] || 'Method not classified';
    return (
      '<tr data-reference-row><td>' +
      esc(row.name) +
      '</td><td class="number published-value">' +
      esc(row.value_label || String(row.value)) +
      '</td><td>' +
      esc(toleranceLabel(row.tolerance)) +
      '</td><td class="number">' +
      (numeric(gap) ? esc(referenceGapText(gap)) : '—') +
      (!comparable ? '<small>Not comparable</small>' : '') +
      '</td><td>' +
      publishedEffortHTML(row.effort) +
      '</td><td>' +
      sourceLink(row.source_url, row.source_name) +
      '<small title="' +
      esc(row.classification_basis || '') +
      '">' +
      esc(row.status || '') +
      ' · ' +
      sourceLink(row.classification_source_url, method) +
      '</small></td></tr>'
    );
  };
  const group = (label, rows, comparable) =>
    rows.length
      ? '<tbody data-comparability="' +
        (comparable ? 'matched' : 'unranked') +
        '"><tr class="benchmark-group"><th colspan="6" scope="colgroup">' +
        esc(label) +
        '</th></tr>' +
        rows.map((row) => renderRow(row, comparable)).join('') +
        '</tbody>'
      : '';
  const ordered = [...matched, ...(knownTolerance && bound ? [currentRow] : [])].sort(
    (a, b) => (numeric(b.value) ? b.value : -Infinity) - (numeric(a.value) ? a.value : -Infinity),
  );
  return (
    '<div class="table-wrap benchmark-table"><table><thead><tr><th>Result</th><th>' +
    esc(reference.metric || metricLabel()) +
    '</th><th>Constraint tolerance</th><th>This run vs reference</th><th>Discovery effort</th><th>Evidence</th></tr></thead>' +
    group(
      'Same tolerance as this run · ' + toleranceLabel(tolerance) + ' · ordered by recorded value',
      ordered,
      true,
    ) +
    group(
      knownTolerance
        ? 'Different or unrecorded tolerance · no ranking against this run'
        : 'Tolerance not recorded · no ranking',
      other,
      false,
    ) +
    (!(knownTolerance && bound)
      ? group('Current solution · not ranked', [currentRow], false)
      : '') +
    '</table></div>'
  );
}

export function renderBenchmark() {
  let panel = $('benchmark-comparison');
  if (!panel) {
    panel = document.createElement('section');
    panel.id = 'benchmark-comparison';
    panel.className = 'benchmark-comparison';
    panel.setAttribute('aria-label', 'Published reference and effort comparison');
    document.querySelector('.metrics').after(panel);
  }
  const reference = state.snapshot.benchmark,
    effort = state.snapshot.effort;
  const start = state.snapshot.events.find((e) => e.event === 'run_start')?.data || {};
  const target = reference?.task_target ?? start.known_best;
  panel.hidden = !reference && !numeric(target) && !effort;
  const referenceOpen = panel.querySelector('.benchmark-disclosure')?.open === true;
  const disclosureKey = (node) =>
    JSON.stringify([
      node.closest('tr')?.querySelector('td')?.textContent ||
        node.closest('section')?.querySelector('.effort-title')?.textContent ||
        'reference',
      node.querySelector('summary')?.textContent,
    ]);
  const openDetails = new Set([...panel.querySelectorAll('details[open]')].map(disclosureKey));
  let html = '';
  if (reference && numeric(reference.value)) {
    const current = measuredValue(
      metricDisplay(state.snapshot.stats, 'best_metric_display', 'best_score'),
    );
    const comparable =
      numeric(current) &&
      reference.current_value === current &&
      numeric(reference.run_tolerance) &&
      reference.run_tolerance >= 0 &&
      reference.reference_tolerance === reference.run_tolerance;
    const gap = comparable ? current - reference.value : null;
    const source = sourceLink(reference.source_url, reference.source_label || 'Published source');
    html =
      '<div class="benchmark-heading"><strong>' +
      esc(reference.label || 'Published reference') +
      '</strong>' +
      source +
      '</div><div class="benchmark-values"><div>This run<strong>' +
      format(current, 9) +
      '</strong></div><div>' +
      esc(reference.metric || 'Reference value') +
      '<strong>' +
      format(reference.value, 9) +
      '</strong></div><div>Gap to reference<strong>' +
      delta(gap) +
      '</strong></div><div>Of reference<strong>' +
      (comparable && reference.value !== 0
        ? ((current / reference.value) * 100).toFixed(4) + '%'
        : '—') +
      '</strong></div></div>';
    if (reference.note) html += '<p class="benchmark-note">' + esc(reference.note) + '</p>';
    html += benchmarkTableHTML(reference);
  }
  if (html)
    html =
      '<details class="benchmark-disclosure"' +
      (referenceOpen ? ' open' : '') +
      '><summary>' +
      esc(reference.label || 'Tolerance-matched reference') +
      '</summary>' +
      html +
      '</details>';
  if (effort) html += renderEffort(effort);
  if (numeric(target))
    html +=
      '<div class="benchmark-target"><span>Task target' +
      (reference?.target_metric ? ' · ' + esc(reference.target_metric) : '') +
      '</span><strong>' +
      esc(target) +
      '</strong><span>Recorded task target; separate from the published reference.</span></div>';
  panel.innerHTML = html;
  panel.querySelectorAll('details').forEach((node) => {
    if (openDetails.has(disclosureKey(node))) node.open = true;
  });
  panel.onclick = (event) => {
    const candidate = event.target.closest('[data-benchmark-candidate]');
    if (candidate) {
      state.selected = candidate.dataset.benchmarkCandidate;
      state.detail = null;
      renderPlot();
      switchTab('code');
    }
  };
}
