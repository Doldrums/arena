// Catalog evidence is rendered as recorded. No scores or scientific rankings are inferred here.
const sessions = new WeakMap();
const finite = value => typeof value === 'number' && Number.isFinite(value);
const number = value => finite(value) ? value.toLocaleString('en-US') : '—';
const percent = (total, denominator) => finite(total) && finite(denominator) && denominator > 0 ? total / denominator * 100 : null;
const percentText = value => finite(value) ? `${value.toFixed(1)}%` : 'Not recorded';
const safeURL = value => {
  try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null; }
  catch { return null; }
};
const text = value => value == null ? 'Not recorded' : typeof value === 'object' ? JSON.stringify(value) : String(value);

export function referenceMatches(record, filter) {
  const anchors = Array.isArray(record?.anchors) ? record.anchors : [];
  if (filter === 'published') return anchors.some(anchor => anchor.kind === 'published_reference');
  if (filter === 'baseline') return anchors.some(anchor => anchor.kind === 'recorded_seed_baseline');
  if (filter === 'numeric') return anchors.length > 0;
  if (filter === 'missing') return anchors.length === 0;
  return true;
}

function ui(root) {
  const doc = root.ownerDocument;
  const make = (tag, cls, value) => { const node = doc.createElement(tag); if (cls) node.className = cls; if (value != null) node.textContent = text(value); return node; };
  const link = (label, href, internal = false) => {
    const node = make('a', 'inline-link', label); node.href = href;
    if (internal) node.dataset.arenaRoute = 'true'; else { node.target = '_blank'; node.rel = 'noopener noreferrer'; }
    return node;
  };
  const panel = (title, description, cls = '') => {
    const node = make('section', `panel insights-panel ${cls}`); node.append(make('h3', '', title));
    if (description) node.append(make('p', 'insights-panel-description', description)); return node;
  };
  return {make, link, panel};
}

function unavailable(root, title, message, retry) {
  const {make} = ui(root), node = make('div', 'insights-unavailable');
  node.append(make('strong', '', title), make('p', '', message));
  if (retry) { const button = make('button', '', 'Retry overview'); button.type = 'button'; button.addEventListener('click', retry); node.append(button); }
  return node;
}

function distribution(root, items, {title, kind, selected, total, onFilter, expanded, onExpand}) {
  const {make, panel} = ui(root);
  const node = panel(title, `Share of all ${number(total)} task packages. Select a bar to filter the catalog.`, kind === 'type' ? 'insights-types' : '');
  const legend = make('div', 'insights-chart-legend');
  legend.append(make('span', 'insights-legend-executable', 'Executable definition'), make('span', 'insights-legend-unsupported', 'Unsupported'));
  node.append(legend);
  const list = make('div', 'insights-bars'); list.setAttribute('role', 'group'); list.setAttribute('aria-label', `${title}, filter task catalog`);
  const sorted = [...items].sort((a, b) => b.total - a.total || a.label.localeCompare(b.label));
  const limit = kind === 'domain' ? items.length : 10;
  for (const item of sorted.slice(0, expanded ? undefined : limit)) {
    const share = finite(item.percentage) ? item.percentage : percent(item.total, total), button = make('button', 'insights-bar'); button.type = 'button';
    button.dataset.insightsAction = `${kind}:${item.id}`; button.dataset.filterKind = kind; button.dataset.filterValue = item.id;
    button.setAttribute('aria-pressed', String(selected === item.id));
    button.setAttribute('aria-label', `${item.label}: ${number(item.total)} tasks, ${percentText(share)} of all tasks; ${number(item.executable)} executable definitions, ${number(item.unsupported)} unsupported. Filter catalog.`);
    button.title = item.description || item.label;
    const track = make('span', 'insights-bar-track'); track.setAttribute('aria-hidden', 'true');
    const fill = make('span', 'insights-bar-fill'); fill.style.width = `${Math.max(0, Math.min(100, share || 0))}%`;
    const executable = make('span', 'insights-bar-executable'), unsupported = make('span', 'insights-bar-unsupported');
    executable.style.width = `${Math.max(0, Math.min(100, percent(item.executable, item.total) || 0))}%`;
    unsupported.style.width = `${Math.max(0, Math.min(100, percent(item.unsupported, item.total) || 0))}%`;
    fill.append(executable, unsupported); track.append(fill);
    const value = make('span', 'insights-bar-value', number(item.total)); value.append(make('small', '', percentText(share)));
    button.append(make('span', 'insights-bar-label', item.label), track, value);
    button.addEventListener('click', () => onFilter(kind, selected === item.id ? null : item.id)); list.append(button);
  }
  node.append(list);
  if (items.length > limit) {
    const more = make('button', 'insights-list-toggle', expanded ? 'Show fewer' : `Show all ${items.length} ${kind === 'domain' ? 'domains' : 'task types'}`);
    more.type = 'button'; more.dataset.insightsAction = `expand:${kind}`; more.setAttribute('aria-expanded', String(expanded)); more.addEventListener('click', onExpand); node.append(more);
  }
  node.append(make('p', 'insights-chart-note', kind === 'domain' ? 'Domains describe scientific context. One package has one primary domain.' : 'Task types describe what the system must produce or optimize. They are a separate classification.'));
  return node;
}

