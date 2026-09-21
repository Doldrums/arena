const STORAGE_KEY = 'arena.queue.session-key';
const finite = value => typeof value === 'number' && Number.isFinite(value);
const count = value => Number.isSafeInteger(value) && value >= 0;
const number = value => finite(value) ? new Intl.NumberFormat('en', {maximumSignificantDigits:6}).format(value) : '—';
const shortNumber = value => new Intl.NumberFormat('en', {notation:'compact', maximumFractionDigits:1}).format(value);
const countText = (value, noun) => `${number(value)} ${noun}${value === 1 ? '' : 's'}`;
const duration = value => !finite(value) || value < 0 ? '—' : value < 60 ? `${number(value)} s` : value < 3600 ? `${number(Math.round(value / 6) / 10)} min` : `${number(Math.round(value / 360) / 10)} h`;
const canon = run => run.metrics?.canonical || {};
const usage = run => run.metrics?.usage || {};
const native = run => run.metrics?.native || {};
const systemName = id => ({'sciel-release':'SCiEL', sciel:'SCiEL · source'})[id] || id || 'Unknown system';
const terminal = run => ['completed','failed','cancelled'].includes(run.state);
const cohortKey = run => {
  const c = canon(run);
  return typeof c.cohort === 'string' && /^[a-f0-9]{64}$/i.test(c.cohort) && typeof c.task_id === 'string' && c.task_id && typeof c.metric === 'string' && c.metric && ['maximize','minimize'].includes(c.direction)
    ? JSON.stringify([c.cohort.toLowerCase(), c.task_id, c.metric, c.direction]) : '';
};
const budget = run => {
  const b = run.metrics?.budget || {};
  return count(b.generation_calls) ? {value:b.generation_calls, label:'Generation-call limit'} : count(b.evaluations) ? {value:b.evaluations, label:b.label || 'Native evaluation budget'} : null;
};
const budgetKey = run => { const b = budget(run); return b ? JSON.stringify([b.label,b.value]) : 'missing'; };
const median = values => { if (!values.length) return null; const sorted = [...values].sort((a,b) => a-b), i = Math.floor(sorted.length/2); return sorted.length % 2 ? sorted[i] : (sorted[i-1]+sorted[i])/2; };
const validity = run => {
  const c = canon(run), total = count(c.evaluations) ? c.evaluations : 0;
  const valid = count(c.valid) ? c.valid : 0, invalid = count(c.invalid) ? c.invalid : 0;
  return {total, valid, invalid, unknown:Math.max(count(c.unknown) ? c.unknown : 0,total-valid-invalid,0)};
};

