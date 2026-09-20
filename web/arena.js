import {renderArenaAtlas} from './arena-atlas.js';
import {renderArenaInsights, renderTaskReferences, referenceMatches} from './arena-insights.js';
const REPOSITORY = 'https://github.com/Doldrums/arena';
const PAGE_SIZE = 25;
const PROTOCOL_LABELS = {
  original: 'Original', recreated_verified: 'Recreated · verified',
  recreated: 'Recreated', unsupported: 'Evaluator to be added',
};
const textValue = value => value == null || value === '' ? 'Not specified' :
  typeof value === 'object' ? JSON.stringify(value) : String(value);
const words = value => textValue(value).replaceAll('_', ' ');
const participantKind = item => item.record_kind === 'research_work' ? 'Research work' : item.repository?.commit ? 'Source pinned' : words(item.registration_status);
const adapterLabel = item => ({not_implemented: 'Integration open', planned: 'Integration planned', integrated: 'Adapter integrated'}[item.adapter_status] || words(item.adapter_status));

function canonicalJSON(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJSON).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalJSON(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}
async function catalogDigest(catalog) {
  const bytes = new TextEncoder().encode(canonicalJSON(catalog));
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, '0')).join('');
}

export function safeExternalURL(value) {
  if (typeof value !== 'string') return null;
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}

export function filterTasks(tasks, {query = '', family = '', protocol = '', domain = '', type = '', reference = '', search_family = ''} = {}, {insights, references, searchFamilies} = {}) {
  const terms = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  const referenceMap = new Map((references?.tasks || []).map(record => [record.task_id, record]));
  return tasks.filter(task => (!family || (family === '__unspecified__' ? !task.family : task.family === family)) &&
    (!search_family || !searchFamilies || (searchFamilies.task_annotations[task.id]?.search_family_id || 'unclassified') === search_family) &&
    (!protocol || task.protocol === protocol) && (!domain || !insights || insights.task_annotations[task.id]?.domain_id === domain) &&
    (!type || !insights || insights.task_annotations[task.id]?.task_type_id === type) &&
    (!reference || !references || referenceMatches(referenceMap.get(task.id), reference)) && terms.every(term =>
      [task.id, task.name, task.description, task.family, task.metric, ...(task.paper_ids || [])]
        .map(textValue).join(' ').toLocaleLowerCase().includes(term)));
}