function coverage(root, insights, catalog) {
  const {make, panel} = ui(root), total = insights.denominator.task_count;
  const node = panel('Evaluator & evidence coverage', 'Source protocol labels describe the available definitions. They are not Arena runtime verification.');
  const counts = catalog.tasks.reduce((all, task) => { all[task.protocol] = (all[task.protocol] || 0) + 1; return all; }, {});
  const protocols = [['original', 'Original', '#789b84'], ['recreated_verified', 'Recreated · verified at source', '#e1b52a'], ['recreated', 'Recreated', '#93a9c0'], ['unsupported', 'Unsupported', '#d6dbe2']];
  const track = make('div', 'insights-coverage-track'); track.setAttribute('role', 'img');
  track.setAttribute('aria-label', protocols.map(([id, label]) => `${label}: ${number(counts[id] || 0)}`).join('; '));
  const list = make('div', 'insights-coverage-list');
  for (const [id, label, color] of protocols) {
    const count = counts[id] || 0, share = percent(count, total);
    const segment = make('span', 'insights-coverage-segment'); segment.style.flexBasis = `${share || 0}%`; segment.style.background = color; segment.style.flexShrink = '1'; track.append(segment);
    const row = make('div', 'insights-coverage-item'), labelNode = make('span'), swatch = make('i', 'insights-swatch'); swatch.style.background = color;
    labelNode.append(swatch, make('span', '', label)); const value = make('strong', '', `${number(count)} `); value.append(make('small', '', percentText(share)));
    row.append(labelNode, value); list.append(row);
  }
  node.append(track, list);
  const facts = make('dl', 'insights-small-facts');
  const coverageRows = Array.isArray(insights.coverage) ? insights.coverage : [];
  for (const [id, label] of [['executable', 'Executable definitions'], ['recorded_contract', 'Recorded input/output'], ['runtime_verified', 'Arena runtime verified']]) {
    const item = coverageRows.find(row => row.id === id), box = make('div');
    const value = make('dd', '', number(item?.total));
    if (item) value.append(make('small', '', `${percentText(percent(item.total, total))} of all tasks`));
    box.append(make('dt', '', label), value); if (item?.description) box.title = item.description; facts.append(box);
  }
  node.append(facts, make('p', 'insights-chart-note', 'Coverage counts can overlap. No recorded Arena verification means unverified availability, not a failed task.'));
  return node;
}

function relevance(root, insights, catalog, current) {
  const {make, panel, link} = ui(root);
  const node = panel('Why these problems matter', 'Scientific roles of the domains, with concrete tasks to inspect. These descriptions do not rank scientific importance.');
  const grid = make('div', 'insights-relevance'), tasks = new Map(catalog.tasks.map(task => [task.id, task]));
  for (const domain of insights.domains) {
    const item = make('details', 'insights-domain-note'); item.dataset.domainNote = domain.id;
    item.open = current.domain === domain.id;
    item.append(make('summary', '', domain.label), make('p', '', domain.why_it_matters || domain.description || 'Scientific context not recorded.'));
    const examples = make('div', 'insights-example-links');
    for (const id of (domain.representative_task_ids || []).slice(0, 2)) {
      const task = tasks.get(id); if (task) examples.append(link(`${task.name || task.id} →`, `/?task=${encodeURIComponent(id)}`, true));
    }
    item.append(examples); grid.append(item);
  }
  node.append(grid); return node;
}