// Read-only projections. Canonical comparisons never mix evaluator contracts;
// native outcomes and partial measurements remain inspectable in the run table.
export function initResultsShowcase({doc = document, fetcher = (...args) => fetch(...args), storage = sessionStorage, pollMs = 30000, requestTimeoutMs = 30000} = {}) {
  const win = doc.defaultView, $ = id => doc.getElementById(id), listeners = [];
  let key = '', payload = null, groups = new Map(), selected = [], epoch = 0, pending = null, timer = null, destroyed = false, page = 0, loadState = 'disconnected';
  try { key = storage.getItem(STORAGE_KEY) || ''; } catch {}
  function on(node, type, handler) { node.addEventListener(type,handler); listeners.push(() => node.removeEventListener(type,handler)); }
  function stopPending() { if (!pending) return; win.clearTimeout(pending.timeout); pending.controller.abort(); pending = null; }
  function node(tag, className, text) { const result = doc.createElement(tag); if (className) result.className = className; if (text !== undefined) result.textContent = String(text); return result; }
  function highlight(label, value, description, tone = '') {
    const card = node('article','showcase-highlight'); if (tone) card.dataset.tone = tone;
    card.append(node('span','showcase-highlight-label',label),node('strong','showcase-highlight-value',value),node('small','',description)); return card;
  }
  const dynamicIds = ['showcase-models','showcase-tokens','showcase-methodology-body','showcase-efficiency','showcase-progress','showcase-validity','showcase-coverage'];
  const noteIds = ['showcase-basis','showcase-score-context','showcase-seed-note','showcase-token-context','showcase-efficiency-note','showcase-validity-note','showcase-coverage-note','showcase-run-count','showcase-table-page'];
  function clear() {
    payload = null; groups = new Map(); selected = []; page = 0;
    $('showcase-content').hidden = true; $('showcase-methodology').hidden = true; $('showcase-empty').hidden = false;
    $('showcase-cohort').replaceChildren(); $('showcase-cohort-label').hidden = true;
    $('showcase-empty').querySelector('h2').textContent = 'Connect to results';
    for (const [id,value,label] of [['showcase-framework','sciel-release','SCiEL · private image'],['showcase-model','all','All models'],['showcase-budget','all','All budgets']]) { const option = node('option','',label); option.value = value; $(id).replaceChildren(option); }
    $('showcase-search').value = ''; $('showcase-state').value = 'all';
    dynamicIds.forEach(id => $(id).replaceChildren()); noteIds.forEach(id => { $(id).textContent = ''; });
    $('showcase-highlights').replaceChildren();
    $('showcase-empty-copy').textContent = 'Connect with your Arena key to view recorded runs and their measurements.';
    setLoadState('disconnected');
  }
  function setLoadState(state) {
    loadState = state;
    $('main').dataset.loadState = state;
    $('main').setAttribute('aria-busy',String(state === 'loading' || state === 'refreshing'));
    const measured = !!payload && selected.length > 0;
    $('showcase-loading').hidden = state !== 'loading';
    $('showcase-toolbar').hidden = !payload;
    $('showcase-highlights').hidden = !measured;
    $('showcase-basis').hidden = !payload;
    $('showcase-content').hidden = !measured;
    $('showcase-methodology').hidden = !measured;
    $('showcase-empty').hidden = measured || state === 'loading';
    $('showcase-empty-retry').hidden = state !== 'error' || !!payload || !key;
  }
  function failedLoad(timedOut) {
    setLoadState('error');
    const message = timedOut ? 'The results request timed out.' : 'Results could not be loaded.';
    $('showcase-status').textContent = payload
      ? `${message} Showing the last loaded results. Refresh to try again.`
      : `${message} Retry loading to try again.`;
    $('showcase-key-error').textContent = `${message} Please try again.`;
    if (!payload) {
      $('showcase-empty').querySelector('h2').textContent = 'Could not load results';
      $('showcase-empty-copy').textContent = timedOut
        ? 'The server is taking longer than expected. Retry when you are ready.'
        : 'Check your connection and retry. Your access key is kept for the next attempt.';
    }
  }
  function setAccess() {
    const access = key ? 'connected' : 'overview';
    if (doc.body.dataset.resultsAccess !== access) {
      doc.body.dataset.resultsAccess = access;
      doc.dispatchEvent(new win.CustomEvent('arena:results-access', {detail:{connected:!!key}}));
    }
    $('showcase-connect').textContent = key ? 'Access key' : 'Connect with key';
    $('showcase-refresh').disabled = !key || !!pending;
    $('showcase-empty-connect').hidden = !!key;
  }
  function options(id, values, initial) {
    const select = $(id), previous = select.value;
    select.replaceChildren(...[...initial,...values].map(([value,label]) => { const option = node('option','',label); option.value = value; return option; }));
    if ([...select.options].some(option => option.value === previous)) select.value = previous;
  }
  function configureFilters() {
    const rows = payload.runs;
    const systems = [...new Set(rows.map(run => run.framework).filter(value => typeof value === 'string' && value && value !== 'sciel-release'))].sort();
    options('showcase-framework',systems.map(id => [id,systemName(id)]),[['sciel-release','SCiEL · private image'],['all','All systems']]);
    options('showcase-model',[...new Set(rows.map(run => run.model).filter(value => typeof value === 'string' && value))].sort().map(value => [value,value]),[['all','All models']]);
    const budgets = new Map(rows.map(run => { const b = budget(run); return [budgetKey(run),b ? `${b.label} · ${number(b.value)}` : 'Budget not recorded']; }));
    options('showcase-budget',[...budgets], [['all','All budgets']]);
  }
  function configureGroups() {
    groups = new Map();
    for (const run of selected) {
      const identity = cohortKey(run);
      if (identity) { if (!groups.has(identity)) groups.set(identity,[]); groups.get(identity).push(run); }
    }
    groups = new Map([...groups].sort((a,b) => b[1].length-a[1].length));
    options('showcase-cohort',[...groups].map(([identity,runs]) => { const c = canon(runs[0]); return [identity,`${c.task_name || c.task_id} · ${c.metric} · ${c.cohort.slice(0,8)}`]; }),groups.size ? [] : [['','No shared evaluator recorded']]);
    $('showcase-cohort').disabled = !groups.size;
    $('showcase-cohort-label').hidden = false;
  }
  function summary() {
    const totals = selected.map(validity).reduce((a,b) => ({valid:a.valid+b.valid,invalid:a.invalid+b.invalid,unknown:a.unknown+b.unknown,total:a.total+b.total}),{valid:0,invalid:0,unknown:0,total:0});
    const models = new Set(selected.map(run => run.model).filter(Boolean));
    const validModels = new Set(selected.filter(run => validity(run).valid > 0).map(run => run.model).filter(Boolean));
    const recorded = selected.filter(run => validity(run).total > 0);
    const hashed = recorded.filter(run => Array.isArray(canon(run).valid_candidate_hashes));
    const hashes = new Set(hashed.flatMap(run => canon(run).valid_candidate_hashes).filter(value => typeof value === 'string' && /^[a-f0-9]{64}$/i.test(value)).map(value => value.toLowerCase()));
    const complete = selected.filter(run => terminal(run) && usage(run).complete === true && count(usage(run).total_tokens));
    const completed = selected.filter(run => run.state === 'completed').length;
    const fraction = totals.valid+totals.invalid ? `${new Intl.NumberFormat('en',{maximumFractionDigits:1}).format(totals.valid/(totals.valid+totals.invalid)*100)}%` : '—';
    $('showcase-highlights').replaceChildren(
      highlight('Runs',number(selected.length),`${countText(new Set(selected.map(run => run.framework)).size,'system')} · ${countText(models.size,'model')}`),
      highlight('Models with valid evidence',models.size ? `${validModels.size} / ${models.size}` : '—','At least one valid canonical evaluation.','amber'),
      highlight('Candidate validity',fraction,`${number(totals.valid)} / ${number(totals.valid+totals.invalid)} classified receipts${totals.unknown ? ` · ${number(totals.unknown)} unclassified` : ''}.`),
      highlight('Distinct valid programs',hashed.length ? number(hashes.size) : '—',`Source hashes; includes the seed.${hashed.length < recorded.length ? ' Partial hash coverage.' : ''}`),
      highlight('Median recorded tokens',number(median(complete.map(run => usage(run).total_tokens))),`${complete.length} / ${selected.length} runs · ended, complete ledgers.`),
      highlight('Completed runs',`${completed} / ${selected.length}`,'Process status; evidence retained for other states.')
    );
    const systems = new Set(selected.map(run => run.framework));
    $('showcase-basis').textContent = `${payload.scope === 'all' ? 'All accessible runs' : 'Your accessible runs'} · ${selected.length} of ${payload.runs.length} loaded · ${systems.size === 1 ? systemName([...systems][0]) : `${systems.size} systems`} · all process statuses retained unless filtered.${payload.truncated ? ` Loaded ${countText(payload.runs.length,'record')} of ${number(payload.total)} available; metrics cover only loaded records.` : ''}`;
  }
  function svgNode(parent, tag, attributes = {}, text) {
    const result = doc.createElementNS('http://www.w3.org/2000/svg',tag);
    Object.entries(attributes).forEach(([name,value]) => result.setAttribute(name,String(value)));
    if (text !== undefined) result.textContent = String(text); parent.append(result); return result;
  }
  function svgPlot(panel, width, height, label) {
    const svg = svgNode(panel,'svg',{viewBox:`0 0 ${width} ${height}`,class:'dashboard-svg',role:'img','aria-label':label});
    svgNode(svg,'title',{},label); return svg;
  }
  function focusRun(run) {
    const index = sortedRuns().findIndex(item => item.id === run.id); if (index < 0) return;
    page = Math.floor(index/20); table();
    const row = [...$('showcase-models').children].find(item => item.dataset.runId === run.id);
    const inspect = row?.querySelector('.inspect-run'); if (inspect) { if (inspect.getAttribute('aria-expanded') !== 'true') inspect.click(); doc.getElementById(inspect.getAttribute('aria-controls'))?.querySelector('summary')?.focus(); }
    row?.scrollIntoView?.({behavior:'smooth',block:'center'});
  }
  function activate(element, run) {
    element.setAttribute('tabindex','0'); element.setAttribute('role','button');
    element.addEventListener('click',() => focusRun(run));
    element.addEventListener('keydown',event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); focusRun(run); } });
  }
  function charts() {
    const members = groups.get($('showcase-cohort').value) || [], c = members.length ? canon(members[0]) : {}, axis = $('showcase-axis').value;
    const resource = run => axis === 'time' ? run.metrics?.wall_seconds : usage(run).total_tokens;
    const hasResource = run => axis === 'time' ? finite(resource(run)) && resource(run) >= 0 : count(resource(run)) && usage(run).complete === true;
    const points = members.filter(run => finite(canon(run).best_score) && hasResource(run));
    const panel = $('showcase-efficiency'); panel.replaceChildren();
    if (!points.length) panel.append(node('p','chart-empty',members.length ? `No paired score and ${axis === 'time' ? 'wall-time' : 'complete token-ledger'} measurement in this cohort.` : 'Canonical comparisons appear when runs share a recorded task and evaluator. Native outcomes remain in the run table.'));
    else {
      const eligible = points.filter(run => terminal(run) && canon(run).status === 'recorded');
      const frontier = new Set(eligible.filter(run => !eligible.some(other => resource(other) <= resource(run) && (c.direction === 'maximize' ? canon(other).best_score >= canon(run).best_score : canon(other).best_score <= canon(run).best_score) && (resource(other) < resource(run) || canon(other).best_score !== canon(run).best_score))).map(run => run.id));
      const width = win.innerWidth <= 510 ? 420 : 600, height = 290, left = 66, right = 30, top = 30, bottom = 55;
      const maxX = Math.max(1,...points.map(resource))*1.08;
      const values = points.map(run => canon(run).best_score), low = Math.min(...values), high = Math.max(...values), pad = (high-low)*.15 || Math.max(Math.abs(high)*.05,.05);
      const minY = low-pad, maxY = high+pad, x = value => left+value/maxX*(width-left-right), y = value => top+(maxY-value)/(maxY-minY)*(height-top-bottom);
      const svg = svgPlot(panel,width,height,`${c.metric} versus ${axis === 'time' ? 'wall time' : 'recorded tokens'}; ${points.length} runs in one evaluator cohort. Exact observations follow.`);
      for (let i=0;i<=4;i++) {
        const xv = maxX*i/4, yv = minY+(maxY-minY)*i/4;
        svgNode(svg,'line',{x1:left,x2:width-right,y1:y(yv),y2:y(yv),class:'plot-grid'});
        svgNode(svg,'text',{x:left-9,y:y(yv)+4,'text-anchor':'end',class:'plot-tick'},number(yv));
        svgNode(svg,'text',{x:x(xv),y:height-bottom+22,'text-anchor':'middle',class:'plot-tick'},axis === 'time' ? duration(xv) : shortNumber(xv));
      }
      svgNode(svg,'text',{x:left,y:16,class:'plot-axis-label'},`${c.metric.length > 32 ? c.metric.slice(0,30)+'…' : c.metric} · ${c.direction === 'maximize' ? 'higher' : 'lower'} is better`);
      svgNode(svg,'text',{x:width/2,y:height-6,'text-anchor':'middle',class:'plot-axis-label'},axis === 'time' ? 'Wall time' : 'Recorded tokens');
      points.forEach((run,i) => {
        const attributes = {cx:x(resource(run)),cy:y(canon(run).best_score),r:frontier.has(run.id) ? 7 : 5,class:`plot-point${run.framework.startsWith('sciel') ? ' is-sciel' : ''}${frontier.has(run.id) ? ' on-frontier' : ''}${canon(run).status === 'partial' ? ' is-partial' : ''}`,'data-run-id':run.id};
        const point = svgNode(svg,'circle',attributes);
        const label = `${systemName(run.framework)} · ${run.model || 'Unknown model'}: ${number(canon(run).best_score)} ${c.metric}; ${axis === 'time' ? duration(resource(run)) : `${number(resource(run))} tokens`}${canon(run).status === 'partial' ? '; partial canonical evidence' : ''}`;
        svgNode(point,'title',{},label); point.setAttribute('aria-label',`${label}. Inspect run.`); activate(point,run);
        if (points.length <= 20) svgNode(svg,'text',{x:x(resource(run))+8,y:y(canon(run).best_score)-8,class:'plot-point-label'},i+1);
      });
      const legend = node('div','plot-key');
      points.forEach((run,i) => { const entry = node('button','plot-key-item'); entry.type = 'button'; entry.append(node('span','plot-key-index',i+1),node('span','',`${systemName(run.framework)} · ${run.model || 'Unknown model'} · ${number(canon(run).best_score)} · ${axis === 'time' ? duration(resource(run)) : `${number(resource(run))} tokens`}${canon(run).status === 'partial' ? ' · partial evidence' : ''}`)); entry.addEventListener('click',() => focusRun(run)); legend.append(entry); });
      panel.append(legend);
      if (eligible.length) {
        const best = (c.direction === 'maximize' ? Math.max : Math.min)(...eligible.map(run => canon(run).best_score));
        const sameScore = eligible.filter(run => canon(run).best_score === best), minimum = Math.min(...sameScore.map(resource));
        const least = sameScore.filter(run => resource(run) === minimum);
        const insight = node('p','chart-insight'); insight.append(node('strong','',`${axis === 'time' ? duration(minimum) : `${number(minimum)} tokens`} at score ${number(best)}. `),doc.createTextNode(`Lowest recorded ${axis === 'time' ? 'wall time' : 'token use'} at the best observed score among ${eligible.length} ended runs with complete evidence: ${least.map(run => `${systemName(run.framework)} · ${run.model || 'Unknown model'}`).join(', ')}.`)); panel.append(insight);
      }
    }
    $('showcase-efficiency-note').textContent = `${points.length} / ${members.length} cohort runs plotted. ${members.length-points.length} lack a paired measurement.${axis === 'tokens' ? ' Partial token ledgers are excluded.' : ' Wall time includes recorded work and waiting.'} Outlined points mark the observed frontier among ended runs with complete evidence. Models and budgets can differ; use the filters to align them.`;
    const progress = $('showcase-progress'); progress.replaceChildren();
    const measured = members.filter(run => finite(canon(run).seed_score) || finite(canon(run).best_score));
    $('showcase-score-context').textContent = members.length ? `${c.task_name || c.task_id} · ${c.metric} · ${c.direction === 'maximize' ? 'higher' : 'lower'} is better` : 'A shared evaluator is required for score comparison.';
    if (!measured.length) progress.append(node('p','chart-empty','No canonical starting-point and result measurements in this cohort.'));
    else {
      const visible = measured.slice(0,12), values = visible.flatMap(run => [canon(run).seed_score,canon(run).best_score]).filter(finite), low = Math.min(...values), high = Math.max(...values), pad = (high-low)*.12 || Math.max(Math.abs(high)*.05,.05);
      const compact = win.innerWidth <= 510, left = compact ? 124 : 168, right = 35, width = compact ? 420 : 600, height = Math.max(220,visible.length*36+70), bottom = height-35, x = value => left+(value-low+pad)/(high-low+pad*2)*(width-left-right);
      const svg = svgPlot(progress,width,height,'Recorded seed and best score per run. Hollow points are seeds; filled points are best scores. Lines connect endpoints, not search trajectories.');
      for (let i=0;i<=4;i++) { const value = low-pad+(high-low+2*pad)*i/4; svgNode(svg,'line',{x1:x(value),x2:x(value),y1:16,y2:bottom,class:'plot-grid'}); svgNode(svg,'text',{x:x(value),y:height-12,'text-anchor':'middle',class:'plot-tick'},number(value)); }
      visible.forEach((run,i) => {
        const item = canon(run), y = 30+i*36;
        const label = svgNode(svg,'text',{x:8,y:y+4,class:'plot-row-label'},(run.model || 'Unknown model').length > (compact ? 15 : 21) ? `${run.model.slice(0,compact ? 13 : 19)}…` : run.model || 'Unknown model'); svgNode(label,'title',{},`${systemName(run.framework)} · ${run.model}`);
        if (finite(item.seed_score) && finite(item.best_score)) svgNode(svg,'line',{x1:x(item.seed_score),x2:x(item.best_score),y1:y,y2:y,class:'plot-dumbbell-line'});
        for (const [field,kind] of [['seed_score','seed'],['best_score','best']]) if (finite(item[field])) { const point = svgNode(svg,'circle',{cx:x(item[field]),cy:y,r:kind === 'seed' ? 7 : 4,class:`plot-endpoint is-${kind}`,'data-run-id':run.id}); const text = `${run.model || 'Unknown model'} · ${kind}: ${number(item[field])}${item.status === 'partial' ? ' · partial evidence' : ''}`; svgNode(point,'title',{},text); point.setAttribute('aria-label',`${text}. Inspect run.`); activate(point,run); }
      });
      progress.append(node('p','plot-legend-note',`○ Seed  ·  ● Best${measured.length > visible.length ? ` · first ${visible.length} of ${measured.length} runs; all values in the table` : ''}`));
    }
    const paired = members.filter(run => finite(canon(run).seed_score) && finite(canon(run).best_score));
    const gain = run => (canon(run).best_score-canon(run).seed_score)*(c.direction === 'minimize' ? -1 : 1);
    const improved = paired.filter(run => gain(run)>0).length, tied = paired.filter(run => gain(run)===0).length, below = paired.length-improved-tied;
    $('showcase-seed-note').textContent = `${improved} improved · ${tied} matched the seed${below ? ` · ${below} below seed` : ''} · ${members.length-paired.length} without a paired measurement.${paired.length && tied === paired.length ? ' No improvement over the starting score is measured in these pairs.' : ''} Endpoints only; no intermediate trajectory is inferred.`;
  }
  function measureRow(label, description, segments, total, maximum, partial = false) {
    const row = node('div',`measure-row${partial ? ' is-partial' : ''}`), heading = node('div','measure-label'), track = node('div','measure-track');
    heading.append(node('strong','',label),node('small','',description));
    track.setAttribute('aria-hidden','true');
    segments.forEach(([tone,value]) => { const fill = node('span','measure-segment'); fill.dataset.tone = tone; fill.style.width = `${maximum > 0 ? value/maximum*100 : 0}%`; track.append(fill); });
    row.append(heading,track,node('span','measure-values',number(total))); return row;
  }
  function measurements() {
    const byModel = new Map();
    selected.forEach(run => { const identity = JSON.stringify([run.framework,run.model]); if (!byModel.has(identity)) byModel.set(identity,{run,valid:0,invalid:0,unknown:0,total:0,runs:0}); const entry = byModel.get(identity), v = validity(run); ['valid','invalid','unknown','total'].forEach(field => { entry[field] += v[field]; }); entry.runs++; });
    const outcomes = [...byModel.values()], visible = outcomes.slice(0,12), maximum = Math.max(1,...visible.map(item => item.total));
    $('showcase-validity').replaceChildren(...visible.map(item => item.total ? measureRow(item.run.model || 'Unknown model',`${systemName(item.run.framework)} · ${item.valid} valid / ${item.invalid} invalid / ${item.unknown} unclassified`,[['valid',item.valid],['invalid',item.invalid],['unknown',item.unknown]],item.total,maximum) : node('p','chart-empty',`${systemName(item.run.framework)} · ${item.run.model || 'Unknown model'}: canonical evaluations not recorded.`)));
    const missing = selected.filter(run => !validity(run).total).length, partial = selected.filter(run => canon(run).status === 'partial').length;
    $('showcase-validity-note').textContent = `Receipt counts, including the initial candidate. ${missing} runs without canonical receipts; ${partial} with partial canonical evidence.${outcomes.length > 12 ? ` Showing 12 of ${outcomes.length} system / model groups; filter to narrow the view.` : ''}`;
    const recorded = selected.filter(run => count(usage(run).total_tokens)), tokens = recorded.slice(0,12), maxTokens = Math.max(1,...tokens.map(run => usage(run).total_tokens));
    $('showcase-tokens').replaceChildren(...tokens.map(run => {
      const u = usage(run), split = count(u.input_tokens) && count(u.output_tokens) && u.input_tokens+u.output_tokens === u.total_tokens;
      const row = measureRow(run.model || 'Unknown model',`${systemName(run.framework)} · ${split ? `${number(u.input_tokens)} input / ${number(u.output_tokens)} output` : 'Token composition not recorded'} · ${u.complete === true ? 'complete ledger' : 'partial ledger'}`,split ? [['input',u.input_tokens],['output',u.output_tokens]] : [['other',u.total_tokens]],u.total_tokens,maxTokens,u.complete !== true); row.dataset.runId = run.id; return row;
    }));
    if (!recorded.length) $('showcase-tokens').append(node('p','chart-empty','Token counts are not recorded for these runs.'));
    $('showcase-token-context').textContent = `${recorded.length} / ${selected.length} runs with token records; ${recorded.filter(run => usage(run).complete === true).length} complete ledgers.${recorded.length > 12 ? ` Showing the first 12; every run is in the table.` : ''} Input + output tokens; hatched bars indicate partial coverage. Counts are not billed cost.`;
  }
  function scoreSource(run) { return finite(canon(run).best_score) || finite(canon(run).seed_score) || validity(run).total > 0 ? {value:canon(run),label:'Canonical'} : {value:native(run),label:'Native'}; }
  function sortedRuns() {
    const sort = $('showcase-sort').value, result = [...selected];
    const metric = run => sort === 'tokens' ? usage(run).complete === true && terminal(run) ? usage(run).total_tokens : null : sort === 'time' ? run.metrics?.wall_seconds : sort === 'created' ? run.created : canon(run).best_score;
    result.sort((a,b) => {
      if (sort !== 'model') { const av = metric(a), bv = metric(b); if (finite(av) !== finite(bv)) return finite(av) ? -1 : 1; if (finite(av) && av !== bv) return (av-bv)*(sort === 'created' || sort === 'score' && canon(a).direction === 'maximize' ? -1 : 1); }
      return String(a.model || '').localeCompare(String(b.model || '')) || String(a.framework || '').localeCompare(String(b.framework || '')) || String(a.id).localeCompare(String(b.id));
    }); return result;
  }
  function evidence(run) {
    const detail = node('details','run-evidence'); detail.append(node('summary','','Inspect'));
    const dl = node('dl'), c = canon(run), n = native(run), u = usage(run), b = budget(run), e = run.metrics?.evidence || {};
    const fields = [['Run',run.id],['System',`${systemName(run.framework)} · ${run.framework}`],['Model',run.model || 'Not recorded'],['Profile',run.profile || 'Not recorded'],['Batch',run.batch_id || 'Not recorded'],['Canonical evidence',c.status || 'missing'],['Task',c.task_name || c.task_id || 'Not recorded'],['Evaluator cohort',c.cohort || 'Not recorded'],['Budget',b ? `${b.label}: ${number(b.value)} (configured limit)` : 'Not recorded'],['Canonical receipts',number(c.evaluations)],['Provider requests',number(u.requests)],['Token coverage',u.complete === true ? 'Complete inspected ledger' : 'Partial or not recorded'],['Input / output tokens',`${number(u.input_tokens)} / ${number(u.output_tokens)}`],['Wall time',duration(run.metrics?.wall_seconds)],['Process return code',run.returncode ?? 'Not recorded'],['Artifacts',number(e.artifact_count)]];
    if (n.metric || finite(n.best_score) || Array.isArray(n.objectives) && n.objectives.length) {
      fields.push(['Native task',n.task || 'Not recorded'],['Native metric',n.metric || 'Multiple objectives'],['Native score',number(n.best_score)],['Native seed',number(n.seed_score)],['Native direction',n.direction || 'Not recorded'],['Native scope',n.scope || 'native'],['Native evidence',n.status || 'Not recorded']);
      for (const [name,field] of [['Score definition','score_kind'],['Stored candidates','candidates'],['Candidate count scope','candidate_count_scope'],['Iteration value','iterations'],['Iteration scope','iteration_count_scope'],['Population size','population_size']]) if (typeof n[field] === 'string' || finite(n[field])) fields.push([name,n[field]]);
      if (n.named_metrics && typeof n.named_metrics === 'object') Object.entries(n.named_metrics).filter(([,value]) => finite(value)).forEach(([name,value]) => fields.push([`Native · ${name}`,number(value)]));
    }
    fields.forEach(([name,value]) => dl.append(node('dt','',name),node('dd','',value))); detail.append(dl);
    if (Array.isArray(n.objectives) && Array.isArray(n.population_objectives) && n.objectives.length) {
      detail.append(node('p','native-objective-note','Native objectives retain their paired candidate measurements.'));
      const table = node('table','native-objectives'), head = node('thead'), header = node('tr'); header.append(node('th','','Candidate')); n.objectives.forEach(item => header.append(node('th','',`${item.metric || 'Objective'} (${item.direction || 'direction not recorded'})`))); head.append(header); table.append(head); const body = node('tbody');
      n.population_objectives.forEach((row,i) => { const tr = node('tr'); tr.append(node('td','',row.candidate ?? row.index ?? i+1)); n.objectives.forEach(item => tr.append(node('td','',number(row[item.metric] ?? row.values?.[item.metric] ?? row.objectives?.[item.metric])))); body.append(tr); }); table.append(body); detail.append(table);
    }
    for (const [label,values] of [['Canonical receipt hashes',c.receipt_hashes],['Valid program hashes',c.valid_candidate_hashes]]) if (Array.isArray(values) && values.length) { const hashes = node('details','evidence-hashes'); hashes.append(node('summary','',`${label} · ${values.length}`),node('pre','',values.filter(value => typeof value === 'string' && /^[a-f0-9]{64}$/i.test(value)).join('\n'))); detail.append(hashes); }
    return detail;
  }
  function table() {
    const open = new Set([...$('showcase-models').querySelectorAll('tr[data-run-id]')].filter(row => row.querySelector('.inspect-run')?.getAttribute('aria-expanded') === 'true').map(row => row.dataset.runId));
    const rows = sortedRuns(); page = Math.min(page,Math.max(0,Math.ceil(rows.length/20)-1));
    $('showcase-models').replaceChildren(...rows.slice(page*20,page*20+20).flatMap((run,index) => {
      const row = node('tr','showcase-model'); row.dataset.runId = run.id;
      const identity = node('td'); identity.append(node('strong','showcase-model-name',run.model || 'Model not recorded'),node('small','',systemName(run.framework)));
      const status = node('td'), state = node('span','showcase-process',run.state || 'unknown'); state.dataset.state = run.state || 'unknown'; status.append(state); if (canon(run).status === 'partial') status.append(node('small','','Partial canonical evidence'));
      if (native(run).status === 'partial') status.append(node('small','','Partial native evidence'));
      const score = node('td'), source = scoreSource(run), pair = node('span','showcase-score-pair'); pair.append(node('span','',number(source.value.seed_score)),node('i','','→'),node('strong','',number(source.value.best_score))); score.append(pair,node('small','score-scope',`${source.label} · ${source.value.metric || (Array.isArray(source.value.objectives) && source.value.objectives.length ? `${source.value.objectives.length} objectives` : 'not recorded')}`));
      score.append(node('small','',source.value.task_name || source.value.task_id || source.value.task || 'Task not recorded'));
      const v = validity(run), validityCell = node('td','',v.total ? `${number(v.valid)} / ${number(v.total)}` : '—'); if (v.unknown) validityCell.append(node('small','',`${v.unknown} unclassified`));
      const u = usage(run), tokens = node('td','',number(u.total_tokens)); if (count(u.total_tokens) && u.complete !== true) tokens.append(node('small','','Partial ledger'));
      const time = node('td','',duration(run.metrics?.wall_seconds)), details = node('td'), detail = evidence(run), expanded = open.has(run.id);
      const detailRow = node('tr','showcase-detail-row'), detailCell = node('td'); detailCell.colSpan = 7;
      detailRow.id = `run-evidence-${page*20+index}`; detailRow.hidden = !expanded;
      detail.open = expanded; detail.querySelector('summary').textContent = `Run evidence · ${systemName(run.framework)} · ${run.model || 'Unknown model'}`;
      detailCell.append(detail); detailRow.append(detailCell);
      const inspect = node('button','inspect-run','Inspect'); inspect.type = 'button'; inspect.setAttribute('aria-expanded',String(expanded)); inspect.setAttribute('aria-controls',detailRow.id);
      inspect.addEventListener('click',() => { const show = inspect.getAttribute('aria-expanded') !== 'true'; detailRow.hidden = !show; detail.open = show; inspect.setAttribute('aria-expanded',String(show)); if (show) detail.querySelector('summary').focus(); });
      detail.addEventListener('toggle',() => { if (!detail.open && !detailRow.hidden) { detailRow.hidden = true; inspect.setAttribute('aria-expanded','false'); inspect.focus(); } });
      details.append(inspect);
      row.append(identity,status,score,validityCell,tokens,time,details); return [row,detailRow];
    }));
    $('showcase-run-count').textContent = `${countText(rows.length,'run')} · canonical and native scopes labelled individually`;
    $('showcase-table-page').textContent = rows.length ? `${page*20+1}–${Math.min(page*20+20,rows.length)} of ${rows.length}` : '0 runs';
    $('showcase-page-prev').disabled = page === 0; $('showcase-page-next').disabled = (page+1)*20 >= rows.length;
  }
  function coverage() {
    const systems = new Map(); selected.forEach(run => { if (!systems.has(run.framework)) systems.set(run.framework,[]); systems.get(run.framework).push(run); });
    const table = node('table','coverage-table'), head = node('thead'), hr = node('tr');
    ['System','Runs','Canonical records','Native outcomes','Complete token ledgers','Wall time'].forEach(label => { const cell = node('th','',label); cell.scope = 'col'; hr.append(cell); }); head.append(hr); table.append(head);
    const body = node('tbody');
    for (const [framework,runs] of systems) {
      const row = node('tr'); const name = node('th','',systemName(framework)); name.scope = 'row'; row.append(name,node('td','',runs.length));
      const values = [runs.filter(run => validity(run).total>0).length,runs.filter(run => finite(native(run).best_score) || Array.isArray(native(run).population_objectives) && native(run).population_objectives.length).length,runs.filter(run => usage(run).complete === true && count(usage(run).total_tokens)).length,runs.filter(run => finite(run.metrics?.wall_seconds) && run.metrics.wall_seconds>=0).length];
      values.forEach(value => { const cell = node('td'), meter = node('span','coverage-meter'); meter.style.setProperty('--coverage',`${value/runs.length*100}%`); meter.append(node('span','',`${value} / ${runs.length}`)); cell.append(meter); row.append(cell); }); body.append(row);
    }
    table.append(body); $('showcase-coverage').replaceChildren(table);
    $('showcase-coverage-note').textContent = 'Recorded measurement availability, not a system ranking. Canonical records can be partial. Native outcomes retain their task-specific evaluation; missing resource records remain unknown.';
    const partial = selected.filter(run => canon(run).status === 'partial').length;
    const notes = [
      ['Comparison scope','Score plots use one immutable task / evaluator cohort, including source and execution identity. The cohort selector changes both score plots; summaries and the run table follow the global filters. Model, native budget and search procedure may differ within a cohort.'],
      ['Starting point','Seed is the first recorded canonical evaluation, not the first successful attempt. Endpoint plots do not imply a convergence trajectory. Native scores never enter canonical plots.'],
      ['Program validity',`${partial} ${partial === 1 ? 'run has' : 'runs have'} partial canonical evidence; validity percentages cover retained, classified receipts. Distinct programs are deduplicated by SHA-256 across filtered runs and include valid seeds. Validity does not establish optimality.`],
      ['Resource accounting','Median tokens use ended runs with complete inspected provider ledgers, including failed processes. Partial tokens remain visible separately. Tokens are not billing records, and wall time includes work and waiting. Configured native budgets are limits, not counts of provider requests.'],
      ['Observed frontier','A run is on the observed frontier when no other eligible run uses less or equal resource with a better or equal score, with at least one strict difference. Only ended runs with fully recorded canonical evidence qualify; token comparisons also require complete ledgers. This describes these observations, not method superiority.'],
      ['Evidence access','Inspect a run for task identity, native outcomes, budget, requests, receipt hashes and source hashes. Failed and cancelled processes retain usable evidence. All summaries cover only the accessible, loaded records.']
    ];
    $('showcase-methodology-body').replaceChildren(...notes.map(([label,text]) => { const p = node('p'); p.append(node('strong','',`${label}. `),doc.createTextNode(text)); return p; }));
  }
  function render() {
    if (!payload) return;
    const framework = $('showcase-framework').value, model = $('showcase-model').value, state = $('showcase-state').value, b = $('showcase-budget').value, search = $('showcase-search').value.trim().toLowerCase();
    selected = payload.runs.filter(run => (framework === 'all' || run.framework === framework) && (model === 'all' || run.model === model) && (b === 'all' || budgetKey(run) === b) && (state === 'all' || state === 'active' && ['queued','preparing','running'].includes(run.state) || state === 'attention' && ['failed','blocked'].includes(run.state) || run.state === state) && [run.framework,run.model,run.profile,run.label,run.id,run.batch_id,canon(run).task_id,canon(run).task_name,native(run).task,native(run).metric].join(' ').toLowerCase().includes(search));
    selected.sort((a,b) => String(a.model || '').localeCompare(String(b.model || '')) || String(a.id).localeCompare(String(b.id)));
    summary(); configureGroups();
    $('showcase-empty').hidden = selected.length > 0; $('showcase-content').hidden = !selected.length; $('showcase-methodology').hidden = !selected.length;
    $('showcase-empty').querySelector('h2').textContent = payload.runs.length ? 'No matching runs' : 'No recorded runs';
    $('showcase-empty-copy').textContent = payload.runs.length ? 'No runs match these filters. Choose another system, model or budget, or clear your search.' : 'No recorded runs are available for this access key yet.';
    const comparable = groups.size === 1 && selected.every(run => cohortKey(run) && finite(canon(run).best_score));
    $('showcase-sort').querySelector('option[value="score"]').disabled = !comparable;
    if (!comparable && $('showcase-sort').value === 'score') $('showcase-sort').value = 'model';
    charts(); measurements(); table(); coverage();
    setLoadState(loadState === 'refreshing' ? 'refreshing' : selected.length ? 'ready' : 'empty');
  }
  async function refresh() {
    if (!key || destroyed || pending) return;
    const current = ++epoch, controller = new win.AbortController();
    pending = {controller,current,timeout:null}; setAccess();
    setLoadState(payload ? 'refreshing' : 'loading');
    const timeout = new Promise((resolve,reject) => {
      pending.timeout = win.setTimeout(() => { const error = new Error('Results request timed out.'); error.name = 'TimeoutError'; reject(error); controller.abort(); },requestTimeoutMs);
    });
    $('showcase-status').textContent = payload ? 'Updating recorded results…' : 'Loading recorded results…';
    try {
      const response = await Promise.race([fetcher('/api/control/results',{headers:{Authorization:`Bearer ${key}`},cache:'no-store',redirect:'error',credentials:'same-origin',signal:controller.signal}),timeout]);
      if (destroyed || current !== epoch) return;
      if (!response.ok) {
        if ([401,403].includes(response.status)) {
          key = ''; try { storage.removeItem(STORAGE_KEY); } catch {} clear();
          const message = response.status === 403 ? 'This key does not have access to results.' : 'Connect with a valid Arena key.';
          $('showcase-status').textContent = message; $('showcase-key-error').textContent = message; return;
        }
        throw new Error('Results are temporarily unavailable. Try refreshing.');
      }
      const next = await Promise.race([response.json(),timeout]);
      if (destroyed || current !== epoch) return;
      if (next?.schema !== 'arena.results/1' || !Array.isArray(next.runs)) throw new Error('The results response could not be read.');
      payload = {...next, runs:next.runs.filter(run => run && typeof run === 'object' && typeof run.id === 'string' && typeof run.framework === 'string')}; configureFilters(); render(); setLoadState(selected.length ? 'ready' : 'empty');
      const date = finite(next.generated_at) ? new Date(next.generated_at * 1000) : null;
      $('showcase-status').textContent = date && Number.isFinite(date.getTime()) ? `Recorded results · updated ${date.toLocaleTimeString('en',{hour:'2-digit',minute:'2-digit'})}` : 'Recorded results';
      $('showcase-key-error').textContent = '';
      if ($('showcase-key-dialog').open) $('showcase-key-dialog').close();
    } catch (error) {
      if (destroyed || current !== epoch || error?.name === 'AbortError') return;
      failedLoad(error?.name === 'TimeoutError');
    } finally { if (current === epoch) { win.clearTimeout(pending?.timeout); pending = null; setAccess(); } }
  }
  function showKey() { $('showcase-key').value = ''; $('showcase-key-dialog').showModal(); $('showcase-key').focus(); }
  function disconnect() {
    epoch++; stopPending(); key = '';
    try { storage.removeItem(STORAGE_KEY); } catch {}
    clear(); setAccess(); $('showcase-key').value = ''; $('showcase-key-error').textContent = '';
    $('showcase-status').textContent = 'Disconnected. Connect to explore recorded results.';
    $('showcase-empty-copy').textContent = 'Connect with your Arena key to view recorded runs and their measurements.';
    if ($('showcase-key-dialog').open) $('showcase-key-dialog').close();
  }
  for (const id of ['showcase-connect','showcase-empty-connect']) on($(id),'click',showKey);
  on($('showcase-key-close'),'click',() => { $('showcase-key').value = ''; $('showcase-key-dialog').close(); });
  on($('showcase-key-dialog'),'cancel',() => { $('showcase-key').value = ''; });
  on($('showcase-disconnect'),'click',disconnect);
  on($('showcase-refresh'),'click',refresh);
  on($('showcase-empty-retry'),'click',refresh);
  on($('showcase-cohort'),'change',charts);
  on($('showcase-axis'),'change',charts);
  for (const id of ['showcase-framework','showcase-model','showcase-state','showcase-budget']) on($(id),'change',() => { page = 0; render(); });
  on($('showcase-search'),'input',() => { page = 0; render(); });
  on($('showcase-sort'),'change',() => { page = 0; table(); });
  on($('showcase-page-prev'),'click',() => { page = Math.max(0,page-1); table(); });
  on($('showcase-page-next'),'click',() => { page++; table(); });
  on($('showcase-key-form'),'submit',event => {
    event.preventDefault(); const entered = $('showcase-key').value.trim(); if (!entered) return;
    epoch++; stopPending(); key = entered; clear();
    try { storage.setItem(STORAGE_KEY,key); } catch {}
    $('showcase-key').value = ''; refresh();
  });
  clear(); setAccess(); if (key) refresh();
  if (pollMs > 0) timer = win.setInterval(() => { if (!doc.hidden) refresh(); },pollMs);
  return {refresh,disconnect,destroy() { destroyed = true; epoch++; stopPending(); $('main').setAttribute('aria-busy','false'); $('showcase-loading').hidden = true; if (timer) win.clearInterval(timer); for (const remove of listeners) remove(); }};
}

if (typeof document !== 'undefined' && document.body?.dataset.resultsShowcase === 'true') initResultsShowcase();
