// A read-only projection of saved laboratory artifacts. No candidate code runs here.
import {renderMethodsProgress} from './methods_progress.js';
import {renderMethodsPopulation, renderMethodsArchitecture} from './methods_atlas.js';
import {renderWorkFlow, destroyWorkFlow} from './workflow.js';
const views = new WeakMap();
const number = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value)) ? Number(value) : null;
const text = value => value == null ? '—' : typeof value === 'object' ? JSON.stringify(value) : String(value);
const short = value => String(value || '').slice(0, 12) || '—';
const score = value => number(value) === null ? '—' : Number(value).toFixed(6);
const dollars = value => number(value) === null ? '—' : '$' + Number(value).toFixed(4);
const duration = value => { const n = number(value); if (n === null) return '—'; const s = Math.max(0, Math.floor(n)); return [Math.floor(s / 3600), Math.floor(s % 3600 / 60), s % 60].map(v => String(v).padStart(2, '0')).join(':'); };
const signed = value => number(value) === null ? '—' : (Number(value) > 0 ? '+' : '') + score(value);
const modeNames = {A: 'Fixed toolbox', B: 'Create & repair', C: 'Create & transfer'};
const stageNames = {initial:'Ready',continued:'Step recorded',generation:'Generating proposal',generating:'Generating proposal',capacity_wait:'Waiting for a shared slot',execution:'Running trial',evaluation:'Running trial',evaluating:'Running trial',replay:'Independent replay',adoption:'Adopting a tool',refused:'Proposal refused',trial:'Trial budget active',completed:'Completed',finished:'Finished',unknown:'Outcome unknown'};
const reusable = row => row.protocol?.permanent_toolbox_method !== false && row.record_kind !== 'solution_execution_bundle';
const allTools = view => [...(view.data.tools || []), ...(view.data.execution_bundles || [])];
const metricName = value => ({sum_radii:'Sum of radii',combined_score:'Combined evaluation score'}[value] || value || 'Task metric not recorded');
const modeNotes = {A: 'Common tools remain fixed.', B: 'Creates and revises its own tools.', C: 'Can trial and adopt independently replayed tools.'};
const capText = (mapping, key) => mapping && Object.hasOwn(mapping, key) ? mapping[key] === null ? 'Unlimited' : text(mapping[key]) : '—';
const labels = {dollars: 'LLM / USD', cpu_seconds: 'CPU / s', gpu_seconds: 'GPU / s', wall_seconds: 'Operation wall / s', storage_bytes: 'Storage / bytes', steps: 'Proposal steps'};
const positive = new Set(['ok', 'passed', 'released', 'adopted', 'active', 'completed', 'supported', 'benefit_observed', 'criterion met']);
const negative = new Set(['failed', 'rejected', 'quarantined', 'refuted', 'invalid', 'invalid_proposal_format', 'refused', 'proposal_refused', 'criterion missed']);
const tabDefinitions = [['architecture','Architecture'],['solutions','Programs'],['hypotheses','Hypotheses'],['lessons','Lessons'],['code','Code & diff'],['proposals','LLM calls'],['workflow','Work Flow'],['events','Events'],['population','Population'],['learning','Bandits & RL'],['tools','Tool library'],['experiments','Experiments'],['transfers','Adoptions']];
function observations(view) {return view.data.observability || {};}
function programCount(view) {return observations(view).programs?.accepted_programs ?? view.data.summary?.solutions ?? view.data.solutions?.length ?? 0;}
function questions(view) {
  const recorded = observations(view).hypotheses?.items;
  if (Array.isArray(recorded)) return recorded;
  const plans = new Map();
  for (const row of view.data.experiments || []) {
    if (!row.question) continue;
    const id = row.plan_id || row.id;
    if (!plans.has(id)) plans.set(id,{id,at:row.at,lab_id:row.lab_id,question:row.question,purpose:row.purpose,criterion:row.criterion,treatment:row.treatment,control:row.control,experiment_ids:[],status:'recorded with experiment'});
    plans.get(id).experiment_ids.push(row.id);
  }
  return [...plans.values()];
}
function tabCounts(view) {
  const stats = view.data.summary || {}, obs = observations(view);
  return {solutions:programCount(view),hypotheses:obs.hypotheses?.count ?? questions(view).length,lessons:obs.knowledge?.legacy_lessons?.count ?? null,proposals:stats.proposals ?? view.data.proposals?.length ?? 0,tools:stats.methods ?? view.data.tools?.length ?? 0,experiments:stats.experiments ?? view.data.experiments?.length ?? 0,transfers:stats.adoptions ?? view.data.transfers?.length ?? 0};
}
function taskMetric(view) {
  const quality = view.data.quality || {};
  if (quality.best_native_metric) return quality.best_native_metric;
  if (view.data.identity?.task?.task === 'oe/circle_packing' || String(view.snapshot.run.task || '').includes('circle26')) return 'sum_radii';
  return quality.metric || view.data.identity?.task?.metric || null;
}
function programState(view) {
  const obs = observations(view).programs;
  if (!obs) return {title:'No evaluated Program record',note:'This snapshot has no admitted Program with a bound evaluation. The solution submission history is unavailable.'};
  if (obs.status === 'no_recorded_solution_actions' && Number(obs.unclassified_proposals || 0) === 0) return {title:'No solution proposal has been submitted',note:obs.reason || 'Recorded actions have not requested standalone program evaluation. Tool-state experiments are tracked separately.'};
  if (obs.status === 'proposal_not_dispatched') return {title:'Proposal request was not sent',note:obs.reason || 'Admission refused the request before any model response.'};
  if (obs.status === 'history_incomplete') return {title:'Program history is incomplete',note:obs.reason || 'Available records cannot establish all solution requests or evaluation outcomes.'};
  if (obs.status === 'submission_unavailable' || Number(obs.unclassified_proposals || 0) > 0 && Number(obs.submitted_solution_actions || 0) === 0) return {title:'No validated solution proposal recorded',note:obs.reason || 'Some model replies could not be classified. Their intended action is unknown; this does not establish that no solution was requested.'};
  return {title:'Solution requested; no accepted Program yet',note:obs.reason || 'Inspect the recorded solution requests and trial outcomes below. An invoked trial can fail before returning an evaluated Program.'};
}
function el(tag, className, value) { const node = document.createElement(tag); if (className) node.className = className; if (value !== undefined) node.textContent = text(value); return node; }
function append(parent, ...children) { for (const child of children.flat()) if (child) parent.append(child); return parent; }
function button(label, action, className = 'methods-link') { const node = el('button', className, label); node.type = 'button'; node.addEventListener('click', action); return node; }
function tag(value) { const raw = value == null ? 'not recorded' : String(value); return el('span', 'methods-status ' + (positive.has(raw.toLowerCase()) ? 'is-positive' : negative.has(raw.toLowerCase()) ? 'is-negative' : ''), raw.replaceAll('_', ' ')); }
function experimentMetric(row) { return 'display_metric' in row ? row.display_metric : row.native_metric || row.metric; }
function experimentValue(row, arm) { const key = 'display_' + arm + '_score'; return key in row ? row[key] : row.native_metric ? row['native_' + arm + '_score'] : row[arm + '_score']; }
function experimentStatus(row) {
  const effect = number(row.effect);
  if (effect === null) return tag(row.passed === false || negative.has(row.status) ? 'failed' : 'unknown');
  if (effect === 0) return tag('No measured gain');
  if (row.passed === true) return tag('Criterion met');
  if (row.passed === false) return tag('Criterion missed');
  return tag('unknown');
}
function empty(title, note) { return append(el('div', 'methods-empty'), el('strong', '', title), el('p', '', note)); }
function fact(label, value, note) { return append(el('div', 'methods-fact'), el('span', '', label), el('strong', '', value), note ? el('small', '', note) : null); }
function detail(label, value) { return append(el('div', 'methods-detail-row'), el('dt', '', label), el('dd', '', value)); }
function jsonPanel(label, data, open = false) { const node = el('details', 'methods-json'); node.open = open; return append(node, el('summary', '', label), el('pre', '', typeof data === 'string' ? data : JSON.stringify(data ?? null, null, 2))); }
function itemId(row) { return row.id || row.method_id || row.proposal_id; }
function name(view, id) { return allTools(view).find(row => row.id === id)?.name || short(id); }
function timestamp(value) { if (!value) return 'Not recorded'; const date = new Date(value); return Number.isNaN(date.valueOf()) ? text(value) : date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit', second: '2-digit'}); }
function table(headers, rows) { const node = el('table', 'methods-table'); const head = el('tr'); headers.forEach(header => head.append(el('th', '', header))); const body = el('tbody'); for (const row of rows) { const tr = el('tr'); for (const cell of row) tr.append(append(el('td'), typeof cell === 'object' && cell?.nodeType ? cell : el('span', '', cell))); body.append(tr); } return append(el('div', 'methods-table-scroll'), append(node, append(el('thead'), head), body)); }
function selectedRows(view, key) { const rows = key === 'tools' ? (view.data.tools || []).filter(reusable) : key === 'code' ? [...new Map(allTools(view).map(row=>[row.id,row])).values()] : key === 'hypotheses' ? questions(view) : view.data[key] || []; const lab = view.data.labs?.find(row => row.id === view.lab); return view.lab === 'all' ? rows : rows.filter(row => (row.lab_id || row.author_lab || row.data?.lab_id) === view.lab || row.adopted_by?.includes(view.lab) || (['tools','code'].includes(key) && [...(lab?.active_methods || []), ...(lab?.active_adapters || [])].includes(row.id)) || (key === 'claims' && (row.methods || []).some(id => [...(lab?.active_methods || []),...(lab?.active_adapters || [])].includes(id) || allTools(view).some(tool=>tool.id===id&&tool.author_lab===view.lab)))); }
function selectedRecord(view) { const chosen = view.selection; if (!chosen) return null; const key = {lab:'labs',tool:'tools',experiment:'experiments',proposal:'proposals',transfer:'transfers',event:'events',solution:'solutions',claim:'claims'}[chosen.kind]; return (chosen.kind === 'tool' ? allTools(view) : chosen.kind === 'question' ? questions(view) : view.data[key])?.find(row => (chosen.kind === 'event' ? String(row.seq ?? row.id) : itemId(row)) === chosen.id); }
function inspectorSignature(view) { return JSON.stringify([view.selection, selectedRecord(view)]); }
function choose(view, kind, id) { view.selection = {kind, id}; renderTable(view); renderInspector(view); }
function reference(view, id) { const node = button(name(view, id), () => choose(view, 'tool', id)); node.title = id; return node; }
function links(view, values) { const node = el('div', 'methods-reference-list'); (values || []).forEach(id => node.append(reference(view, id))); if (!node.children.length) node.textContent = '—'; return node; }
function shell(root, view) {
  root.replaceChildren();
  const policy = el('section', 'methods-run-policy'); policy.setAttribute('aria-label', 'Run policy');
  const summary = el('section', 'methods-summary'); summary.setAttribute('aria-label', 'Research campaign summary');
  const progress = el('section', 'methods-search-progress'); progress.setAttribute('aria-label', 'Search progress');
  const budget = el('details', 'methods-budget'); append(budget, el('summary', '', 'Resource ledger'), el('div', 'methods-budget-body'));
  const overhead = el('section', 'methods-overhead panel'); overhead.setAttribute('aria-label', 'Observed service overhead');
  const labs = el('section', 'methods-labs panel'); labs.setAttribute('aria-label', 'Research laboratories');
  const split = el('div', 'methods-workbench');
  const workspace = el('section', 'methods-records panel');
  const tabs = el('div', 'methods-tabs'); tabs.setAttribute('role', 'tablist'); tabs.setAttribute('aria-label', 'Research records');
  for (const [id, label] of tabDefinitions) {
    const control = button('', () => { view.tab = id; renderTable(view); }, 'methods-tab'); control.dataset.methodsTab = id; control.dataset.label = label; control.id = 'methods-tab-' + id; control.setAttribute('role', 'tab'); control.setAttribute('aria-controls', 'methods-record-content'); append(control,el('span','methods-tab-label',label),el('span','methods-tab-count')); tabs.append(control);
  }
  tabs.addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    const items = [...tabs.querySelectorAll('button')], index = items.indexOf(document.activeElement); if (index < 0) return;
    event.preventDefault(); const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + items.length) % items.length; items[next].click(); items[next].focus();
  });
  const content = el('div', 'methods-record-content'); content.id = 'methods-record-content'; content.setAttribute('role', 'tabpanel');
  const inspector = el('aside', 'methods-inspector panel'); inspector.setAttribute('aria-label', 'Saved artifact inspector');
  const population = el('div', 'methods-population-view'), architecture = el('div', 'methods-architecture-view'), workflow = el('div', 'methods-workflow-view');
  const workflowScope=el('p','methods-table-caption','All laboratories · Work Flow includes the complete run. Laboratory filters apply to the other views.');
  append(workspace, tabs, content); append(split, workspace, inspector); append(root, policy, summary, progress, labs, split, budget, overhead);
  Object.assign(view, {policy, summary, progress, budget, overhead, labs, tabs, content, inspector, population, architecture, workflow, workflowScope, split});
}
function budgetTable(budget, fallbackLimits = {}) {
  const limits = budget.limits || fallbackLimits;
  const rows = Object.entries(labels).map(([key, label]) => [label, text(budget.spent?.[key]), text(budget.reserved?.[key]), capText(budget.remaining, key), capText(limits, key)]);
  return table(['Resource', 'Spent', 'Reserved', 'Remaining', 'Ceiling'], rows);
}
function labBudget(budget) { return append(el('details', 'methods-json'), el('summary', '', 'Lab resource ledger'), budgetTable(budget)); }
function renderPolicy(view) {
  const policy = view.data.run_policy || {}, classification = policy.classification || view.snapshot.run.classification;
  view.policy.hidden = classification !== 'continuous_run';
  if (view.policy.hidden) return;
  const limits = view.data.budget?.limits || {};
  const unlimited = Object.keys(labels).every(key => Object.hasOwn(limits, key) && limits[key] === null);
  const status = view.snapshot.run.status, reason = view.snapshot.run.status_reason;
  const stopped = ['completed', 'stopped', 'failed', 'interrupted'].includes(status);
  view.policy.replaceChildren(tag('Continuous run'), el('span', '', unlimited ? 'No total resource ceiling' : 'Resource ceilings follow the ledger'), el('span', 'methods-muted', 'Per-call execution limits remain in force'));
  if (reason && stopped) view.policy.append(el('span', 'methods-stop-reason', 'Stopped: ' + reason));
}

