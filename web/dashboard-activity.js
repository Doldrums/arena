import { $, empty, esc, numeric, phaseNames, state } from './dashboard-state.js';
import { matches, more, toolbar } from './dashboard-tabs.js';

export function researchOutcome(event) {
  const phase = event.phase || event.event,
    data = event.data || {};
  if (!['conclusion', 'reflection'].includes(phase)) return null;
  const name = phase === 'conclusion' ? 'Conclusion' : 'Reflection';
  const error = data.error != null || data.lesson_error != null;
  if (error || ['rejected', 'failed', 'error'].includes(data.status))
    return { title: name + ' rejected', color: 'negative-text', icon: '!' };
  if (data.status === 'invalid')
    return { title: name + ' invalid', color: 'negative-text', icon: '!' };
  if (data.status === 'skipped') return { title: name + ' skipped', color: '', icon: '−' };
  if (data.status !== 'parsed') return { title: name + ' recorded', color: '', icon: '·' };
  if (phase === 'reflection') {
    if (!data.applied || typeof data.applied !== 'object')
      return { title: 'Reflection not applied', color: '', icon: '·' };
    const changed = data.changed === true || data.comparison_reviews_changed === true;
    return {
      title: changed
        ? 'Knowledge revised'
        : data.changed === false
          ? 'Reflection accepted · no change'
          : 'Reflection accepted',
      color: 'green',
      icon: '✓',
    };
  }
  if (data.lesson_admission?.status === 'suppressed')
    return { title: 'Conclusion recorded · lessons suppressed', color: '', icon: '·' };
  if (data.verdict_matches_observation === false)
    return { title: 'Conclusion recorded · verdict mismatch', color: 'yellow', icon: '!' };
  return {
    title: 'Conclusion recorded',
    color: data.llm ? 'green' : '',
    icon: data.llm ? '✓' : '·',
  };
}

export function eventTitle(event) {
  if (event.event === 'research_tool') {
    const phase = event.data?.phase || event.phase;
    const data = event.data || event;
    if (phase === 'invocation_result' && data.result_schema === 'sciel-tool-result/1')
      return 'Tool check · ' + (data.tool_result_status || 'outcome unrecorded');
    if (phase === 'replay_result' && data.replay_policy === 'independent_execution')
      return (
        'Independent execution · ' +
        (data.matched === true
          ? 'verified; measurements may differ'
          : data.matched === false
            ? 'criterion not met'
            : 'result recorded')
      );
    const labels = {
      registered: 'Tool version registered',
      published: 'Tool published for sharing',
      llm_start: 'Tool model request started',
      llm_result: 'Tool model response recorded',
      invocation_started: 'Tool invocation pending',
      invocation_result: 'Tool execution · ' + (event.data?.status || 'outcome unrecorded'),
      context_prepared: 'Tool context prepared',
      child_link: 'Tool receipts linked to program',
      episode_finished: 'Tool episode finished',
      rejected: 'Tool proposal rejected',
      cell_created: 'Research question opened',
      cell_activated: 'Research cell scheduled',
      cell_revision: 'Research cell revision recorded',
      replay_result:
        'Independent replay · ' +
        (event.data?.matched === true
          ? 'reproduced'
          : event.data?.matched === false
            ? 'not reproduced'
            : 'result recorded'),
      adopted: 'Tool adopted for further trials',
      post_adoption_use: 'Tool invoked after adoption',
      post_adoption_attempt: 'Post-adoption tool attempt',
    };
    return labels[phase] || 'Tool event recorded';
  }
  if (event.event === 'decision' && event.data?.policy === 'candidate_novelty') {
    const data = event.data;
    return (
      'Candidate novelty · ' +
      (data.remeasurement === true
        ? 'eligible remeasurement'
        : data.accept === false
          ? 'duplicate rejected'
          : data.accept === true
            ? 'candidate accepted'
            : 'decision recorded')
    );
  }
  if (event.event === 'decision' && event.data?.policy === 'output_novelty') {
    const data = event.data;
    return data.status === 'exact_recorded_repeat'
      ? 'Exact recorded output repeated' +
          (data.remeasurement ? ' · remeasurement' : ' · mutation not admitted')
      : data.status === 'non_improving_near_repeat'
        ? 'Near output without improvement' +
          (data.remeasurement ? ' · remeasurement' : ' · mutation not admitted')
        : data.status === 'unsupported'
          ? 'Output identity unavailable · evaluation retained'
          : 'New recorded output';
  }
  return (
    researchOutcome(event)?.title ||
    phaseNames[event.phase] ||
    phaseNames[event.event] ||
    event.summary ||
    event.phase ||
    event.event
  );
}

