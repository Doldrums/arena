import { $, MAX_ROWS, esc, mounts, scientificIdentity, state } from './dashboard-state.js';
import { renderResearchTools } from './research_tools.js';
import { getJSON } from './dashboard-controller.js';
import { renderResearchCells } from './research_cells.js';
import { renderPackings, suspendPackings } from './packings.js';
import { destroyWorkFlow, renderWorkFlow } from './workflow.js';
import { destroyPopulation, renderPopulation } from './dashboard-population.js';
import { renderHypotheses, renderLessons, renderTrials } from './dashboard-records.js';
import { renderEvents } from './dashboard-activity.js';
import { renderLLMCalls } from './llm_calls.js';
import { learningHTML } from './learning.js';
import { renderArchitecture } from './dashboard-architecture.js';
import { renderCode } from './dashboard-source.js';

export function switchTab(tab, query = '') {
  state.tab = tab;
  state.query = query;
  state.limit = 60;
  const url = new URL(location.href);
  url.searchParams.set('tab', tab);
  history.replaceState(null, '', url);
  document.querySelectorAll('[data-tab]').forEach((button) => {
    const active = button.dataset.tab === tab;
    button.classList.toggle('active', active);
    button.setAttribute('aria-selected', String(active));
    button.tabIndex = active ? 0 : -1;
  });
  $('tab-content').setAttribute('aria-labelledby', 'tab-' + tab);
  renderTab();
}

export function toolbar(description, placeholder) {
  return (
    '<div class="table-toolbar"><span>' +
    esc(description) +
    '</span>' +
    (placeholder
      ? '<input id="content-search" type="search" placeholder="' +
        esc(placeholder) +
        '" aria-label="' +
        esc(placeholder) +
        '" value="' +
        esc(state.query) +
        '">'
      : '') +
    '</div>'
  );
}

export function more(total) {
  return total > state.limit
    ? state.limit >= MAX_ROWS
      ? '<p class="display-limit">Showing the latest ' +
        MAX_ROWS +
        ' matching records of ' +
        total +
        '. Use search to narrow the history.</p>'
      : '<button class="load-more" data-more>Show more · ' + (total - state.limit) + '</button>'
    : '';
}

export function matches(value) {
  return !state.query || JSON.stringify(value).toLowerCase().includes(state.query.toLowerCase());
}

export function renderTools() {
  const identity = scientificIdentity(state.snapshot);
  if (!mounts.toolsMount || mounts.toolsIdentity !== identity) {
    mounts.toolsMount = document.createElement('div');
    mounts.toolsIdentity = identity;
  }
  if (mounts.toolsMount.parentNode !== $('tab-content'))
    $('tab-content').replaceChildren(mounts.toolsMount);
  renderResearchTools(mounts.toolsMount, state.snapshot.research_tools, {
    runId: state.runId,
    identity,
    fetchJSON: getJSON,
    onProgram: (id) => {
      state.selected = id;
      state.detail = null;
      switchTab('code');
    },
  });
}

export function renderCells() {
  const identity = scientificIdentity(state.snapshot);
  if (!mounts.cellsMount || mounts.cellsIdentity !== identity) {
    mounts.cellsMount = document.createElement('div');
    mounts.cellsIdentity = identity;
  }
  if (mounts.cellsMount.parentNode !== $('tab-content'))
    $('tab-content').replaceChildren(mounts.cellsMount);
  renderResearchCells(mounts.cellsMount, state.snapshot.research_tools, {
    runId: state.runId,
    identity,
    fetchJSON: getJSON,
    onProgram: (id) => {
      state.selected = id;
      state.detail = null;
      switchTab('code');
    },
  });
}

export function renderPackingGallery() {
  if (!mounts.packingsMount) mounts.packingsMount = document.createElement('div');
  if (mounts.packingsMount.parentNode !== $('tab-content'))
    $('tab-content').replaceChildren(mounts.packingsMount);
  renderPackings(mounts.packingsMount, {
    runId: state.runId,
    identity: scientificIdentity(state.snapshot),
    version: state.contentVersion,
    fetchJSON: getJSON,
    onProgram: (id) => {
      state.selected = id;
      state.detail = null;
      switchTab('code');
    },
  });
}

export function destroyWorkflow() {
  if (mounts.workflowMount) destroyWorkFlow(mounts.workflowMount);
  mounts.workflowMount = null;
}

export function renderWorkflow() {
  if (!state.snapshot) return;
  if (!mounts.workflowMount) mounts.workflowMount = document.createElement('div');
  if (mounts.workflowMount.parentNode !== $('tab-content'))
    $('tab-content').replaceChildren(mounts.workflowMount);
  renderWorkFlow(mounts.workflowMount, {
    runId: state.runId,
    identity: scientificIdentity(state.snapshot),
    version: state.contentVersion,
    fetchJSON: getJSON,
    follow: state.follow,
    connected: state.timingConnected,
    live: state.snapshot.runtime?.active === true,
  });
}

export function renderTab() {
  if (!state.snapshot) return;
  if (state.snapshot.kind === 'methods' || state.snapshot.run.kind === 'methods') return;
  if (state.tab !== 'population') destroyPopulation();
  if (state.tab !== 'workflow') destroyWorkflow();
  if (state.tab !== 'packings' && mounts.packingsMount) suspendPackings(mounts.packingsMount);
  const focused = document.activeElement?.id;
  const selection = focused === 'content-search' ? document.activeElement.selectionStart : null;
  const opened = [...$('tab-content').querySelectorAll('details[open]')].map((d) => d.dataset.seq);
  const researchOpened = [
    ...$('tab-content').querySelectorAll('details[data-reliability-panel][open]'),
  ].map((d) => d.dataset.reliabilityPanel);
  const researchFocused =
    document.activeElement?.tagName === 'SUMMARY'
      ? document.activeElement.parentElement?.dataset.reliabilityPanel
      : null;
  if (state.tab === 'trials') renderTrials();
  else if (state.tab === 'hypotheses') renderHypotheses();
  else if (state.tab === 'lessons') renderLessons();
  else if (state.tab === 'events') renderEvents();
  else if (state.tab === 'workflow') renderWorkflow();
  else if (state.tab === 'tools') renderTools();
  else if (state.tab === 'research-cells') renderCells();
  else if (state.tab === 'packings') renderPackingGallery();
  else if (state.tab === 'llm')
    renderLLMCalls($('tab-content'), {
      runId: state.runId,
      identity: scientificIdentity(state.snapshot),
      version: state.contentVersion,
      query: state.query,
      fetchJSON: getJSON,
    });
  else if (state.tab === 'population') renderPopulation();
  else if (state.tab === 'learning')
    $('tab-content').innerHTML = learningHTML(state.snapshot.learning);
  else if (state.tab === 'architecture') renderArchitecture();
  else renderCode();
  if (focused === 'content-search' && $('content-search')) {
    $('content-search').focus({ preventScroll: true });
    $('content-search').setSelectionRange(selection, selection);
  }
  if (state.tab === 'events')
    $('tab-content')
      .querySelectorAll('details')
      .forEach((d) => {
        d.open = opened.includes(d.dataset.seq);
      });
  if (state.tab === 'lessons')
    $('tab-content')
      .querySelectorAll('details[data-reliability-panel]')
      .forEach((d) => {
        d.open = researchOpened.includes(d.dataset.reliabilityPanel);
        if (researchFocused === d.dataset.reliabilityPanel)
          d.querySelector('summary')?.focus({ preventScroll: true });
      });
}