function renderSummary(view) {
  const stats = view.data.summary || {}, quality = view.data.quality || {}, budget = view.data.budget || {}, spent = budget.spent || {}, reserved = budget.reserved || {};
  const obs = observations(view), knowledge = obs.knowledge || {}, metric = taskMetric(view);
  const value = quality.best_native_metric ? quality.best_native_score : metric === 'sum_radii' ? null : quality.best_score;
  const elapsed = fact('Session time', duration(view.snapshot.timing?.session?.elapsed_seconds ?? view.data.elapsed_seconds ?? view.snapshot.runtime?.elapsed_seconds), view.snapshot.runtime?.active === true ? 'Live · heartbeat bounded' : 'Recorded time');
  elapsed.querySelector('strong').dataset.methodsElapsed = '';
  view.summary.replaceChildren(
    elapsed,
    fact(metric ? metricName(metric) : 'Task value', score(value), quality.best_solution_id ? 'Best evaluated Program' : 'No evaluated Program yet'),
    fact('Programs evaluated', programCount(view), 'Admitted Program + evaluation records'),
    fact('Stored active knowledge', text(knowledge.stored_records) + ' / ' + text(knowledge.active_referenced_records), 'Stored evidence / active revision references'),
    fact('Research labs', stats.labs ?? view.data.labs?.length ?? 0, 'Independent histories'),
    fact('Reusable tool versions', (view.data.tools || []).some(row => !reusable(row)) ? (view.data.tools || []).filter(reusable).length : stats.methods ?? view.data.tools?.length ?? 0, (stats.released ?? 0) + ' released'),
    fact('Experiments', stats.experiments ?? view.data.experiments?.length ?? 0, (stats.invocations ?? 0) + ' actual invocations'),
    fact('Recorded spend', dollars(spent.dollars), (number(reserved.dollars) > 0 ? dollars(reserved.dollars) + ' reserved' : 'No monetary reserve'))
  );
  [...view.summary.children].forEach((node,index)=>node.classList.add(index<4?'methods-primary-fact':'methods-secondary-fact'));
  const body = view.budget.querySelector('.methods-budget-body'); body.replaceChildren();
  append(body, budgetTable(budget, view.data.limits));
  if (view.data.run_policy?.classification === 'continuous_run') {
    const policy = view.data.run_policy;
    append(body, el('p', 'methods-footnote', 'Run limits · steps: ' + capText(policy, 'max_steps') + ' · elapsed seconds: ' + capText(policy, 'calendar_seconds') + ' · storage bytes: ' + capText(policy, 'storage_bytes') + ' · queue wait seconds: ' + capText(policy, 'capacity_wait_seconds')));
  }
  const unknown = stats.unknown ?? budget.unknown_count ?? 0;
  append(body, el('p', 'methods-footnote', 'Reserved resources include unfinished calls. Unknown outcomes retain their reservation.' + (unknown ? ' ' + unknown + ' unknown outcome(s).' : '')));
  const accounting = view.data.accounting || budget.accounting;
  if (accounting) append(body, jsonPanel('Measurement coverage', accounting));
  if (quality.scope) append(body, el('p', 'methods-footnote', 'Solution quality scope: ' + text(quality.scope)));
  if (budget.measurement_scope) append(body, el('p', 'methods-footnote', budget.measurement_scope));
  for (const warning of view.snapshot.warnings || []) append(body, el('p', 'methods-footnote', typeof warning === 'string' ? warning : warning.message || JSON.stringify(warning)));
  view.budget.querySelector('summary').textContent = 'Resource ledger · ' + dollars(spent.dollars) + ' recorded' + (unknown ? ' · ' + unknown + ' unknown' : '');
}
function renderOverhead(view) {
  const overhead = view.snapshot.runtime?.overhead;
  view.overhead.hidden = !overhead;
  if (!overhead) return;
  const seconds = value => number(value) === null ? '—' : Number(value).toFixed(2) + ' s';
  const bytes = value => number(value) === null ? '—' : Number(value) >= 1048576 ? (Number(value) / 1048576).toFixed(2) + ' MiB' : (Number(value) / 1024).toFixed(1) + ' KiB';
  const previousOpen = view.overhead.querySelector('details')?.open;
  view.overhead.replaceChildren(append(el('div', 'methods-overhead-heading'), el('h2', '', 'Observed overhead'), el('span', '', overhead.budget_enforced === false ? 'Observation · outside budget enforcement' : 'Resource observation')),
    append(el('div', 'methods-overhead-metrics'), fact('Controller CPU', seconds(overhead.controller_cpu_seconds)), fact('Container CPU', seconds(overhead.container_cpu_seconds), overhead.container_cpu_complete === false ? 'Partial coverage' : 'Observed containers'), fact('Unmetered controller CPU', seconds(overhead.unmetered_controller_cpu_seconds_estimate), overhead.unmetered_controller_cpu_seconds_estimate == null ? 'Resolved at the terminal boundary' : 'Estimate after ledger subtraction'), fact('Output growth', bytes(overhead.output_logical_bytes_delta ?? overhead.output_logical_bytes?.delta ?? overhead.output_bytes_delta), 'Logical bytes since observer start')),
    el('p', 'methods-footnote', 'These observations overlap the ledger and must not be added to its CPU totals. Docker host / VM overhead is not attributed to this run.'));
  const details = jsonPanel('Measurement coverage & exclusions', overhead, previousOpen); view.overhead.append(details);
}

