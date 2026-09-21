const STORAGE_KEY = 'arena.queue.session-key';
const finite = value => typeof value === 'number' && Number.isFinite(value);
const count = value => Number.isSafeInteger(value) && value >= 0;
const number = value => finite(value) ? new Intl.NumberFormat('en', {maximumSignificantDigits:6}).format(value) : '—';
const countText = (value, noun) => `${number(value)} ${noun}${value === 1 ? '' : 's'}`;
const canon = run => run.metrics?.canonical || {};
const usage = run => run.metrics?.usage || {};
const cohortKey = run => {
  const c = canon(run);
  return typeof c.cohort === 'string' && /^[a-f0-9]{64}$/i.test(c.cohort) && typeof c.task_id === 'string' && c.task_id && typeof c.metric === 'string' && c.metric && ['maximize','minimize'].includes(c.direction)
    ? JSON.stringify([c.cohort.toLowerCase(), c.task_id, c.metric, c.direction]) : '';
};
const range = values => !values.length ? '—' : Math.min(...values) === Math.max(...values) ? number(values[0]) : `${number(Math.min(...values))}–${number(Math.max(...values))}`;

// This page is a read-only presentation of the same scoped evidence as the workspace.
// It never estimates billing, promotes a native score into a canonical result, or
// chooses a winning model from incomplete resource measurements.
export function initResultsShowcase({doc = document, fetcher = (...args) => fetch(...args), storage = sessionStorage, pollMs = 30000, requestTimeoutMs = 30000} = {}) {
  const win = doc.defaultView, $ = id => doc.getElementById(id), listeners = [];
  let key = '', payload = null, groups = new Map(), selected = [], epoch = 0, pending = null, timer = null, destroyed = false;
  try { key = storage.getItem(STORAGE_KEY) || ''; } catch {}
  function on(node, type, handler) { node.addEventListener(type,handler); listeners.push(() => node.removeEventListener(type,handler)); }
  function stopPending() { if (!pending) return; win.clearTimeout(pending.timeout); pending.controller.abort(); pending = null; }
  function node(tag, className, text) { const result = doc.createElement(tag); if (className) result.className = className; if (text !== undefined) result.textContent = String(text); return result; }
  function highlight(label, value, description, tone) {
    const card = node('article','showcase-highlight'); card.dataset.tone = tone;
    card.append(node('span','showcase-highlight-label',label),node('strong','showcase-highlight-value',value),node('small','',description)); return card;
  }
  function clear() {
    payload = null; groups = new Map(); selected = [];
    $('showcase-content').hidden = true; $('showcase-methodology').hidden = true; $('showcase-empty').hidden = false;
    $('showcase-cohort-label').hidden = true; $('showcase-cohort').replaceChildren();
    for (const id of ['showcase-models','showcase-tokens','showcase-methodology-body']) $(id).replaceChildren();
    for (const id of ['showcase-basis','showcase-score-context','showcase-seed-note','showcase-token-context','showcase-budget-note']) $(id).textContent = '';
    $('showcase-budget-value').textContent = '—';
    $('showcase-highlights').replaceChildren(
      highlight('Models with valid programs','—','Canonical evidence, across models.','amber'),
      highlight('Distinct valid programs','—','Programs counted by source identity.','iris'),
      highlight('Candidate validity','—','Measured by the task evaluator.','blue'),
      highlight('Completed runs','—','The process behind each result.','neutral')
    );
  }
  function setAccess() {
    $('showcase-connect').textContent = key ? 'Access key' : 'Connect with key';
    $('showcase-refresh').disabled = !key || !!pending;
    $('showcase-empty-connect').hidden = !!key;
  }
  function configureGroups() {
    const previous = $('showcase-cohort').value;
    groups = new Map();
    for (const run of payload.runs) {
      if (run?.framework !== 'sciel-release') continue;
      const identity = cohortKey(run);
      if (identity) { if (!groups.has(identity)) groups.set(identity,[]); groups.get(identity).push(run); }
    }
    groups = new Map([...groups].sort((a,b) => b[1].length - a[1].length));
    const options = [...groups].map(([identity,runs]) => { const c = canon(runs[0]); const option = node('option','',`${c.task_name || c.task_id} · ${c.metric} · ${c.cohort.slice(0,8)}`); option.value = identity; return option; });
    $('showcase-cohort').replaceChildren(...options);
    if (groups.has(previous)) $('showcase-cohort').value = previous;
    $('showcase-cohort-label').hidden = groups.size < 2;
  }
  function render() {
    selected = [...(groups.get($('showcase-cohort').value) || [])].sort((a,b) => String(a.model || '').localeCompare(String(b.model || '')) || (a.created || 0) - (b.created || 0));
    if (!selected.length) {
      const saved = payload; clear(); payload = saved;
      $('showcase-empty-copy').textContent = 'No canonical SCiEL private-image results are recorded for this access key yet. Individual system runs remain available in the experiment board.';
      return;
    }
    $('showcase-empty').hidden = true; $('showcase-content').hidden = false; $('showcase-methodology').hidden = false;
    const c = canon(selected[0]);
    const models = new Set(selected.map(run => run.model).filter(value => typeof value === 'string' && value));
    const validModels = new Set(selected.filter(run => count(canon(run).valid) && canon(run).valid > 0).map(run => run.model).filter(value => typeof value === 'string' && value));
    const records = selected.filter(run => count(canon(run).evaluations) && canon(run).evaluations > 0);
    const valid = records.reduce((sum,run) => sum + (count(canon(run).valid) ? canon(run).valid : 0),0);
    const invalid = records.reduce((sum,run) => sum + (count(canon(run).invalid) ? canon(run).invalid : 0),0);
    const unknown = records.reduce((sum,run) => {
      const item = canon(run);
      return sum + (count(item.unknown) ? item.unknown : count(item.valid) && count(item.invalid) ? Math.max(0,item.evaluations-item.valid-item.invalid) : item.evaluations);
    },0);
    const hashed = records.filter(run => Array.isArray(canon(run).valid_candidate_hashes));
    const hashes = new Set(hashed.flatMap(run => canon(run).valid_candidate_hashes).filter(value => typeof value === 'string' && /^[a-f0-9]{64}$/i.test(value)).map(value => value.toLowerCase()));
    const completed = selected.filter(run => run.state === 'completed').length;
    const partialEvidence = selected.filter(run => canon(run).status === 'partial').length;
    const completeUsage = selected.filter(run => usage(run).complete === true && count(usage(run).total_tokens));
    const knownBudgets = selected.map(run => run.metrics?.budget).filter(budget => count(budget?.evaluations));
    const budgetLabels = new Set(knownBudgets.map(budget => budget.label || 'Native evaluation budget'));
    const budgetValue = budgetLabels.size === 1 ? range(knownBudgets.map(budget => budget.evaluations)) : knownBudgets.length ? 'Mixed' : '—';
    const budgetLabel = budgetLabels.size === 1 ? [...budgetLabels][0] : 'Native search budgets';
    const validFraction = valid + invalid > 0 ? `${new Intl.NumberFormat('en',{maximumFractionDigits:1}).format(valid / (valid + invalid) * 100)}%` : '—';
    $('showcase-highlights').replaceChildren(
      highlight('Models with valid programs',models.size ? `${validModels.size} / ${models.size}` : '—','At least one valid evaluation per model.','amber'),
      highlight('Distinct valid programs',hashed.length ? number(hashes.size) : '—',`Deduplicated across runs; includes the seed.${hashed.length < records.length ? ' Hash coverage is partial.' : ''}`,'iris'),
      highlight('Candidate validity',validFraction,`${number(valid)} / ${number(valid + invalid)} classified evaluations.${unknown ? ` ${countText(unknown,'receipt')} unclassified.` : ''}`,'blue'),
      highlight('Completed runs',`${completed} / ${selected.length}`,'All recorded process statuses remain below.','neutral')
    );
    const sourceCount = payload.runs.filter(run => run?.framework === 'sciel-release').length;
    $('showcase-basis').textContent = `${c.task_name || c.task_id} · ${countText(selected.length,'run')} · same task and evaluator · SCiEL private image${sourceCount > selected.length ? ` · ${countText(sourceCount-selected.length,'other SCiEL run')} outside this study` : ''}.${payload.truncated ? ` Loaded ${countText(payload.runs.length,'record')} of ${number(payload.total)} available; this view covers the loaded records.` : ''}`;
    $('showcase-score-context').textContent = `${c.metric} · ${c.direction === 'maximize' ? 'higher' : 'lower'} is better · ${countText(valid,'valid evaluation')}`;
    $('showcase-models').replaceChildren(...selected.map(run => {
      const row = node('article','showcase-model'); row.dataset.runId = typeof run.id === 'string' ? run.id : '';
      const identity = node('div'), result = canon(run), state = ['completed','failed','cancelled','blocked','queued','running','preparing'].includes(run.state) ? run.state : 'unknown';
      const processCopy = {completed:'Completed',failed:'Failed · recorded evidence retained',cancelled:'Cancelled · recorded evidence retained',blocked:'Blocked',queued:'Queued',running:'Running',preparing:'Preparing',unknown:'Process status not recorded'}[state];
      const process = node('span','showcase-process',processCopy); process.dataset.state = state;
      identity.append(node('h3','showcase-model-name',run.model || 'Model not recorded'),process);
      if (result.status === 'partial') identity.append(node('span','showcase-process','Partial canonical evidence'));
      const scores = node('div','showcase-score-pair'); scores.setAttribute('aria-label',`Seed ${number(result.seed_score)}; best ${number(result.best_score)}`);
      scores.append(node('span','',number(result.seed_score)),node('i','','→'),node('strong','',number(result.best_score)));
      row.append(identity,scores); return row;
    }));
    const paired = selected.filter(run => finite(canon(run).seed_score) && finite(canon(run).best_score));
    const improved = paired.filter(run => c.direction === 'maximize' ? canon(run).best_score > canon(run).seed_score : canon(run).best_score < canon(run).seed_score);
    const tied = paired.filter(run => canon(run).best_score === canon(run).seed_score);
    $('showcase-seed-note').textContent = paired.length === selected.length && tied.length === selected.length
      ? `The best score matches the seed in all ${countText(selected.length,'run')}. No improvement over the starting score is measured.`
      : `${countText(improved.length,'run')} improved on the recorded seed; ${countText(tied.length,'run')} matched it.${paired.length < selected.length ? ` Seed comparisons are unavailable for ${countText(selected.length-paired.length,'run')}.` : ''}`;
    $('showcase-budget-value').textContent = budgetValue;
    $('showcase-budget-title').textContent = budgetLabel;
    $('showcase-budget-note').textContent = knownBudgets.length ? `Configured for ${knownBudgets.length} of ${selected.length} runs. This is the native search limit, not the number of LLM requests.` : 'A confirmed search budget is not recorded for this study.';
    $('showcase-token-context').textContent = completeUsage.length ? `${range(completeUsage.map(run => usage(run).total_tokens))} tokens per run · ${countText(completeUsage.length,'complete provider ledger')}.` : 'Complete provider-ledger token counts are not recorded for this study.';
    const maximum = Math.max(1,...selected.map(run => count(usage(run).total_tokens) ? usage(run).total_tokens : 0));
    $('showcase-tokens').replaceChildren(...selected.map(run => {
      const u = usage(run);
      if (!count(u.total_tokens)) return node('p','showcase-token-missing',`${run.model || 'Unknown model'} · tokens not recorded`);
      const entry = node('div','showcase-token'), heading = node('div','showcase-token-heading');
      entry.dataset.runId = typeof run.id === 'string' ? run.id : '';
      heading.append(node('span','',run.model || 'Model not recorded'),node('strong','',`${number(u.total_tokens)}${u.complete === true ? '' : ' · partial'}`));
      const track = node('div','showcase-token-track'), fill = node('div',`showcase-token-fill${u.complete === true ? '' : ' is-partial'}`);
      track.setAttribute('aria-hidden','true'); fill.style.width = `${u.total_tokens / maximum * 100}%`; track.append(fill); entry.append(heading,track); return entry;
    }));
    const methodology = [
      ['Study scope.',`${c.task_name || c.task_id}; metric ${c.metric}, ${c.direction === 'maximize' ? 'higher' : 'lower'} is better. Grouped by task, evaluator and source identity. This view contains ${countText(selected.length,'recorded run')}; it does not combine unrelated task scores.`],
      ['Program validity.',`${countText(valid,'valid evaluation')}, ${countText(invalid,'invalid evaluation')} and ${countText(unknown,'unclassified receipt')}. Repeated evaluations count separately here. Distinct programs are deduplicated by source hash, including a valid seed; validity alone does not establish an optimal solution.`],
      ['Starting point and resources.','Seed → best preserves the starting score. The native search budget is separate from request counts. Token counts describe the inspected provider ledger, not a billing record; partial coverage is labeled and excluded from the complete-ledger range.'],
      ['Process and evidence.',`${completed} of ${selected.length} processes completed. ${countText(partialEvidence,'run')} ${partialEvidence === 1 ? 'has' : 'have'} partial canonical evidence; validity percentages cover retained, classified receipts. Useful evidence from failed or cancelled runs stays visible. Canonical records are checked against their candidate and evaluation artifacts. Run details and individual evidence are available in the experiment board.`]
    ];
    if (records.length < selected.length) methodology.push(['Missing evidence.',`${countText(selected.length-records.length,'run')} in this study has no canonical receipts. Missing scores and token counts remain unknown.`]);
    $('showcase-methodology-body').replaceChildren(...methodology.map(([label,text]) => { const paragraph = node('p'); paragraph.append(node('strong','',`${label} `),doc.createTextNode(text)); return paragraph; }));
  }
  async function refresh() {
    if (!key || destroyed || pending) return;
    const current = ++epoch, controller = new win.AbortController();
    pending = {controller,current,timeout:null}; setAccess();
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
      payload = next; configureGroups(); render();
      const date = finite(next.generated_at) ? new Date(next.generated_at * 1000) : null;
      $('showcase-status').textContent = date && Number.isFinite(date.getTime()) ? `Recorded results · updated ${date.toLocaleTimeString('en',{hour:'2-digit',minute:'2-digit'})}` : 'Recorded results';
      $('showcase-key-error').textContent = '';
      if ($('showcase-key-dialog').open) $('showcase-key-dialog').close();
    } catch (error) {
      if (destroyed || current !== epoch || error?.name === 'AbortError') return;
      if (error?.name === 'TimeoutError') {
        $('showcase-status').textContent = 'The results request timed out. Refresh to try again.';
        $('showcase-key-error').textContent = 'The results request timed out. Please try again.';
        return;
      }
      $('showcase-status').textContent = 'Results are temporarily unavailable. Try refreshing.';
      $('showcase-key-error').textContent = 'Could not connect to results. Check the key and try again.';
    } finally { if (current === epoch) { win.clearTimeout(pending?.timeout); pending = null; setAccess(); } }
  }
  function showKey() { $('showcase-key').value = ''; $('showcase-key-dialog').showModal(); $('showcase-key').focus(); }
  function disconnect() {
    epoch++; stopPending(); key = '';
    try { storage.removeItem(STORAGE_KEY); } catch {}
    clear(); setAccess(); $('showcase-key').value = ''; $('showcase-key-error').textContent = '';
    $('showcase-status').textContent = 'Disconnected. Connect to explore recorded results.';
    $('showcase-empty-copy').textContent = 'Connect with your Arena key to see SCiEL’s recorded scores, valid programs and resource use.';
    if ($('showcase-key-dialog').open) $('showcase-key-dialog').close();
  }
  for (const id of ['showcase-connect','showcase-empty-connect']) on($(id),'click',showKey);
  on($('showcase-key-close'),'click',() => { $('showcase-key').value = ''; $('showcase-key-dialog').close(); });
  on($('showcase-key-dialog'),'cancel',() => { $('showcase-key').value = ''; });
  on($('showcase-disconnect'),'click',disconnect);
  on($('showcase-refresh'),'click',refresh);
  on($('showcase-cohort'),'change',render);
  on($('showcase-key-form'),'submit',event => {
    event.preventDefault(); const entered = $('showcase-key').value.trim(); if (!entered) return;
    epoch++; stopPending(); key = entered; clear();
    try { storage.setItem(STORAGE_KEY,key); } catch {}
    $('showcase-key').value = ''; refresh();
  });
  clear(); setAccess(); if (key) refresh();
  if (pollMs > 0) timer = win.setInterval(() => { if (!doc.hidden) refresh(); },pollMs);
  return {refresh,disconnect,destroy() { destroyed = true; epoch++; stopPending(); if (timer) win.clearInterval(timer); for (const remove of listeners) remove(); }};
}

if (typeof document !== 'undefined' && document.body?.dataset.resultsShowcase === 'true') initResultsShowcase();
