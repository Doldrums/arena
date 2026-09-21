import { $, badge, empty, esc, key, nameOf, state } from './dashboard-state.js';
import { renderMethodsDashboard } from './methods.js';
import { getJSON } from './dashboard-controller.js';
import {
  architectureGraphHTML,
  bindArchitectureGraph,
  updateArchitectureGraphPhase,
} from './architecture.js';

export function renderMethodsRun() {
  const snapshot = state.snapshot,
    run = snapshot.run;
  $('run-title').textContent = nameOf(run);
  $('run-task').textContent = 'RESEARCH PRACTICES / LABORATORIES';
  $('run-status').innerHTML = badge(run.status);
  $('run-subtitle').textContent = [
    run.task || 'Research campaign',
    snapshot.methods?.identity?.generator?.model || run.models?.[0],
    run.status_reason,
  ]
    .filter(Boolean)
    .join(' · ');
  $('run-path').textContent = run.path || '';
  const warnings = (snapshot.warnings || []).map((value) =>
    typeof value === 'string' ? value : value.message || JSON.stringify(value),
  );
  $('run-note').hidden = !warnings.length;
  $('run-note').textContent = warnings.join(' ');
  let root = $('methods-dashboard');
  if (!root) {
    root = document.createElement('section');
    root.id = 'methods-dashboard';
    root.className = 'methods-dashboard';
    root.setAttribute('aria-label', 'Research labs dashboard');
    document.querySelector('.page-heading').after(root);
  }
  root.hidden = false;
  renderMethodsDashboard(root, snapshot, {
    fetchJSON: getJSON,
    follow: state.follow,
    connected: state.timingConnected,
  });
}

export function renderArchitecturePhase() {
  const runtime = state.snapshot?.runtime;
  if (document.querySelector('.architecture-map')) {
    updateArchitectureGraphPhase($('tab-content'), runtime);
    return;
  }
  const current =
    runtime?.active === true
      ? { generating: 'generation', evaluating: 'evaluation' }[runtime.stage]
      : null;
  document.querySelectorAll('.architecture-stage').forEach((node) => {
    const active = node.dataset.stage === current;
    node.classList.toggle('current', active);
    const status = node.querySelector('.stage-status');
    if (status)
      status.textContent = active
        ? 'Current phase'
        : node.classList.contains('enabled')
          ? 'Enabled'
          : node.classList.contains('disabled')
            ? 'Disabled'
            : 'Not recorded';
  });
}

export function architectureValue(field) {
  if (field.status === 'unknown' || field.value === undefined)
    return '<span class="architecture-unknown">Not recorded</span>';
  if (
    field.value === null &&
    ['budget', 'max_iterations', 'research.max_aux_calls'].includes(field.key)
  )
    return '<span>Unlimited</span>';
  if (field.value === null) return '<span class="architecture-unknown">Not set</span>';
  const value = field.value;
  if (typeof value === 'boolean')
    return (
      '<span class="configuration-flag ' +
      (value ? 'enabled' : 'disabled') +
      '">' +
      (value ? 'Enabled' : 'Disabled') +
      '</span>'
    );
  const display = (item) =>
    item && typeof item === 'object'
      ? item.model
        ? item.model + (item.weight !== undefined ? ' (weight ' + item.weight + ')' : '')
        : Object.entries(item)
            .map(
              ([key, value]) =>
                key +
                ': ' +
                (value && typeof value === 'object' ? JSON.stringify(value) : String(value)),
            )
            .join(' · ')
      : String(item);
  const text = Array.isArray(value)
    ? value.length
      ? value.map(display).join(' · ')
      : 'None'
    : display(value);
  return '<span>' + esc(text) + '</span>';
}