function parameterText(parameters) {
  return Object.entries(parameters || {}).map(([key, value]) => `${key.replaceAll('_', ' ')}: ${Array.isArray(value) ? value.join(' × ') : text(value).replaceAll('_', ' ')}`).join(' · ');
}

function evaluationSize(evaluation, seed = false) {
  if (evaluation?.case_count == null) return null;
  const count = text(evaluation.case_count), kind = evaluation.case_count_kind;
  if (kind === 'candidate_construction') return `${count} construction${evaluation.case_count === 1 ? '' : 's'}`;
  if (kind === 'historical_smoke' || seed) return `${count} items (historical smoke)`;
  if (kind === 'test_id_rows') return `${count} rows (in-distribution test)`;
  if (kind === 'named_initial_value_problem') return `${count} named initial-value problem${evaluation.case_count === 1 ? '' : 's'}`;
  return `${count} cases${kind ? ` (${kind.replaceAll('_', ' ')})` : ' (scope not recorded)'}`;
}

function referenceTable(root, records, catalog, {detail = false} = {}) {
  const {make, link} = ui(root), names = new Map((catalog?.tasks || []).map(task => [task.id, task.name]));
  const wrapper = make('div', 'table-wrap'), table = make('table', 'insights-reference-table'), head = make('thead'), tr = make('tr');
  for (const label of [detail ? 'Reference' : 'Task / instance', 'Value & metric', 'Evidence', 'Source']) { const th = make('th', '', label); th.scope = 'col'; tr.append(th); }
  head.append(tr); table.append(head); const body = make('tbody');
  for (const record of records) {
    const anchors = [...(record.anchors || [])].sort((a, b) => Number(b.kind === 'published_reference') - Number(a.kind === 'published_reference'));
    const groups = detail ? anchors.map(anchor => [anchor]) : [anchors];
    for (const group of groups) {
      const row = make('tr'), label = make('td'), value = make('td', 'insights-reference-value'), evidence = make('td'), source = make('td');
      row.dataset.referenceTask = record.task_id;
      if (!detail) {
        label.append(link(names.get(record.task_id) || record.task_id, `/?task=${encodeURIComponent(record.task_id)}`, true));
        const parameters = parameterText(record.evaluation?.parameters);
        if (parameters) label.append(make('small', '', parameters));
      }
      for (const anchor of group) {
        const kind = anchor.kind === 'published_reference' ? 'Published reference' : 'Seed smoke';
        if (detail) {
          label.append(make('span', '', anchor.label || kind));
          if (anchor.scope) label.append(make('small', '', text(anchor.scope)));
          if (anchor.notes?.length) label.append(make('small', '', anchor.notes.map(text).join(' ')));
        }
        const valueBlock = make('div', 'insights-anchor-value');
        valueBlock.append(make('span', '', `${detail ? '' : `${kind}: `}${text(anchor.value)}`));
        value.append(valueBlock);
        const evidenceBlock = make('div', 'insights-anchor-evidence');
        evidenceBlock.append(make('span', '', anchor.kind === 'published_reference' ? 'Source-declared published value' : 'Historical seed smoke'));
        if (anchor.reproduction === 'recorded_upstream') evidenceBlock.append(make('small', '', 'Upstream artifact check recorded'));
        if (anchor.kind === 'recorded_seed_baseline') evidenceBlock.append(make('small', '', anchor.validity === true ? 'Source validity: true' : 'Validity not recorded'));
        const size = evaluationSize(anchor.evaluation, anchor.kind === 'recorded_seed_baseline');
        if (size) evidenceBlock.append(make('small', '', size));
        evidence.append(evidenceBlock);
        const url = safeURL(anchor.source?.url);
        const sourceBlock = make('div', 'insights-anchor-source');
        if (url) sourceBlock.append(link(`${detail ? 'Source' : kind} ↗`, url)); else sourceBlock.append(make('span', '', 'Not linked'));
        if (detail && anchor.source?.locator) sourceBlock.append(make('small', '', anchor.source.locator));
        if (detail) {
          for (const item of anchor.primary_sources || []) {
            const primaryURL = safeURL(item.url);
            if (primaryURL) sourceBlock.append(link(`${item.type === 'paper' ? 'Paper' : 'Primary source'} ↗`, primaryURL));
          }
          const receiptURL = safeURL(anchor.reproduction_source?.url);
          if (receiptURL) sourceBlock.append(link('Artifact check receipt ↗', receiptURL));
        }
        source.append(sourceBlock);
      }
      const first = group[0];
      value.append(make('small', '', `${first.metric_label || first.metric || record.metric || 'Metric not recorded'} · ${first.direction || record.direction || 'direction not recorded'}`));
      row.append(label, value, evidence, source); body.append(row);
    }
  }
  table.append(body); wrapper.append(table); return wrapper;
}

