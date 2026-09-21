import { $, MAX_ROWS, state } from './dashboard-state.js';
import {
  connection,
  refreshAll,
  refreshRuns,
  renderRuns,
  selectRun,
} from './dashboard-controller.js';
import { connectStream } from './dashboard-stream.js';
import { renderRuntime, renderTiming } from './dashboard-runtime.js';
import { renderMethodsRun } from './dashboard-architecture.js';
import { renderTab, renderWorkflow, switchTab } from './dashboard-tabs.js';
import { updatePopulationMap } from './dashboard-population.js';
import { renderPlot } from './dashboard-chart.js';
import { displayedCode, renderCode } from './dashboard-source.js';
import { noveltyReceiptHTML } from './dashboard-activity.js';

$('run-list').addEventListener('click', (event) => {
  const button = event.target.closest('[data-run]');
  if (button) selectRun(button.dataset.run);
});

$('run-search').addEventListener('input', renderRuns);

$('refresh-button').addEventListener('click', refreshAll);

$('empty-retry').addEventListener('click', refreshAll);

$('follow-button').addEventListener('click', () => {
  state.follow = !state.follow;
  $('follow-button').setAttribute('aria-pressed', String(state.follow));
  $('follow-button').querySelector('span').textContent = state.follow
    ? 'Pause updates'
    : 'Resume updates';
  $('follow-button').querySelector('svg').innerHTML = state.follow
    ? '<path d="M7 5v14M17 5v14"/>'
    : '<path d="m8 5 11 7-11 7Z"/>';
  if (state.follow) connectStream();
  else {
    state.stream?.close();
    state.stream = null;
    connection('Updates paused', '');
  }
  renderRuntime();
  if (state.snapshot?.kind === 'methods' || state.snapshot?.run.kind === 'methods')
    renderMethodsRun();
  else if (state.tab === 'workflow') renderWorkflow();
  if (state.tab === 'population') updatePopulationMap();
});

document.querySelectorAll('[data-axis]').forEach((button) =>
  button.addEventListener('click', () => {
    state.axis = button.dataset.axis;
    document.querySelectorAll('[data-axis]').forEach((b) => {
      b.classList.toggle('active', b === button);
      b.setAttribute('aria-pressed', String(b === button));
    });
    renderPlot();
  }),
);

document
  .querySelectorAll('[data-tab]')
  .forEach((button) => button.addEventListener('click', () => switchTab(button.dataset.tab)));

document.querySelector('.tabs').addEventListener('keydown', (event) => {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
  const tabs = [...document.querySelectorAll('[data-tab]')],
    index = tabs.indexOf(document.activeElement);
  if (index < 0) return;
  event.preventDefault();
  const next =
    event.key === 'Home'
      ? 0
      : event.key === 'End'
        ? tabs.length - 1
        : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
  switchTab(tabs[next].dataset.tab);
  tabs[next].focus();
});

$('all-events-button').addEventListener('click', () => {
  switchTab('events');
  document
    .querySelector('.research-panel')
    .scrollIntoView({
      behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth',
      block: 'start',
    });
});

$('tab-content').addEventListener('input', (event) => {
  if (event.target.id === 'content-search') {
    state.query = event.target.value;
    state.limit = 60;
    renderTab();
  }
});

$('tab-content').addEventListener('change', (event) => {
  if (event.target.id === 'code-select') {
    state.selected = event.target.value;
    state.detail = null;
    renderPlot();
    renderCode();
  }
});

$('tab-content').addEventListener('keydown', (event) => {
  if (event.target.closest('button,a,input,select,textarea')) return;
  const row = event.target.closest('tr[data-candidate]');
  if (row && (event.key === 'Enter' || event.key === ' ')) {
    event.preventDefault();
    row.click();
  }
});

$('tab-content').addEventListener(
  'toggle',
  (event) => {
    const details = event.target;
    if (!details.matches('details[data-seq]') || !details.open) return;
    const pre = details.querySelector('.event-data');
    if (!pre || pre.textContent) return;
    const record = state.snapshot.events.find((e) => String(e.seq) === details.dataset.seq);
    if (record) {
      if (record.event === 'decision' && record.data?.policy === 'candidate_novelty')
        details.querySelector('.event-receipt').innerHTML = noveltyReceiptHTML(record.data);
      const text = JSON.stringify(record.data, null, 2);
      pre.textContent =
        text.slice(0, 80000) +
        (text.length > 80000 ? '\n… Display truncated at 80,000 characters.' : '');
    }
  },
  true,
);

$('tab-content').addEventListener('click', async (event) => {
  const llmLink = event.target.closest('[data-llm-experiment]');
  if (llmLink) {
    switchTab('llm', llmLink.dataset.llmExperiment);
    return;
  }
  const candidate = event.target.closest('[data-candidate]');
  if (candidate) {
    state.selected = candidate.dataset.candidate;
    state.detail = null;
    renderPlot();
    switchTab('code');
    return;
  }
  const evidence = event.target.closest('[data-evidence]');
  if (evidence) {
    switchTab('hypotheses');
    state.query = evidence.dataset.evidence;
    renderTab();
    return;
  }
  const mode = event.target.closest('[data-code-mode]');
  if (mode) {
    state.codeMode = mode.dataset.codeMode;
    renderCode();
    return;
  }
  if (event.target.closest('[data-more]')) {
    state.limit = Math.min(MAX_ROWS, state.limit + 60);
    renderTab();
    return;
  }
  if (event.target.id === 'copy-code') {
    try {
      await navigator.clipboard.writeText(displayedCode());
      event.target.textContent = 'Copied';
      setTimeout(() => {
        if ($('copy-code')) $('copy-code').textContent = 'Copy';
      }, 1600);
    } catch (error) {
      event.target.textContent = 'Select code manually';
    }
  }
});

for (const id of ['help-button', 'empty-help'])
  $(id).addEventListener('click', () => $('help-dialog').showModal());

for (const id of ['close-help', 'help-done'])
  $(id).addEventListener('click', () => $('help-dialog').close());

new ResizeObserver(() => renderPlot()).observe($('score-chart'));

document
  .querySelectorAll('[data-tab]')
  .forEach((button) => (button.tabIndex = button.dataset.tab === 'trials' ? 0 : -1));

const requestedTab = new URL(location.href).searchParams.get('tab');

if (
  [...document.querySelectorAll('[data-tab]')].some((button) => button.dataset.tab === requestedTab)
)
  switchTab(requestedTab);

setInterval(() => refreshRuns(), 10000);

setInterval(() => renderTiming(), 1000);

refreshRuns(true);
