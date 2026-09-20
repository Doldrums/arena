// Saved measurements only. Method-state comparisons never become a task best.
const progressViews = new WeakMap();
const SVG_NS = 'http://www.w3.org/2000/svg';
const MAX_RECORDS = 200;
const finite = value => (typeof value === 'number' || typeof value === 'string' && value.trim() !== '') && Number.isFinite(Number(value)) ? Number(value) : null;
const array = value => Array.isArray(value) ? value : [];
const label = value => value == null ? 'Not recorded' : String(value);
const metricLabel = value => ({sum_radii: 'Sum of radii', combined_score: 'Combined evaluation score', evaluation_score: 'Evaluation score'}[value] || label(value));
// Inspection retains the complete round-trip measurement; axis labels have a
// separate width budget so responsive charts do not clip leading digits.
const valueLabel = value => finite(value) === null ? 'Not measured' : String(Number(value));
function compactTick(value, step, width = 8) {
  const decimals = Math.max(0, Math.min(12, 1 - Math.floor(Math.log10(Math.abs(step) || 1))));
  const fixed = String(Number(value.toFixed(decimals)));
  if (fixed.length <= width && (value === 0 || Number(fixed) !== 0)) return fixed;
  for (let precision = 3; precision >= 0; precision--) {
    const scientific = value.toExponential(precision).replace(/\.?0+e/, 'e').replace('e+', 'e');
    if (scientific.length <= width) return scientific;
  }
  return value.toExponential(0).replace('e+', 'e');
}
function tickFormat(low, high) {
  const step = (high - low) / 4;
  const labels = Array.from({length: 5}, (_, index) => compactTick(low + step * index, step));
  // A narrow range near a large baseline may need more digits than the margin
  // can hold. Show explicit deltas rather than five identical rounded ticks.
  const offset = new Set(labels).size < labels.length ? low : null;
  return {offset, label: value => offset === null ? compactTick(value, step) : 'Δ' + compactTick(value - offset, step, 7)};
}
const shortId = value => String(value || '').slice(0, 12);
const atNumber = value => finite(value) ?? (Number.isFinite(Date.parse(value)) ? Date.parse(value) / 1000 : null);