function referencesPanel(root, references, catalog, current, onFilter, matchingTasks) {
  const {make, panel} = ui(root), summary = references.summary || {};
  const node = panel('Published references & SOTA evidence', 'Coverage counts cover the full catalog; examples follow your filters. Published values and seed smoke scores retain separate scopes.');
  const buttons = make('div', 'insights-reference-summary');
  for (const [filter, label, key] of [['published', 'Published reference', 'tasks_with_published_reference'], ['baseline', 'Seed baseline', 'tasks_with_recorded_baseline'], ['missing', 'No numeric reference', 'tasks_without_numeric_reference']]) {
    const button = make('button', '', label); button.type = 'button'; button.append(make('strong', '', number(summary[key])));
    button.dataset.insightsAction = `reference:${filter}`; button.setAttribute('aria-pressed', String(current.reference === filter));
    button.setAttribute('aria-label', `${label}: ${number(summary[key])} tasks. Filter catalog.`);
    button.addEventListener('click', () => onFilter('reference', current.reference === filter ? null : filter)); buttons.append(button);
  }
  node.append(buttons);
  const eligible = new Set(matchingTasks.map(task => task.id));
  const candidates = references.tasks.filter(record => eligible.has(record.task_id) && record.anchors?.length && referenceMatches(record, current.reference));
  const highlighted = new Map((references.highlights || []).map((item, index) => [item.task_id, index]));
  candidates.sort((a, b) => (highlighted.get(a.task_id) ?? 1000) - (highlighted.get(b.task_id) ?? 1000) || Number(b.anchors.some(anchor => anchor.kind === 'published_reference')) - Number(a.anchors.some(anchor => anchor.kind === 'published_reference')) || a.task_id.localeCompare(b.task_id));
  if (candidates.length) {
    node.append(referenceTable(root, candidates.slice(0, 4), catalog));
    node.append(make('p', 'insights-chart-note', `Showing ${Math.min(4, candidates.length)} of ${number(candidates.length)} task records with values in this selection. Open a task for every reference and its scope.`));
  } else node.append(make('p', 'insights-chart-note', current.reference === 'missing' ? 'The catalog below is filtered to tasks without a numeric reference in this snapshot.' : 'No numeric references are recorded for the selected tasks in this snapshot.'));
  const sota = summary.current_sota_status === 'not_assessed' || summary.verified_current_sota === 0 ? 'Current SOTA has not been established by this catalog. Source-declared values remain references, not verified current records.' : `Current SOTA verification is recorded for ${number(summary.verified_current_sota)} tasks; consult each source and comparison scope.`;
  node.append(make('p', 'insights-chart-note', sota));
  if (references.as_of) node.append(make('p', 'insights-chart-note', `Reference snapshot: ${references.as_of}.`));
  return node;
}

export function renderTaskReferences(root, {record, references, error, loading}) {
  const {make} = ui(root), node = make('section', 'arena-detail-section insights-task-reference');
  node.dataset.taskReferences = 'true'; node.append(make('h3', '', 'References & comparison scope'));
  if (error) node.append(make('p', '', 'Reference data is unavailable. This does not establish that the task has no reference.'));
  else if (loading && !references) node.append(make('p', '', 'Loading recorded references…'));
  else if (!record?.anchors?.length) node.append(make('p', '', 'No numeric reference is recorded for this task in the reference snapshot.'));
  else {
    node.append(referenceTable(root, [record], null, {detail: true}));
    node.append(make('p', 'insights-chart-note', 'Published values are source-declared. Seed smoke scores describe earlier checks. Neither alone establishes current SOTA or a comparable new result.'));
    const evaluation = record.evaluation;
    const parameters = parameterText(evaluation?.parameters);
    if (parameters) node.append(make('p', 'insights-chart-note', `Task instance: ${parameters}.`));
    const size = evaluationSize(evaluation);
    if (size) node.append(make('p', 'insights-chart-note', `Evaluation size: ${size}.`));
    if (evaluation?.notes?.length) node.append(make('p', 'insights-chart-note', evaluation.notes.map(text).join(' ')));
  }
  root.append(node);
}