function renderLabs(view) {
  const latestByLab = new Map((view.data.proposals || []).map(row => [row.lab_id, row]));
  const version = JSON.stringify([view.lab, view.data.labs, [...latestByLab.values()].map(row => [row.id, row.status])]); if (view.labsVersion === version) return; view.labsVersion = version;
  const header = append(el('div', 'methods-section-heading'), append(el('div'), el('h2', '', 'Research labs'), el('p', '', 'Follow a lab from proposal to a tool that changes its next experiment.')),
    button('All labs', () => {view.lab = 'all'; renderLabs(view); renderTable(view);}, 'methods-filter' + (view.lab === 'all' ? ' selected' : '')));
  view.labs.replaceChildren(header);
  const rows = el('div', 'methods-lab-list');
  for (const lab of view.data.labs || []) {
    const row = button('', () => {view.lab = lab.id; renderLabs(view); renderTable(view); choose(view, 'lab', lab.id);}, 'methods-lab' + (view.lab === lab.id ? ' selected' : ''));
    row.setAttribute('aria-pressed', String(view.lab === lab.id)); row.dataset.labId = lab.id;
    append(row, el('span', 'methods-lab-mode', lab.mode || '·'));
    append(row, append(el('span', 'methods-lab-identity'), el('strong', '', lab.id), el('small', '', modeNames[lab.mode] || lab.mode || 'Research lab')));
    append(row, append(el('span', 'methods-lab-agenda'), el('span', '', lab.agenda || modeNotes[lab.mode] || 'Agenda not recorded'), el('small', '', modeNotes[lab.mode] || '')));
    const latestProposal = latestByLab.get(lab.id);
    const recordedFailure = negative.has(latestProposal?.status) ? ({invalid:'invalid format', invalid_proposal_format:'invalid format', refused:'refused', proposal_refused:'refused'}[latestProposal.status] || latestProposal.status) : null;
    const stage = el('span', 'methods-lab-stage'); append(stage, tag(lab.revision_available === false ? 'Revision unavailable' : stageNames[lab.current_stage || lab.status] || lab.current_stage || lab.status), recordedFailure ? el('small', 'methods-last-proposal-error', 'Last proposal: ' + recordedFailure) : null, el('small', '', lab.last_activity_at ? timestamp(lab.last_activity_at) : 'No activity time'));
    append(row, stage, append(el('span', 'methods-lab-count'), el('strong', '', lab.steps ?? 0), el('small', '', 'steps')), append(el('span', 'methods-lab-count'), el('strong', '', lab.revision_available === false ? 'Unknown' : (lab.active_methods?.length ?? 0) + (lab.active_adapters?.length ?? 0)), el('small', '', 'active tools')), append(el('span', 'methods-lab-revision'), el('strong', '', 'r' + (lab.revision_number ?? '—')), el('small', '', short(lab.revision_id))));
    rows.append(row);
  }
  if (!rows.children.length) rows.append(empty('Laboratories are initializing', 'Their immutable revisions appear as soon as they are recorded.'));
  view.labs.append(rows);
}
function visualLive(view) {
  const runtime = view.snapshot.runtime || {}, maxAge = number(runtime.stale_after_seconds);
  const age = (number(runtime.heartbeat_age_seconds) ?? 0) + Math.max(0, (performance.now() - view.receivedAt) / 1000);
  return runtime.active === true && runtime.stale !== true && view.follow && view.connected && (maxAge === null || age < maxAge);
}
function experimentLinks(view, values) {
  const node = el('div','methods-reference-list');
  for (const id of values || []) node.append(button(short(id),()=>choose(view,'experiment',id)));
  if (!node.children.length) node.textContent = '—';
  return node;
}
function renderProgramEmpty(view) {
  if (view.lab !== 'all' && programCount(view) > 0) {view.content.append(empty('No evaluated Programs for this lab','Choose All labs to inspect the admitted Program records.'));return;}
  const state = programState(view), obs = observations(view).programs;
  view.content.append(empty(state.title,state.note));
  if (obs) {
    const rows = [['Parsed solution actions',obs.submitted_solution_actions],['Solution trials invoked',obs.invoked_solution_experiments],['Refused solution actions',obs.refused_solution_actions],['Failed solution experiments',obs.failed_solution_experiments],['Invalid solution experiments',obs.invalid_solution_experiments],['Nonaccepted evaluations',obs.nonaccepted_solution_evaluations],['Requests not dispatched',obs.not_dispatched_proposals],['Unclassified model replies',obs.unclassified_proposals]];
    view.content.append(table(['Recorded request / outcome','Count'],rows.map(([label,value])=>[label,text(value)])));
  }
}
function renderKnowledge(view) {
  const knowledge = observations(view).knowledge || {}, lessons = knowledge.legacy_lessons || {}, claims = selectedRows(view,'claims');
  view.content.append(empty(lessons.status === 'not_implemented' ? 'Lesson cards are not produced by this runner' : 'Lesson-card status not recorded',lessons.reason || 'This snapshot does not include a legacy Lesson-card inventory. Research evidence below is a separate record type.'));
  const summary = el('div','methods-knowledge-summary');
  append(summary,fact('Stored evidence',text(knowledge.stored_records)),fact('Active references',text(knowledge.active_referenced_records)),fact('Stored claim revisions',knowledge.stored_claims ?? view.data.summary?.claims ?? view.data.claims?.length ?? 0),fact('Delivered to prompts',text(knowledge.prompt_delivery?.count)));
  append(view.content,summary,el('p','methods-table-caption',knowledge.prompt_delivery?.reason || 'Active evidence references do not establish delivery to a model prompt.'),el('h3','methods-inline-heading','Research evidence · scoped claim revisions'));
  if (claims.length) view.content.append(table(['Claim / scope','Evidence level','Support / contrary / inconclusive','Tools'],[...claims].reverse().map(row=>[
    append(el('div'),button(short(row.id),()=>choose(view,'claim',row.id)),el('small','methods-row-note',row.scope || 'Scope not recorded')),
    text(row.evidence_level).replaceAll('_',' '),[(row.supporting||[]).length,(row.contradicting||[]).length,(row.inconclusive||[]).length].join(' / '),links(view,row.methods)
  ])));
  else view.content.append(empty('No claim revisions in this view','Claims link recorded experimental evidence. They are separate from Lesson cards and causal proof.'));
  if (Object.keys(knowledge).length) {const coverage = jsonPanel('Knowledge inventory & coverage',knowledge);coverage.classList.add('methods-coverage-panel');view.content.append(coverage);}
}
function renderLearning(view) {
  const features = observations(view).features || [], controllers = features.filter(row=>row.id==='rl'||row.id==='bandits');
  const inactive = controllers.length === 2 && controllers.every(row=>row.enabled===false);
  view.content.append(empty(inactive?'Bandits and RL are not enabled':'Controller telemetry',inactive?'This run uses the laboratory coordinator. It does not record learned action probabilities, rewards or RL policy updates.':'Only recorded controller configuration is shown. No policy or reward curve is inferred from task scores.'));
  if (features.length) view.content.append(table(['Component','Configured state','What this run records'],features.map(row=>[row.label || row.id,tag(row.enabled===true?'Enabled':row.enabled===false?'Not enabled':'Not recorded'),el('span','methods-feature-reason',row.reason || row.status)])));
  else view.content.append(el('p','methods-table-caption','Controller feature declarations are not available in this snapshot.'));
}
function renderTable(view) {
  const workflow = view.tab === 'workflow';
  if(!workflow && view.workflowActive){destroyWorkFlow(view.workflow);view.workflowActive=false;}
  view.split.classList.toggle('is-workflow',workflow);
  view.inspector.hidden=workflow;
  const visual = view.tab === 'population' || view.tab === 'architecture';
  const version = JSON.stringify([view.lab, view.tab, view.data[view.tab], allTools(view), view.data.summary, view.data.observability,view.tab==='lessons'?view.data.claims:null, visual ? [view.data.labs, view.data.identity, view.data.transfers, view.data.solutions, view.data.storage, visualLive(view)] : view.data.labs?.map(row => [row.id, row.active_methods, row.active_adapters])]); if (!workflow && view.tableVersion === version) return; view.tableVersion = version;
  const counts = tabCounts(view);
  for (const control of view.tabs.querySelectorAll('button')) { const id = control.dataset.methodsTab, active = id === view.tab; control.classList.toggle('active', active); control.setAttribute('aria-selected', String(active)); control.tabIndex = active ? 0 : -1; control.querySelector('.methods-tab-count').textContent = Object.hasOwn(counts,id)?' ('+text(counts[id])+')':''; }
  view.content.setAttribute('aria-labelledby', 'methods-tab-' + view.tab);
  if(workflow){
    if(view.workflow.parentNode!==view.content)view.content.replaceChildren(view.workflowScope,view.workflow);
    view.workflowActive=true;
    renderWorkFlow(view.workflow,{runId:view.runId,identity:JSON.stringify([view.snapshot.run.id,view.snapshot.run.run_id,view.snapshot.run.task_hash,view.data.identity]),version:view.snapshot.content_version ?? version,fetchJSON:view.fetchJSON,follow:view.follow,connected:view.connected,live:view.snapshot.runtime?.active===true});
    return;
  }
  if (visual) {
    const node = view[view.tab];
    if (node.parentNode !== view.content) view.content.replaceChildren(node);
    const render = view.tab === 'population' ? renderMethodsPopulation : renderMethodsArchitecture;
    view.architectureLive = visualLive(view);
    render(node, view.data, {onSelect: (kind, id) => choose(view, kind, id), live: view.architectureLive});
    return;
  }
  const captions = {tools:'Versions are immutable. Only recorded invocations count.',solutions:'Programs · admitted standalone Program records with bound evaluations. Tool-state trials are separate.',hypotheses:observations(view).hypotheses?'Experiment questions · precommitted plans and criteria, including plans without results. These are not legacy H cards.':'Experiment questions saved with trial records. The complete precommitted plan inventory is unavailable.',lessons:'Lessons and research evidence have distinct record types.',code:'Code & diff · select a saved source version to inspect its files and exact parent diff.',experiments:'Paired treatment and control. Zero effect is retained.',proposals:'LLM calls · open the exact saved request, response and dispatch receipt.',transfers:'Adoption and subsequent use are separate recorded events.',events:'Latest recorded journal events.',learning:'Host controller configuration for this laboratory runner.'};
  const filter = el('div', 'methods-table-caption', (view.lab === 'all'||view.tab==='learning' ? 'All laboratories' : view.lab) + ' · ' + captions[view.tab]);
  view.content.replaceChildren(filter);
  if (view.tab === 'lessons') {renderKnowledge(view);return;}
  if (view.tab === 'learning') {renderLearning(view);return;}
  let rows = selectedRows(view, view.tab);
  if (view.tab !== 'tools' && view.tab !== 'code') rows = [...rows].reverse();
  if (!rows.length) {if(view.tab==='solutions'){renderProgramEmpty(view);return;}view.content.append(empty('No ' + ({tools:'tools',hypotheses:'experiment questions',code:'source versions',experiments:'experiments',proposals:'LLM calls',transfers:'adoptions',events:'events'}[view.tab]) + ' recorded', view.lab === 'all' ? 'The monitor updates as new artifacts are saved.' : 'Choose All labs to inspect the other laboratories.')); return;}
  let node;
  if (view.tab === 'tools') node = table(['Tool / version', 'Owner', 'State', 'Invoked', 'Parents'], rows.map(row => [append(el('div'), button(row.name || short(row.id), () => choose(view, 'tool', row.id)), el('small', 'methods-hash', short(row.id) + ' · ' + (row.kind || 'method'))), row.provenance === 'common_toolbox' ? 'Common toolbox' : row.author_lab || 'Common', append(el('div'), tag(row.status), row.replayed ? el('small', 'methods-hash', 'Independently replayed') : null), row.invocations ?? 0, links(view, row.parents)]));
  else if (view.tab === 'solutions') node = table(['Program', 'Lab', 'Task value', 'Evaluation'], rows.map(row => [append(el('div'), button(short(row.program_id || row.id), () => choose(view, 'solution', row.id)), el('small', 'methods-hash', timestamp(row.at))), row.lab_id, append(el('div'), el('span', 'mono', score(row.native_metric ? row.native_score : row.score)), el('small', 'methods-hash', metricName(row.native_metric || 'combined_score'))), tag(row.valid === false ? 'invalid' : row.confirmed === true ? 'confirmed' : 'evaluated')]));
  else if (view.tab === 'hypotheses') node = table(['Experiment question / plan','Lab','Precommitted criterion','Result records'],rows.map(row=>[append(el('div'),button(short(row.id),()=>choose(view,'question',row.id)),el('small','methods-row-note methods-question-text',row.question || 'Question not recorded')),row.lab_id,append(el('div'),el('span','',row.criterion?.metric || 'Metric not recorded'),el('small','methods-hash',(row.criterion?.direction || '')+' · minimum effect '+text(row.criterion?.minimum_effect))),row.experiment_ids?.length?experimentLinks(view,row.experiment_ids):el('span','methods-muted','No result recorded')]));
  else if (view.tab === 'code') node = table(['Saved source / version','Role','Owner','Parent versions'],rows.map(row=>[append(el('div'),button(row.name || short(row.id),()=>choose(view,'tool',row.id)),el('small','methods-hash',short(row.id))),reusable(row)?'Reusable tool':'Program execution bundle',row.provenance==='common_toolbox'?'Common toolbox':row.author_lab || 'Not recorded',links(view,row.parents)]));
  else if (view.tab === 'experiments') node = table(['Experiment / question', 'Lab', 'Treatment', 'Effect / criterion', 'Result'], rows.map(row => [append(el('div'), button(short(row.id), () => choose(view, 'experiment', row.id)), el('small', 'methods-row-note', row.question || 'Question not recorded')), row.lab_id, append(el('div'), el('span', 'mono', score(experimentValue(row, 'treatment'))), el('small', 'methods-hash', experimentMetric(row) || 'Metric not recorded')), append(el('div'), el('span', 'mono', signed(row.effect)), el('small', 'methods-hash', row.metric || 'Metric not recorded')), experimentStatus(row)]));
  else if (view.tab === 'proposals') node = table(['Model call', 'Lab', 'Proposal', 'Result', 'Cost'], rows.map(row => [append(el('div'), button('#' + (row.index ?? '—') + ' · ' + short(row.id), () => choose(view, 'proposal', row.id)), el('small', 'methods-hash', timestamp(row.at))), row.lab_id, row.kind || '—', tag(row.status), dollars(row.cost?.dollars ?? row.cost)]));
  else if (view.tab === 'transfers') node = table(['Adoption', 'Recipient', 'New revision', 'Next actual use'], rows.map(row => [button(name(view, row.method_id || row.selected_methods?.[0]) || short(row.id), () => choose(view, 'transfer', itemId(row))), row.lab_id || row.recipient_lab, short(row.new_revision || row.revision_id), row.next_use_experiment_id ? button(short(row.next_use_experiment_id), () => choose(view, 'experiment', row.next_use_experiment_id)) : el('span', 'methods-muted', 'Not observed') ]));
  else node = table(['Time', 'Lab', 'Event', 'Record'], rows.map(row => [timestamp(row.at || row.timestamp), row.lab_id || row.data?.lab_id || '—', String(row.kind || row.event || '').replaceAll('_', ' '), button(short(row.id || row.data?.id || row.seq), () => choose(view, 'event', String(row.seq ?? row.id)))]));
  view.content.append(node);
  if (counts[view.tab] > rows.length && view.lab === 'all') view.content.append(el('p', 'methods-footnote', 'Showing ' + rows.length + ' recent records of ' + counts[view.tab] + '. The journal retains the full history.'));
}
function inspectorHeading(view, title, subtitle) {
  view.inspector.replaceChildren(append(el('div', 'methods-inspector-heading'), append(el('div'), el('span', 'methods-eyebrow', 'SAVED ARTIFACT'), el('h2', '', title), subtitle ? el('p', '', subtitle) : null), button('×', () => {view.selection = null; renderInspector(view);}, 'methods-inspector-close')));
  view.inspector.querySelector('.methods-inspector-close').setAttribute('aria-label', 'Close artifact inspector');
}
function inspectorDefault(view) {
  view.inspector.replaceChildren(append(el('div', 'methods-inspector-heading'), append(el('div'), el('span', 'methods-eyebrow', 'RESEARCH PROCESS'), el('h2', '', 'From an idea to actual use'))));
  const list = el('ol', 'methods-process');
  for (const [title, description] of [['Propose', 'The lab receives its revision, tools and prior evidence.'], ['Execute & repair', 'A bounded trial checks the exact saved source. Failures feed the next proposal.'], ['Independent replay', 'Another lab runs the assigned version independently.'], ['Adopt', 'A recipient trial can create a new immutable lab revision.'], ['Use again', 'Only a later recorded invocation demonstrates use after adoption.']]) list.append(append(el('li'), el('strong', '', title), el('span', '', description)));
  append(view.inspector, list, el('p', 'methods-footnote', 'Select a tool, experiment or model call to inspect its saved evidence. Release is not proof of benefit.'));
}
function renderInspector(view) {
  const selectionKey = JSON.stringify(view.selection), sameSelection = view.inspectorSelection === selectionKey;
  const savedScroll = view.inspector.scrollTop;
  view.inspectorSelection = selectionKey;
  view.inspectorVersion = inspectorSignature(view);
  view.request++;
  const chosen = view.selection;
  if (!chosen) {inspectorDefault(view); return;}
  const row = selectedRecord(view);
  if (!row) {inspectorHeading(view, 'Record outside this snapshot', short(chosen.id)); view.inspector.append(el('p', 'methods-footnote', 'The history is retained in the journal; this bounded view no longer includes this record.')); return;}
  inspectorHeading(view, chosen.kind === 'tool' ? row.name || 'Tool version' : chosen.kind === 'lab' ? row.id : ({solution:'Program', experiment:'Experiment', question:'Experiment question',claim:'Research claim',proposal:'LLM call',transfer:'Adoption',event:'Journal event'}[chosen.kind]), chosen.kind === 'lab' ? modeNames[row.mode] : chosen.id);
  if (chosen.kind === 'lab') {
    append(view.inspector, el('p', 'methods-inspector-copy', row.agenda), append(el('dl', 'methods-details'), detail('Revision', row.revision_id), detail('State', row.status), detail('Budget account', row.budget_account)), el('h3', 'methods-mini-heading', row.revision_available === false ? 'Current tools unknown' : 'Active tools'), row.revision_available === false ? el('p', '', 'The latest revision could not be verified. Last-known tools are historical only.') : links(view, [...(row.active_methods || []), ...(row.active_adapters || [])]), row.budget ? labBudget(row.budget) : null, jsonPanel('Revision & capabilities', row));
  } else if (chosen.kind === 'tool') {
    append(view.inspector, append(el('dl', 'methods-details'), detail('State', row.status), detail('Author', row.author_lab || 'Common toolbox'), detail('Role', reusable(row) ? 'Reusable method' : 'Solution execution bundle'), detail('Actual invocations', row.invocations ?? 0), detail('Adopted by', row.adopted_by?.join(', ') || 'No recorded adoption')), el('h3', 'methods-mini-heading', 'Parent versions'), links(view, row.parents), el('h3', 'methods-mini-heading', 'Dependencies'), links(view, row.dependencies), el('p', 'methods-footnote', 'A dependency does not receive invocation credit merely because it is included.'), jsonPanel('Scope & evidence', {scope: row.scope, replayed: row.replayed, evidence: row.evidence, evidence_refs: row.evidence_refs}));
    loadDetail(view, 'method', row.id);
  } else if (chosen.kind === 'proposal') {
    append(view.inspector, append(el('dl', 'methods-details'), detail('Lab', row.lab_id), detail('Proposal', row.kind), detail('Result', row.status), detail('Cost', dollars(row.cost?.dollars ?? row.cost))));
    if (row.diagnostic || row.error) append(view.inspector, jsonPanel('Proposal diagnostic', row.diagnostic || row.error, true));
    if (row.method_id) append(view.inspector, el('h3', 'methods-mini-heading', row.kind === 'Solution' || allTools(view).some(tool => tool.id === row.method_id && !reusable(tool)) ? 'Solution source bundle' : 'Produced tool'), reference(view, row.method_id));
    if (row.experiment_id) view.inspector.append(button('Open resulting experiment', () => choose(view, 'experiment', row.experiment_id)));
    loadDetail(view, 'proposal', row.id);
  } else if (chosen.kind === 'solution') {
    append(view.inspector, append(el('dl', 'methods-details'), detail('Lab', row.lab_id), detail('Program', row.program_id || row.id), detail('Task metric', metricName(row.native_metric || 'combined_score')), detail('Task value', score(row.native_metric ? row.native_score : row.score)), detail('Confirmed', row.confirmed === true ? 'Yes' : row.confirmed === false ? 'No' : 'Not recorded'), detail('Valid', row.valid === true ? 'Yes' : row.valid === false ? 'No' : 'Not recorded')),
      el('p', 'methods-footnote', 'This is an evaluated solution program. Its execution bundle is not a reusable library tool.'));
    if (row.experiment_id) view.inspector.append(button('Open evaluation experiment', () => choose(view, 'experiment', row.experiment_id)));
    append(view.inspector, jsonPanel('Bound evaluation & provenance', row));
    if (row.method_id) loadDetail(view, 'method', row.method_id);
  } else if (chosen.kind === 'question') {
    append(view.inspector,el('p','methods-inspector-copy',row.question || 'Question not recorded'),append(el('dl','methods-details'),detail('Record type','Precommitted experiment plan'),detail('Lab',row.lab_id),detail('Purpose',row.purpose),detail('Plan status',row.status)),el('p','methods-footnote','This is an experiment question and test criterion, not a legacy H card or an accepted causal claim.'),el('h3','methods-mini-heading','Treatment'),links(view,row.treatment),el('h3','methods-mini-heading','Control'),links(view,row.control),jsonPanel('Precommitted criterion',row.criterion,true),el('h3','methods-mini-heading','Recorded experiments'),experimentLinks(view,row.experiment_ids));
    if(row.proposal_id)view.inspector.append(button('Open originating LLM call',()=>choose(view,'proposal',row.proposal_id)));
    view.inspector.append(jsonPanel('Saved plan record',row));
  } else if (chosen.kind === 'claim') {
    append(view.inspector,el('p','methods-inspector-copy',row.scope || 'Scope not recorded'),append(el('dl','methods-details'),detail('Evidence level',row.evidence_level),detail('Uncertainty',row.uncertainty)),el('h3','methods-mini-heading','Supporting experiments'),experimentLinks(view,row.supporting),el('h3','methods-mini-heading','Contradicting experiments'),experimentLinks(view,row.contradicting),el('h3','methods-mini-heading','Inconclusive experiments'),experimentLinks(view,row.inconclusive),el('h3','methods-mini-heading','Methods'),links(view,row.methods),jsonPanel('Saved claim revision',row));
  } else if (chosen.kind === 'experiment') {
    append(view.inspector, el('p', 'methods-inspector-copy', row.question), append(el('dl', 'methods-details'), detail('Lab', row.lab_id), detail('Purpose', row.purpose), detail('Task metric', experimentMetric(row)), detail('Control score', score(experimentValue(row, 'control'))), detail('Treatment score', score(experimentValue(row, 'treatment'))), detail('Paired effect', signed(row.effect)), detail('Effect metric', row.metric), detail('Criterion passed', row.passed === true ? 'Yes' : row.passed === false ? 'No' : 'Unknown')), el('h3', 'methods-mini-heading', 'Treatment'), links(view, row.treatment), el('h3', 'methods-mini-heading', 'Control'), links(view, row.control), jsonPanel('Precommitted criterion', row.criterion), jsonPanel('Measurements & diagnostics', row.results ?? row), jsonPanel('Actual invocation receipts', row.invocation_refs));
    const claims = (view.data.claims || []).filter(claim => claim.experiment_id === row.id || [...(claim.supporting || []), ...(claim.contradicting || []), ...(claim.inconclusive || [])].includes(row.id));
    if (claims.length) view.inspector.append(jsonPanel('Research claims', claims));
  } else append(view.inspector, jsonPanel(chosen.kind === 'transfer' ? 'Adoption, revision & subsequent invocation' : 'Recorded event', row, true));
  if (sameSelection) view.inspector.scrollTop = savedScroll;
}
async function loadDetail(view, kind, id) {
  const identity = view.runId, key = kind + ':' + id;
  if (view.detail?.identity === identity && view.detail.key === key) {
    view.inspector.append(view.detail.holder);
    return;
  }
  const holder = el('div', 'methods-loaded-detail'); holder.textContent = 'Loading saved artifact…'; view.inspector.append(holder);
  const detail = {identity, key, holder}; view.detail = detail;
  try {
    let payload = view.cache.get(key);
    if (!payload) {payload = await view.fetchJSON('/api/runs/' + encodeURIComponent(identity) + '/' + kind + '/' + encodeURIComponent(id)); if (identity === view.runId) view.cache.set(key, payload);}
    if (view.detail !== detail || identity !== view.runId || !holder.isConnected) {
      if (view.detail === detail) view.detail = null;
      return;
    }
    holder.replaceChildren();
    if (kind === 'method') {
      const files = payload.files || payload.method?.files || {};
      if (payload.diff !== undefined) holder.append(jsonPanel('Diff from parent', payload.diff || 'No source difference recorded.', true));
      for (const [path, source] of Object.entries(files)) holder.append(jsonPanel('Source · ' + path, source, !payload.diff));
      if (!Object.keys(files).length) holder.append(el('p', 'methods-footnote', 'No saved source is available.'));
      holder.append(jsonPanel('Immutable manifest', payload.manifest || payload.method?.manifest || payload));
    } else {
      const requestBody = payload.request ?? payload.context ?? payload.proposal_intent;
      const response = payload.response ?? payload.response_record ?? payload.proposal;
      holder.append(jsonPanel('LLM request / saved context', requestBody, true), jsonPanel('LLM response', response, true), jsonPanel('Cost & dispatch receipt', payload.receipt ?? payload));
    }
  } catch (error) {
    if (view.detail === detail && identity === view.runId && holder.isConnected) holder.replaceChildren(el('p', 'methods-detail-error', error.message || 'Saved artifact unavailable.'), button('Retry', () => {holder.remove(); if (view.detail === detail) view.detail = null; loadDetail(view, kind, id);}));
    else if (view.detail === detail) view.detail = null;
  }
}

