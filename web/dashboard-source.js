import {
  $,
  MAX_ROWS,
  currentTrial,
  empty,
  esc,
  key,
  short,
  sourceIdentity,
  state,
} from './dashboard-state.js';
import { getJSON } from './dashboard-controller.js';
import { resultHistoryDetailHTML } from './dashboard-population.js';

export function codeToolbar() {
  const trials = state.snapshot.trials.slice(-MAX_ROWS);
  const selected = currentTrial();
  if (selected && !trials.includes(selected)) trials.unshift(selected);
  if (state.selected && !trials.some((trial) => key(trial) === state.selected))
    trials.unshift({
      id: state.selected,
      candidate_id: state.selected,
      parent_id: state.detail?.parent_id,
      iteration: '—',
    });
  return (
    '<div class="code-toolbar"><select id="code-select" class="code-select" aria-label="Program to inspect">' +
    trials
      .map(
        (t) =>
          '<option value="' +
          esc(key(t)) +
          '" ' +
          (key(t) === state.selected ? 'selected' : '') +
          '>' +
          esc(
            (t.candidate_id || t.id) + ' ← ' + (t.parent_id || '∅') + ' · iteration ' + t.iteration,
          ) +
          '</option>',
      )
      .join('') +
    '</select><div class="code-actions"><div class="segmented"><button data-code-mode="diff" class="' +
    (state.codeMode === 'diff' ? 'active' : '') +
    '">Diff</button><button data-code-mode="code" class="' +
    (state.codeMode === 'code' ? 'active' : '') +
    '">Candidate</button><button data-code-mode="parent_code" class="' +
    (state.codeMode === 'parent_code' ? 'active' : '') +
    '">Parent</button></div><button class="button" id="copy-code">Copy</button></div></div>'
  );
}

export function renderCode() {
  if (!state.snapshot.trials.length && !state.selected) {
    $('tab-content').innerHTML = empty('No code recorded yet');
    return;
  }
  if (!state.selected) state.selected = key(state.snapshot.trials[0]);
  $('tab-content').innerHTML =
    codeToolbar() + '<div id="code-body"><div class="loading">Loading source code…</div></div>';
  const identity = sourceIdentity();
  if (state.detail?.id === state.selected && state.detailKey === identity) {
    renderCodeBody();
    return;
  }
  if (state.detailPending?.identity === identity) return;
  const request = ++state.detailRequest,
    runId = state.runId,
    candidate = state.selected;
  state.detailPending = { identity };
  getJSON('/api/runs/' + encodeURIComponent(runId) + '/program/' + encodeURIComponent(candidate))
    .then((detail) => {
      if (request !== state.detailRequest || sourceIdentity() !== identity) return;
      state.detail = { ...detail, id: candidate };
      state.detailKey = identity;
      if (state.tab === 'code') renderCodeBody();
    })
    .catch((error) => {
      if (
        request === state.detailRequest &&
        sourceIdentity() === identity &&
        state.tab === 'code' &&
        $('code-body')
      )
        $('code-body').innerHTML = empty('Source code unavailable', error.message);
    })
    .finally(() => {
      if (request === state.detailRequest) state.detailPending = null;
    });
}

export function displayedCode() {
  const detail = state.detail;
  if (!detail) return '';
  const value = detail[state.codeMode];
  return Array.isArray(value) ? value.join('\n') : value || '';
}

export function renderCodeBody() {
  if (!$('code-body') || !state.detail) return;
  const d = state.detail,
    code = displayedCode();
  const sourceNames = {
    checkpoint: 'Saved source',
    'journal.child_code': 'Source from journal',
    'journal.code_fragment': 'Hash-verified source',
    'journal.hash_bound_response': 'Hash-verified source',
  };
  const sourceLabel =
    state.codeMode === 'diff' && d.diff_kind === 'recorded_excerpt'
      ? 'Saved change excerpt · full diff unavailable'
      : sourceNames[d.code_source] || 'Saved source';
  const metadata =
    '<div class="code-meta"><span>' +
    esc(sourceLabel) +
    '</span><span class="mono">' +
    esc(short(d.parent_source_sha256)) +
    ' → ' +
    esc(short(d.source_sha256)) +
    '</span></div>' +
    resultHistoryDetailHTML(d.result_history);
  if (!code) {
    const reason =
      state.codeMode === 'diff'
        ? d.code && d.parent_code
          ? 'No differences between the sources.'
          : 'A diff requires saved source for both the candidate and its parent.'
        : state.codeMode === 'parent_code'
          ? 'Parent source is not available in the journal or checkpoint.'
          : 'No executable source was saved for this attempt.';
    $('code-body').innerHTML = metadata + empty('No data to display', reason);
    $('copy-code').disabled = true;
    return;
  }
  $('copy-code').disabled = false;
  const lines = code.split('\n');
  $('code-body').innerHTML =
    metadata +
    (lines.length > 2000
      ? '<p class="display-limit">Showing the first 2,000 lines. Copy includes the complete saved source.</p>'
      : '') +
    '<pre class="code-view" tabindex="0" aria-label="' +
    (state.codeMode === 'diff' ? 'Program diff' : 'Source code') +
    '">' +
    lines
      .slice(0, 2000)
      .map((line, index) => {
        let cls = '';
        if (state.codeMode === 'diff') {
          if (line.startsWith('@@')) cls = 'hunk';
          else if (line.startsWith('+') && !line.startsWith('+++')) cls = 'add';
          else if (line.startsWith('-') && !line.startsWith('---')) cls = 'remove';
        }
        return (
          '<span class="code-line ' +
          cls +
          '"><span class="line-number">' +
          (index + 1) +
          '</span><span class="line-text">' +
          esc(line) +
          '</span></span>'
        );
      })
      .join('') +
    '</pre>';
}