function element(view, tag, className, text) {
  const node = view.document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = label(text);
  return node;
}
function svgNode(view, tag, attributes = {}, text) {
  const node = view.document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
  if (text !== undefined) node.textContent = String(text);
  return node;
}
function chronological(rows) {
  return array(rows).filter(row => row && typeof row.id === 'string').map((row, index) => ({row, index})).sort((a, b) => {
    const aSeq = finite(a.row.registration_seq), bSeq = finite(b.row.registration_seq);
    if (aSeq !== null && bSeq !== null && aSeq !== bSeq) return aSeq - bSeq;
    const aAt = atNumber(a.row.at), bAt = atNumber(b.row.at);
    return aAt !== null && bAt !== null && aAt !== bAt ? aAt - bAt : a.index - b.index;
  }).map(item => item.row).slice(-MAX_RECORDS);
}
function solutionPoint(row, quality) {
  if (row.valid !== true || typeof row.program_id !== 'string' || !row.program_id) return null;
  const native = typeof row.native_metric === 'string' && row.native_metric;
  const value = finite(native ? row.native_score : row.score);
  if (value === null) return null;
  return {row, kind: 'solution', metric: native || quality.metric || 'evaluation_score', treatment: value, control: null};
}
function armValue(row, arm) {
  const records = array(row.results?.[arm]);
  if (arm === 'treatment' && row.valid_treatment === false) return null;
  if (records.some(item => !item || item.status && item.status !== 'ok' || !item.measurement || item.measurement.valid !== true)) return null;
  const displayKey = 'display_' + arm + '_score';
  return finite(Object.hasOwn(row, displayKey) ? row[displayKey] : row.native_metric ? row['native_' + arm + '_score'] : row[arm + '_score']);
}
function toolPoint(row) {
  const metric = Object.hasOwn(row, 'display_metric') ? row.display_metric : row.native_metric || row.metric || row.criterion?.metric;
  const knownMetric = typeof metric === 'string' && metric ? metric : null;
  return {row, kind: 'experiment', metric: knownMetric, control: knownMetric ? armValue(row, 'control') : null, treatment: knownMetric ? armValue(row, 'treatment') : null};
}
function prepare(methods) {
  const quality = methods.quality || {};
  const solutions = chronological(methods.solutions).map(row => solutionPoint(row, quality)).filter(Boolean);
  const solutionExperiments = new Set(array(methods.solutions).map(row => row.experiment_id).filter(Boolean));
  const experiments = chronological(methods.experiments).filter(row => row.purpose !== 'solution' && !solutionExperiments.has(row.id)).map(toolPoint);
  return {solutions, experiments, proposals: chronological(methods.proposals), quality};
}
function makeButton(view, title, action) {
  const node = element(view, 'button', '', title);
  node.type = 'button'; node.addEventListener('click', action);
  return node;
}
function mount(root) {
  const view = {root, document: root.ownerDocument, mode: null, metrics: {}, points: new Map(), calls: new Map(), selected: null, preview: null};
  view.panel = element(view, 'section', 'methods-progress');
  view.panel.setAttribute('aria-label', 'Search progress');
  const heading = element(view, 'header', 'methods-progress-heading');
  const title = element(view, 'div');
  title.append(element(view, 'h2', '', 'Search progress'));
  view.subtitle = element(view, 'p'); title.append(view.subtitle);
  const modes = element(view, 'div', 'methods-progress-modes'); modes.setAttribute('aria-label', 'Measurement view');
  view.buttons = new Map();
  for (const [mode, name] of [['solutions', 'Solutions'], ['experiments', 'Tool experiments']]) {
    const button = makeButton(view, name, () => {view.mode = mode; view.preview = null; draw(view);});
    button.dataset.progressMode = mode; view.buttons.set(mode, button); modes.append(button);
  }
  heading.append(title, modes);
  const toolbar = element(view, 'div', 'methods-progress-toolbar');
  view.metricName = element(view, 'strong', 'methods-progress-metric');
  const metricLabelNode = element(view, 'label', 'methods-progress-metric-select');
  metricLabelNode.append(element(view, 'span', '', 'Metric'));
  view.metricSelect = element(view, 'select'); view.metricSelect.setAttribute('aria-label', 'Chart metric');
  view.metricSelect.addEventListener('change', () => {view.metrics[view.mode] = view.metricSelect.value; view.preview = null; draw(view);});
  metricLabelNode.append(view.metricSelect); view.metricControl = metricLabelNode;
  view.legend = element(view, 'div', 'methods-progress-legend'); toolbar.append(view.metricName, metricLabelNode, view.legend);
  view.plot = element(view, 'div', 'methods-progress-plot');
  view.svg = svgNode(view, 'svg', {viewBox: '0 0 1000 280', role: 'group', 'aria-label': 'Saved measurements'});
  view.empty = element(view, 'div', 'methods-progress-empty');
  view.tooltip = element(view, 'div', 'methods-progress-tooltip'); view.tooltip.hidden = true; view.tooltip.setAttribute('role', 'tooltip');
  view.plot.append(view.svg, view.empty, view.tooltip);
  view.footer = element(view, 'p', 'methods-progress-scope');
  view.activity = element(view, 'div', 'methods-progress-activity');
  view.activitySummary = element(view, 'p');
  view.activityDots = element(view, 'div', 'methods-progress-calls'); view.activityDots.setAttribute('aria-label', 'Model calls in displayed history');
  view.activity.append(view.activitySummary, view.activityDots);
  view.panel.append(heading, toolbar, view.plot, view.footer, view.activity); root.replaceChildren(view.panel);
  view.plot.addEventListener('pointerleave', () => {if (!view.selected && !view.plot.contains(view.document.activeElement)) hidePreview(view);});
  view.panel.addEventListener('keydown', event => {
    if (event.key === 'Escape') {view.selected = null; hidePreview(view); view.points.forEach(node => node.classList.remove('is-selected'));}
  });
  const ResizeObserver = view.document.defaultView.ResizeObserver;
  if (ResizeObserver) {
    view.observer = new ResizeObserver(() => {
      if (!root.isConnected) {view.observer.disconnect(); return;}
      if (view.data && Math.abs(Math.max(340, view.plot.clientWidth || 1000) - view.width) > 1) draw(view);
    });
    view.observer.observe(root);
  }
  return view;
}
function hidePreview(view) {view.preview = null; view.tooltip.hidden = true;}
function addTip(view, name, text) {
  const row = element(view, 'div', 'methods-progress-tip-row'); row.append(element(view, 'span', '', name), element(view, 'strong', '', text)); view.tooltip.append(row);
}
function preview(view, point) {
  view.preview = point.row.id;
  const row = point.row; view.tooltip.replaceChildren();
  view.tooltip.append(element(view, 'h3', '', point.kind === 'solution' ? row.program_id : 'Experiment ' + shortId(row.id)));
  if (row.question) view.tooltip.append(element(view, 'p', '', String(row.question).slice(0, 360)));
  addTip(view, 'Lab', label(row.lab_id));
  addTip(view, 'Metric', point.metric ? metricLabel(point.metric) : 'Not recorded');
  if (point.kind === 'experiment') {
    addTip(view, 'Control', valueLabel(point.control)); addTip(view, 'Treatment', valueLabel(point.treatment));
    addTip(view, 'Criterion', row.passed === true ? 'Met on assigned inputs' : row.passed === false ? 'Not met' : 'Not recorded');
    if (row.criterion?.metric) addTip(view, 'Effect criterion', metricLabel(row.criterion.metric) + ' · ' + label(row.criterion.direction) + ' · minimum ' + valueLabel(row.criterion.minimum_effect));
    if (array(row.treatment).length) addTip(view, 'Treatment versions', array(row.treatment).map(shortId).join(', '));
    if (array(row.control).length) addTip(view, 'Control versions', array(row.control).map(shortId).join(', '));
  } else {
    addTip(view, 'Evaluated value', valueLabel(point.treatment));
    addTip(view, 'Confirmation', row.confirmed === true ? 'Confirmed' : 'No independent confirmation recorded');
  }
  if (row.at != null) addTip(view, 'Recorded', label(row.at));
  view.tooltip.append(element(view, 'small', '', 'Click or press Enter to inspect the saved record.'));
  view.tooltip.hidden = false;
  view.tooltip.style.left = point.x > view.width * .61 ? '12px' : 'auto';
  view.tooltip.style.right = point.x > view.width * .61 ? 'auto' : '12px';
}
function focusPoint(view, point, group) {
  const row = point.row;
  group.dataset.progressPoint = row.id;
  group.setAttribute('tabindex', '0'); group.setAttribute('role', 'button');
  group.setAttribute('aria-label', (point.kind === 'solution' ? row.program_id + ', value ' + valueLabel(point.treatment) : 'Experiment ' + shortId(row.id) + ', control ' + valueLabel(point.control) + ', treatment ' + valueLabel(point.treatment)) + ', ' + metricLabel(point.metric) + ', lab ' + label(row.lab_id));
  const open = () => {view.selected = row.id; view.points.forEach((node, id) => node.classList.toggle('is-selected', id === row.id)); preview(view, point); view.onSelect?.(point.kind, row.id);};
  group.addEventListener('pointerenter', () => {if (!view.selected) preview(view, point);});
  group.addEventListener('focus', () => preview(view, point));
  group.addEventListener('click', open);
  group.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') {event.preventDefault(); open();}
    if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
      event.preventDefault(); const points = [...view.points.values()], index = points.indexOf(group);
      points[index + (event.key === 'ArrowRight' ? 1 : -1)]?.focus({preventScroll: true});
    }
  });
  if (view.selected === row.id) group.classList.add('is-selected');
  view.points.set(row.id, group);
}
function partial(view, key, visibleCount) {
  const methods = view.methods;
  return methods.summary?.history_complete === false || methods.projection?.history_complete === false ||
    (finite(methods.summary?.[key]) ?? visibleCount) > visibleCount || array(methods[key]).length > MAX_RECORDS;
}
function renderActivity(view) {
  const rows = view.data.proposals;
  let cost = 0, known = 0;
  for (const row of rows) {const n = finite(row.cost); if (n !== null && n >= 0) {cost += n; known++;}}
  const scope = partial(view, 'proposals', rows.length) ? 'Displayed window: ' : '';
  view.activitySummary.textContent = scope + rows.length + ' model calls · ' + view.data.experiments.length + ' tool experiments · ' + view.data.solutions.length + ' evaluated solutions' +
    (rows.length ? ' · Known call spend $' + cost.toFixed(4) + (known < rows.length ? ' · ' + (rows.length - known) + ' costs unknown' : '') : '');
  const active = view.document.activeElement?.dataset?.progressProposal;
  const nextCalls = new Map();
  for (const row of rows) {
    const costValue = finite(row.cost);
    const description = 'Model call ' + (row.index == null ? shortId(row.id) : '#' + row.index) + ' · ' + label(row.lab_id) + ' · ' + label(row.status) + ' · ' + (costValue === null ? 'cost unknown' : '$' + costValue.toFixed(4));
    const dot = view.calls.get(row.id) || makeButton(view, '', () => view.onSelect?.('proposal', row.id));
    dot.className = 'methods-progress-call' + (['refused', 'invalid', 'failed'].includes(row.status) ? ' is-refused' : '');
    if (!view.calls.has(row.id)) dot.classList.add('is-new');
    dot.dataset.progressProposal = row.id; dot.title = description; dot.setAttribute('aria-label', description);
    view.activityDots.append(dot);
    nextCalls.set(row.id, dot);
    if (active === row.id) dot.focus({preventScroll: true});
  }
  for (const [id, node] of view.calls) if (!nextCalls.has(id)) node.remove();
  view.calls = nextCalls;
  if (active && !nextCalls.has(active)) view.buttons.get(view.mode).focus({preventScroll: true});
}
function draw(view) {
  const isSolution = view.mode === 'solutions';
  const all = view.data[view.mode];
  const metrics = [...new Set(all.map(point => point.metric).filter(Boolean))];
  const currentMetric = metrics.includes(view.metrics[view.mode]) ? view.metrics[view.mode] : metrics[0] || null;
  view.metrics[view.mode] = currentMetric;
  const metricSignature = metrics.join('\u0000');
  if (view.metricSignature !== metricSignature) {
    view.metricSelect.replaceChildren(...metrics.map(metric => {const node = element(view, 'option', '', metricLabel(metric)); node.value = metric; return node;}));
    view.metricSignature = metricSignature;
  }
  view.metricSelect.value = currentMetric || ''; view.metricControl.hidden = metrics.length < 2;
  view.metricName.textContent = currentMetric ? metricLabel(currentMetric) : 'Awaiting measurements';
  view.buttons.forEach((node, mode) => {node.setAttribute('aria-pressed', String(mode === view.mode)); node.classList.toggle('is-active', mode === view.mode);});
  view.subtitle.textContent = isSolution ? 'Actual valid Program evaluations' : 'Paired comparisons on assigned inputs' + (!view.data.solutions.length ? ' · No evaluated solutions yet' : '');
  const selectedPoints = all.map((point, index) => ({...point, index})).filter(point => point.metric === currentMetric || !point.metric);
  const values = selectedPoints.flatMap(point => [point.control, point.treatment]).filter(value => value !== null);
  const hasValues = values.length > 0;
  const truncated = partial(view, isSolution ? 'solutions' : 'experiments', isSolution ? array(view.methods.solutions).length : array(view.methods.experiments).length);
  const direction = view.data.quality.direction;
  const drawBest = isSolution && ['max', 'min'].includes(direction);
  view.legend.replaceChildren();
  const legends = isSolution ? [['solution', 'Evaluated solution'], ...(drawBest ? [['best', truncated ? 'Best in displayed history' : 'Best observed']] : [])] : [['control', 'Control'], ['treatment', 'Treatment']];
  for (const [kind, name] of legends) {const item = element(view, 'span', 'methods-progress-key ' + kind, name); view.legend.append(item);}
  const activePoint = view.document.activeElement?.dataset?.progressPoint;
  view.svg.replaceChildren(); view.points.clear();
  view.width = Math.max(340, view.plot.clientWidth || 1000);
  view.svg.setAttribute('viewBox', '0 0 ' + view.width + ' 280');
  const LEFT = 78, RIGHT = view.width - 28, TOP = 20, BOTTOM = 218;
  let low = hasValues ? Math.min(...values) : 0, high = hasValues ? Math.max(...values) : 1;
  const pad = high === low ? Math.max(Math.abs(high) * .04, .01) : (high - low) * .1;
  low -= pad; high += pad;
  const axis = tickFormat(low, high);
  const y = value => BOTTOM - (value - low) / (high - low) * (BOTTOM - TOP);
  const x = index => all.length <= 1 ? (LEFT + RIGHT) / 2 : LEFT + index / (all.length - 1) * (RIGHT - LEFT);
  if (hasValues) for (let i = 0; i <= 4; i++) {
    const value = low + (high - low) * i / 4, pos = y(value);
    view.svg.append(svgNode(view, 'line', {x1: LEFT, x2: RIGHT, y1: pos, y2: pos, class: 'methods-progress-grid'}), svgNode(view, 'text', {x: LEFT - 14, y: pos + 4, 'text-anchor': 'end', class: 'methods-progress-axis', 'data-progress-y-tick': 'true'}, axis.label(value)));
  }
  view.svg.append(svgNode(view, 'line', {x1: LEFT, x2: RIGHT, y1: BOTTOM, y2: BOTTOM, class: 'methods-progress-axis-line'}));
  const ticks = new Set([0, all.length - 1]);
  for (let i = 1; i < 5 && all.length > 5; i++) ticks.add(Math.round((all.length - 1) * i / 5));
  if (all.length) for (const index of [...ticks].sort((a, b) => a - b)) view.svg.append(svgNode(view, 'text', {x: x(index), y: 258, 'text-anchor': 'middle', class: 'methods-progress-axis'}, index + 1));
  view.svg.append(svgNode(view, 'text', {x: (LEFT + RIGHT) / 2, y: 278, 'text-anchor': 'middle', class: 'methods-progress-axis'}, (isSolution ? 'Solution' : 'Experiment') + ' order · displayed history'));
  if (drawBest && hasValues) {
    let best = null, path = '';
    for (const point of selectedPoints) {
      if (point.treatment === null) continue;
      best = best === null ? point.treatment : direction === 'min' ? Math.min(best, point.treatment) : Math.max(best, point.treatment);
      path += (path ? ' H ' + x(point.index) + ' V ' + y(best) : 'M ' + x(point.index) + ' ' + y(best));
    }
    view.svg.append(svgNode(view, 'path', {d: path, class: 'methods-progress-best', 'data-progress-best': 'true'}));
  }
  let unmeasured = 0;
  for (const point of selectedPoints) {
    point.x = x(point.index);
    const group = svgNode(view, 'g', {class: 'methods-progress-point'});
    if (point.control !== null && point.treatment !== null && !isSolution) group.append(svgNode(view, 'line', {x1: point.x, x2: point.x, y1: y(point.control), y2: y(point.treatment), class: 'methods-progress-pair'}));
    for (const arm of isSolution ? ['treatment'] : ['control', 'treatment']) {
      if (point[arm] === null) continue;
      group.append(svgNode(view, 'circle', {cx: point.x, cy: y(point[arm]), r: arm === 'control' ? 5.5 : 3.5, class: 'methods-progress-dot ' + (isSolution ? 'solution' : arm), 'data-value': point[arm], 'data-arm': arm}));
    }
    if (point.control === null && point.treatment === null) {
      unmeasured++;
      group.append(svgNode(view, 'path', {d: `M ${point.x - 3} 230 l 6 6 m -6 0 l 6 -6`, class: 'methods-progress-unmeasured'}));
    }
    const hitWidth = Math.min(20, (RIGHT - LEFT) / Math.max(1, all.length - 1));
    group.append(svgNode(view, 'rect', {x: point.x - hitWidth / 2, y: TOP, width: hitWidth, height: 220, class: 'methods-progress-hit'}));
    focusPoint(view, point, group); view.svg.append(group);
  }
  if (unmeasured) view.svg.append(svgNode(view, 'text', {x: LEFT - 14, y: 237, 'text-anchor': 'end', class: 'methods-progress-axis'}, 'Unmeasured'));
  view.empty.hidden = hasValues;
  view.empty.replaceChildren(element(view, 'strong', '', isSolution ? 'No evaluated solutions yet' : 'No valid tool measurements yet'), element(view, 'span', '', isSolution ? 'Tool trials and model calls remain visible in the activity below.' : 'Each completed control and treatment will appear at its own experiment.'));
  const scope = truncated ? 'Partial / bounded history. ' : '';
  view.footer.textContent = scope + (isSolution ? 'Only bound, valid Program evaluations. ' + (drawBest ? (direction === 'min' ? 'Lower' : 'Higher') + ' is better; the line follows ' + (truncated ? 'the displayed window.' : 'observed evaluations.') : 'No best line: optimization direction not recorded.') : 'Pairs belong to separate experiments; different labs, inputs and controls are not a global improvement curve.') +
    (metrics.length > 1 ? ' Other metrics are available in the selector.' : '') + (unmeasured ? ' ' + unmeasured + ' experiments have no valid measurement in this metric.' : '') +
    (hasValues && axis.offset !== null ? ' Y-axis Δ ticks are changes from ' + valueLabel(axis.offset) + '; inspected values are absolute.' : '');
  if (view.selected && !view.points.has(view.selected)) view.selected = null;
  const active = activePoint && view.points.get(activePoint);
  if (active) active.focus({preventScroll: true});
  else if (activePoint) view.buttons.get(view.mode).focus({preventScroll: true});
  const previewPoint = selectedPoints.find(point => point.row.id === (view.selected || view.preview));
  if (previewPoint) preview(view, previewPoint); else hidePreview(view);
  renderActivity(view);
}

export function renderMethodsProgress(root, methods, {onSelect} = {}) {
  let view = progressViews.get(root);
  if (!view) {view = mount(root); progressViews.set(root, view);}
  view.methods = methods || {}; view.data = prepare(view.methods); view.onSelect = onSelect;
  if (view.mode === null) view.mode = view.data.solutions.length ? 'solutions' : 'experiments';
  draw(view);
}
