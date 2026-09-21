import {
  $,
  badge,
  delta,
  empty,
  esc,
  hypothesisText,
  key,
  numeric,
  plural,
  state,
} from './dashboard-state.js';
import { matches, more, toolbar } from './dashboard-tabs.js';
import {
  metricBadge,
  metricDisplay,
  metricHTML,
  metricLabel,
  trialDifference,
} from './dashboard-metrics.js';

export function renderTrials() {
  const trials = state.snapshot.trials.filter(matches).slice().reverse();
  let html = toolbar(
    'All attempts are recorded, including failures and duplicates',
    'Search programs',
  );
  if (!trials.length) {
    $('tab-content').innerHTML =
      html + empty('No programs yet', 'Candidate evaluations and changes will appear here.');
    return;
  }
  html +=
    '<div class="table-wrap"><table><thead><tr><th>Iteration</th><th>Program</th><th>Change</th><th>' +
    esc(metricLabel()) +
    '</th><th>Δ vs. parent</th><th>Result</th><th></th></tr></thead><tbody>';
  html += trials
    .slice(0, state.limit)
    .map((t) => {
      const id = key(t);
      const history = state.snapshot.result_history?.by_program?.[t.candidate_id || t.id];
      const repeated =
        history?.output_match_count > 0
          ? '<span class="history-match" title="Exact saved output also occurs in another evaluation; this does not establish algorithm equivalence.">Same recorded output</span>'
          : '';
      return (
        '<tr class="interactive' +
        (id === state.selected ? ' selected' : '') +
        '" data-candidate="' +
        esc(id) +
        '" tabindex="0" aria-label="Open program ' +
        esc(id) +
        '"><td class="trial-index">' +
        esc(t.iteration ?? '—') +
        '</td><td><span class="program-id"><span class="program-icon">⌘</span>' +
        esc(t.candidate_id || t.id) +
        '</span>' +
        repeated +
        '</td><td class="trial-text" title="' +
        esc(hypothesisText(t.hypothesis)) +
        '">' +
        esc(hypothesisText(t.hypothesis) || t.operator || 'No hypothesis recorded') +
        '</td><td class="number">' +
        metricHTML(metricDisplay(t)) +
        '</td><td class="number ' +
        (trialDifference(t) > 0 ? 'positive' : trialDifference(t) < 0 ? 'negative-text' : '') +
        '">' +
        delta(trialDifference(t)) +
        '</td><td>' +
        metricBadge(t) +
        '</td><td class="row-action"><button class="inline-link" data-llm-experiment="' +
        esc(t.id) +
        '" aria-label="LLM request and response for ' +
        esc(t.id) +
        '">LLM ↗</button></td></tr>'
      );
    })
    .join('');
  $('tab-content').innerHTML = html + '</tbody></table></div>' + more(trials.length);
}

export function renderHypotheses() {
  const list = state.snapshot.hypotheses.filter(matches).slice().reverse();
  let html = toolbar(
    'Model predictions and measured outcomes are shown separately',
    'Search hypotheses',
  );
  if (!list.length) {
    $('tab-content').innerHTML =
      html +
      empty(
        'No hypotheses recorded',
        'Hypotheses will appear when the research loop produces its first prediction.',
      );
    return;
  }
  html +=
    '<div class="cards">' +
    list
      .slice(0, state.limit)
      .map((t) => {
        const h = t.hypothesis || {},
          conclusion =
            typeof t.conclusion === 'string'
              ? t.conclusion
              : t.conclusion?.explanation || t.conclusion?.llm?.explanation;
        return (
          '<article class="research-card"><div class="card-meta"><span class="mono">' +
          esc(t.id) +
          '</span><span>· Iteration ' +
          esc(t.iteration) +
          '</span><span>· ' +
          esc(t.parent_id || 'No parent') +
          '</span>' +
          badge(t.forecast_verdict) +
          '</div><h3>' +
          esc(hypothesisText(h)) +
          '</h3>' +
          (h.reasoning ? '<p>' + esc(h.reasoning) + '</p>' : '') +
          '<div class="card-facts"><div>Predicted Δ · score units<strong>[' +
          delta(h.predicted_low) +
          '; ' +
          delta(h.predicted_high) +
          ']</strong></div><div>Measured Δ<strong class="' +
          (trialDifference(t) > 0 ? 'positive' : '') +
          '">' +
          delta(trialDifference(t)) +
          '</strong></div><div>Model confidence<strong>' +
          (numeric(h.confidence) ? Math.round(h.confidence * 100) + '%' : '—') +
          '</strong></div><div>' +
          esc(metricLabel()) +
          '<strong>' +
          metricHTML(metricDisplay(t)) +
          '</strong></div></div>' +
          (conclusion
            ? '<div class="card-subsection"><span class="label">Model analysis</span><p>' +
              esc(conclusion) +
              '</p></div>'
            : '') +
          '<div class="card-actions"><button class="inline-link" data-candidate="' +
          esc(key(t)) +
          '">View code and diff ↗</button><button class="inline-link" data-llm-experiment="' +
          esc(t.id) +
          '">LLM request &amp; response ↗</button></div></article>'
        );
      })
      .join('') +
    '</div>' +
    more(list.length);
  $('tab-content').innerHTML = html;
}