export function renderActivity() {
  const relevant = state.snapshot.events.filter(
    (e) =>
      ['hypothesis', 'outcome', 'conclusion', 'reflection'].includes(e.phase) ||
      ['run_end', 'run_start', 'sh_cut', 'checkpoint_restore'].includes(e.event) ||
      (e.event === 'research_tool' &&
        [
          'registered',
          'published',
          'invocation_result',
          'child_link',
          'cell_created',
          'replay_result',
          'adopted',
          'post_adoption_use',
        ].includes(e.data?.phase || e.phase)),
  );
  $('activity-feed').innerHTML =
    relevant
      .slice(-7)
      .reverse()
      .map((e) => {
        const phase = e.phase || e.event;
        const outcome = researchOutcome(e);
        const color = outcome?.color || (phase === 'hypothesis' ? 'blue' : '');
        const icon = outcome?.icon || (phase === 'hypothesis' ? '?' : '·');
        const label =
          e.data?.experiment_id ||
          (numeric(e.iteration) ? 'Iteration ' + e.iteration : 'Event ' + e.seq);
        const detail = e.data?.error_detail || e.data?.lesson_error_detail;
        const subtitle = label + (detail ? ' · ' + detail : '');
        return (
          '<div class="activity-item" data-event-seq="' +
          esc(e.seq) +
          '"><span class="activity-icon ' +
          color +
          '">' +
          icon +
          '</span><div class="activity-copy"><div class="activity-title">' +
          esc(eventTitle(e)) +
          '</div><div class="activity-subtitle" title="' +
          esc(subtitle) +
          '">' +
          esc(subtitle) +
          '</div></div><span class="activity-seq">' +
          esc(e.seq) +
          '</span></div>'
        );
      })
      .join('') || empty('Waiting for events');
}

export function renderEvents() {
  const list = state.snapshot.events.filter(matches).slice().reverse();
  let html = toolbar('Events in journal order', 'Search events');
  html +=
    '<div class="event-list">' +
    list
      .slice(0, state.limit)
      .map(
        (e) =>
          '<details class="event-row" data-seq="' +
          esc(e.seq) +
          '"><summary><span class="number">' +
          esc(e.seq) +
          '</span><span class="event-title">' +
          esc(eventTitle(e)) +
          '</span><span class="badge neutral">' +
          esc(e.phase || e.event) +
          '</span></summary><div class="event-receipt"></div><pre class="event-data"></pre></details>',
      )
      .join('') +
    '</div>' +
    more(list.length);
  $('tab-content').innerHTML = html;
}

export function noveltyReceiptHTML(data) {
  const neighbors = Array.isArray(data.neighbors) ? data.neighbors.slice(0, 10) : [];
  const verdict =
    data.remeasurement === true
      ? 'Eligible remeasurement'
      : data.accept === false
        ? 'Duplicate rejected'
        : data.accept === true
          ? 'Candidate accepted'
          : 'Decision recorded';
  const kind =
    {
      sha256: 'Exact source SHA256',
      ast: 'Structural AST',
      embedding: 'Code embedding (advisory)',
      new: 'No previous source',
    }[data.match_kind] ||
    data.match_kind ||
    'Not recorded';
  let html =
    '<section class="novelty-receipt"><h3>' +
    esc(verdict) +
    '</h3><p>SHA256 → AST → code embedding · final source after repair and entry-point grafting.</p><dl class="novelty-facts">' +
    [
      ['Match', kind],
      ['Matched program', data.matched_program_id || 'None recorded'],
      ['Reason', data.reason || 'Not recorded'],
    ]
      .map(([label, value]) => '<div><dt>' + esc(label) + '</dt><dd>' + esc(value) + '</dd></div>')
      .join('') +
    '</dl>' +
    '<p>Embedding cosine is advisory; similar code is not proof of equivalent behavior. Remeasurements are recorded separately from new mutations.</p>';
  if (!neighbors.length) html += '<p>No nearest-source details were recorded.</p>';
  for (const neighbor of neighbors) {
    if (!neighbor || typeof neighbor !== 'object') continue;
    const difference = typeof neighbor.ast_diff === 'string' ? neighbor.ast_diff : null;
    const truncated = neighbor.ast_diff_truncated === true || (difference?.length || 0) > 12000;
    html +=
      '<article class="novelty-neighbor"><h4>' +
      esc(neighbor.program_id || 'Program ID not recorded') +
      ' <span>cosine ' +
      esc(numeric(neighbor.similarity) ? neighbor.similarity.toFixed(6) : 'not recorded') +
      '</span></h4>' +
      (difference === null
        ? '<p>AST diff unavailable in this record.</p>'
        : difference === ''
          ? '<p>No structural AST differences.</p>'
          : '<pre class="novelty-ast-diff" tabindex="0" aria-label="Recorded AST difference">' +
            esc(difference.slice(0, 12000)) +
            '</pre>') +
      (truncated
        ? '<p class="novelty-truncated">AST diff truncated; inspect the source for the complete program.</p>'
        : '') +
      '</article>';
  }
  if (Array.isArray(data.neighbors) && data.neighbors.length > 10)
    html += '<p>Showing the first 10 recorded neighbors.</p>';
  return html + '<p class="novelty-original">Original journal record</p></section>';
}
