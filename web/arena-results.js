import {initResultsOverview} from './arena-results-overview.js';

const KEY_STORAGE = 'arena.queue.session-key';
const STATES = new Set(['queued', 'preparing', 'running', 'completed', 'failed', 'blocked', 'cancelled']);
const finite = value => typeof value === 'number' && Number.isFinite(value);
const count = value => finite(value) && Number.isSafeInteger(value) && value >= 0;
const number = value => finite(value) ? new Intl.NumberFormat('en', {maximumSignificantDigits:6}).format(value) : '—';
const plural = (value, word) => `${number(value)} ${word}${value === 1 ? '' : 's'}`;
const duration = seconds => !finite(seconds) || seconds < 0 ? '—' : seconds < 60 ? `${number(seconds)} s` : seconds < 3600 ? `${number(seconds / 60)} min` : `${number(seconds / 3600)} h`;
const systemName = id => ({'sciel-release':'SCiEL · private image', sciel:'SCiEL · source'})[id] || id || 'Unknown system';
const canonical = run => run.metrics?.canonical || {};
const usage = run => run.metrics?.usage || {};
const isSciel = run => run.framework === 'sciel-release' || run.framework === 'sciel';
const comparableKey = run => {
  const c = canonical(run);
  return typeof c.cohort === 'string' && c.cohort && typeof c.task_id === 'string' && c.task_id &&
    typeof c.metric === 'string' && c.metric && ['maximize','minimize'].includes(c.direction)
    ? JSON.stringify([c.cohort,c.task_id,c.metric,c.direction]) : '';
};
const budget = run => {
  const b = run.metrics?.budget || {};
  if (count(b.generation_calls)) return {value:b.generation_calls,label:'Generation-call limit'};
  if (count(b.evaluations)) return {value:b.evaluations,label:b.label || 'Evaluation budget'};
  return null;
};