export function reliabilityHTML(view) {
  if (!view)
    return '<section class="research-reliability"><h3>Research reliability</h3><p>Delivery and validation metadata not recorded.</p></section>';
  const memory = view.memory || {},
    conclusions = view.conclusions || {},
    ideas = view.ideas || {},
    latest = memory.latest;
  const count = (value) => (numeric(value) ? String(value) : 'Unknown');
  const fact = (label, value) =>
    '<div><span>' + esc(label) + '</span><strong>' + esc(value) + '</strong></div>';
  const known = (section, value) => (section.recorded ? count(value) : 'Not recorded');
  const diagnostic = (item) =>
    [
      item.reason,
      ...Object.entries(item.diagnostic || {}).map(([key, value]) => key + ': ' + value),
    ]
      .filter(Boolean)
      .join(' · ');
  const rows = (history, columns) =>
    '<div class="table-wrap reliability-table"><table><thead><tr>' +
    columns.map(([title]) => '<th>' + esc(title) + '</th>').join('') +
    '</tr></thead><tbody>' +
    (history || [])
      .slice(-120)
      .reverse()
      .map(
        (item) =>
          '<tr>' + columns.map(([, get]) => '<td>' + esc(get(item)) + '</td>').join('') + '</tr>',
      )
      .join('') +
    '</tbody></table></div>';
  let html =
    '<section class="research-reliability"><h3>Research reliability</h3><p>Stored lessons and delivered advice are different. Counts below use recorded metadata.</p><div class="reliability-metrics">' +
    fact('Stored active', count(memory.stored_active)) +
    fact('Latest ranked', count(latest?.ranked)) +
    fact('Latest selected', count(latest?.selected)) +
    fact('Latest delivered', count(latest?.delivered)) +
    fact('Latest dropped by size', count(latest?.dropped_by_size)) +
    '</div>';
  html +=
    '<p class="reliability-note">' +
    esc(count(memory.zero_delivered_due_size)) +
    ' attempts delivered no ranked lessons with size omissions · ' +
    esc(count(memory.metadata_known)) +
    ' / ' +
    esc(count(memory.attempts)) +
    ' attempts have delivery metadata. This does not imply that all historical context was absent.</p>';
  html +=
    '<details data-reliability-panel="memory"><summary>Memory delivery by attempt</summary>' +
    rows(memory.history, [
      ['Attempt', (item) => item.experiment_id],
      ['Stored active', (item) => count(item.stored_active)],
      ['Ranked', (item) => count(item.ranked)],
      ['Selected', (item) => count(item.selected)],
      ['Delivered', (item) => count(item.delivered)],
      ['Dropped by size', (item) => count(item.dropped_by_size)],
      [
        'Omissions',
        (item) =>
          item.delivery_consistent === false
            ? 'Inconsistent recorded IDs'
            : Object.entries(item.omission_reasons || {})
                .map(([key, value]) => key + ': ' + value)
                .join(', ') || '—',
      ],
    ]) +
    '</details>';
  html +=
    '<div class="reliability-outcomes"><div><h3>Conclusions</h3><p>Final outcomes, after any bounded correction.</p><div class="reliability-metrics">' +
    fact('Parsed', known(conclusions, conclusions.parsed)) +
    fact('Rejected', known(conclusions, conclusions.rejected)) +
    fact('Skipped', known(conclusions, conclusions.skipped)) +
    fact('Corrections scheduled', known(conclusions, conclusions.repairs)) +
    '</div></div>';
  html +=
    '<div><h3>Two-stage ideas</h3><p>Terminal card failures before code generation.</p><div class="reliability-metrics">' +
    fact('Finished', known(ideas, ideas.finished)) +
    fact('Rejected before code', known(ideas, ideas.rejected_before_code)) +
    fact('Invalid cards', known(ideas, ideas.invalid_cards)) +
    fact('Correction exhausted', known(ideas, ideas.repair_exhausted)) +
    fact('Duplicate cards', known(ideas, ideas.duplicates)) +
    '</div></div></div>';
  html +=
    '<details data-reliability-panel="conclusions"><summary>Conclusion diagnostics</summary>' +
    rows(conclusions.history, [
      ['Experiment', (item) => item.experiment_id],
      ['Final status', (item) => item.status],
      ['Corrections', (item) => count(item.repairs)],
      ['Recorded validation diagnostic', diagnostic],
    ]) +
    '</details>';
  html +=
    '<details data-reliability-panel="ideas"><summary>Idea diagnostics</summary>' +
    rows(ideas.history, [
      ['Idea', (item) => item.idea_id],
      ['Final status', (item) => item.status],
      [
        'Code requested',
        (item) => (item.code_requested ? 'Yes' : item.card_requested ? 'No' : 'Unknown'),
      ],
      ['Card validation failures', (item) => count(item.card_rejections)],
      ['Recorded diagnostic', diagnostic],
    ]) +
    '</details>';
  return (
    html + '<p class="reliability-note">' + (view.notes || []).map(esc).join(' ') + '</p></section>'
  );
}