export function renderArenaInsights(root, options) {
  const {insights, references, catalog, current, matchingTasks = catalog?.tasks || [], errors = {}, loading, onFilter, onRetry} = options;
  const previous = sessions.get(root), key = [insights, references, catalog, current.domain, current.type, current.reference, current.query, current.family, current.search_family, current.protocol, errors.insights, errors.references, loading];
  if (previous && key.every((value, index) => value === previous.key[index])) return;
  const focus = root.contains(root.ownerDocument.activeElement) ? root.ownerDocument.activeElement?.dataset.insightsAction : null;
  const openNotes = [...root.querySelectorAll('[data-domain-note][open]')].map(node => node.dataset.domainNote);
  const session = {key, expanded: previous?.expanded || {domain: false, type: false}}; sessions.set(root, session);
  const {make} = ui(root), container = make('div', 'arena-insights');
  const heading = make('div', 'insights-heading'); heading.append(make('h2', '', 'Scientific overview'), make('p', '', 'Explore the problem mix, evaluation definitions and source evidence before choosing a task.'));
  const jump = make('a', 'insights-catalog-jump', `${number(matchingTasks.length)} matching tasks · View catalog ↓`); jump.href = '#arena-list-panel';
  heading.append(jump); container.append(heading);
  if (insights && catalog) {
    const grid = make('div', 'insights-grid');
    for (const [kind, title, items] of [['domain', 'Scientific domains', insights.domains], ['type', 'Task types', insights.task_types]]) {
      grid.append(distribution(root, items, {title, kind, selected: current[kind], total: insights.denominator.task_count, onFilter,
        expanded: session.expanded[kind], onExpand: () => { session.expanded[kind] = !session.expanded[kind]; session.key = []; renderArenaInsights(root, options); }}));
    }
    const context = make('div', 'insights-grid insights-context');
    context.append(coverage(root, insights, catalog), relevance(root, insights, catalog, current));
    container.append(grid, context);
    const methodology = make('details', 'insights-methodology'); methodology.append(make('summary', '', 'How to read these counts'));
    methodology.append(make('p', '', insights.methodology?.unit || 'Each task package contributes once to its primary domain and once to its task type. Multiple packages can describe variants of the same scientific problem.'));
    methodology.append(make('p', '', insights.methodology?.classification_authority || 'Domain and task-type assignments are Arena editorial classifications, based on the pinned task metadata. They are not claims made by the source authors.'));
    methodology.append(make('p', '', insights.methodology?.percentages || 'Percentages use the complete catalog, including unsupported definitions.'));
    if (insights.methodology?.papers) methodology.append(make('p', '', insights.methodology.papers));
    container.append(methodology);
  } else container.append(unavailable(root, loading && !errors.insights ? 'Loading scientific overview…' : 'Scientific overview unavailable', 'The task catalog remains available below. Domain and task-type counts require the recorded overview.', errors.insights ? onRetry : null));
  if (references && catalog) container.append(referencesPanel(root, references, catalog, current, onFilter, matchingTasks));
  else container.append(unavailable(root, loading && !errors.references ? 'Loading reference evidence…' : 'Reference evidence unavailable', 'Missing reference data is not evidence that no baseline or SOTA exists.', errors.references ? onRetry : null));
  root.replaceChildren(container);
  for (const note of root.querySelectorAll('[data-domain-note]')) if (openNotes.includes(note.dataset.domainNote)) note.open = true;
  if (focus) [...root.querySelectorAll('[data-insights-action]')].find(node => node.dataset.insightsAction === focus)?.focus({preventScroll: true});
}
