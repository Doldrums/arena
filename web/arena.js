const REPOSITORY = 'https://github.com/Doldrums/arena';
const PAGE_SIZE = 25;
const PROTOCOL_LABELS = {
  original: 'Original', recreated_verified: 'Recreated · verified',
  recreated: 'Recreated', unsupported: 'Unsupported',
};
const textValue = value => value == null || value === '' ? 'Not specified' :
  typeof value === 'object' ? JSON.stringify(value) : String(value);
const words = value => textValue(value).replaceAll('_', ' ');

export function safeExternalURL(value) {
  if (typeof value !== 'string') return null;
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}

export function filterTasks(tasks, {query = '', family = '', protocol = ''} = {}) {
  const terms = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  return tasks.filter(task => (!family || task.family === family) &&
    (!protocol || task.protocol === protocol) && terms.every(term =>
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
  const state = {catalog: null, participants: null, errors: {}, loading: true};
  let loadRevision = 0;

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
      query: params.get('q') || '', family: params.get('family') || '',
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
  function navigate(href, {replace = false, focus = false} = {}) {
    win.history[replace ? 'replaceState' : 'pushState'](null, '', href);
    render();
    if (focus) $('main').focus({preventScroll: true});
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
    const metrics = [
      ['Task definitions', counts[0], 'Versioned evaluation contracts'],
      ['Executable definitions', counts[1], 'Runtime availability not yet verified'],
      ['Participants', state.participants?.participants.length ?? '—',
        state.participants?.summary?.integrated_count == null ? 'Integration status unavailable' : `${state.participants.summary.integrated_count} integrated drivers`],
    ];
    for (const [label, value, note] of metrics) {
      const metric = element('article', 'metric');
      metric.append(element('div', 'metric-label', label),
        element('div', 'metric-value', typeof value === 'number' ? value.toLocaleString('en-US') : value),
        element('div', 'metric-foot', note)); container.append(metric);
    }
    $('nav-task-count').textContent = tasks?.length.toLocaleString('en-US') ?? '';
    $('nav-participant-count').textContent = state.participants?.participants.length ?? '';
    $('arena-connection').textContent = state.loading ? 'Loading registry…' :
      Object.keys(state.errors).length ? 'Registry partly unavailable' : 'Registry loaded';
    $('arena-connection-dot').className = `connection-dot ${state.loading ? '' : Object.keys(state.errors).length ? 'error' : 'connected'}`;
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
    fact(facts, 'Executable definition', task.executable ? 'Present' : 'Not available');
    fact(facts, 'Runtime availability', words(task.runtime_readiness));
    fact(facts, 'Source status', words(task.declared_status)); holder.append(facts);
    if (source?.repository?.commit) fact(facts, 'Source revision', source.repository.commit);
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
    heading.append(title, badge(words(participant.registration_status)));
    holder.append(heading, element('p', 'arena-detail-description', participant.description || 'No description supplied.'));
    const facts = element('dl', 'arena-detail-facts');
    fact(facts, 'Registration', words(participant.registration_status));
    fact(facts, 'Arena adapter', words(participant.adapter_status));
    fact(facts, 'Source revision', participant.repository?.commit);
    for (const [label, key] of [['Native execution', 'native_run'], ['Canonical evaluation', 'canonical_evaluation'], ['Pause', 'pause'], ['Resume', 'resume']]) {
      const value = participant.capabilities?.[key]; fact(facts, label, value === true ? 'Available' : value === false ? 'Not integrated' : 'Not specified');
    }
    holder.append(facts);
    externalLinks(holder, [['Participant repository', participant.repository?.url], ['Propose an integration', `${REPOSITORY}/compare`]]);
    recordDetails(holder, participant);
  }
  function taskResults(current) {
    const tasks = filterTasks(state.catalog.tasks, current);
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
        element('td', 'arena-definition', task.executable ? 'Executable source' : 'Not executable'));
      body.append(row);
    }
    table.append(body); const wrapper = element('div', 'table-wrap'); wrapper.append(table); results.append(wrapper);
    const pagination = $('arena-pagination'); pagination.replaceChildren(); pagination.hidden = pages <= 1;
    pagination.append(element('span', '', `Page ${page} of ${pages}`));
    const controls = element('div');
    const previous = button('← Previous', () => navigate(route({page: page - 1}), {focus: true})); previous.disabled = page === 1;
    const next = button('Next →', () => navigate(route({page: page + 1}), {focus: true})); next.disabled = page === pages;
    controls.append(previous, next); pagination.append(controls);
  }
  function participantResults(current) {
    const terms = current.query.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
    const all = state.participants.participants;
    const participants = all.filter(item => terms.every(term => [item.id, item.name, item.description].join(' ').toLocaleLowerCase().includes(term)));
    $('arena-result-count').textContent = `${participants.length} of ${all.length} participants`;
    const results = $('arena-results'); results.replaceChildren();
    if (!participants.length) { empty(results, all.length ? 'No participants match your search' : 'No participants registered', all.length ? 'Try another name or clear the search.' : 'Propose a participant through a pull request.'); return; }
    const grid = element('div', 'arena-participants');
    for (const item of participants) {
      const card = element('article', 'arena-participant');
      const title = element('h3'); title.append(link(item.name || item.id, route({participant: item.id}), 'arena-task-link', true));
      const status = element('div', 'arena-participant-status'); status.append(badge(words(item.registration_status)), badge(`Adapter: ${words(item.adapter_status)}`));
      card.append(title, status, element('p', '', item.description || 'No description supplied.'),
        link('View participant →', route({participant: item.id}), 'inline-link', true)); grid.append(card);
    }
    results.append(grid);
  }
  function render() {
    const current = locationState(), isTasks = current.view === 'tasks';
    const dataset = isTasks ? state.catalog : state.participants;
    const error = state.errors[isTasks ? 'catalog' : 'participants'];
    const selected = isTasks ? current.task : current.participant;
    const viewName = isTasks ? 'Tasks' : 'Participants';
    doc.title = `Arena · ${viewName}`;
    $('arena-title').textContent = viewName; $('arena-breadcrumb').textContent = viewName;
    $('arena-subtitle').textContent = isTasks ? 'Browse tasks and inspect their evaluation contracts.' : 'Research systems and their Arena integration status.';
    $('arena-contribute').textContent = isTasks ? 'Add a task ↗' : 'Add a participant ↗';
    for (const node of doc.querySelectorAll('[data-arena-view]')) {
      if (node.dataset.arenaView === current.view) node.setAttribute('aria-current', 'page'); else node.removeAttribute('aria-current');
    }
    summary();
    $('arena-scope').hidden = !dataset;
    $('arena-scope').textContent = isTasks ? 'Executable definitions are listed separately from runtime availability. Original, recreated and unsupported protocols retain their source labels.' : 'Registrations and execution capabilities are separate. Planned participants cannot be launched from this read-only board.';
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
    $('arena-family').value = current.family; $('arena-protocol').value = current.protocol;
    $('family-filter-label').hidden = !isTasks; $('protocol-filter-label').hidden = !isTasks;
    $('arena-clear').hidden = !(current.query || current.family || current.protocol);
    $('arena-results-title').textContent = isTasks ? 'Task catalog' : 'Participant registry';
    $('arena-results').setAttribute('aria-busy', String(!dataset && !error));
    if (!dataset) {
      $('arena-result-count').textContent = error ? 'Unavailable' : 'Loading…'; $('arena-results').replaceChildren();
      if (error) empty($('arena-results'), 'Registry unavailable', 'Use Try again above to reload the registry.');
      else $('arena-results').append(element('div', 'loading', `Loading ${isTasks ? 'task definitions' : 'participants'}…`));
      return;
    }
    if (selected) {
      if (isTasks) taskDetail(dataset.tasks.find(item => item.id === selected));
      else participantDetail(dataset.participants.find(item => item.id === selected));
    } else if (isTasks) taskResults(current); else participantResults(current);
    const sourceCount = state.catalog?.sources?.length;
    $('arena-source-note').textContent = sourceCount ? `Catalog records from ${sourceCount} pinned source${sourceCount === 1 ? '' : 's'}. Inspect a task for provenance.` : 'Versioned task definitions and participant registrations.';
  }
  function populateFamilies() {
    const select = $('arena-family'); select.replaceChildren();
    const all = element('option', '', 'All families'); all.value = ''; select.append(all);
    for (const family of [...new Set((state.catalog?.tasks || []).map(task => task.family).filter(Boolean))].sort()) {
      const option = element('option', '', family); option.value = family; select.append(option);
    }
  }
  async function load() {
    const revision = ++loadRevision; state.loading = true; state.errors = {}; render();
    await Promise.all(['catalog', 'participants'].map(async name => {
      try {
        const data = await fetchJSON(`/api/${name}`);
        const field = name === 'catalog' ? 'tasks' : 'participants';
        if (!data || !Array.isArray(data[field]) || data[field].some(item => !item || typeof item.id !== 'string')) throw new Error('The server returned an invalid registry.');
        if (revision !== loadRevision) return;
        state[name] = data;
        if (name === 'catalog') populateFamilies();
      } catch (error) {
        if (revision !== loadRevision) return;
        state[name] = null; state.errors[name] = typeof error?.message === 'string' ? error.message : 'Request failed.';
      }
      if (revision === loadRevision) render();
    }));
    if (revision === loadRevision) { state.loading = false; render(); }
  }
  function updateFilters() {
    const current = locationState();
    navigate(route({q: $('arena-search').value, family: current.view === 'tasks' ? $('arena-family').value : null,
      protocol: current.view === 'tasks' ? $('arena-protocol').value : null, page: null, task: null, participant: null}), {replace: true});
  }
  $('arena-search').addEventListener('input', updateFilters);
  $('arena-family').addEventListener('change', updateFilters);
  $('arena-protocol').addEventListener('change', updateFilters);
  $('arena-filters').addEventListener('submit', event => { event.preventDefault(); updateFilters(); });
  $('arena-clear').addEventListener('click', () => navigate(route({q: null, family: null, protocol: null, page: null}), {replace: true}));
  doc.addEventListener('click', event => {
    const anchor = event.target.closest?.('a[data-arena-route], a[data-arena-view]');
    if (!anchor || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault(); navigate(anchor.href, {focus: true});
  });
  win.addEventListener('popstate', render);
  const ready = load();
  return {ready, reload: load, render};
}

if (typeof document !== 'undefined' && document.body.dataset.arenaApp === 'true') createArenaApp();