export function renderLessons() {
  const list = state.snapshot.lessons.filter(matches).slice().reverse();
  let html =
    toolbar('Evidence-linked knowledge · original model wording', 'Search lessons') +
    reliabilityHTML(state.snapshot.reliability);
  if (!list.length) {
    $('tab-content').innerHTML =
      html +
      empty(
        'No lessons yet',
        'Lessons will appear after results are analyzed. Experiments may still be running without recorded lessons.',
      );
    return;
  }
  html +=
    '<div class="cards">' +
    list
      .slice(0, state.limit)
      .map((l) => {
        const evidence = Array.isArray(l.evidence_ids) ? l.evidence_ids : [];
        const exposure = numeric(l.exposure_count)
          ? l.exposure_count + ' ' + plural(l.exposure_count, ['time', 'times'])
          : 'Not recorded';
        return (
          '<article class="research-card"><div class="card-meta"><span class="mono">' +
          esc(l.id) +
          '</span><span>· ' +
          esc(
            l.scope === 'global'
              ? 'Global'
              : l.scope === 'branch'
                ? 'Branch ' + (l.branch || '')
                : l.scope || '',
          ) +
          '</span><span>· ' +
          esc(
            l.polarity === 'negative'
              ? 'Negative evidence'
              : l.polarity === 'positive'
                ? 'Positive evidence'
                : l.polarity || 'Observation',
          ) +
          '</span>' +
          badge(l.status || 'active') +
          '</div><h3>' +
          esc(l.rule) +
          '</h3><div class="card-facts"><div>Supporting experiments<div class="card-actions">' +
          evidence
            .map(
              (id) =>
                '<button class="evidence-id" data-evidence="' +
                esc(id) +
                '">' +
                esc(id) +
                '</button>',
            )
            .join('') +
          '</div></div><div>Used in generation<strong>' +
          esc(exposure) +
          '</strong></div></div></article>'
        );
      })
      .join('') +
    '</div>' +
    more(list.length);
  $('tab-content').innerHTML = html;
}
