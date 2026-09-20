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

const FIELD_STORIES = {
  physics: {tone:'amber', symbol:'orbit', question:'Which equations capture physical behavior?', topics:'Oscillation · heat flow · dynamical systems', examples:['coevo-oscillation-1','a2dept-ode-integration-discretized-heat-equation-n-20']},
  'chemistry-materials': {tone:'lilac', symbol:'bonds', question:'How do reactions and materials behave?', topics:'Reaction kinetics · materials · stress & strain', examples:['a2dept-ode-integration-robertson-kinetics','coevo-stress-strain']},
  'biology-health': {tone:'green', symbol:'life', question:'How can we model living systems?', topics:'Growth · populations · biological data', examples:['coevo-e-coli-growth','dga2d-ode-solver-lotka-volterra']},
  mathematics: {tone:'blue', symbol:'construction', question:'Can a construction improve a bound?', topics:'Geometry · algebra · mathematical bounds', examples:['alphaevolve-circle-packing-in-unit-square','alphaevolve-matrix-multiplication-4-4-4']},
  'earth-environment': {tone:'green', symbol:'earth', question:'What can environmental observations predict?', topics:'Volcanic sensors · forest-cover observations', examples:['loongflow-predict-volcanic-eruptions-ingv-oe','loongflow-tabular-playground-series-dec-2021']},
  'robotics-control': {tone:'lilac', symbol:'control', question:'Which feedback makes a system behave reliably?', topics:'Controllers · rewards · learned movement', examples:['a2dept-feedback-control-cartpole-stabilization','text2reward-button-press-v2']},
  'operations-research': {tone:'amber', symbol:'routes', question:'How should limited resources be allocated?', topics:'Routing · packing · scheduling', examples:['a2dept-capacitated-electric-vehicle-routing-with-time-windows','reference-online-bin-packing']},
  'computer-systems': {tone:'blue', symbol:'systems', question:'Can the same workload use fewer resources?', topics:'Compute · placement · infrastructure', examples:['adaevolve-expert-placement-load-balancing','pairwise-validator-txn-scheduling']},
  'machine-learning': {tone:'lilac', symbol:'intelligence', question:'What improves reasoning and generalization?', topics:'Learning · prompts · reasoning · retrieval', examples:['adaevolve-arc-agi-2','promptbreeder-gsm8k']},
  'software-engineering': {tone:'green', symbol:'software', question:'Does generated software meet its contract?', topics:'Program synthesis · behavior · correctness', examples:['sciel-bench-kattis-alphabet','sciel-bench-web-scraper-api-docs']},
  'finance-economics': {tone:'blue', symbol:'decisions', question:'How do policies balance return and risk?', topics:'Allocation · trading policies · risk', examples:['ael-harness-d-full-portfolio-allocation','algoevolve-numin-intraday-equity-trading']},
  unknown: {tone:'neutral', symbol:'mixed', question:'Which scientific target does this task define?', topics:'Mixed suites · open classification', examples:['deliberate-evolution-lsr-transform','adaevolve-frontier-cs']},
};
const FIELD_SYMBOLS = {
  orbit:'M20 48c0-14 56-14 56 0s-56 14-56 0 M34 24c12-7 40 41 28 48S22 31 34 24 M62 24c12 7-16 55-28 48s16-55 28-48',
  bonds:'M48 20 72 34v28L48 76 24 62V34z M48 20v18m24-4L56 44m16 18L56 52M48 76V58M24 62l16-10M24 34l16 10',
  life:'M31 18c43 13-9 46 34 60 M65 18C22 31 74 64 31 78 M37 24h22M40 39h16M40 57h16M37 72h22',
  construction:'M29 24h15v15H29z M52 24h15v15H52z M17 47h15v15H17z M40 47h15v15H40z M63 47h15v15H63z M29 70h15M52 70h15',
  earth:'M18 50c0-19 17-31 34-28s29 13 26 30-19 28-36 24S18 67 18 50z M28 46c4-13 22-18 33-8s-1 28-13 28-25-7-20-20z M40 45c6-6 17 3 10 9s-16-3-10-9',
  control:'M24 72h47 M34 72V51l21-20 16 10 M28 51a6 6 0 1 0 12 0 6 6 0 1 0-12 0 M49 29a6 6 0 1 0 12 0 6 6 0 1 0-12 0 M67 39l7 13 9-11',
  routes:'M22 68V27h24v42h27V27 M16 68a6 6 0 1 0 12 0 6 6 0 1 0-12 0 M67 27a6 6 0 1 0 12 0 6 6 0 1 0-12 0',
  systems:'M21 23h20v20H21z M55 23h20v20H55z M21 57h20v20H21z M55 57h20v20H55z M41 33h14M31 43v14M65 43v14M41 67h14',
  intelligence:'M24 31h1m23-9h1m23 9h1M17 49h1m29 0h1m29 0h1M24 67h1m23 9h1m23-9h1',
  software:'m34 28-18 20 18 20 M62 28l18 20-18 20 M53 23 43 73',
  decisions:'M20 48h56 M48 20v56 M27 28l42 42 M27 68l42-42',
  mixed:'M26 24h12v12H26z M57 24h12v12H57z M26 57h12v12H26z M57 57h12v12H57z',
};
function scientificFields(root, insights, catalog, current, onFilter) {
  const {make,link} = ui(root), section = make('section','insights-fields');
  section.setAttribute('aria-label','Explore scientific directions');
  const header = make('div','fields-heading');
  const intro=make('div');intro.append(make('span','fields-eyebrow','FOLLOW A QUESTION'),make('h3','','Where will curiosity take you?'),
    make('p','','Explore scientific questions, from the behavior of matter to the design of intelligent systems.'));
  header.append(intro,make('span','fields-heading-note',`${number(insights.domains.filter(item=>item.id!=='unknown').length)} research directions`));section.append(header);
  const grid=make('div','fields-grid'); grid.setAttribute('role','group');grid.setAttribute('aria-label','Scientific directions, filter task catalog');
  const order=Object.keys(FIELD_STORIES), domains=[...insights.domains].sort((a,b)=>(order.indexOf(a.id)<0?99:order.indexOf(a.id))-(order.indexOf(b.id)<0?99:order.indexOf(b.id)));
  for(const domain of domains){
    const story=FIELD_STORIES[domain.id] || {tone:'blue',symbol:'mixed',question:domain.description || domain.label,topics:'Explore the recorded scientific context'};
    const card=make('button','field-card');card.type='button';card.dataset.tone=story.tone;card.dataset.domainCard=domain.id;
    card.dataset.insightsAction=`field:${domain.id}`;card.dataset.filterKind='domain';card.dataset.filterValue=domain.id;
    card.setAttribute('aria-pressed',String(current.domain===domain.id));
    card.setAttribute('aria-label',`${domain.label}: ${number(domain.total)} tasks; ${number(domain.executable)} executable definitions, ${number(domain.unsupported)} unsupported. ${story.question} Filter catalog.`);
    const copy=make('span','field-copy'),meta=make('span','field-meta');
    meta.append(make('span','field-topics',story.topics),make('span','field-count',`${number(domain.total)} tasks`));
    copy.append(meta,make('span','field-title',domain.label),make('span','field-question',story.question));
    const visual=make('span','field-visual');visual.setAttribute('aria-hidden','true');
    const svg=root.ownerDocument.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 96 96');svg.setAttribute('class',`field-symbol field-symbol-${story.symbol}`);
    const path=root.ownerDocument.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',FIELD_SYMBOLS[story.symbol] || FIELD_SYMBOLS.mixed);svg.append(path);visual.append(svg);
    visual.append(make('span','field-explore',current.domain===domain.id?'Selected direction':'Explore direction'),make('span','field-arrow',current.domain===domain.id?'✓':'↗'));
    card.append(copy,visual);card.addEventListener('click',()=>onFilter('domain',current.domain===domain.id?null:domain.id));grid.append(card);
  }
  section.append(grid);
  const selected=insights.domains.find(domain=>domain.id===current.domain);
  if(selected){
    const story=FIELD_STORIES[selected.id],detail=make('div','field-detail');detail.dataset.fieldDetail=selected.id;
    const description=make('div');description.append(make('span','fields-eyebrow','INSIDE THIS DIRECTION'),make('h4','',selected.label),make('p','',selected.why_it_matters || selected.description));
    const examples=make('div','field-examples');examples.append(make('span','fields-eyebrow','START WITH A TASK'));
    const tasks=new Map(catalog.tasks.map(task=>[task.id,task]));
    const ids=story?.examples || selected.representative_task_ids || [];
    for(const id of ids.slice(0,2)){
      const task=tasks.get(id);if(!task || insights.task_annotations?.[id]?.domain_id!==selected.id)continue;
      const row=make('div','field-example');row.append(link(`${task.name || id} ↗`,`/?task=${encodeURIComponent(id)}`,true),make('small','',task.executable?'Evaluation definition recorded':'Source-only definition'));examples.append(row);
    }
    const browse=make('a','field-catalog-link','Browse matching tasks ↓');browse.href='#arena-list-panel';examples.append(browse);detail.append(description,examples);section.append(detail);
  }
  section.append(make('p','fields-footnote','Each direction gets its own space. Counts describe this task collection; variants of the same benchmark are counted separately.'));
  return section;
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
  const compositionOpen = Boolean(root.querySelector('.insights-composition[open]'));
  const session = {key, expanded: previous?.expanded || {domain: false, type: false}}; sessions.set(root, session);
  const {make} = ui(root), container = make('div', 'arena-insights');
  const heading = make('div', 'insights-heading'); heading.append(make('h2', '', 'Scientific overview'), make('p', '', 'Explore the problem mix, evaluation definitions and source evidence before choosing a task.'));
  const jump = make('a', 'insights-catalog-jump', `${number(matchingTasks.length)} matching tasks · View catalog ↓`); jump.href = '#arena-list-panel';
  heading.append(jump); container.append(heading);
  if (insights && catalog) {
    container.append(scientificFields(root,insights,catalog,current,onFilter));
    const composition=make('details','insights-composition');composition.open=compositionOpen;
    const compositionSummary=make('summary');compositionSummary.append(make('span','','Corpus composition'),make('small','',`${number(insights.denominator.task_count)} task packages · domain shares & evaluation coverage`));composition.append(compositionSummary);
    const grid=make('div','insights-grid');
    grid.append(distribution(root,insights.domains,{title:'Domain distribution in this corpus',kind:'domain',selected:current.domain,total:insights.denominator.task_count,onFilter,expanded:true}),coverage(root,insights,catalog));
    composition.append(grid);container.append(composition);
    container.append(distribution(root,insights.task_types,{title:'What the tasks ask you to do',kind:'type',selected:current.type,total:insights.denominator.task_count,onFilter,
      expanded:session.expanded.type,onExpand:()=>{session.expanded.type=!session.expanded.type;session.key=[];renderArenaInsights(root,options);}}));
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
  if (focus) [...root.querySelectorAll('[data-insights-action]')].find(node => node.dataset.insightsAction === focus)?.focus({preventScroll: true});
}