export function createArenaApp({document: doc = document, window: win = window,
  fetchJSON = async path => {
    const response = await fetch(path, {headers: {Accept: 'application/json'}});
    if (!response.ok) throw new Error(`Request failed (${response.status})`);
    return response.json();
  }} = {}) {
  const $ = id => doc.getElementById(id);
  const state = {catalog: null, participants: null, insights: null, references: null, searchFamilies: null, errors: {}, loading: true};
  let loadRevision = 0;
  let lastCatalogRoute = null;
  let pendingCatalogHash = null;

  function element(tag, className, text) {
    const node = doc.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = String(text);
    return node;
  }
  function link(text, href, className = 'inline-link', internal = false) {
    const node = element('a', className, text);
    node.href = href;
    if (internal) node.dataset.arenaRoute = 'true';
    else { node.target = '_blank'; node.rel = 'noopener noreferrer'; }
    return node;
  }
  function button(text, action, className = 'button') {
    const node = element('button', className, text);
    node.type = 'button'; node.addEventListener('click', action);
    return node;
  }
  function locationState() {
    const params = new URL(win.location.href).searchParams;
    return {view: params.get('view') === 'participants' ? 'participants' : 'tasks',
      atlasMode: params.get('atlas') === 'families' ? 'families' : 'methods',
      search_family: params.get('search_family') || '', query: params.get('q') || '', family: params.get('family') || '',
      domain: params.get('domain') || '', type: params.get('type') || '', reference: params.get('reference') || '',
      protocol: params.get('protocol') || '', task: params.get('task'),
      participant: params.get('participant'), page: Math.max(1, Number.parseInt(params.get('page'), 10) || 1)};
  }
  function route(changes = {}) {
    const url = new URL(win.location.href);
    url.pathname = '/'; url.hash = '';
    for (const [key, value] of Object.entries(changes)) {
      if (value == null || value === '') url.searchParams.delete(key);
      else url.searchParams.set(key, value);
    }
    return url.pathname + url.search;
  }
  function catalogHashTarget(url = new URL(win.location.href)) {
    const browser = $('arena-catalog-browser');
    if (!browser || !url.hash) return null;
    let target;
    try { target = $(decodeURIComponent(url.hash.slice(1))); } catch { return null; }
    return target && (target === browser || browser.contains(target)) ? target : null;
  }
  function revealCatalog({scroll = false, focus = false, target = $('arena-list-panel')} = {}) {
    const current = locationState();
    if (current.view === 'tasks' ? current.task : current.participant) return;
    const browser = $('arena-catalog-browser');
    if (browser) browser.open = true;
    if (scroll) {
      const reducedMotion = win.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
      target?.scrollIntoView?.({behavior: reducedMotion ? 'instant' : 'smooth', block: 'start'});
    }
    if (focus) {
      const heading = target === $('arena-list-panel') ? $('arena-results-title') : target;
      heading?.setAttribute('tabindex', '-1'); heading?.focus({preventScroll: true});
    }
  }
  function catalogDisclosure(current) {
    const browser = $('arena-catalog-browser');
    if (!browser) return;
    const isTasks = current.view === 'tasks', selected = isTasks ? current.task : current.participant;
    browser.hidden = Boolean(selected);
    if ($('arena-catalog-toggle')) $('arena-catalog-toggle').hidden = !isTasks;
    if ($('arena-analysis')) $('arena-analysis').hidden = !isTasks || Boolean(selected);
    const url = new URL(win.location.href), hashTarget = catalogHashTarget(url);
    const filters = [current.query, current.family, current.protocol, current.domain, current.type, current.reference, current.search_family];
    const key = JSON.stringify([current.view, current.task, current.participant, ...filters, url.searchParams.get('page'), url.hash]);
    if (lastCatalogRoute?.key !== key) pendingCatalogHash = !selected && isTasks ? hashTarget?.id || null : null;
    if (!isTasks) browser.open = true;
    else if (lastCatalogRoute?.key !== key && !selected) {
      if (filters.some(Boolean) || url.searchParams.has('page') || hashTarget || lastCatalogRoute?.task) browser.open = true;
      else if (lastCatalogRoute?.view === 'participants') browser.open = false;
    }
    lastCatalogRoute = {key, view: current.view, task: current.task};
  }
  function finishCatalogHashNavigation() {
    if (!pendingCatalogHash || state.loading) return;
    const target = $(pendingCatalogHash), browser = $('arena-catalog-browser');
    pendingCatalogHash = null;
    if (target && browser?.open && !browser.hidden) revealCatalog({scroll: true, target});
  }
  function navigate(href, {replace = false, focus = false, catalog = false, scrollCatalog = false, target} = {}) {
    win.history[replace ? 'replaceState' : 'pushState'](null, '', href);
    render();
    if (catalog) revealCatalog({scroll: scrollCatalog, focus, target});
    else if (focus) $('main').focus({preventScroll: true});
  }
  function filterCatalog(kind, value) {
    navigate(route({[kind]: value, page: null, task: null}), {catalog: true, scrollCatalog: true});
  }
  function badge(text, kind = 'neutral') { return element('span', `badge ${kind}`, text); }
  function fact(list, label, value) {
    const item = element('div'); item.append(element('dt', '', label), element('dd', '', textValue(value)));
    list.append(item);
  }
  function section(container, title) {
    const item = element('section', 'arena-detail-section'); item.append(element('h3', '', title));
    container.append(item); return item;
  }
  function empty(container, title, message) {
    const node = element('div', 'arena-empty');
    node.append(element('strong', '', title), element('p', '', message)); container.append(node);
  }
  function recordDetails(container, record) {
    const details = element('details', 'arena-detail-section');
    details.append(element('summary', 'inline-link', 'View complete registry record'),
      element('pre', '', JSON.stringify(record, null, 2)));
    container.append(details);
  }
  function externalLinks(container, candidates) {
    const holder = element('div', 'arena-detail-links');
    const seen = new Set();
    for (const [title, candidate] of candidates) {
      const url = safeExternalURL(candidate);
      if (url && !seen.has(url)) { holder.append(link(`${title} ↗`, url)); seen.add(url); }
    }
    if (holder.childNodes.length) container.append(holder);
  }
  function summary() {
    const container = $('arena-summary'); container.replaceChildren();
    const tasks = state.catalog?.tasks;
    const counts = tasks ? [tasks.length, tasks.filter(task => task.executable).length] : ['—', '—'];
    const metrics = locationState().view === 'tasks' ? [
      ['Task packages', counts[0], `${typeof counts[1] === 'number' ? counts[1].toLocaleString('en-US') : '—'} with evaluation definitions`],
      ['Research domains', state.insights ? state.insights.domains.filter(item => item.id !== 'unknown').length : '—', state.insights?.summary?.unknown_domain_count != null ? `${state.insights.summary.unknown_domain_count} packages unclassified` : 'Primary scientific context'],
      ['Task families', tasks ? new Set(tasks.map(task => task.family).filter(Boolean)).size : '—', 'Packing, equations, algorithms & more'],
      ['Research papers', state.insights?.summary?.corpus_paper_count ?? '—', state.insights?.summary?.source_group_count != null ? 'Plus the SCiEL task collection' : 'Excludes source supplements'],
    ] : [
      ['Research works', state.participants?.summary?.research_work_count ?? state.participants?.participants.filter(item => item.papers?.length).length ?? '—', 'Papers, methods and source material'],
      ['Method families', state.participants ? new Set(state.participants.participants.map(item => item.search_family?.id).filter(Boolean)).size : '—', 'Explore related research approaches'],
      ['Source-pinned systems', state.participants?.summary?.pinned_registration_count ?? state.participants?.participants.filter(item => item.repository?.commit).length ?? '—', 'Versioned framework registrations'],
    ];
    container.classList.toggle('arena-task-metrics', locationState().view === 'tasks');
    for (const [index, [label, value, note]] of metrics.entries()) {
      const metric = element('article', 'metric');
      const caption = element('div', 'metric-label');
      const icon = element('span', 'arena-metric-icon'); icon.setAttribute('aria-hidden', 'true');
      const svg = doc.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('viewBox', '0 0 24 24');
      const path = doc.createElementNS(svg.namespaceURI, 'path');
      path.setAttribute('d', ['M4 4h6v6H4z M14 4h6v6h-6z M4 14h6v6H4z M14 14h6v6h-6z', 'M12 3v18 M3 12h18 M5.6 5.6l12.8 12.8 M5.6 18.4 18.4 5.6', 'M6 5h12 M6 12h12 M6 19h12 M12 5v14 M4 3h4v4H4z M16 10h4v4h-4z M4 17h4v4H4z', 'M4 4h7l1 2 1-2h7v15h-7l-1 2-1-2H4z M12 6v13'][index % 4]);
      svg.append(path); icon.append(svg); caption.append(element('span', '', label), icon);
      metric.append(caption,
        element('div', 'metric-value', typeof value === 'number' ? value.toLocaleString('en-US') : value),
        element('div', 'metric-foot', note));
      if (index === 0) { const glow = element('span', 'arena-curious-glow'); glow.setAttribute('aria-hidden', 'true'); glow.append(element('span', 'arena-curious-eye'), element('span', 'arena-curious-eye')); metric.append(glow); }
      container.append(metric);
    }
    $('nav-task-count').textContent = tasks?.length.toLocaleString('en-US') ?? '';
    $('nav-participant-count').textContent = state.participants?.participants.length ?? '';
    const registryError = state.errors.catalog || state.errors.participants;
    $('arena-connection').textContent = state.loading ? 'Loading registry…' : registryError ? 'Registry partly unavailable' : 'Registry loaded';
    $('arena-connection-dot').className = `connection-dot ${state.loading ? '' : registryError ? 'error' : 'connected'}`;
  }
  function taskDetail(task) {
    const holder = $('arena-detail'); holder.replaceChildren();
    holder.append(link('← Back to task catalog', route({task: null}), 'inline-link', true));
    if (!task) { empty(holder, 'Task not found', 'This task is not in the current catalog. Return to the catalog to choose an available definition.'); return; }
    const source = state.catalog.sources?.find(item => item.id === task.source_id || item.source_id === task.source_id);
    const heading = element('div', 'arena-detail-top');
    const title = element('div'); title.append(element('h2', 'arena-detail-title', task.name || task.id), element('span', 'arena-task-id', task.id));
    heading.append(title, badge(PROTOCOL_LABELS[task.protocol] || words(task.protocol)));
    holder.append(heading, element('p', 'arena-detail-description', task.description || 'No description supplied.'));
    const facts = element('dl', 'arena-detail-facts');
    fact(facts, 'Family', task.family); fact(facts, 'Metric', task.metric);
    fact(facts, 'Direction', ['max', 'maximize'].includes(task.direction) ? 'Maximize' : ['min', 'minimize'].includes(task.direction) ? 'Minimize' : task.direction);
    fact(facts, 'Executable definition', task.executable ? 'Present' : 'Evaluator to be added');
    fact(facts, 'Runtime availability', words(task.runtime_readiness));
    fact(facts, 'Source status', words(task.declared_status)); holder.append(facts);
    if (source?.repository?.commit) fact(facts, 'Source revision', source.repository.commit);
    const annotation = state.insights?.task_annotations?.[task.id];
    const domain = state.insights?.domains.find(item => item.id === annotation?.domain_id);
    const taskType = state.insights?.task_types.find(item => item.id === annotation?.task_type_id);
    const searchFamily = state.searchFamilies?.groups.find(item => item.id === state.searchFamilies.task_annotations[task.id]?.search_family_id);
    if (searchFamily) fact(facts, 'Source method family', searchFamily.label);
    if (domain) fact(facts, 'Scientific domain', domain.label);
    if (taskType) fact(facts, 'Task type', taskType.label);
    if (domain || taskType) {
      const context = section(holder, 'Scientific context'); context.dataset.taskScience = 'true';
      if (domain?.why_it_matters) context.append(element('p', '', domain.why_it_matters));
      if (taskType?.description) context.append(element('p', '', taskType.description));
      if (annotation?.rationale) context.append(element('p', 'arena-classification-note', `Arena classification: ${annotation.rationale}`));
    }
    const contract = section(holder, 'Input / output');
    contract.dataset.taskContract = 'true';
    const hasContract = typeof task.contract === 'string' && task.contract.trim().length > 0;
    contract.append(element('p', 'arena-contract-text', hasContract ? task.contract : 'Input/output contract not recorded in the task snapshot.'));
    if (hasContract) contract.append(element('p', 'arena-contract-note', 'Source declaration; runtime conformance has not been verified.'));
    if (task.contract_source) {
      externalLinks(contract, [['Pinned contract source', task.contract_source.url]]);
      const metadata = element('dl', 'arena-contract-source');
      if (task.contract_source.path) fact(metadata, 'Source file', task.contract_source.path);
      if (task.contract_source.sha256) fact(metadata, 'Source SHA-256', task.contract_source.sha256);
      if (metadata.childNodes.length) contract.append(metadata);
    }
    if (task.requirements?.length) {
      const requirements = section(holder, 'Requirements'); const list = element('ul');
      for (const item of task.requirements) list.append(element('li', '', textValue(item)));
      requirements.append(list);
    }
    if (task.paper_ids?.length) {
      const papers = section(holder, 'Related papers');
      papers.append(element('p', '', task.paper_ids.map(textValue).join(' · ')));
    }
    renderTaskReferences(holder, {record: state.references?.tasks.find(item => item.task_id === task.id), references: state.references, error: state.errors.references, loading: state.loading});
    const provenance = section(holder, 'Source & provenance');
    provenance.append(element('p', '', 'The source contract describes the evaluation. An executable definition alone does not confirm that its dependencies or runtime are available in Arena.'));
    if (task.unsupported_reason) provenance.append(element('p', '', task.unsupported_reason));
    if (task.provenance?.validation_level) provenance.append(element('p', '', `Validation: ${words(task.provenance.validation_level)}.`));
    if (task.provenance?.limitations?.length) {
      const list = element('ul');
      for (const limitation of task.provenance.limitations) list.append(element('li', '', textValue(limitation)));
      provenance.append(list);
    }
    const refs = [['Repository', source?.repository?.url || source?.repository_url || source?.url],
      ['Task source', task.source_url || task.provenance?.source_url],
      ['Benchmark', task.benchmark?.url || task.provenance?.benchmark_url]];
    const sources = task.provenance?.sources;
    if (Array.isArray(sources)) for (const item of sources) refs.push(['Source', typeof item === 'string' ? item : item.url]);
    externalLinks(provenance, refs);
    recordDetails(holder, task);
  }
  function participantDetail(participant) {
    const holder = $('arena-detail'); holder.replaceChildren();
    holder.append(link('← Back to participants', route({participant: null}), 'inline-link', true));
    if (!participant) { empty(holder, 'Participant not found', 'This participant is not in the current registry.'); return; }
    const heading = element('div', 'arena-detail-top');
    const title = element('div'); title.append(element('h2', 'arena-detail-title', participant.name || participant.id), element('span', 'arena-task-id', participant.id));
    heading.append(title, badge(participantKind(participant)));
    holder.append(heading, element('p', 'arena-detail-description', participant.description || 'No description supplied.'));
    participantPapers(holder, participant, true);
    const facts = element('dl', 'arena-detail-facts');
    if (participant.search_family?.label) fact(facts, 'Method family', participant.search_family.label);
    fact(facts, 'Arena integration', adapterLabel(participant));
    if (participant.repository?.commit) {
      fact(facts, 'Source revision', participant.repository.commit);
      for (const [label, key] of [['Native execution', 'native_run'], ['Canonical evaluation', 'canonical_evaluation'], ['Pause', 'pause'], ['Resume', 'resume']]) {
        const value = participant.capabilities?.[key]; fact(facts, label, value === true ? 'Available' : value === false ? 'Integration pending' : 'To be specified');
      }
    }
    holder.append(facts);
    externalLinks(holder, participantSourceLinks(participant).concat([['Propose an integration', `${REPOSITORY}/compare?expand=1&template=participant.md`]]));
    if (participant.provenance?.filename) {
      const provenance = section(holder, 'Research provenance');
      provenance.append(element('p', '', `Curated from ${participant.provenance.filename}${participant.provenance.line_start ? `, lines ${participant.provenance.line_start}–${participant.provenance.line_end}` : ''}. Paper and source links identify the original research.`));
    }
    recordDetails(holder, participant);
  }
  function participantSourceLinks(participant) {
    const refs = (participant.code_links || []).map(item => [item.label || 'Research source', item.url]);
    if (participant.repository?.url && !refs.some(([,url]) => url === participant.repository.url)) refs.unshift(['Code', participant.repository.url]);
    return refs;
  }
  function participantPapers(container, participant, detailed = false) {
    if (!participant.papers?.length) return;
    const list = element('div', `arena-participant-papers${detailed ? ' is-detail' : ''}`);
    for (const paper of participant.papers) {
      const row = element('div', 'arena-paper-citation');
      const title = safeExternalURL(paper.url) ? link(paper.title || paper.id, paper.url, 'arena-paper-title') : element('span', 'arena-paper-title', paper.title || paper.id);
      const metadata = [paper.year, paper.venue].filter(Boolean).join(' · ');
      row.append(element('span', 'arena-paper-label', paper.kind === 'technical_report' ? 'Report' : 'Paper'), title);
      if (metadata) row.append(element('span', 'arena-paper-meta', metadata));
      list.append(row);
    }
    container.append(list);
  }
  function taskResults(current) {
    const tasks = filterTasks(state.catalog.tasks, current, state);
    const results = $('arena-results'); results.replaceChildren();
    $('arena-result-count').textContent = `${tasks.length.toLocaleString('en-US')} of ${state.catalog.tasks.length.toLocaleString('en-US')} tasks`;
    if (!tasks.length) {
      empty(results, state.catalog.tasks.length ? 'No tasks match these filters' : 'No tasks in the catalog',
        state.catalog.tasks.length ? 'Try another search or clear the filters to show all tasks.' : 'Task definitions can be proposed through a pull request.'); return;
    }
    const pages = Math.ceil(tasks.length / PAGE_SIZE), page = Math.min(current.page, pages);
    const table = element('table', 'arena-table');
    const head = element('thead'); const header = element('tr');
    for (const label of ['Task', 'Family', 'Protocol', 'Definition']) { const th = element('th', '', label); th.scope = 'col'; header.append(th); }
    head.append(header); table.append(head); const body = element('tbody');
    for (const task of tasks.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)) {
      const row = element('tr'); const title = element('td');
      title.append(link(task.name || task.id, route({task: task.id}), 'arena-task-link', true), element('span', 'arena-task-id', task.id));
      if (task.description) title.append(element('p', 'arena-task-description', task.description));
      const protocol = element('td'); protocol.append(badge(PROTOCOL_LABELS[task.protocol] || words(task.protocol)));
      row.append(title, element('td', 'muted', task.family || 'Unspecified'), protocol,
        element('td', 'arena-definition', task.executable ? 'Executable source' : 'Evaluator to be added'));
      body.append(row);
    }
    table.append(body); const wrapper = element('div', 'table-wrap'); wrapper.append(table); results.append(wrapper);
    const pagination = $('arena-pagination'); pagination.replaceChildren(); pagination.hidden = pages <= 1;
    pagination.append(element('span', '', `Page ${page} of ${pages}`));
    const controls = element('div');
    const previous = button('← Previous', () => navigate(route({page: page - 1}), {focus: true, catalog: true, scrollCatalog: true})); previous.disabled = page === 1;
    const next = button('Next →', () => navigate(route({page: page + 1}), {focus: true, catalog: true, scrollCatalog: true})); next.disabled = page === pages;
    controls.append(previous, next); pagination.append(controls);
  }
  function participantResults(current) {
    const terms = current.query.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
    const all = state.participants.participants;
    const participants = all.filter(item => (!current.family || item.search_family?.id === current.family) && terms.every(term => [item.id, item.name, item.description, item.search_family?.label, ...(item.papers || []).flatMap(paper => [paper.title, paper.year, paper.venue])].join(' ').toLocaleLowerCase().includes(term)));
    $('arena-result-count').textContent = `${participants.length} of ${all.length} participants`;
    const results = $('arena-results'); results.replaceChildren();
    if (!participants.length) { empty(results, all.length ? 'No participants match your search' : 'No participants registered', all.length ? 'Try another name or clear the search.' : 'Propose a participant through a pull request.'); return; }
    const grid = element('div', 'arena-participants');
    const pages = Math.ceil(participants.length / PAGE_SIZE), page = Math.min(current.page, pages);
    for (const item of participants.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)) {
      const card = element('article', 'arena-participant');
      card.dataset.participant = item.id;
      const title = element('h3'); title.append(link(item.name || item.id, route({participant: item.id}), 'arena-task-link', true));
      const status = element('div', 'arena-participant-status'); status.append(badge(participantKind(item)), badge(adapterLabel(item)));
      const art = element('div', 'arena-participant-art'); art.dataset.participant = item.id; art.setAttribute('aria-hidden', 'true');
      art.append(element('span', 'arena-participant-glyph'));
      const heading = element('div', 'arena-participant-heading'), identity = element('div');
      identity.append(title, element('span', 'arena-participant-family', item.search_family?.label || 'Research system')); heading.append(art, identity);
      card.append(heading, element('p', 'arena-participant-description', item.description || 'Research system registration.'));
      participantPapers(card, item);
      const footer = element('div', 'arena-participant-footer');
      externalLinks(footer, [...(item.papers || []).map(paper => [paper.kind === 'technical_report' ? 'Report' : 'Paper', paper.url]), ...participantSourceLinks(item)]);
      footer.append(link('Details →', route({participant: item.id}), 'inline-link', true));
      card.append(status, footer); grid.append(card);
    }
    results.append(grid);
    const pagination = $('arena-pagination'); pagination.replaceChildren(); pagination.hidden = pages <= 1;
    if (pages > 1) {
      pagination.append(element('span', '', `Page ${page} of ${pages}`));
      const controls = element('div');
      const previous = button('← Previous', () => navigate(route({page: page - 1}), {focus: true, catalog: true, scrollCatalog: true})); previous.disabled = page === 1;
      const next = button('Next →', () => navigate(route({page: page + 1}), {focus: true, catalog: true, scrollCatalog: true})); next.disabled = page === pages;
      controls.append(previous, next); pagination.append(controls);
    }
  }
  function render() {
    const current = locationState(), isTasks = current.view === 'tasks';
    const dataset = isTasks ? state.catalog : state.participants;
    const error = state.errors[isTasks ? 'catalog' : 'participants'];
    const selected = isTasks ? current.task : current.participant;
    const viewName = isTasks ? 'Tasks' : 'Participants';
    doc.title = `Empira · ${viewName}`;
    $('arena-title').textContent = viewName; $('arena-breadcrumb').textContent = viewName;
    $('arena-subtitle').textContent = isTasks ? 'Versioned scientific tasks and evaluation definitions.' : 'Research systems, their papers and the methods they build on.';
    $('arena-contribute').textContent = isTasks ? 'Add a task ↗' : 'Add a participant ↗';
    $('arena-contribute').href = `${REPOSITORY}/compare?expand=1&template=${isTasks ? 'task' : 'participant'}.md`;
    const showIntroduction = isTasks && !selected;
    for (const id of ['arena-intro', 'arena-positioning', 'arena-growth', 'arena-faq']) if ($(id)) $(id).hidden = !showIntroduction;
    $('arena-page-heading').hidden = showIntroduction;
    catalogDisclosure(current);
    for (const node of doc.querySelectorAll('[data-arena-view]')) {
      if (node.dataset.arenaView === current.view) node.setAttribute('aria-current', 'page'); else node.removeAttribute('aria-current');
    }
    summary();
    $('arena-atlas').hidden = !isTasks || Boolean(selected);
    if (isTasks && !selected) renderArenaAtlas($('arena-atlas'), {
      catalog: state.catalog, insights: state.insights, searchFamilies: state.searchFamilies, current, errors: state.errors, loading: state.loading,
      onFilter: filterCatalog,
      onTask: id => navigate(route({task: id}), {focus: true}),
      onModeChange: mode => navigate(route({atlas: mode === 'methods' ? null : mode})),
    });
    $('arena-insights').hidden = !isTasks || Boolean(selected);
    $('arena-statistics').hidden = !isTasks || Boolean(selected);
    if (isTasks && !selected) renderArenaInsights($('arena-insights'), {
      insights: state.insights, references: state.references, catalog: state.catalog, current, analysisRoot: $('arena-analysis'), statisticsRoot: $('arena-statistics'),
      matchingTasks: state.catalog ? filterTasks(state.catalog.tasks, current, state) : [],
      errors: state.errors, loading: state.loading, onFilter: filterCatalog, onRetry: load,
    });
    const chips = $('arena-active-filters'); chips.replaceChildren();
    chips.hidden = !isTasks || !(current.domain || current.type || current.reference || current.search_family || current.family);
    if (!chips.hidden) {
      chips.append(element('span', '', 'Selected filters'));
      for (const [key, value, labels, prefix] of [['domain', current.domain, state.insights?.domains, 'Domain'], ['type', current.type, state.insights?.task_types, 'Type'], ['reference', current.reference, null, 'Reference'], ['search_family', current.search_family, state.searchFamilies?.groups, 'Search method'], ['family', current.family, null, 'Task family']]) {
        if (!value) continue;
        const label = labels?.find(item => item.id === value)?.label || ({__unspecified__: 'Unspecified', published: 'Published reference', baseline: 'Seed baseline', missing: 'No numeric reference', numeric: 'Numeric reference'}[value]) || words(value);
        const chip = element('div', 'arena-filter-chip'); chip.append(element('span', '', `${prefix}: ${label}`));
        const remove = button('×', () => navigate(route({[key]: null, page: null}), {catalog: true}), ''); remove.setAttribute('aria-label', `Remove ${prefix.toLowerCase()} filter: ${label}`); chip.append(remove); chips.append(chip);
      }
      if ((current.domain || current.type) && !state.insights || current.reference && !state.references || current.search_family && !state.searchFamilies) chips.append(element('span', '', 'Some filters await overview data; available catalog rows remain visible.'));
    }
    $('arena-scope').hidden = !dataset;
    $('arena-scope').textContent = isTasks ? 'Evaluation definitions and runtime integration are tracked separately. Original source declarations remain available in each task record.' : 'Research works identify methods and their original publications. Source-pinned registrations and framework integrations are tracked separately.';
    $('arena-error').hidden = !error; $('arena-error').replaceChildren();
    if (error) {
      $('arena-error').append(element('p', 'arena-error-message', `Could not load ${isTasks ? 'the task catalog' : 'participants'}. ${error}`), button('Try again', load));
    }
    $('arena-detail').hidden = !selected || !dataset;
    $('arena-list-panel').hidden = Boolean(selected && dataset);
    $('arena-pagination').hidden = true;
    $('arena-search').placeholder = `Search ${current.view}`;
    $('arena-search').setAttribute('aria-label', `Search ${current.view}`);
    if ($('arena-search').value !== current.query) $('arena-search').value = current.query;
    populateFamilies();
    $('arena-family').value = current.family; $('arena-protocol').value = current.protocol;
    $('family-filter-label').hidden = false; $('protocol-filter-label').hidden = !isTasks;
    $('arena-clear').hidden = !(current.query || current.family || current.protocol || current.domain || current.type || current.reference || current.search_family);
    $('arena-results-title').textContent = isTasks ? 'Task catalog' : 'Systems & research';
    $('arena-results').setAttribute('aria-busy', String(!dataset && !error));
    if (!dataset) {
      $('arena-result-count').textContent = error ? 'Unavailable' : 'Loading…'; $('arena-results').replaceChildren();
      if (error) empty($('arena-results'), 'Registry unavailable', 'Use Try again above to reload the registry.');
      else $('arena-results').append(element('div', 'loading', `Loading ${isTasks ? 'task definitions' : 'participants'}…`));
      finishCatalogHashNavigation();
      return;
    }
    if (selected) {
      if (isTasks) taskDetail(dataset.tasks.find(item => item.id === selected));
      else participantDetail(dataset.participants.find(item => item.id === selected));
    } else if (isTasks) taskResults(current); else participantResults(current);
    const sourceCount = state.catalog?.sources?.length;
    $('arena-source-note').textContent = sourceCount ? `Catalog records from ${sourceCount} pinned source${sourceCount === 1 ? '' : 's'}. Inspect a task for provenance.` : 'Versioned task definitions and participant registrations.';
    finishCatalogHashNavigation();
  }
  function populateFamilies() {
    const select = $('arena-family'); select.replaceChildren();
    const all = element('option', '', 'All families'); all.value = ''; select.append(all);
    if (locationState().view === 'participants') {
      const families = new Map((state.participants?.participants || []).filter(item => item.search_family).map(item => [item.search_family.id, item.search_family.label]));
      for (const [id, label] of families) { const option = element('option', '', label); option.value = id; select.append(option); }
      return;
    }
    for (const family of [...new Set((state.catalog?.tasks || []).map(task => task.family).filter(Boolean))].sort()) {
      const option = element('option', '', family); option.value = family; select.append(option);
    }
    if (state.catalog?.tasks.some(task => !task.family)) {
      const option = element('option', '', 'Unspecified'); option.value = '__unspecified__'; select.append(option);
    }
  }
  async function load() {
    const revision = ++loadRevision; state.loading = true; state.errors = {};
    // Metadata is promoted together after verifying the catalog revision.
    const metadata = {};
    state.insights = null; state.references = null; state.searchFamilies = null;
    render();
    await Promise.all(['catalog', 'participants', 'insights', 'references', 'searchFamilies'].map(async name => {
      try {
        const data = await fetchJSON(`/api/${name === 'searchFamilies' ? 'search-families' : name}`);
        if (name === 'searchFamilies') {
          if (!data || !Array.isArray(data.groups) || !data.task_annotations || data.groups.some(item => typeof item.id !== 'string' || typeof item.label !== 'string' || !Array.isArray(item.task_ids))) throw new Error('The server returned an invalid search-method map.');
        } else if (name === 'insights') {
          if (!data || !Array.isArray(data.domains) || !Array.isArray(data.task_types) || !data.task_annotations || typeof data.denominator?.task_count !== 'number' || [...data.domains, ...data.task_types].some(item => typeof item.id !== 'string' || typeof item.label !== 'string' || typeof item.total !== 'number')) throw new Error('The server returned an invalid scientific overview.');
        } else if (name === 'references') {
          if (!data || !Array.isArray(data.tasks) || data.tasks.some(item => !item || typeof item.task_id !== 'string' || !Array.isArray(item.anchors))) throw new Error('The server returned invalid reference evidence.');
        } else {
          const field = name === 'catalog' ? 'tasks' : 'participants';
          if (!data || !Array.isArray(data[field]) || data[field].some(item => !item || typeof item.id !== 'string')) throw new Error('The server returned an invalid registry.');
        }
        if (revision !== loadRevision) return;
        if (name === 'catalog' || name === 'participants') state[name] = data;
        else metadata[name] = data;
        if (name === 'catalog') populateFamilies();
      } catch (error) {
        if (revision !== loadRevision) return;
        state[name] = null; state.errors[name] = typeof error?.message === 'string' ? error.message : 'Request failed.';
      }
      if (revision === loadRevision) render();
    }));
    if (revision !== loadRevision) return;
    let digest;
    if (state.catalog && Object.values(metadata).some(data => data.catalog_digest)) {
      try { digest = await catalogDigest(state.catalog); } catch { /* Unverifiable metadata stays unavailable. */ }
    }
    if (revision !== loadRevision) return;
    for (const [name, data] of Object.entries(metadata)) {
      const digestMismatch = data.catalog_digest && data.catalog_digest !== digest;
      const bindingMismatch = data.catalog_binding && !state.catalog?.sources?.some(source => canonicalJSON(source) === canonicalJSON(data.catalog_binding));
      if (!state.catalog || digestMismatch || bindingMismatch) {
        state[name] = null;
        state.errors[name] = 'Metadata does not match the loaded catalog revision. Reload to fetch a consistent snapshot.';
      } else state[name] = data;
    }
    state.loading = false; render();
  }
  function updateFilters() {
    const current = locationState();
    navigate(route({q: $('arena-search').value, family: $('arena-family').value,
      protocol: current.view === 'tasks' ? $('arena-protocol').value : null, page: null, task: null, participant: null}), {replace: true, catalog: true});
  }
  $('arena-search').addEventListener('input', updateFilters);
  $('arena-family').addEventListener('change', updateFilters);
  $('arena-protocol').addEventListener('change', updateFilters);
  $('arena-filters').addEventListener('submit', event => { event.preventDefault(); updateFilters(); });
  $('arena-clear').addEventListener('click', () => navigate(route({q: null, family: null, protocol: null, domain: null, type: null, reference: null, search_family: null, page: null}), {replace: true, catalog: true}));
  doc.addEventListener('click', event => {
    const anchor = event.target.closest?.('a[href]');
    if (!anchor || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const url = new URL(anchor.href), currentURL = new URL(win.location.href);
    const hashTarget = url.origin === currentURL.origin && url.pathname === currentURL.pathname && url.search === currentURL.search ? catalogHashTarget(url) : null;
    if (hashTarget) {
      event.preventDefault(); navigate(anchor.href, {catalog: true, scrollCatalog: true, focus: true, target: hashTarget});
    } else if (anchor.matches('a[data-arena-route], a[data-arena-view]')) {
      const current = locationState();
      const backToCatalog = current.view === 'tasks' && current.task && url.searchParams.get('view') !== 'participants' && !url.searchParams.has('task');
      event.preventDefault(); navigate(anchor.href, {focus: true, catalog: Boolean(backToCatalog), scrollCatalog: Boolean(backToCatalog)});
    }
  });
  win.addEventListener('popstate', render);
  win.addEventListener('hashchange', () => {
    render();
    const target = catalogHashTarget();
    if (target) revealCatalog({scroll: true, target});
  });
  const ready = load();
  return {ready, reload: load, render};
}

if (typeof document !== 'undefined' && document.body.dataset.arenaApp === 'true') createArenaApp();
