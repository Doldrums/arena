const ACTIVE = new Set(['preparing', 'running']);
const ATTENTION = new Set(['failed', 'blocked']);
const STATES = new Set(['queued', 'preparing', 'running', 'completed', 'failed', 'blocked', 'cancelled']);
const KEY_STORAGE = 'arena.queue.session-key';

export function initQueue({doc = document, fetcher = (...args) => fetch(...args), storage = sessionStorage, pollMs = 5000} = {}) {
  const win = doc.defaultView, $ = id => doc.getElementById(id);
  let key = '', rows = [], templates = [], selected = '', stream = 'stdout', offset = 0, timer = null, busy = false, epoch = 0, detailEpoch = 0, submitId = '', destroyed = false;
  try { key = storage.getItem(KEY_STORAGE) || ''; } catch {}
  function element(tag, className, text) {
    const node = doc.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text ?? '');
    return node;
  }
  function status(text) { $('queue-status').textContent = text; }
  function close(id) { $(id).close(); }
  async function api(path, options = {}) {
    const response = await fetcher(path, {cache:'no-store', credentials:'same-origin', redirect:'error', ...options,
      headers:{'Authorization':`Bearer ${key}`, ...(options.body ? {'Content-Type':'application/json'} : {}), ...options.headers}});
    if (!response.ok) {
      const message = response.status === 401 ? 'The access key is missing, expired or revoked.' :
        response.status === 403 ? 'Your key does not allow this action or access to this run.' :
        response.status === 404 ? 'This queue endpoint or run is not available.' :
        response.status === 409 ? 'The queue changed. Refresh before trying again.' :
        `The request could not be completed (HTTP ${response.status}).`;
      throw new Error(message);
    }
    return response.json();
  }
  function badge(state) {
    const safeState = STATES.has(state) ? state : 'unknown';
    const node = element('span', 'queue-state', safeState.replaceAll('_', ' '));
    node.dataset.state = safeState;
    return node;
  }
  const time = value => typeof value === 'number' ? new Date(value * 1000).toLocaleString() : '—';
  function metrics(counts = {}) {
    const values = [['Queued', counts.queued || 0], ['Active', (counts.preparing || 0) + (counts.running || 0)],
      ['Completed', counts.completed || 0], ['Needs attention', (counts.failed || 0) + (counts.blocked || 0)]];
    $('queue-metrics').replaceChildren(...values.map(([label, count]) => {
      const article = element('article', 'queue-metric');
      article.append(element('span', '', label), element('strong', '', count));
      return article;
    }));
  }
  function renderList() {
    const search = $('queue-search').value.toLowerCase(), filter = $('queue-filter').value;
    const filtered = rows.filter(run => {
      const text = [run.label, run.framework, run.profile, run.model, run.batch_id, run.id].join(' ').toLowerCase();
      return text.includes(search) && (filter === 'all' || (filter === 'active' ? ACTIVE.has(run.state) : filter === 'attention' ? ATTENTION.has(run.state) : run.state === filter));
    });
    $('queue-list').replaceChildren(...filtered.map(run => {
      const row = element('button', 'queue-run'); row.type = 'button';
      row.setAttribute('aria-pressed', String(run.id === selected));
      const line = element('span', 'queue-run-line');
      line.append(element('span', 'queue-run-title', run.label || run.framework || run.template), badge(run.state));
      row.append(line, element('small', '', [run.framework, run.profile, run.model].filter(Boolean).join(' · ')),
        element('small', '', `${run.batch_id ? `${run.batch_id} · ` : ''}${time(run.created)}`));
      row.addEventListener('click', () => { selected = run.id; renderList(); refreshDetail(); });
      return row;
    }));
    if (!filtered.length) $('queue-list').append(element('p', 'queue-empty', rows.length ? 'No runs match these filters.' : 'No runs have been queued yet.'));
  }
  function detail(run) {
    const panel = $('queue-detail'), heading = element('div', 'queue-detail-heading');
    heading.append(element('h2', '', run.label || run.framework || run.template), badge(run.state));
    const fields = [['Run', run.id], ['Framework', run.framework], ['Profile', run.profile], ['Model', run.model],
      ['Batch', run.batch_id || '—'], ['Created', time(run.created)], ['Started', time(run.started)], ['Ended', time(run.ended)],
      ['Resources', `${run.resources?.cpus ?? '—'} CPU · ${run.resources?.memory_mb ? (run.resources.memory_mb / 1024).toFixed(1) : '—'} GiB · ${run.resources?.evaluation_slots ?? '—'} evaluation slots`],
      ['Evaluation', run.canonical_evaluation ? 'Canonical evaluation recorded' : 'Native framework evaluation'], ['Config revision', run.revision || '—']];
    const dl = element('dl'); fields.forEach(([name, value]) => dl.append(element('dt','',name), element('dd','',value)));
    panel.replaceChildren(heading, dl);
    if (run.reason) panel.append(element('p', 'run-reason', run.reason));
    if (run.cancel_requested) panel.append(element('p','run-reason','Cancellation requested. Resources stay reserved until the worker confirms the run has stopped.'));
    const logsHeading = element('div', 'queue-logs-heading'), select = element('select'); select.setAttribute('aria-label', 'Log stream');
    for (const [value, label] of [['stdout','Lifecycle'],['stderr','Worker errors'],['native_stdout','Framework output'],['native_stderr','Framework errors']]) { const option = element('option', '', label); option.value = value; select.append(option); }
    select.value = stream;
    select.addEventListener('change', () => { stream = select.value; refreshDetail(); });
    logsHeading.append(element('h3', '', 'Run logs'), select);
    const logs = element('pre', 'queue-logs', 'Loading logs…'); logs.id = 'queue-run-logs'; logs.setAttribute('aria-label','Run lifecycle logs');
    panel.append(logsHeading, logs, element('p','queue-log-note','Framework logs require additional access. Known credentials are redacted; native artifacts remain in private worker storage.'));
    if (ACTIVE.has(run.state) || run.state === 'queued') {
      const actions = element('div','queue-detail-actions'), cancel = element('button','', run.cancel_requested ? 'Cancellation requested' : 'Cancel run');
      cancel.type = 'button'; cancel.disabled = Boolean(run.cancel_requested);
      cancel.addEventListener('click', async () => {
        cancel.disabled = true;
        try { await api(`/api/queue/${encodeURIComponent(run.id)}/cancel`, {method:'POST',body:'{}'}); await refresh(); }
        catch (error) { status(error.message); cancel.disabled = false; }
      });
      actions.append(cancel); panel.append(actions);
    }
  }
  async function refreshDetail() {
    if (!key || !selected) return;
    const generation = ++detailEpoch, authEpoch = epoch, id = selected;
    try {
      const value = await api(`/api/queue/${encodeURIComponent(id)}`);
      if (destroyed || generation !== detailEpoch || authEpoch !== epoch || id !== selected) return;
      detail(value.run);
      try {
        const logs = await api(`/api/queue/${encodeURIComponent(id)}/logs?stream=${stream}&tail=true&limit=16384`);
        if (generation !== detailEpoch || authEpoch !== epoch || destroyed) return;
        const node = $('queue-run-logs');
        node.textContent = `${logs.truncated ? '… Earlier events omitted\n' : ''}${logs.text || 'No events recorded for this stream yet.'}`;
      } catch (error) { if (generation === detailEpoch && authEpoch === epoch && $('queue-run-logs')) $('queue-run-logs').textContent = error.message; }
    } catch (error) {
      if (generation === detailEpoch && authEpoch === epoch && !destroyed) $('queue-detail').replaceChildren(element('p','queue-empty',error.message));
    }
  }
  function templateNote() {
    const template = templates.find(item => item.id === $('queue-template').value);
    $('queue-template-note').textContent = template ? `${template.model} · ${template.resources?.cpus ?? '—'} CPU · ${((template.resources?.memory_mb || 0) / 1024).toFixed(1)} GiB reserved. ${template.status === 'blocked' ? template.blocked_reason || 'Configuration requires preparation.' : ''}` : 'No reviewed launch configuration is available for this key.';
    $('queue-submit').disabled = !template || template.status !== 'ready';
  }
  async function refresh() {
    if (!key || busy || destroyed) return;
    busy = true; const generation = epoch;
    try {
      const result = await api(`/api/queue?limit=200&offset=${offset}`);
      if (generation !== epoch || destroyed) return;
      rows = result.runs || []; metrics(result.counts); renderList();
      $('queue-prev').disabled = offset === 0;
      $('queue-next').disabled = offset + rows.length >= result.total;
      $('queue-page-note').textContent = result.total ? `${offset + 1}–${offset + rows.length} of ${result.total}` : '0 runs';
      const resources = result.resources || {}, used = resources.used || {}, limits = resources.limits || {};
      $('queue-capacity').textContent = `${used.active || 0} / ${limits.max_active ?? '—'} active runs · ${used.cpus || 0} / ${limits.cpus ?? '—'} CPU reserved · ${((used.memory_mb || 0) / 1024).toFixed(0)} / ${limits.memory_mb ? (limits.memory_mb / 1024).toFixed(0) : '—'} GiB · ${used.evaluation_slots || 0} / ${limits.evaluation_slots ?? '—'} evaluation slots`;
      status(`Updated ${new Date().toLocaleTimeString()}`);
      $('queue-connect').textContent = 'Access key'; $('queue-refresh').disabled = false;
      const resultTemplates = await api('/api/control/templates');
      if (generation !== epoch || destroyed) return;
      templates = resultTemplates.templates || [];
      $('queue-new').disabled = !templates.some(template => template.status === 'ready');
      await refreshDetail();
    } catch (error) { if (generation === epoch && !destroyed) status(error.message); }
    finally { busy = false; }
  }
  function disconnect() {
    epoch++; detailEpoch++; key = ''; selected = ''; rows = []; templates = []; offset = 0;
    try { storage.removeItem(KEY_STORAGE); } catch {}
    $('queue-key').value = ''; $('queue-connect').textContent = 'Connect with key'; $('queue-new').disabled = true; $('queue-refresh').disabled = true;
    $('queue-capacity').textContent = ''; metrics(); renderList();
    $('queue-prev').disabled = true; $('queue-next').disabled = true; $('queue-page-note').textContent = '';
    $('queue-detail').replaceChildren(element('p','queue-empty','Select a run to inspect its status and logs.'));
    status('Disconnected. The key and displayed run details have been cleared.');
  }
  $('queue-connect').addEventListener('click', () => { $('queue-key-error').textContent = ''; $('queue-key-dialog').showModal(); $('queue-key').focus(); });
  for (const node of doc.querySelectorAll('[data-close]')) node.addEventListener('click', () => close(node.dataset.close));
  $('queue-disconnect').addEventListener('click', () => { disconnect(); close('queue-key-dialog'); });
  $('queue-key-form').addEventListener('submit', async event => {
    event.preventDefault(); const value = $('queue-key').value.trim();
    if (!value || /[\r\n]/.test(value)) { $('queue-key-error').textContent = 'Enter a valid access key.'; return; }
    disconnect(); key = value;
    try { storage.setItem(KEY_STORAGE, key); } catch {}
    $('queue-key').value = ''; close('queue-key-dialog'); await refresh();
  });
  $('queue-refresh').addEventListener('click', refresh);
  $('queue-prev').addEventListener('click', () => { if (!busy) { offset = Math.max(0, offset - 200); refresh(); } });
  $('queue-next').addEventListener('click', () => { if (!busy) { offset += 200; refresh(); } });
  $('queue-search').addEventListener('input', renderList);
  $('queue-filter').addEventListener('change', renderList);
  $('queue-template').addEventListener('change', templateNote);
  $('queue-new').addEventListener('click', () => {
    $('queue-submit-error').textContent = ''; $('queue-label').value = '';
    submitId = win.crypto.randomUUID();
    $('queue-template').replaceChildren(...templates.map(template => {
      const option = element('option', '', `${template.name || template.framework || template.id} · ${template.model}${template.status === 'blocked' ? ' · Preparing' : ''}`);
      option.value = template.id; option.disabled = template.status !== 'ready'; return option;
    }));
    const ready = templates.find(template => template.status === 'ready'); if (ready) $('queue-template').value = ready.id;
    templateNote(); $('queue-submit-dialog').showModal();
  });
  $('queue-submit-form').addEventListener('submit', async event => {
    event.preventDefault(); const template = templates.find(item => item.id === $('queue-template').value);
    if (!template || template.status !== 'ready') return;
    const generation = epoch;
    $('queue-submit').disabled = true;
    try {
      const label = $('queue-label').value.trim();
      const result = await api('/api/queue', {method:'POST',body:JSON.stringify({schema:'arena.control-submit/1',template:template.id,model:template.model,...(label ? {label} : {}),idempotency_key:submitId})});
      if (generation !== epoch || destroyed) return;
      selected = result.run.id; close('queue-submit-dialog'); await refresh();
    } catch (error) { $('queue-submit-error').textContent = error.message; }
    finally { templateNote(); }
  });
  metrics(); if (key) refresh();
  if (pollMs > 0) timer = win.setInterval(() => { if (!doc.hidden) refresh(); }, pollMs);
  return {refresh, disconnect, destroy() { destroyed = true; epoch++; detailEpoch++; if (timer) win.clearInterval(timer); }};
}

if (typeof document !== 'undefined' && document.body?.dataset.queueApp === 'true') initQueue();
