import {DOMAIN_STYLE} from './research-map-layout.js';

const number = value => new Intl.NumberFormat('en', {maximumSignificantDigits:7}).format(value);
const known = value => typeof value === 'number' && Number.isFinite(value);

export function renderResearchInspector({doc, root, model, selected, onSelect}) {
  const element = (tag, className, text) => {
    const node = doc.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const append = (...nodes) => root.append(...nodes);
  const paragraph = text => element('p', '', text);
  const heading = text => element('h3', 'map-mini-title', text);
  const link = (text, href, primary=false) => {
    const node = element('a', `map-inspector-link${primary ? ' primary' : ''}`, text);
    node.href = href;
    return node;
  };
  const statPairs = pairs => {
    const list = element('dl', 'map-stats-list');
    for (const [label, value] of pairs) {
      const row = element('div');
      row.append(element('dt', '', label), element('dd', '', known(value) ? number(value) : value));
      list.append(row);
    }
    return list;
  };
  const summary = pairs => {
    const grid = element('div', 'map-summary-numbers');
    for (const [value, label] of pairs) {
      const item = element('div');
      item.append(element('strong', '', known(value) ? number(value) : value), element('span', '', label));
      grid.append(item);
    }
    return grid;
  };
  const nodeList = nodes => {
    const list = element('div', 'map-node-list');
    for (const item of nodes) {
      const button = element('button'); button.type = 'button';
      const dot = element('i');
      dot.style.background = item.participantId === 'sciel' ? '#edb744' : (DOMAIN_STYLE[item.domainId]?.color || '#7e8c9f');
      button.append(dot, element('span', '', item.label), element('small', '', '↗'));
      button.addEventListener('click', () => onSelect(item.id)); list.append(button);
    }
    return list;
  };
  function researchActivity(value) {
    if (!value || value.coverage === 'not_recorded') return;
    append(heading('The research process, recorded'));
    const track = element('div', 'map-progress-track');
    track.append(element('span', '', 'Cells'), element('i'), element('span', '', 'Tools'), element('i'), element('span', '', 'Observations'));
    append(track);
    const counters = value.counts;
    append(statPairs([
      ['Research cells', known(counters.cells_created) ? counters.cells_created : 'Not recorded'],
      ['Cell revisions', known(counters.cell_revisions) ? counters.cell_revisions : 'Not recorded'],
      ['Tools registered', known(counters.tools_registered) ? counters.tools_registered : 'Not recorded'],
      ['Tool executions', known(counters.tool_executions) ? counters.tool_executions : 'Not recorded'],
      ['Observation deliveries', known(counters.shared_observation_deliveries) ? counters.shared_observation_deliveries : 'Not recorded'],
    ]));
    append(element('p', 'map-micro-note', `${value.recordedRuns} of ${value.totalRuns} research runs include process records. ${value.coverage === 'partial' ? 'Partial coverage; these are recorded lower bounds. ' : ''}Counts are events across runs, not unique inventions or evidence of causal improvement.`));
  }
  root.replaceChildren();
  const header = element('div', 'map-inspector-header');
  header.append(element('span', 'map-eyebrow', selected ? 'IN THE LANDSCAPE' : 'INSIDE THE ARENA'));
  if (selected) {
    const back = element('button', 'map-back', '×'); back.type = 'button';
    back.setAttribute('aria-label', 'Clear selection');
    back.addEventListener('click', () => onSelect(null)); header.append(back);
  }
  append(header);
  if (!selected) {
    append(element('h2', '', 'Research that\nbuilds on itself.'), paragraph('A shared landscape for systems that search, experiment, and develop their own research methods.'));
    append(summary([[model.summary.catalogTasks, 'catalog tasks'], [model.summary.participants, 'systems & works']]));
    append(element('p', 'map-micro-note', `${model.summary.domains} research directions · select a cluster or a node.`));
    append(heading('Explore participating systems'));
    const systems = model.nodes.filter(node => node.kind === 'participant');
    const prioritized = ['sciel', 'shinka', 'dgm', 'alphaevolve'];
    const picks = prioritized.map(id => systems.find(node => node.participantId === id)).filter(Boolean);
    append(nodeList(picks));
    append(heading('From exploration to evidence'));
    append(paragraph('Colored fields show the task landscape. Outlined nodes and darker links locate published measurements within it.'));
    append(statPairs([
      ['Research observations', model.summary.researchRuns ?? 'Not published'],
      ['Integration runs', model.summary.integrationRuns ?? 'Not published'],
    ]));
    append(element('p', 'map-micro-note', 'Separate published collections. Select “Recorded activity” to focus on measured outcomes.'));
    append(link('Inspect experiment results', '/experiments/results', true));
    return;
  }
  const kind = {participant:'System / research work', domain:'Research direction', task:'Catalog task', research:'Published experiment evidence'};
  append(element('span', 'map-badge', kind[selected.kind]), element('h2', '', selected.label));
  if (selected.attribution?.display) append(element('p', 'map-attribution', `by ${selected.attribution.display}`));
  if (selected.description) append(paragraph(selected.description));
  if (selected.kind === 'domain') {
    append(summary([[selected.counts.catalogTasks, 'catalog tasks'], [selected.counts.measured, 'measured outcomes']]));
    if (selected.why_it_matters) append(heading('Why this direction matters'), paragraph(selected.why_it_matters));
    const members = model.nodes.filter(node => node.domainId === selected.domainId && node.kind !== 'domain');
    const measured = members.filter(node => node.counts.measured).sort((a,b) => b.counts.measured-a.counts.measured);
    append(heading(measured.length ? 'Recorded research' : 'Explore the questions'));
    append(nodeList((measured.length ? measured : members).slice(0, 5)));
    append(link('Explore all tasks in this direction', `/?domain=${encodeURIComponent(selected.domainId)}`));
  } else if (selected.kind === 'participant') {
    append(summary([[selected.counts.literatureTasks, 'tasks citing this work'], [selected.counts.measured, 'measured outcomes']]));
    if (selected.registrationStatus === 'literature') append(element('p', 'map-micro-note', 'Literature record. A citation link describes the source of a task; it does not mean this system ran it.'));
    const linkedIds = new Set(model.links.filter(edge => edge.target === selected.id && edge.kind === 'measured' &&
      edge.measurements?.some(row=>row.measured>0)).map(edge => edge.source));
    const recorded = model.nodes.filter(node => linkedIds.has(node.id));
    if (recorded.length) append(heading('Measured research'), nodeList(recorded.slice(0, 6)));
    else append(heading('Research links'), paragraph('Explore the tasks connected to this work. Published task measurements have not been linked to this record yet.'));
    researchActivity(selected.selfImprovement);
    if (selected.integrationSummary) {
      append(heading('Published integration runs'), statPairs([
        ['Recorded', selected.integrationSummary.runs], ['Completed', selected.integrationSummary.completed],
        ['Active at publication', selected.integrationSummary.active], ['Failed', selected.integrationSummary.failed],
      ]));
    }
    for (const paper of (selected.papers || []).slice(0, 2)) if (paper.url) append(link(paper.title || 'Read the paper', paper.url));
    if (selected.participantId) append(link('System & research details', `/?view=participants&participant=${encodeURIComponent(selected.participantId)}`));
  } else {
    if (selected.source === 'catalog') append(element('p', 'map-micro-note', selected.executable ? 'An evaluator is declared in the task package. Runtime readiness is verified separately.' : 'Task definition available; the evaluator is being developed.'));
    else append(element('p', 'map-micro-note', 'Native experiment record. Its task and evaluator identity remain separate from catalog packages.'));
    const measurements = selected.measurements || [];
    if (measurements.length) {
      append(heading('Recorded outcomes'));
      for (const measurement of measurements.slice(0, 3)) {
        if (!['minimize','maximize'].includes(measurement.direction)) {
          append(paragraph('Multiple objectives · no scalar ranking. Inspect the paired outcomes in the experiment board.'));
          append(statPairs([['Recorded outcomes', measurement.runs]]));
          continue;
        }
        const best = measurement.direction === 'minimize' ? measurement.bestMin : measurement.bestMax;
        append(statPairs([
          [measurement.metric.replaceAll('_', ' '), known(best) ? number(best) : 'Not measured'],
          ['Measured outcomes', measurement.measured],
          ['Improved on initial score', measurement.improved],
        ]));
        append(element('p', 'map-micro-note', `${measurement.direction === 'minimize' ? 'Lower' : 'Higher'} is better · ${measurement.scope === 'native_result' ? 'Native system protocol' : `Evaluator ${measurement.protocol.slice(0,8)}`}. ${measurement.models.join(' · ') || 'Model not recorded'}.`));
      }
      if (measurements.length > 3) append(element('p', 'map-micro-note', `${measurements.length} separate evaluator groups. All groups are available in the experiment board.`));
    }
    researchActivity(selected.selfImprovement);
    if (selected.kind === 'task') append(link('Open task & evaluator', `/?task=${encodeURIComponent(selected.taskId)}`));
  }
  if (selected.counts.measured) append(link('Inspect experiment results', '/experiments/results', true));
}