export function destroyMethodsDashboard(root) {
  const view=views.get(root);
  if(view?.workflowActive)destroyWorkFlow(view.workflow);
  if(view){view.request++;view.detail=null;}
  views.delete(root);
  root.replaceChildren();
}

export function renderMethodsDashboard(root, snapshot, options = {}) {
  let view = views.get(root);
  const identity=JSON.stringify([snapshot.run.id,snapshot.run.run_id,snapshot.run.task_hash,snapshot.methods?.identity]);
  if (!view || view.identity !== identity) {
    if(view)destroyMethodsDashboard(root);
    view = {runId: snapshot.run.id, identity, tab: 'population', lab: 'all', selection: null, cache: new Map(), request: 0}; views.set(root, view); shell(root, view);
  }
  Object.assign(view, {snapshot, data: snapshot.methods || {}, fetchJSON: options.fetchJSON || (async url => {const response = await fetch(url); if (!response.ok) throw new Error('Artifact unavailable (' + response.status + ').'); return response.json();}), follow: options.follow !== false, connected: options.connected !== false, receivedAt: performance.now(), advance: 0});
  const active = document.activeElement, focusTab = active?.dataset?.methodsTab, focusLab = active?.dataset?.labId;
  const inspectorVersion = inspectorSignature(view);
  renderPolicy(view); renderSummary(view); renderOverhead(view); renderLabs(view); renderTable(view);
  renderMethodsProgress(view.progress, view.data, {onSelect: (kind, id) => choose(view, kind, id)});
  if (view.inspectorVersion !== inspectorVersion) {renderInspector(view); view.inspectorVersion = inspectorVersion;}
  if (focusTab) root.querySelector('[data-methods-tab="' + focusTab + '"]')?.focus({preventScroll: true});
  if (focusLab) [...root.querySelectorAll('[data-lab-id]')].find(node => node.dataset.labId === focusLab)?.focus({preventScroll: true});
}

export function updateMethodsTiming(root, {follow = true, connected = true} = {}) {
  const view = views.get(root); if (!view) return;
  const runtime = view.snapshot.runtime || {}, timing = view.snapshot.timing;
  const base = number(timing?.session?.elapsed_seconds ?? view.data.elapsed_seconds ?? runtime.elapsed_seconds);
  const freshness = Math.max(0, (number(runtime.stale_after_seconds) ?? 0) - (number(runtime.heartbeat_age_seconds) ?? 0));
  if (runtime.active === true && follow && connected && timing?.live !== false) view.advance = Math.max(view.advance, Math.min(freshness, (performance.now() - view.receivedAt) / 1000));
  const node = root.querySelector('[data-methods-elapsed]'); if (node) node.textContent = duration(base === null ? null : base + view.advance);
  Object.assign(view, {follow, connected});
  if (view.tab === 'workflow' || view.tab === 'architecture' && view.architectureLive !== visualLive(view)) renderTable(view);
}