export function initResults({doc = document, fetcher = (...args) => fetch(...args), storage = sessionStorage, pollMs = 30000} = {}) {
  const win = doc.defaultView, $ = id => doc.getElementById(id);
  let key = '', rows = [], filtered = [], payload = null, epoch = 0, pending = null, timer = null, destroyed = false;
  const listeners = [];
  let published = null, controlAvailable = null, capabilityController = null;
  try { key = storage.getItem(KEY_STORAGE) || ''; } catch {}
  function on(node, event, callback) { node.addEventListener(event,callback); listeners.push(() => node.removeEventListener(event,callback)); }
  function element(tag, className, text) {
    const node = doc.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text ?? '');
    return node;
  }
  function note(parent, text) { parent.append(element('small','cell-note',text)); }
  function status(text) { $('results-status').textContent = text; }
  function access(connected) {
    doc.body.dataset.resultsAccess = connected ? 'connected' : 'overview';
    doc.dispatchEvent(new win.CustomEvent('arena:results-access',{detail:{connected}}));
  }
  function showPublished(message = 'Published results') {
    $('private-results-content').hidden = true;
    $('published-results-overview').hidden = false;
    $('results-refresh').hidden = true;
    $('results-connect').hidden = controlAvailable !== true;
    $('results-connect').textContent = key ? 'Access key' : 'Connect with key';
    $('results-intro').textContent = 'Recorded results across research tasks, systems and models.';
    $('results-footer-scope').textContent = 'Published results · read only';
    status(message); access(false);
    if (!published) published = initResultsOverview({doc,fetcher,storage,pollMs,rootId:'published-results-overview'});
  }
  function showPrivate() {
    access(true); published?.destroy(); published = null;
    $('published-results-overview').replaceChildren(); $('published-results-overview').hidden = true;
    $('private-results-content').hidden = false;
    $('results-refresh').hidden = false; $('results-connect').hidden = false;
    $('results-footer-scope').textContent = 'Private workspace · recorded results only';
  }
  async function discoverControl() {
    if (destroyed || capabilityController || controlAvailable !== null) return;
    const controller = new win.AbortController(); capabilityController = controller;
    const timeout = win.setTimeout(() => controller.abort(),10000);
    try {
      const response = await fetcher('/api/health',{cache:'no-store',credentials:'same-origin',redirect:'error',signal:controller.signal});
      const health = response.ok ? await response.json() : null;
      if (destroyed || controller.signal.aborted || controlAvailable !== null) return;
      controlAvailable = health?.component === 'arena' && health.mode === 'private_control' && health.capabilities?.launch === true;
      $('results-connect').hidden = !controlAvailable;
    } catch {} finally { win.clearTimeout(timeout); if (capabilityController === controller) capabilityController = null; }
  }
  function configureOptions(id, values, initial) {
    const select = $(id), previous = select.value;
    select.replaceChildren(...[...initial,...values].map(([value,label]) => { const item = element('option','',label); item.value = value; return item; }));
    if ([...select.options].some(option => option.value === previous)) select.value = previous;
  }
  function filterOptions() {
    const frameworks = [...new Set(rows.map(row => row.framework).filter(value => typeof value === 'string' && value !== 'sciel-release'))].sort();
    configureOptions('results-framework',frameworks.map(id => [id,systemName(id)]),[['sciel-release','SCiEL · private image'],['all','All systems']]);
    const models = [...new Set(rows.map(row => row.model).filter(value => typeof value === 'string'))].sort();
    configureOptions('results-model',models.map(value => [value,value]),[['all','All models']]);
  }
  function metric(label, value, description, accent = '') {
    const node = element('article','result-metric'); if (accent) node.dataset.accent = accent;
    node.append(element('span','result-metric-label',label),element('strong','result-metric-value',value),element('p','result-metric-note',description));
    return node;
  }
  function overview() {
    const recorded = filtered.filter(run => count(canonical(run).evaluations) && canonical(run).evaluations > 0);
    const knownValidity = filtered.filter(run => count(canonical(run).valid) && count(canonical(run).invalid) && count(canonical(run).evaluations) && canonical(run).evaluations > 0);
    const valid = knownValidity.reduce((sum,run) => sum + canonical(run).valid,0);
    const invalid = knownValidity.reduce((sum,run) => sum + canonical(run).invalid,0);
    const unknown = recorded.reduce((sum,run) => {
      const c = canonical(run);
      return sum + (count(c.valid) && count(c.invalid) ? Math.max(0,c.evaluations - c.valid - c.invalid) : c.evaluations);
    },0);
    const distinct = filtered.filter(run => count(canonical(run).unique_valid_candidates) && count(canonical(run).evaluations) && canonical(run).evaluations > 0);
    const candidates = distinct.reduce((sum,run) => sum + canonical(run).unique_valid_candidates,0);
    const hashed = recorded.filter(run => Array.isArray(canonical(run).valid_candidate_hashes));
    const programHashes = new Set(hashed.flatMap(run => canonical(run).valid_candidate_hashes).filter(value => typeof value === 'string' && /^[a-f0-9]{64}$/i.test(value)).map(value => value.toLowerCase()));
    const models = new Set(filtered.map(run => run.model).filter(Boolean));
    const modelsWithValid = new Set(filtered.filter(run => count(canonical(run).valid) && canonical(run).valid > 0).map(run => run.model).filter(Boolean));
    const budgets = filtered.map(budget).filter(Boolean), labels = [...new Set(budgets.map(item => item.label))];
    const limits = [...new Set(budgets.map(item => item.value))].sort((a,b) => a-b);
    const budgetValue = labels.length === 1 && limits.length ? limits.length === 1 ? number(limits[0]) : `${number(limits[0])}–${number(limits.at(-1))}` : budgets.length ? 'Mixed' : '—';
    $('results-overview').replaceChildren(
      metric('Models with valid evidence',models.size ? `${modelsWithValid.size} / ${models.size}` : '—','At least one valid canonical receipt per model; includes all visible process statuses.'),
      metric('Recorded candidate validity',valid + invalid > 0 ? `${number(valid)} / ${number(valid + invalid)}` : '—',`${valid + invalid > 0 ? 'Valid / classified receipts. ' : 'No classified receipts. '}${unknown ? `${plural(unknown,'receipt')} with unknown validity. ` : ''}${plural(filtered.length - recorded.length,'run')} without canonical receipts.`),
      metric(hashed.length ? 'Distinct valid programs' : 'Within-run valid candidates',hashed.length ? number(programHashes.size) : distinct.length ? number(candidates) : '—',hashed.length ? `Deduplicated by program hash across visible runs.${hashed.length < recorded.length ? ` Hash lists are unavailable for ${plural(recorded.length-hashed.length,'run')}; this count is partial.` : ''} Includes the seed when it has a valid receipt.` : `Counted within each run, then summed. Repeated candidates across runs remain separate.${distinct.length < recorded.length ? ' Some runs lack candidate identity counts.' : ''}`),
      metric('Configured search budget',budgetValue,labels.length === 1 ? `${labels[0]}. Recorded for ${budgets.length} of ${filtered.length} visible runs; not a count of all model requests.` : budgets.length ? 'Different budget types. See each run’s configured limit below.' : 'No confirmed budget is available for the visible runs.','amber')
    );
  }
  function scoreCell(run) {
    const c = canonical(run), native = run.metrics?.native || {};
    const paired = Array.isArray(native.population_objectives) && native.population_objectives.length > 0 && Array.isArray(native.objectives) && native.objectives.length > 0;
    const showNative = !(count(c.evaluations) && c.evaluations > 0) && !finite(c.best_score) && (finite(native.best_score) || paired);
    const score = showNative ? native : c, cell = element('td'), pair = element('span','score-pair');
    if (showNative && paired && !finite(score.best_score)) {
      cell.append(element('strong','native-paired-title',`${plural(native.objectives.length,'objective')}`));
    } else if (showNative && !finite(score.seed_score)) {
      pair.append(element('strong','',number(score.best_score))); cell.append(pair);
    } else {
      pair.append(element('span','',number(score.seed_score)),element('span','score-arrow','→'),element('strong','',number(score.best_score))); cell.append(pair);
    }
    if (showNative) cell.append(element('span','score-scope','Native'));
    else if (finite(score.best_score)) {
      const scope = element('span','score-scope','Best single evaluation');
      scope.title = 'Best valid individual evaluator receipt, including individual confirmation trials; not a confirmed mean or a published reference result.';
      cell.append(scope);
    }
    if (score.metric) note(cell,`${score.metric}${score.direction === 'maximize' ? ' · higher is better' : score.direction === 'minimize' ? ' · lower is better' : ''}`);
    if (!showNative && score.protocol) note(cell,`Evaluator protocol: ${score.protocol}`);
    if (showNative) note(cell,score.task || 'Native task not recorded');
    if (showNative && typeof score.score_kind === 'string') note(cell,score.score_kind);
    if (showNative && paired && !finite(score.best_score)) {
      note(cell,`${plural(native.population_objectives.length,'paired population record')} · inspect evidence`);
      return cell;
    }
    if (finite(score.seed_score) && finite(score.best_score) && ['maximize','minimize'].includes(score.direction)) {
      const difference = score.direction === 'maximize' ? score.best_score - score.seed_score : score.seed_score - score.best_score;
      note(cell,difference === 0 ? 'No measured gain over seed' : difference > 0 ? `Gain over seed: ${number(difference)}` : 'Recorded best is below the seed');
    } else note(cell,finite(score.best_score) ? 'Seed comparison unavailable' : 'No canonical score recorded');
    return cell;
  }
  function evidence(run) {
    const detail = element('details','run-evidence'), c = canonical(run), n = run.metrics?.native || {}, e = run.metrics?.evidence || {};
    const issues = Array.isArray(e.issues) ? e.issues.filter(value => typeof value === 'string') : [];
    detail.append(element('summary','',issues.length ? `Evidence · ${plural(issues.length,'issue')}` : 'Evidence ↗'));
    const dl = element('dl');
    const fields = [['Run ID',run.id],['Profile',run.profile],['Batch',run.batch_id || '—'],['Task',c.task_name || c.task_id || '—'],['Canonical records',c.status || 'missing'],['Evaluator cohort',c.cohort || '—'],['Process return code',run.returncode ?? '—'],['Artifacts',count(e.artifact_count) ? number(e.artifact_count) : '—'],['Native score',`${number(n.best_score)}${n.metric ? ` · ${n.metric}` : ''}`],['Native task / scope',[n.task,n.scope || 'native'].filter(Boolean).join(' · ')],['Native direction',n.direction || '—'],['Provider receipts',count(usage(run).requests) ? plural(usage(run).requests,'recorded request') : 'Unknown'],['Token coverage',usage(run).complete === true ? 'Complete for the inspected provider ledger' : 'Partial or not recorded']];
    if (typeof n.score_kind === 'string') fields.push(['Native score definition',n.score_kind]);
    if (count(n.candidates)) fields.push(['Stored native candidates',number(n.candidates)]);
    if (typeof n.candidate_count_scope === 'string') fields.push(['Candidate-count scope',n.candidate_count_scope]);
    if (count(n.iterations)) fields.push(['Native iteration value',number(n.iterations)]);
    if (typeof n.iteration_count_scope === 'string') fields.push(['Iteration-count scope',n.iteration_count_scope]);
    if (count(n.native_generation)) fields.push(['Stored native generation',number(n.native_generation)]);
    if (count(n.population_size)) fields.push(['Native population size',number(n.population_size)]);
    if (n.named_metrics && typeof n.named_metrics === 'object' && !Array.isArray(n.named_metrics)) {
      for (const [name,value] of Object.entries(n.named_metrics)) if (finite(value)) fields.push([`Native · ${name}`,number(value)]);
    }
    for (const [name,value] of fields) dl.append(element('dt','',name),element('dd','',value));
    detail.append(dl);
    const objectives = Array.isArray(n.objectives) ? n.objectives.filter(value => value && typeof value.metric === 'string') : [];
    if (objectives.length && Array.isArray(n.population_objectives) && n.population_objectives.length) {
      const section = element('div','native-objectives');
      section.append(element('p','cell-note','Paired native population objectives · source order'));
      for (const objective of objectives) section.append(element('p','cell-note',`${objective.metric} · ${objective.direction === 'maximize' ? 'higher is better' : objective.direction === 'minimize' ? 'lower is better' : 'direction not recorded'}`));
      const values = element('ol','native-objective-pairs'); values.tabIndex = 0; values.setAttribute('aria-label','Paired native population objectives');
      for (const point of n.population_objectives) {
        const item = element('li');
        for (const objective of objectives) item.append(element('span','',`${objective.metric}: ${number(point?.[objective.metric])}`));
        values.append(item);
      }
      section.append(values); detail.append(section);
    }
    if (issues.length) { const list = element('ul'); for (const issue of issues) list.append(element('li','',issue)); detail.append(list); }
    const hashes = Array.isArray(c.receipt_hashes) ? c.receipt_hashes.filter(value => typeof value === 'string' && /^[a-f0-9]{64}$/i.test(value)) : [];
    if (hashes.length) {
      detail.append(element('p','cell-note',`${plural(hashes.length,'canonical receipt hash')} · SHA-256`));
      const pre = element('pre','receipt-hashes',hashes.join('\n')); pre.tabIndex = 0; pre.setAttribute('aria-label','Canonical receipt SHA-256 hashes'); detail.append(pre);
    }
    const nativeHashes = Array.isArray(n.evidence_hashes) ? n.evidence_hashes.filter(value => typeof value === 'string' && /^[a-f0-9]{64}$/i.test(value)) : [];
    if (nativeHashes.length) {
      detail.append(element('p','cell-note',`${plural(nativeHashes.length,'native artifact hash')} · SHA-256`));
      const pre = element('pre','receipt-hashes',nativeHashes.join('\n')); pre.tabIndex = 0; pre.setAttribute('aria-label','Native artifact SHA-256 hashes'); detail.append(pre);
    }
    return detail;
  }
  function matrix() {
    const openRuns = new Set([...$('results-matrix').querySelectorAll('tr[data-run-id]')].filter(row => row.querySelector('details[open]')).map(row => row.dataset.runId));
    $('matrix-eyebrow').textContent = $('results-framework').value === 'all' ? 'ALL SYSTEMS · RECORDED RUNS' : systemName($('results-framework').value).toUpperCase();
    $('results-count').textContent = plural(filtered.length,'run');
    const container = $('results-matrix');
    if (!filtered.length) { container.removeAttribute('tabindex'); container.replaceChildren(element('p','empty',rows.length ? 'No runs match these filters. Choose All systems or adjust the model and status filters.' : 'No recorded runs are available for this access key.')); return; }
    container.tabIndex = 0; container.setAttribute('role','region'); container.setAttribute('aria-label','Run results; scroll horizontally for all evidence columns');
    const table = element('table'), head = element('thead'), header = element('tr'), body = element('tbody');
    table.append(element('caption','','Runs, canonical evidence and recorded budgets. Scores are comparable only within the same evaluator cohort.'));
    for (const label of ['System / model','Process','Canonical validity','Score / seed reference','Valid candidates','Configured budget','Recorded resources','Provenance']) { const th = element('th','',label); th.scope = 'col'; header.append(th); }
    head.append(header);
    for (const run of filtered) {
      const row = element('tr'); row.dataset.runId = run.id;
      const identity = element('td'); identity.append(element('strong','run-identity',systemName(run.framework)),element('span','run-model',run.model || 'Model not recorded'));
      note(identity,canonical(run).task_name || canonical(run).task_id || run.metrics?.native?.task || run.profile || 'Task not recorded');
      note(identity,run.label || run.id);
      const process = element('td'), state = STATES.has(run.state) ? run.state : 'unknown', badge = element('span','run-state',state); badge.dataset.state = state; process.append(badge); note(process,run.returncode === 0 ? 'Process exit 0' : Number.isInteger(run.returncode) ? `Process exit ${run.returncode}` : 'Exit code not recorded');
      const c = canonical(run), validity = element('td');
      if (count(c.evaluations) && c.evaluations > 0) {
        validity.append(element('span','',`${count(c.valid) ? number(c.valid) : '—'} valid · ${count(c.invalid) ? number(c.invalid) : '—'} invalid`));
        note(validity,`${plural(c.evaluations,'receipt')}${c.status === 'partial' ? ' · partial evidence' : ''}`);
        const unknown = count(c.valid) && count(c.invalid) ? c.evaluations - c.valid - c.invalid : null;
        if (count(unknown) && unknown > 0) note(validity,`${number(unknown)} with unknown validity`);
      } else { validity.append(element('span','','—')); note(validity,'No canonical receipts'); }
      const distinct = element('td','',count(c.unique_valid_candidates) && count(c.evaluations) && c.evaluations > 0 ? number(c.unique_valid_candidates) : '—'); note(distinct,'Distinct within this run');
      const configured = budget(run), limit = element('td','',configured ? number(configured.value) : '—'); note(limit,configured?.label || 'No confirmed limit');
      const resources = element('td'), u = usage(run);
      resources.append(element('span','',count(u.total_tokens) ? `${number(u.total_tokens)} tokens` : 'Tokens not recorded'));
      if (count(u.total_tokens) && u.complete !== true) note(resources,'Partial token coverage');
      note(resources,`${duration(run.metrics?.wall_seconds)} wall time`);
      if (count(u.requests)) note(resources,plural(u.requests,'recorded request'));
      const provenance = element('td'), details = evidence(run); details.open = openRuns.has(run.id); provenance.append(details);
      row.append(identity,process,validity,scoreCell(run),distinct,limit,resources,provenance); body.append(row);
    }
    table.append(head,body); container.replaceChildren(table);
  }
  function cohortOptions() {
    const groups = new Map();
    for (const run of filtered) { const key = comparableKey(run); if (key && !groups.has(key)) groups.set(key,canonical(run)); }
    configureOptions('results-cohort',[...groups].map(([key,c]) => [key,`${c.task_name || c.task_id} · ${c.metric} · ${c.direction === 'maximize' ? 'higher' : 'lower'} is better · ${c.cohort.slice(0,10)}`]),groups.size ? [] : [['','No recorded cohort']]);
    $('results-cohort').disabled = !groups.size;
  }
  function chart() {
    const panel = $('results-chart'), cohort = $('results-cohort').value, axis = doc.querySelector('input[name="results-axis"]:checked')?.value || 'tokens';
    const members = filtered.filter(run => comparableKey(run) && comparableKey(run) === cohort);
    const points = members.filter(run => finite(canonical(run).best_score) && (axis === 'tokens' ? count(usage(run).total_tokens) && usage(run).complete === true : finite(run.metrics?.wall_seconds) && run.metrics.wall_seconds >= 0));
    panel.replaceChildren();
    if (!points.length) { panel.append(element('p','empty',members.length ? `No paired canonical score and ${axis === 'tokens' ? 'complete recorded-ledger token count' : 'wall-time measurement'} for this cohort. Unknown or partial values are not plotted.` : 'Choose runs with a recorded task, metric, direction and evaluator cohort to inspect score and resources.')); return; }
    const c = canonical(points[0]), xValue = run => axis === 'tokens' ? usage(run).total_tokens : run.metrics.wall_seconds;
    const xs = points.map(xValue), ys = points.map(run => canonical(run).best_score), minX = Math.min(0,...xs), maxX = Math.max(...xs) || 1;
    const low = Math.min(...ys), high = Math.max(...ys), pad = (high - low) * .12 || Math.max(Math.abs(high) * .05,.05), minY = low-pad, maxY = high+pad;
    const width = 1050, left = 80, right = 45, top = 30, bottom = 65, height = 330;
    const x = value => left + (value-minX)/(maxX-minX)*(width-left-right), y = value => top + (maxY-value)/(maxY-minY)*(height-top-bottom);
    const svg = doc.createElementNS('http://www.w3.org/2000/svg','svg'); svg.setAttribute('viewBox',`0 0 ${width} ${height}`); svg.setAttribute('class','scatter'); svg.setAttribute('role','img'); svg.setAttribute('aria-label',`${c.metric} versus ${axis === 'tokens' ? 'recorded tokens' : 'wall time'}. ${points.length} runs. Exact values follow in the legend.`);
    function svgNode(tag, attributes, text) { const node = doc.createElementNS('http://www.w3.org/2000/svg',tag); for (const [key,value] of Object.entries(attributes)) node.setAttribute(key,String(value)); if (text !== undefined) node.textContent = text; svg.append(node); return node; }
    for (let step = 0; step <= 4; step++) {
      const value = minY + (maxY-minY)*step/4, pos = y(value);
      svgNode('line',{x1:left,x2:width-right,y1:pos,y2:pos,class:'grid-line'});
      svgNode('text',{x:left-10,y:pos+4,'text-anchor':'end'},number(value));
      const xv = minX+(maxX-minX)*step/4;
      svgNode('text',{x:x(xv),y:height-bottom+22,'text-anchor':'middle'},axis === 'tokens' ? number(xv) : duration(xv));
    }
    svgNode('line',{x1:left,x2:width-right,y1:height-bottom,y2:height-bottom,class:'axis'});
    svgNode('text',{x:left,y:15},`Best single evaluation · ${c.metric} · ${c.direction === 'maximize' ? 'higher' : 'lower'} is better`);
    svgNode('text',{x:width/2,y:height-10,'text-anchor':'middle'},axis === 'tokens' ? 'Recorded tokens · complete ledger coverage only' : 'Recorded wall time');
    const legend = element('ol','plot-key');
    points.forEach((run,index) => {
      const px = x(xValue(run)), py = y(canonical(run).best_score), circle = svgNode('circle',{cx:px,cy:py,r:6,class:`point${isSciel(run) ? ' sciel' : ''}`});
      const title = doc.createElementNS('http://www.w3.org/2000/svg','title'); title.textContent = `${index+1}. ${systemName(run.framework)} · ${run.model}: Best single evaluation ${number(canonical(run).best_score)}, ${axis === 'tokens' ? `${number(xValue(run))} tokens` : duration(xValue(run))}`; circle.append(title);
      svgNode('text',{x:px+9,y:py-9,class:'point-label'},String(index+1));
      const item = element('li'); item.append(element('strong','',`${index+1}. ${systemName(run.framework)} · ${run.model || 'Unknown model'}`),element('small','',`${number(canonical(run).best_score)} ${c.metric} · ${axis === 'tokens' ? `${number(xValue(run))} tokens` : duration(xValue(run))} · ${run.state}`),element('small','',run.id)); legend.append(item);
    });
    panel.append(element('p','plot-description',`Best single evaluation per run, including individual confirmation trials; not confirmed means or published reference results.${c.protocol ? ` Evaluator protocol: ${c.protocol}.` : ''} ${plural(points.length,'run')} plotted; ${members.length-points.length} omitted because paired measurements are unavailable or incomplete. Amber identifies SCiEL. Points can overlap; every run is listed below.`));
    const plot = element('div','results-chart-plot'); plot.tabIndex = 0; plot.setAttribute('aria-label','Score and resource plot; scroll horizontally on small screens'); plot.append(svg); panel.append(plot,legend);
  }
  function render() {
    const framework = $('results-framework').value, model = $('results-model').value, state = $('results-state').value, search = $('results-search').value.toLowerCase();
    filtered = rows.filter(run => (framework === 'all' || run.framework === framework) && (model === 'all' || run.model === model) &&
      (state === 'all' || state === 'active' && ['queued','preparing','running'].includes(run.state) || state === 'attention' && ['failed','blocked'].includes(run.state) || run.state === state) &&
      [run.framework,run.model,run.profile,run.label,run.id,run.batch_id,canonical(run).task_id,canonical(run).task_name,run.metrics?.native?.task,run.metrics?.native?.metric].join(' ').toLowerCase().includes(search));
    $('results-intro').textContent = ['sciel-release','sciel'].includes(framework) ? 'SCiEL across models, tasks and search budgets.' : framework === 'all' ? 'Recorded outcomes across systems, models and research tasks.' : `${systemName(framework)} across models, tasks and search budgets.`;
    overview(); matrix(); cohortOptions(); chart();
    const notices = $('results-notices'); notices.replaceChildren();
    if (payload?.truncated) notices.append(element('p','',`This response is truncated: ${rows.length} of ${count(payload.total) ? number(payload.total) : 'all'} runs are shown. Summary and comparisons cover only the loaded runs.`));
    const methodology = $('results-measurement-notes'); methodology.replaceChildren();
    if (Array.isArray(payload?.notes)) for (const text of payload.notes) if (typeof text === 'string') methodology.append(element('p','',text));
    $('results-methodology').hidden = !methodology.childElementCount;
  }
  function clear(message) {
    rows = []; filtered = []; payload = null; filterOptions(); render();
    $('results-matrix').replaceChildren(element('p','empty',message));
  }
  async function refresh() {
    if (destroyed || pending) return;
    if (!key || controlAvailable === false) { if (!published) showPublished(); else await published.refresh(); return; }
    const generation = epoch, token = {}; pending = token;
    const controller = new win.AbortController(); token.controller = controller;
    const timeout = win.setTimeout(() => controller.abort(),30000);
    $('results-refresh').disabled = true;
    try {
      const response = await fetcher('/api/control/results',{cache:'no-store',credentials:'same-origin',redirect:'error',signal:controller.signal,headers:{Authorization:`Bearer ${key}`}});
      if (generation !== epoch || destroyed) return;
      if ([404,405,501].includes(response.status)) controlAvailable = false;
      else if (response.ok || [401,403].includes(response.status)) controlAvailable = true;
      if (!response.ok) throw new Error(response.status === 401 ? 'The access key is missing, expired or revoked.' : response.status === 403 ? 'This key does not have access to results.' : `Results could not be loaded (HTTP ${response.status}).`);
      const result = await response.json();
      if (generation !== epoch || destroyed) return;
      if (result.schema !== 'arena.results/1' || !Array.isArray(result.runs)) throw new Error('The results response has an unsupported format.');
      payload = result; rows = result.runs.filter(run => run && typeof run === 'object' && typeof run.id === 'string');
      filterOptions(); render(); showPrivate();
      const date = finite(result.generated_at) ? new Date(result.generated_at*1000) : null;
      status(`${result.scope === 'all' ? 'All accessible runs' : 'Your runs'} · ${date && !Number.isNaN(date.valueOf()) ? `Updated ${date.toLocaleTimeString()}` : 'Recorded evidence loaded'}`);
      $('results-connect').textContent = 'Access key';
    } catch (error) {
      if (generation === epoch && !destroyed) {
        clear('Private results are unavailable.');
        const reason = controlAvailable === false ? 'Published results' : error.name === 'AbortError' ? 'Private results timed out. Showing published results.' : `${error.message} Showing published results.`;
        showPublished(reason);
      }
    } finally {
      win.clearTimeout(timeout);
      if (pending === token) pending = null;
      if (generation === epoch && !destroyed) $('results-refresh').disabled = !key;
    }
  }
  function disconnect(showOverview = true) {
    epoch++; pending?.controller.abort(); pending = null; key = '';
    try { storage.removeItem(KEY_STORAGE); } catch {}
    $('results-key').value = ''; $('results-refresh').disabled = true; $('results-connect').textContent = 'Connect with key';
    clear('Private results cleared.');
    if (showOverview) { showPublished('Published results · private key disconnected.'); discoverControl(); }
  }
  on($('results-connect'),'click',() => { $('results-key-error').textContent = ''; $('results-key-dialog').showModal(); $('results-key').focus(); });
  on($('results-key-close'),'click',() => $('results-key-dialog').close());
  on($('results-disconnect'),'click',() => { disconnect(); $('results-key-dialog').close(); });
  on($('results-key-form'),'submit',async event => {
    event.preventDefault(); const value = $('results-key').value.trim();
    if (!value || /[\r\n]/.test(value)) { $('results-key-error').textContent = 'Enter a valid access key.'; return; }
    disconnect(false); key = value;
    try { storage.setItem(KEY_STORAGE,key); } catch {}
    $('results-key').value = ''; $('results-key-dialog').close(); await refresh();
  });
  on($('results-refresh'),'click',refresh);
  for (const id of ['results-framework','results-model','results-state']) on($(id),'change',render);
  on($('results-search'),'input',render); on($('results-cohort'),'change',chart);
  for (const input of doc.querySelectorAll('input[name="results-axis"]')) on(input,'change',chart);
  overview();
  if (key) refresh(); else { showPublished(); discoverControl(); }
  if (pollMs > 0) timer = win.setInterval(() => { if (key && controlAvailable !== false && !doc.hidden && !$('results-key-dialog').open && !doc.activeElement?.closest('.run-evidence')) refresh(); },pollMs);
  return {refresh,disconnect,destroy() { destroyed = true; epoch++; pending?.controller.abort(); capabilityController?.abort(); published?.destroy(); if (timer) win.clearInterval(timer); for (const remove of listeners) remove(); }};
}

if (typeof document !== 'undefined' && document.body?.dataset.resultsApp === 'true') initResults();