export function renderArchitecture() {
  const architecture = state.snapshot.architecture;
  if (!architecture) {
    $('tab-content').innerHTML = empty(
      'Architecture not recorded',
      'This run has no saved configuration. Current defaults are not substituted for missing values.',
    );
    return;
  }
  const previousSelection = document.querySelector('.architecture-map')?.dataset.selectedNode;
  const configurationOpen = document.querySelector('.architecture-configuration')?.open;
  const inactiveOpen = document.querySelector('.graph-inactive')?.open;
  const stages = architecture.stages || [],
    primary = stages.filter(
      (stage) => !['conclusion', 'reflection', 'retrieval'].includes(stage.id),
    ),
    feedback = stages.filter((stage) =>
      ['conclusion', 'reflection', 'retrieval'].includes(stage.id),
    );
  const runtimeStage =
    state.snapshot.runtime?.active === true
      ? { generating: 'generation', evaluating: 'evaluation' }[state.snapshot.runtime.stage]
      : null;
  const stageHTML = (stage, index) => {
    const status = ['enabled', 'disabled'].includes(stage.status) ? stage.status : 'unknown';
    const statusText = { enabled: 'Enabled', disabled: 'Disabled', unknown: 'Not recorded' }[
      status
    ];
    return (
      '<li class="architecture-stage ' +
      status +
      (runtimeStage === stage.id ? ' current' : '') +
      '" data-stage="' +
      esc(stage.id) +
      '"><div class="stage-top"><span class="stage-number">' +
      String(index + 1).padStart(2, '0') +
      '</span><span class="stage-status">' +
      (runtimeStage === stage.id ? 'Current phase' : statusText) +
      '</span></div><h3>' +
      esc(stage.label) +
      '</h3><p>' +
      esc(stage.description || '') +
      '</p></li>'
    );
  };
  let html =
    '<div class="architecture"><div class="architecture-heading"><div><h2>Architecture of this run</h2><p>' +
    esc(
      architecture.graph
        ? 'What runs at each step, and what changes after an experiment.'
        : architecture.summary || 'Configuration saved with the selected experiment.',
    ) +
    '</p></div><span class="badge ' +
    (architecture.recorded ? 'success' : 'neutral') +
    '">' +
    (architecture.recorded ? 'Recorded configuration' : 'Configuration unavailable') +
    '</span></div>';
  if (architecture.graph) html += architectureGraphHTML(architecture.graph);
  else {
    html +=
      '<div class="architecture-diagram" aria-label="Recorded engine pipeline"><div class="architecture-lane-label">Program evolution</div><ol class="architecture-flow">' +
      primary.map(stageHTML).join('') +
      '</ol>';
    if (feedback.length)
      html +=
        '<div class="architecture-lane-label feedback-label"><span>Research feedback</span><span class="feedback-return">' +
        (feedback.every((stage) => stage.status === 'disabled')
          ? 'Disabled for this run'
          : feedback.every((stage) => stage.status === 'unknown')
            ? 'Not recorded'
            : 'Evidence → knowledge → next proposal') +
        '</span></div><ol class="architecture-flow architecture-feedback">' +
        feedback.map(stageHTML).join('') +
        '</ol>';
    if (architecture.edges?.length)
      html +=
        '<div class="architecture-edges" aria-label="Pipeline connections">' +
        architecture.edges
          .map((edge) => {
            const from = stages.find((s) => s.id === edge.from)?.label || edge.from,
              to = stages.find((s) => s.id === edge.to)?.label || edge.to;
            return (
              '<span>' +
              esc(from) +
              ' <span aria-hidden="true">→</span> ' +
              esc(to) +
              (edge.label ? ' <small>' + esc(edge.label) + '</small>' : '') +
              '</span>'
            );
          })
          .join('') +
        '</div>';
    html += '</div>';
  }
  html +=
    '<details class="architecture-configuration"' +
    (configurationOpen ? ' open' : '') +
    '><summary>Recorded configuration <span>Models, limits and provenance</span></summary><div class="architecture-sections">' +
    (architecture.sections || [])
      .map(
        (section) =>
          '<article class="configuration-card" data-section="' +
          esc(section.id) +
          '"><h3>' +
          esc(section.title) +
          '</h3><dl>' +
          (section.fields || [])
            .map(
              (field) =>
                '<div class="configuration-row" data-field="' +
                esc(field.key) +
                '"><dt>' +
                esc(field.label) +
                '</dt><dd' +
                (field.source ? ' title="Recorded in ' + esc(field.source) + '"' : '') +
                '>' +
                architectureValue(field) +
                (field.note ? '<small>' + esc(field.note) + '</small>' : '') +
                '</dd></div>',
            )
            .join('') +
          '</dl></article>',
      )
      .join('') +
    '</div></details>';
  if (architecture.warnings?.length)
    html +=
      '<div class="architecture-notes">' +
      architecture.warnings.map((note) => '<p>' + esc(note) + '</p>').join('') +
      '</div>';
  html +=
    '<div class="architecture-source">Source: <code>' +
    esc(architecture.source || 'unavailable') +
    '</code><span>Missing values remain unknown; current defaults are not substituted.</span></div></div>';
  $('tab-content').innerHTML = html;
  if (architecture.graph) {
    bindArchitectureGraph($('tab-content'), architecture.graph, previousSelection);
    if (inactiveOpen && document.querySelector('.graph-inactive'))
      document.querySelector('.graph-inactive').open = true;
    renderArchitecturePhase();
  }
}
